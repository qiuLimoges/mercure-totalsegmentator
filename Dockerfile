FROM continuumio/miniconda3



RUN mkdir -m777 /app
WORKDIR /app
ADD docker-entrypoint.sh ./
ADD mercure-totalsegmentator ./mercure-totalsegmentator

RUN chmod 777 ./docker-entrypoint.sh


RUN conda create -n env python=3.9
RUN echo "source activate env" > ~/.bashrc
ENV PATH /opt/conda/envs/env/bin:$PATH
RUN chmod -R 777 /opt/conda/envs

RUN apt-get update && apt-get install --no-install-recommends --no-install-suggests -y git build-essential cmake pigz
RUN apt-get update && apt-get install --no-install-recommends --no-install-suggests -y libsm6 libxrender-dev libxext6 ffmpeg
RUN apt-get install unzip

ADD environment.yml ./
RUN conda env create -f ./environment.yml

# Pull the environment name out of the environment.yml
RUN echo "source activate $(head -1 ./environment.yml | cut -d' ' -f2)" > ~/.bashrc
ENV PATH /opt/conda/envs/$(head -1 ./environment.yml | cut -d' ' -f2)/bin:$PATH

# Workaround for opencv package issue
# see here: https://stackoverflow.com/questions/72706073/attributeerror-partially-initialized-module-cv2-has-no-attribute-gapi-wip-gs

RUN python -m pip uninstall -y opencv-python
RUN python -m pip install opencv-python==4.5.5.64

# Add TotalSegmentator model weights to container
WORKDIR /root

RUN mkdir -m777 /app/totalsegmentator
ENV WEIGHTS_DIR="/app/totalsegmentator/nnunet/results/nnUNet/3d_fullres/"
RUN mkdir -m777 -p ${WEIGHTS_DIR}



# Uncomment parts 1 to 5 for full res - GPU preferred!!
# # Part 1 - Organs
ENV WEIGHTS_URL_1="https://zenodo.org/record/6802342/files/Task251_TotalSegmentator_part1_organs_1139subj.zip"
ENV WEIGHTS_ZIP_1="Task251_TotalSegmentator_part1_organs_1139subj.zip"

RUN wget --directory-prefix ${WEIGHTS_DIR} ${WEIGHTS_URL_1} \
    && unzip ${WEIGHTS_DIR}${WEIGHTS_ZIP_1} -d ${WEIGHTS_DIR} \
    && rm ${WEIGHTS_DIR}${WEIGHTS_ZIP_1}

# # Part 2 - Vertebrae
ENV WEIGHTS_URL_2="https://zenodo.org/record/6802358/files/Task252_TotalSegmentator_part2_vertebrae_1139subj.zip"
ENV WEIGHTS_ZIP_2="Task252_TotalSegmentator_part2_vertebrae_1139subj.zip"

RUN wget --directory-prefix ${WEIGHTS_DIR} ${WEIGHTS_URL_2} \
    && unzip ${WEIGHTS_DIR}${WEIGHTS_ZIP_2} -d ${WEIGHTS_DIR} \
    && rm ${WEIGHTS_DIR}${WEIGHTS_ZIP_2}

# # Part 3 - Cardiac
ENV WEIGHTS_URL_3="https://zenodo.org/record/6802360/files/Task253_TotalSegmentator_part3_cardiac_1139subj.zip"
ENV WEIGHTS_ZIP_3="Task253_TotalSegmentator_part3_cardiac_1139subj.zip"

RUN wget --directory-prefix ${WEIGHTS_DIR} ${WEIGHTS_URL_3} \
    && unzip ${WEIGHTS_DIR}${WEIGHTS_ZIP_3} -d ${WEIGHTS_DIR} \
    && rm ${WEIGHTS_DIR}${WEIGHTS_ZIP_3}

# # Part 4 - Muscles
ENV WEIGHTS_URL_4="https://zenodo.org/record/6802366/files/Task254_TotalSegmentator_part4_muscles_1139subj.zip"
ENV WEIGHTS_ZIP_4="Task254_TotalSegmentator_part4_muscles_1139subj.zip"

RUN wget --directory-prefix ${WEIGHTS_DIR} ${WEIGHTS_URL_4} \
    && unzip ${WEIGHTS_DIR}${WEIGHTS_ZIP_4} -d ${WEIGHTS_DIR} \
    && rm ${WEIGHTS_DIR}${WEIGHTS_ZIP_4}

# # Part 5 - Ribs
ENV WEIGHTS_URL_5="https://zenodo.org/record/6802452/files/Task255_TotalSegmentator_part5_ribs_1139subj.zip"
ENV WEIGHTS_ZIP_5="Task255_TotalSegmentator_part5_ribs_1139subj.zip"


RUN wget --directory-prefix ${WEIGHTS_DIR} ${WEIGHTS_URL_5} \
    && unzip ${WEIGHTS_DIR}${WEIGHTS_ZIP_5} -d ${WEIGHTS_DIR} \
    && rm ${WEIGHTS_DIR}${WEIGHTS_ZIP_5}


# Part 6 - Task 256 for fast processing
ENV WEIGHTS_URL_6="https://zenodo.org/record/6802052/files/Task256_TotalSegmentator_3mm_1139subj.zip"
ENV WEIGHTS_ZIP_6="Task256_TotalSegmentator_3mm_1139subj.zip"


RUN wget --directory-prefix ${WEIGHTS_DIR} ${WEIGHTS_URL_6} \
    && unzip ${WEIGHTS_DIR}${WEIGHTS_ZIP_6} -d ${WEIGHTS_DIR} \
    && rm ${WEIGHTS_DIR}${WEIGHTS_ZIP_6}

# Set TOTALSEG_WEIGHTS_PATH ENV variable – this is auto-detected by TotalSegmentator
# See: https://github.com/wasserth/TotalSegmentator/blob/f4651171a4c6eae686dd67b77efe6aa78911734d/totalsegmentator/libs.py#L77
#ENV TOTALSEG_WEIGHTS_PATH="/root/.totalsegmentator/nnunet/results/"
ENV TOTALSEG_WEIGHTS_PATH="/app/totalsegmentator/nnunet/results/"
RUN chmod -R 777 /app/totalsegmentator
WORKDIR /app

CMD ["./docker-entrypoint.sh"]
