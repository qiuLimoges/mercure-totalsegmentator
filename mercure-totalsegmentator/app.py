#TotalSegmentator App for mercure-totalsegmentator module

# TotalSegmentator (https://github.com/wasserth/TotalSegmentator) is a software tool for segmentation of anatomical structures 
# in CT images and is distributed under the Apache 2.0 licence. The original creators of TotalSegmentator were not involved in 
# creation of the code in this app.

# This TotalSegmentator App folllows the MONAI Deploy SDK framework and contains code reused / adapted from the 
# TOTALSegmentator-AIDE app (https://github.com/GSTT-CSC/TotalSegmentator-AIDE)
# Modifications include :
# -Adaption of total_segmentator_operator.py to run --fast and --ml options of TotalSegmentator software
# -Modification of dcm2nii_operator.py to run in mercure module environment
# -Modification of rtstruct_writer_operator.py to loop through segmentations in single nii file
# -Additional operators for DICOM SEG and RGB DICOM output formats


import logging
import monai.deploy.core as md
from monai.deploy.core import (
    Application,
    DataPath,
    ExecutionContext,
    Image,
    InputContext,
    IOType,
    Operator,
    OutputContext,
    resource
)

from dcm2nii_operator import Dcm2NiiOperator
from total_segmentator_operator import TotalSegmentatorOperator
from masked_dcm_writer_operator import MaskedDICOMWriterOperator
from seg_dcm_writer_operator import SegDICOMWriterOperator
from rtstruct_writer_operator import RTStructWriterOperator

from monai.deploy.core import Application, resource

@md.resource(cpu=1)
class TotalSegmentatorApp(Application):
    """
    TotalSegmentator - segmentation of 104 anatomical structures in CT images.
    """

    name = "mercure-totalsegmentator"
    description = "Robust segmentation of 104 anatomical structures in CT images"
    version = "0.1.1"

    def compose(self):
        """Operators go in here
        """

        logging.info(f"Begin {self.compose.__name__}")

        # DICOM to NIfTI operator
        dcm2nii_op = Dcm2NiiOperator()

        # TotalSegmentator segmentation
        totalsegmentator_op = TotalSegmentatorOperator()

        # RT Struct Writer operator
        custom_tags = {"SeriesDescription": "AI generated image, not for clinical use."}
        rtstructwriter_op = RTStructWriterOperator(custom_tags=custom_tags)

        #Masked DICOM writer
        maskedDICOMwriter_op=MaskedDICOMWriterOperator()

        segDICOMwriter_op=SegDICOMWriterOperator()

        # Operator pipeline
        self.add_flow(dcm2nii_op, totalsegmentator_op, {"input_files": "input_files"})
        self.add_flow(totalsegmentator_op, rtstructwriter_op, {"input_files": "input_files"})
        self.add_flow(totalsegmentator_op, maskedDICOMwriter_op, {"input_files": "input_files"})
        self.add_flow(totalsegmentator_op, segDICOMwriter_op, {"input_files": "input_files"})
        

        logging.info(f"End {self.compose.__name__}")
