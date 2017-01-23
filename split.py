
import multiprocessing
import argparse
import os
import os.path
import struct
import subprocess
import tempfile
import time
import wave

import musicbrainzngs as mb

import idgetter


READBUF = 44100 * 60
args = None

def convert(fileinfo):
    artist, album, trackname, trackfilename = fileinfo
    print(fileinfo)
    newname = '.'.join([os.path.splitext(os.path.split(trackfilename)[1])[0], "mp3"])
    newpath = os.sep.join(('done', newname))
    print('ffmpeg -i "{0}" -codec:a libmp3lame -qscale:a 2 -metadata album="{2}" -metadata artist="{3}" -metadata title="{4}" "{1}" '.format(trackfilename, newpath, album, artist, trackname))
    os.system('ffmpeg -i "{0}" -codec:a libmp3lame -qscale:a 2 -metadata album="{2}" -metadata artist="{3}" -metadata title="{4}" "{1}" '.format(trackfilename, newpath, album, artist, trackname))
    os.remove(trackfilename)

def splittrack(filename):
    newname = '.'.join([os.path.splitext(os.path.split(filename)[1])[0], "mp3"])
    with tempfile.NamedTemporaryFile(dir='tmp', suffix='.wav', delete=False) as tmpfile:
        tmp_file_name = tmpfile.name
    newpath = os.sep.join((os.path.split(filename)[0], "conversions", newname))
    artist, album, tracklist = idgetter.get_track_list(newname)
    print(' '.join(['ffmpeg', '-i', filename, '-codec:a', 'pcm_s16le', tmp_file_name]))
    if tracklist is None:
        return
    #os.system(' '.join(['ffmpeg', '-i', filename, '-codec:a', 'pcm_s16le', tmp_file_name]))
    proc = subprocess.Popen(['ffmpeg', '-i', filename, '-y', '-codec:a', 'pcm_s16le', tmp_file_name], shell=False)
    (outwavdata, err) = proc.communicate()
    f = wave.open(tmp_file_name, 'rb')
    chans = f.getnchannels()
    samps = f.getnframes()
    sampwidth = f.getsampwidth()
    samprate = f.getframerate()
    assert sampwidth == 2
    chana = []
    chanb = []
    tracks = []
    zerorow = 0
    sliceStart = False
    j = 0
    #for i in range(samps):
    while True:
        twoch_samps = f.readframes(READBUF)
        for twoch_samp in range(0,len(twoch_samps),sampwidth*chans):
            l,r = struct.unpack('<2h', twoch_samps[twoch_samp:twoch_samp+(sampwidth*chans)])
            chana.append(l)
            chanb.append(r)
            if abs(l) < 200:
                zerorow += 1
            else:
                if zerorow > 10000:
                    print("%d in a row" % (zerorow))
                    ender = -int(zerorow / 2)
                    if sliceStart:
                        try:
                            trackfilename = '%s -  %s (%s).wav' % (artist, tracklist[j], album)
                            trackname = tracklist[j]
                        except IndexError:
                            trackfilename = 'file_%d.wav' % (j)
                            trackname = 'Track %d' % (j)
                        tout = wave.open(trackfilename, 'wb')
                        tout.setnchannels(2)
                        tout.setsampwidth(sampwidth)
                        tout.setframerate(samprate)
                        tout.writeframes(b''.join((struct.pack('<hh',smpl, smpr) for smpl, smpr in zip(chana[0:ender], chanb[0:ender]))))
                        tout.close()
                        tracks.append((artist, album, trackname, trackfilename))
                        j += 1
                        chana = chana[ender:]
                        chanb = chanb[ender:]
                    sliceStart = True
                zerorow = 0
        if len(twoch_samps) < (READBUF * sampwidth * chans):
            break
    if len(chana) > 10000:
        try:
            trackfilename = '%s -  %s (%s).wav' % (artist, tracklist[j], album)
            trackname = tracklist[j]
        except IndexError:
            trackfilename = 'file_%d.wav' % (j)
            trackname = 'Track %d' % (j)
        tout = wave.open(trackfilename, 'wb')
        tout.setnchannels(2)
        tout.setsampwidth(sampwidth)
        tout.setframerate(samprate)
        tout.writeframes(b''.join((struct.pack('<hh',smpl, smpr) for smpl, smpr in zip(chana[0:ender], chanb[0:ender]))))
        tout.close()
        tracks.append((artist, album, trackname, trackfilename))
    f.close()
    os.remove(tmp_file_name)
    print(tracks)
    list(map(convert, tracks))
    print("And that' it")
    #move source file to args.finished
    return


def get_media_paths(folder):
  return [os.path.join(folder, f) 
      for f in os.listdir(folder) 
      if '.' in f and os.path.splitext(f)[1] in ('.mp3')]

if __name__ == '__main__':
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser(description='Convert media to media')
    parser.add_argument('-s', '--source', required=True, help='Source directory containing mp4 or webm files')
    parser.add_argument('-d', '--destination', required=True, help='Destination directory to place converted files')
    parser.add_argument('-f', '--finished', required=True, help='Directory to move source files after conversion')
    args = parser.parse_args()
    folder = os.path.abspath(args.source)
    media = get_media_paths(folder)
    print(media)
    mb.set_useragent("Zed Track Splitter", "0.1", "http://gitgud.malvager.net/zed")

    splitpool = multiprocessing.Pool(processes=1)
    splitpool.map(splittrack, media)
    splitpool.close() 
    splitpool.join()
