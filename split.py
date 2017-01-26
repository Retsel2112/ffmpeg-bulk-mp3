
import argparse
import errno
import multiprocessing
import os
import os.path
import shutil
import struct
import subprocess
import sys
import tempfile
import wave

import musicbrainzngs as mb

import idgetter

READBUF = 44100 * 60
SILENCE_LEVEL = 1000
SILENCE_DURATION = 10000
SPLIT_EPSILON = 3 # seconds of leeway around musicbrainz track length and track silence location

def reached(a, b, rate = 44100):
    if a > b:
        print("checked %d vs %d" % (a/rate, b/rate))
        return True
    return False
    if abs(a - b) < SPLIT_EPSILON * rate:
        return True
    return False

def convert(fileinfo):
    artist, album, trackname, trackorder, trackfilename, trackdestination = fileinfo
    print(fileinfo)
    newname = '.'.join([os.path.splitext(os.path.split(trackfilename)[1])[0], "mp3"])
    newpath = os.sep.join((trackdestination, newname))
    #print('ffmpeg -loglevel error -i "{0}" -codec:a libmp3lame -qscale:a 2 -metadata album="{2}" -metadata artist="{3}" -metadata title="{4}" -metadata track="{5}" "{1}" '.format(trackfilename, newpath, album, artist, trackname, trackorder))
    #os.system('ffmpeg -loglevel error -i "{0}" -codec:a libmp3lame -qscale:a 2 -metadata album="{2}" -metadata artist="{3}" -metadata title="{4}" -metadata track="{5}" "{1}" '.format(trackfilename, newpath, album, artist, trackname, trackorder))
    print(' '.join([
    'ffmpeg', 
    '-loglevel', 'error', 
    '-i', trackfilename, 
    '-codec:a', 'libmp3lame', 
    '-qscale:a', '2', 
    '-metadata', 'album={}'.format(album), 
    '-metadata', 'artist={}'.format(artist),
    '-metadata', 'title={}'.format(trackname),
    '-metadata', 'track={}'.format(trackorder),
    newpath]))
    proc = subprocess.Popen([
    'ffmpeg', 
    '-loglevel', 'error', 
    '-i', trackfilename, 
    '-codec:a', 'libmp3lame', 
    '-qscale:a', '2', 
    '-metadata', 'album={}'.format(album), 
    '-metadata', 'artist={}'.format(artist),
    '-metadata', 'title={}'.format(trackname),
    '-metadata', 'track={}'.format(trackorder),
    newpath])
    (outdata,err) = proc.communicate()
    os.remove(trackfilename)

