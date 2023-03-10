# operator to write DICOM SEG files
import logging
import os
import shutil
import subprocess
from pathlib import Path

import monai.deploy.core as md
from monai.deploy.core import DataPath, ExecutionContext, InputContext, IOType, Operator, OutputContext

import glob
import highdicom as hd
import numpy as np
import nibabel as nib
import pydicom
from pydicom.sr.codedict import codes
#from pydicom.filereader import dcmread
from totalsegmentator.map_to_binary import class_map


@md.input("input_files", DataPath, IOType.DISK)
@md.output("dicom_files", DataPath, IOType.DISK)

class SegDICOMWriterOperator(Operator):
    """
    SegDICOMWriterOperator - converts TotalSegmentator NIfTI segmentations to DICOM SEG files
    """

    def compute(self, op_input: InputContext, op_output: OutputContext, context: ExecutionContext):
        
        # Path to directory containing single-frame legacy CT Image instances
        dcm_output_path = op_output.get().path
        input_path = op_input.get("input_files").path
        series_dir = Path(os.path.join(input_path, 'dcm_input'))

        #image_files = series_dir.glob('*')
        image_files = sorted(series_dir.glob("*.dcm"), reverse=True)
        print(image_files,'got past glob')

        # Read CT Image data sets from PS3.10 files on disk
        image_datasets = [pydicom.dcmread(str(f)) for f in image_files]
        print('got past dcm_read')
        # Read CT Image data sets from PS3.10 files on disk
        seg_class=class_map['total']

        nii_seg_file = os.path.join(input_path,'nii_input','nii_seg_output.nii')

        nii = nib.load(nii_seg_file)
        spacing = nii.header.get_zooms()
        vox_vol = spacing[0] * spacing[1] * spacing[2]


        nii_img = nii.get_fdata().astype("uint16")  # match to DICOM datatype, convert to boolean
        # rotate nii to match DICOM orientation
        nii_img = np.rot90(nii_img, 1, (0, 1))  # rotate segmentation in-plane
        roi_num = np.max(nii_img)

        # Describe the algorithm that created the segmentation
        algorithm_identification = hd.AlgorithmIdentificationSequence(
            name='TotalSegmentator',
            version='v1.0',
            family=codes.DCM.ArtificialIntelligence
        )
        print('got to loop')
        for roi in range(1,roi_num+1):
            volume_mm = np.sum((nii_img==roi), where=True)*vox_vol
            # add segmentation to RT Struct
            if (volume_mm>0):
                mask=np.rollaxis(np.array(nii_img==roi),2)
                print(mask.shape)
                seg_name=seg_class[roi]
                code_name = seg_name.split('_')[0].capitalize()
                sct_name = [s for s in codes.SCT.trait_names() if s == code_name]
                if(sct_name):
                    sct_type = getattr(codes.SCT, sct_name[0])
                else:
                    sct_type = codes.SCT.Organ

                # Describe the segment
                description_segment_1 = hd.seg.SegmentDescription(
                    segment_number=1,
                    segment_label=seg_name,
                    segmented_property_category=codes.SCT.Organ,
                    segmented_property_type=sct_type,
                    algorithm_type=hd.seg.SegmentAlgorithmTypeValues.AUTOMATIC,
                    algorithm_identification=algorithm_identification,
                    tracking_uid=hd.UID(),
                    tracking_id='Total Segmentator ROIs'
                )

                # Create the Segmentation instance
                seg_dataset = hd.seg.Segmentation(
                    source_images=image_datasets,
                    pixel_array=mask,
                    segmentation_type=hd.seg.SegmentationTypeValues.BINARY,
                    segment_descriptions=[description_segment_1],
                    series_instance_uid=hd.UID(),
                    series_number=1000+roi,
                    sop_instance_uid=hd.UID(),
                    instance_number=1,
                    manufacturer='CBI',
                    manufacturer_model_name='Mercure',
                    software_versions='v1',
                    device_serial_number='Mercure',
                    series_description=seg_name,
                )
                
                #print(seg_dataset)
                seg_dataset.save_as(os.path.join(dcm_output_path, "seg_"+seg_name+".dcm"))
        
