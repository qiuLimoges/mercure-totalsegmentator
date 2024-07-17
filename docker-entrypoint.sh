#!/usr/bin/env bash
set -Eeo pipefail
echo "-- Starting TotalSegmentator..."
conda run -n mercure-totalsegmentator python mercure-totalsegmentator -i $MERCURE_IN_DIR -o $MERCURE_OUT_DIR --output_type dicom
echo "-- Done."
