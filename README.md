# mercure-totalsegmentator
Mercure module to deploy [TotalSegmentator](https://github.com/wasserth/TotalSegmentator) tool for segmentation of 104 classes in CT images. Currently running CPU compatible version at lower resolution (3mm) only.
### Installation
1. Clone repo.
2. Build Docker container locally by running make (modify makefile with new docker tag as needed).
3. Test container :\
`docker run -it -v /input_data:/input -v /output_data:/output --env MERCURE_IN_DIR=/input  --env MERCURE_OUT_DIR=/output *docker-tag*`
### Output
Segmentations are written to specified output directory in three different formats :
- DICOM RTStruct ( with segmentated VOI volume ( mm<sup>3</sup> ) in description field )
- DICOM SEG
- DICOM RGB ( with masks of each VOI overlaid )