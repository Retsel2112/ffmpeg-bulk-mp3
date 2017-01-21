#ffmpeg.exe -i "\\10.0.0.10\Data\Folder\ytdl\Somali Yacht Club - The Sun (2014) (Full Album)-DGPyHQ2FSUQ.mp4" -codec:a libmp3lame -qscale:a 2 \\10.0.0.10\Data\Folder\ytdl\conversions\test2.mp3
from multiprocessing import Pool
import argparse
import os
import os.path
import struct
import subprocess
import tempfile
import time
import wave

def convert(filename):
    newname = '.'.join([os.path.splitext(os.path.split(filename)[1])[0], "mp3"])
    with tempfile.NamedTemporaryFile(dir='/tmp', suffix='.wav', delete=False) as tmpfile:
        tmp_file_name = tmpfile.name
    newpath = os.sep.join((os.path.split(filename)[0], "conversions", newname))
    print(' '.join(['ffmpeg', '-i', filename, '-codec:a', 'pcm_s16le', tmp_file_name]))
    #os.system(' '.join(['ffmpeg', '-i', filename, '-codec:a', 'pcm_s16le', tmp_file_name]))
    proc = subprocess.Popen(['ffmpeg', '-i', filename, '-y', '-codec:a', 'pcm_s16le', tmp_file_name], shell=False)
    (outwavdata, err) = proc.communicate()
    f = wave.open(tmp_file_name, 'rb')
    chans = f.getnchannels()
    samps = f.getnframes()
    sampwidth = f.getsampwidth()
    assert sampwidth == 2
    s = f.readframes(samps)
    f.close()
    unpstr = '<{0}h'.format(samps*chans)
    x = list(struct.unpack(unpstr, s))
    cha = x[0]
    chb = x[1]
    print(type(cha))
    print(len(cha))
    print(type(chb))
    print(len(chb))


def get_media_paths(folder):
  return [os.path.join(folder, f) 
      for f in os.listdir(folder) 
      if os.path.splitext(f)[1] in ('.mp3')]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert media to media')
    parser.add_argument('-d', '--directory', required=True, help='Source directory containing mp4 or webm files')
    args = parser.parse_args()
    folder = os.path.abspath(args.directory)
    media = get_media_paths(folder)
    print(media)
    convert(media[0])
    #pool = Pool()
    #pool.map(convert, media)
    #pool.close() 
    #pool.join()
