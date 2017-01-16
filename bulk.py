#ffmpeg.exe -i "\\10.0.0.10\Data\Folder\ytdl\Somali Yacht Club - The Sun (2014) (Full Album)-DGPyHQ2FSUQ.mp4" -codec:a libmp3lame -qscale:a 2 \\10.0.0.10\Data\Folder\ytdl\conversions\test2.mp3
from multiprocessing import Pool
import os
import os.path

import time

def convert(filename):
    newname = '.'.join([os.path.splitext(os.path.split(filename)[1])[0], "mp3"])
    newpath = os.sep.join((os.path.split(filename)[0], "conversions", newname))
    os.system("ffmpeg -i \"{0}\" -codec:a libmp3lame -qscale:a 2 \"{1}\" ".format(filename, newpath))

def get_media_paths(folder):
  return [os.path.join(folder, f) 
      for f in os.listdir(folder) 
      if os.path.splitext(f)[1] in ('.mp4', '.webm')]

if __name__ == '__main__':
    folder = os.path.abspath('..')
    media = get_media_paths(folder)
    pool = Pool()
    pool.map(convert, media)
    pool.close() 
    pool.join()