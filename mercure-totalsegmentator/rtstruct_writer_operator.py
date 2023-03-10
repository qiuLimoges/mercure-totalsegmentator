import logging
import os
import shutil
import subprocess
from pathlib import Path

# generate DICOM RT struct file for segmentations
# code resused / adapted from TOTALSegmentator- AIDE, see https://github.com/GSTT-CSC/TotalSegmentator-AIDE
# Adapted to work with --ml 
import os.path
from os import listdir
from os.path import isfile, join

import nibabel as nib
import numpy as np
from rt_utils import RTStructBuilder

import monai.deploy.core as md
from monai.deploy.core import DataPath, ExecutionContext, InputContext, IOType, Operator, OutputContext
from totalsegmentator.map_to_binary import class_map


@md.input("input_files", DataPath, IOType.DISK)
@md.output("dicom_files", DataPath, IOType.DISK)
@md.env(pip_packages=["pydicom >= 2.3.0", "rt-utils >= 1.2.7"])
class RTStructWriterOperator(Operator):
    """
    RTStructWriterOperator - converts TotalSegmentator NIfTI segmentations to DICOM RT Struct format
    """

    def compute(self, op_input: InputContext, op_output: OutputContext, context: ExecutionContext):

        logging.info(f"Begin {self.compute.__name__}")
        input_path = op_input.get("input_files").path
        dcm_input_path = os.path.join(input_path,'dcm_input')
        nii_seg_output_path = input_path
        dcm_output_path = op_output.get().path
        rt_struct_output_filename = 'output-rt-struct_vols.dcm'
        
        # get roi names
        seg_class=class_map['total']


        logging.info(f"Creating RT Struct ...")

        # create new RT Struct - requires original DICOM
        rtstruct = RTStructBuilder.create_new(dicom_series_path=dcm_input_path)

        nii_seg_file = os.path.join(nii_seg_output_path,'nii_input','nii_seg_output.nii')

        nii = nib.load(nii_seg_file)
        spacing = nii.header.get_zooms()
        vox_vol = spacing[0] * spacing[1] * spacing[2]
        

        nii_img = nii.get_fdata().astype("uint16")  # match to DICOM datatype, convert to boolean
        # rotate nii to match DICOM orientation
        nii_img = np.rot90(nii_img, 1, (0, 1))  # rotate segmentation in-plane
        roi_num = np.max(nii_img)

        for roi in range(1,roi_num+1):
            volume_mm = np.sum((nii_img==roi), where=True)*vox_vol
            # add segmentation to RT Struct
            if (volume_mm>0):
                rtstruct.add_roi(
                    mask=(nii_img==roi),
                    name=seg_class[roi],
                    description=str(volume_mm)
                )

        rtstruct.save(os.path.join(dcm_output_path, rt_struct_output_filename))
        logging.info(f"RT Struct written to {os.path.join(dcm_output_path, rt_struct_output_filename)}")

        logging.info(f"RT Struct creation complete ...")


        logging.info(f"End {self.compute.__name__}")