def splittrack(packarg):
    args, filename = packarg
    newname = '.'.join([os.path.splitext(os.path.split(filename)[1])[0], "mp3"])
    with tempfile.NamedTemporaryFile(dir='tmp', suffix='.wav', delete=False) as tmpfile:
        tmp_file_name = tmpfile.name
    artist, album, tracklist = idgetter.get_track_list(newname)
    print(' '.join(['ffmpeg', '-i', filename, '-codec:a', 'pcm_s16le', tmp_file_name]))
    if tracklist is None:
        return
    #os.system(' '.join(['ffmpeg', '-i', filename, '-codec:a', 'pcm_s16le', tmp_file_name]))
    proc = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-i', filename, '-y', '-codec:a', 'pcm_s16le', tmp_file_name], shell=False)
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
    j = 0
    samples_processed = 0
    # the track length returned by musicbrainz is in mulliseconds.
    # convert that to seconds then multiply by our sample rate to get an idea
    # of when the next track should end, sample-wise
    split_estimate = int((tracklist[j][1] / 1000) * samprate)
    while True:
        twoch_samps = f.readframes(READBUF)
        for twoch_samp in range(0,len(twoch_samps),sampwidth*chans):
            samples_processed += 1
            l,r = struct.unpack('<2h', twoch_samps[twoch_samp:twoch_samp+(sampwidth*chans)])
            chana.append(l)
            chanb.append(r)
            if abs(l) < SILENCE_LEVEL:
                zerorow += 1
            if zerorow > SILENCE_DURATION and reached(samples_processed, split_estimate, samprate):
                print("%d in a row" % (zerorow))
                ender = max(-int(zerorow / 2), -10000)
                try:
                    trackfilename = '%s -  %s (%s).wav' % (artist, tracklist[j][0], album)
                    trackname = tracklist[j][0]
                except IndexError:
                    trackfilename = '%s_%s_%d.wav' % (artist, album, j)
                    trackname = 'Track %d' % (j)
                tout = wave.open(trackfilename, 'wb')
                tout.setnchannels(2)
                tout.setsampwidth(sampwidth)
                tout.setframerate(samprate)
                tout.writeframes(b''.join((struct.pack('<hh',smpl, smpr) for smpl, smpr in zip(chana[0:ender], chanb[0:ender]))))
                tout.close()
                tracks.append((artist, album, trackname, '%d/%d' % (j+1, len(tracklist)), trackfilename, args.destination))
                j += 1
                if j != len(tracklist):
                    split_estimate += int((tracklist[j][1] / 1000) * samprate)
                else:
                    split_estimate = samps * 2
                chana = chana[ender:]
                chanb = chanb[ender:]
                zerorow = 0
        if len(twoch_samps) < (READBUF * sampwidth * chans):
            break
    if len(chana) > 10000:
        try:
            trackfilename = '%s -  %s (%s).wav' % (artist, tracklist[j][0], album)
            trackname = tracklist[j][0]
        except IndexError:
            trackfilename = '%s_%s_%d.wav' % (artist, album, j)
            trackname = 'Track %d' % (j)
        tout = wave.open(trackfilename, 'wb')
        tout.setnchannels(2)
        tout.setsampwidth(sampwidth)
        tout.setframerate(samprate)
        tout.writeframes(b''.join((struct.pack('<hh',smpl, smpr) for smpl, smpr in zip(chana[0:ender], chanb[0:ender]))))
        tout.close()
        tracks.append((artist, album, trackname, '%d/%d' % (j+1, len(tracklist)), trackfilename, args.destination))
    f.close()
    os.remove(tmp_file_name)
    print(tracks)
    list(map(convert, tracks))
    print("And that's it")
    shutil.move(filename, os.path.join(args.finished, os.path.basename(filename)))
    return


def get_media_paths(folder):
  return [os.path.join(folder, f) 
      for f in os.listdir(folder) 
      if '.' in f and os.path.splitext(f)[1] in ('.mp3')]

if __name__ == '__main__':
    #multiprocessing.freeze_support()
    parser = argparse.ArgumentParser(description='Convert media to media')
    parser.add_argument('-s', '--source', required=True, help='Source directory containing mp4 or webm files')
    parser.add_argument('-d', '--destination', required=True, help='Destination directory to place converted files')
    parser.add_argument('-f', '--finished', required=True, help='Directory to move source files after conversion')
    parser.add_argument('-m', '--multiproc', required=False, help='Maximum number of concurrent conversion processes (up to cpu_count) (default: 4)', type=int, default=4)
    args = parser.parse_args()
    args.finished = os.path.abspath(args.finished)
    args.destination = os.path.abspath(args.destination)
    args.source = os.path.abspath(args.source)
    try:
        os.makedirs(args.destination)
    except OSError as ex:
        if ex.errno != errno.EEXIST:
            raise
    try:
        os.makedirs(args.finished)
    except OSError as ex:
        if ex.errno != errno.EEXIST:
            raise
    folder = os.path.abspath(args.source)
    media = get_media_paths(folder)
    print(media)
    mb.set_useragent("Zed Track Splitter", "0.1", "http://gitgud.malvager.net/zed")

    splitpool = multiprocessing.Pool(min(os.cpu_count(), args.multiproc))
    splitpool.map(splittrack, ((args, m) for m in media))
    splitpool.close() 
    splitpool.join()

