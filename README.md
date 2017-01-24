# ffmpeg-bulk-mp3

Python script to shell out bulk youtube-dl downloads to mp3 conversions

Requires ffmpeg, currently runs on Windows (because my beefy box is Windows)
Might run on other platforms. Untested.

Expects bulk.py to be run in the subdirectory "conversions" where converted files will be placed.
Must be a subdirectory of folder containing mp4 and webm files to convert.

Expects split.py to be run something like:
python split.py -s E:\media\src -d E:\media\split -f E:\media\fin
