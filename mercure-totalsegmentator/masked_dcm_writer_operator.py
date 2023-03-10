# operator to write RGB DICOM with segmentations overlaid as color masks
import logging
import os
import shutil
import subprocess
from pathlib import Path

import monai.deploy.core as md
from monai.deploy.core import DataPath, ExecutionContext, InputContext, IOType, Operator, OutputContext


from PIL import Image, ImageOps
import matplotlib as mpl
from matplotlib import cm
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
import nibabel as nib
import numpy as np
import pydicom
from pydicom.uid import generate_uid
import SimpleITK as sitk

import sys
import time

@md.input("input_files", DataPath, IOType.DISK)
@md.output("dicom_files", DataPath, IOType.DISK)

class MaskedDICOMWriterOperator(Operator):
    """
    MaskedDICOMWriterOperator - converts TotalSegmentator NIfTI segmentations to DICOM RGB mask images
    """

    def compute(self, op_input: InputContext, op_output: OutputContext, context: ExecutionContext):
        
        logging.info(f"Creating masked DICOMs ...")
        
        #generate segmentation mask colourmap
        new_prism= mpl.colormaps['prism']
        newcolors = new_prism(np.linspace(0, 1, 80))
        black = np.array([0, 0, 0, 1])
        newcolors[0, :] = black
        newcmp = ListedColormap(newcolors)
        cm.register_cmap('newcmp',newcmp)
        cm.get_cmap('newcmp')

        
        input_path = op_input.get("input_files").path
        
        dcm_output_path = op_output.get().path
        
        
        nii_seg_file = os.path.join(input_path,'nii_input','nii_seg_output.nii')
        nii = nib.load(nii_seg_file)
        nii_seg = nii.get_fdata().astype("uint16")  # match to DICOM datatype, convert to boolean
        # rotate nii to match DICOM orientation
        nii_seg = np.rot90(nii_seg, 1, (0, 1))  # rotate segmentation in-plane
        
        
        # Get the list of series IDs.
        series_reader = sitk.ImageSeriesReader()
        data_directory = os.path.join(input_path, 'dcm_input')
      
        series_ID = series_reader.GetGDCMSeriesIDs(data_directory)
        print(series_ID)
        if not series_ID:
            print("ERROR: given directory \""+data_directory+"\" does not contain a DICOM series.")


        series_file_names = series_reader.GetGDCMSeriesFileNames(data_directory, series_ID[0])
        series_reader.SetFileNames(series_file_names)

        series_reader.MetaDataDictionaryArrayUpdateOn()
        series_reader.LoadPrivateTagsOn()
        in_image = series_reader.Execute()


        tags_to_copy = [
                            "0010|0010",  # Patient Name
                            "0010|0020",  # Patient ID
                            "0010|0030",  # Patient Birth Date
                            "0020|000D",  # Study Instance UID, for machine consumption
                            "0020|0010",  # Study ID, for human consumption
                            "0008|0020",  # Study Date
                            "0008|0030",  # Study Time
                            "0008|0050",  # Accession Number
                            "0008|0060",  # Modality
                        ]

        modification_time = time.strftime("%H%M%S")
        modification_date = time.strftime("%Y%m%d")

        direction = in_image.GetDirection()
        series_tag_values = [
            (k, series_reader.GetMetaData(0, k))
            for k in tags_to_copy
            if series_reader.HasMetaDataKey(0, k)
            ] + [
            ("0008|0031", modification_time),  # Series Time
            ("0008|0021", modification_date),  # Series Date
            ("0008|0008", "DERIVED\\SECONDARY"),  # Image Type
            (
                "0020|000e",
                "1.2.826.0.1.3680043.2.1125."
                + modification_date
                + ".1"
                + modification_time,
            ),
            # Series Instance UID
            (
                "0020|0037",
                "\\".join(
                    map(
                        str,
                        (
                            direction[0],
                            direction[3],
                            direction[6],
                            # Image Orientation (Patient)
                            direction[1],
                            direction[4],
                            direction[7],
                        ),
                    )
                ),
            ),
            (
                "0008|103e",
                series_reader.GetMetaData(0, "0008|103e") + " Processed-SimpleITK",
            ),
            ]  # Series Description
        
        in_image = sitk.Cast(in_image, sitk.sitkFloat32)
        vol = sitk.GetArrayFromImage(in_image)
        
        writer = sitk.ImageFileWriter()
        writer.KeepOriginalImageUIDOn()

        modification_time = time.strftime("%H%M%S")
        modification_date = time.strftime("%Y%m%d")
        
        zdim = vol.shape[0]
        series_uid_out = generate_uid()
        SOP_Instance_UID = generate_uid()
        series_description = series_reader.GetMetaData(0,"0008|103e")

        for i in range(zdim):
            raw_img = vol[i,:,:]
            seg_img = nii_seg[:,:,i]

            
            # Normalize the background (input) image
            background = 255 * ( 1.0 / raw_img.max() * (raw_img - raw_img.min()) )
            background = background.astype(np.ubyte)
            background_image = Image.fromarray(background).convert("RGB")

            seg_array = seg_img
            mask_image = Image.fromarray(np.uint8(newcmp(seg_array)*255)).convert("RGB")
        

            # # Blend the two images
            final_image = Image.blend(mask_image, background_image, 0.75)
            final_array = np.array(final_image).astype(np.uint8) 
            out_image = sitk.GetImageFromArray(final_array,isVector=True)
            
             
            
            for tag, value in series_tag_values:
                out_image.SetMetaData(tag, value)
              
                
            
            out_image.SetMetaData("0008|0012", time.strftime("%Y%m%d")) #   Instance Creation Date               
            out_image.SetMetaData("0008|0013", time.strftime("%H%M%S")) #   Instance Creation Time              
            out_image.SetMetaData("0020|0032","\\".join(map(str, in_image.TransformIndexToPhysicalPoint((0, 0, i)))),) #   Image Position (Patient)          
            out_image.SetMetaData("0020|0013", str(i)) #   Instance Number              
            out_image.SetMetaData('0008|103e', "Segmentation_masks_(" + series_description + ")") # series description
            out_image.SetMetaData('0020|000e', SOP_Instance_UID) # SOP_Instance_UID
            out_image.SetMetaData('0020|000e', series_uid_out) # series instance UID
            out_image.SetMetaData('0028|0004', 'RGB') # PhotometricInterpretation
            out_image.SetMetaData('0028|0002', '3') # SamplesPerPixel
            out_image.SetMetaData("0008|0031", modification_time),  # Series Time
            out_image.SetMetaData("0008|0021", modification_date),  # Series Date
            out_image.SetMetaData("0008|0008", "DERIVED\\SECONDARY"),  # Image Type
            out_image.SetMetaData('0028|0101', '8') #BitsStored            
            out_image.SetMetaData('0028|0100', '8') #BitsAllocated            
            out_image.SetMetaData('0028|0102', '7') #highbit
            
            writer.SetFileName(os.path.join(dcm_output_path, series_uid_out + '_seg-mask_' + f'{i:03d}' + '.dcm'))
            writer.Execute(out_image)
