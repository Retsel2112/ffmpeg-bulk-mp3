
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
import fsm

#READBUF = 44100 * 60
READBUF = int(44100 / 10)
SILENCE_LEVEL = 200
LOUD_LEVEL = 2200
SILENCE_DURATION = 10000
BLIND_SILENCE_DURATION = 30000
LOUD_DURATION = 22000
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
    '-n',
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
    '-n',
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
    print(' '.join(['ffmpeg', '-n', '-i', filename, '-codec:a', 'pcm_s16le', tmp_file_name]))
    if tracklist is None:
        if args.noconv is not None:
            shutil.move(filename, os.path.join(args.noconv, os.path.basename(filename)))
        return
    for t in tracklist:
        print(t)
    #os.system(' '.join(['ffmpeg', '-i', filename, '-codec:a', 'pcm_s16le', tmp_file_name]))
    proc = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-i', filename, '-y', '-codec:a', 'pcm_s16le', tmp_file_name], shell=False)
    (outwavdata, err) = proc.communicate()
    if tracklist[0][1] == 0:
        tracks = splittrack_nohints(artist, album, tracklist, tmp_file_name, args.destination)
    else:
        tracks = splittrack_trustbutverify(artist, album, tracklist, tmp_file_name, args.destination)
    os.remove(tmp_file_name)
    list(map(convert, tracks))
    print("And that's it")
    shutil.move(filename, os.path.join(args.finished, os.path.basename(filename)))
    return

def splittrack_trustbutverify(artist, album, tracklist, tmp_file_name, destination):
    f = wave.open(tmp_file_name, 'rb')
    chans = f.getnchannels()
    samps = f.getnframes()
    sampwidth = f.getsampwidth()
    samprate = f.getframerate()
    assert sampwidth == 2
    chana = []
    chanb = []
    tracks = []
    j = 0
    split_here = 0

    # hold up - does the total album length from our tracklist seem accurate,
    # given the values we just read as samps and samprate?
    # Count the expected number of seconds:
    tracktime = 0
    for _, split_estimate in tracklist:
        tracktime += split_estimate / 1000 # because split_estimate is in milliseconds
    realtime = samps / samprate # because samples / (samples / second) gives seconds
    if abs(realtime - tracktime) > 15:
        # more than 15 seconds off? screw those track estimates, something is missing.
        f.close()
        return splittrack_nohints(artist, album, tracklist, tmp_file_name, destination)

    # the track length returned by musicbrainz is in mulliseconds.
    # convert that to seconds then multiply by our sample rate to get an idea
    # of when the next track should end, sample-wise
    silence_interval_check = int(samprate / 1000)
    overshoot = samprate
    for trackname, split_estimate in tracklist:
        next_track_length = int(split_estimate / 1000 * samprate)
        #When reading in, overshoot by a second:
        twoch_samps = f.readframes(next_track_length + overshoot)
        print(len(twoch_samps)/samprate)
        for twoch_samp in range(0,len(twoch_samps),sampwidth*chans):
            l,r = struct.unpack('<2h', twoch_samps[twoch_samp:twoch_samp+(sampwidth*chans)])
            chana.append(l)
            chanb.append(r)
        try:
            if len(tracklist) > 9:
                trackfilename = '%s - %s - %02d - %s.wav' % (artist, album, j+1, trackname)
            else:
                trackfilename = '%s - %s - %d - %s.wav' % (artist, album, j+1, trackname)
        except IndexError:
            trackfilename = '%s_%s_%d.wav' % (artist, album, j)
            trackname = 'Track %d' % (j)
        #rewind until the last place we see something like silence
        #In... like... the last two seconds?
        last_silence = -overshoot
        for interval in range(0, -100, -1):
            i_s = int((interval - 1) * samprate / 10)
            i_e = int(interval * samprate / 10)
            avga = sum((abs(s) for s in chana[i_s:(i_e if i_e else None)])) / abs(i_e - i_s)
            avgb = sum((abs(s) for s in chanb[i_s:(i_e if i_e else None)])) / abs(i_e - i_s)
            print("%d from %d to %d" % (avga + avgb, i_s, i_e))
            if (avga + avgb) < SILENCE_LEVEL:
                last_silence = int((i_s + i_e) / 2)
                print("Backing up %d" % (last_silence))
                break

        tout = wave.open(trackfilename, 'wb')
        tout.setnchannels(2)
        tout.setsampwidth(sampwidth)
        tout.setframerate(samprate)
        tout.writeframes(b''.join((struct.pack('<hh',smpl, smpr) for smpl, smpr in zip(chana[:last_silence], chanb[:last_silence]))))
        tout.close()
        tracks.append((artist, album, trackname, '%d/%d' % (j+1, len(tracklist)), trackfilename, destination))
        j += 1
        chana = chana[last_silence:]
        chanb = chana[last_silence:]
        if len(twoch_samps) < (READBUF * sampwidth * chans):
            break
    if len(chana) > 10000:
        try:
            if len(tracklist) > 9:
                trackfilename = '%s - %s - %02d - %s.wav' % (artist, album, j+1, tracklist[j][0])
            else:
                trackfilename = '%s - %s - %d - %s.wav' % (artist, album, j+1, tracklist[j][0])
            trackname = tracklist[j][0]
        except IndexError:
            trackfilename = '%s_%s_%d.wav' % (artist, album, j)
            trackname = 'Track %d' % (j)
        tout = wave.open(trackfilename, 'wb')
        tout.setnchannels(2)
        tout.setsampwidth(sampwidth)
        tout.setframerate(samprate)
        tout.writeframes(b''.join((struct.pack('<hh',smpl, smpr) for smpl, smpr in zip(chana, chanb))))
        tout.close()
        tracks.append((artist, album, trackname, '%d/%d' % (j+1, len(tracklist)), trackfilename, destination))
    f.close()
    return tracks

def splittrack_nohints(artist, album, tracklist, tmp_file_name, destination):
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
    samples_read = 0
    vol_state = fsm.fsm()
    while True:
        twoch_samps = f.readframes(READBUF)
        samples_read += READBUF
        for twoch_samp in range(0,len(twoch_samps),sampwidth*chans):
            l,r = struct.unpack('<2h', twoch_samps[twoch_samp:twoch_samp+(sampwidth*chans)])
            chana.append(l)
            chanb.append(r)
        # I just signed an executive order that all tracks must be at least 25 seconds in length.
        if (samples_read / samprate) < 25:
            continue
        avga = sum((abs(s) for s in chana[-READBUF:])) / READBUF
        avgb = sum((abs(s) for s in chanb[-READBUF:])) / READBUF
        vol_state.add_sample(avga + avgb)
        if vol_state.should_split():
            split_here = -(vol_state.last_quiet() * READBUF)
            try:
                trackname = tracklist[j][0]
                if len(tracklist) > 9:
                    trackfilename = '%s - %s - %02d - %s.wav' % (artist, album, j+1, trackname)
                else:
                    trackfilename = '%s - %s - %d - %s.wav' % (artist, album, j+1, trackname)
            except IndexError:
                trackfilename = '%s_%s_%d.wav' % (artist, album, j)
                trackname = 'Track %d' % (j)
            tout = wave.open(trackfilename, 'wb')
            tout.setnchannels(2)
            tout.setsampwidth(sampwidth)
            tout.setframerate(samprate)
            tout.writeframes(b''.join((struct.pack('<hh',smpl, smpr) for smpl, smpr in zip(chana[0:split_here], chanb[0:split_here]))))
            tout.close()
            tracks.append((artist, album, trackname, '%d/%d' % (j+1, len(tracklist)), trackfilename, destination))
            j += 1
            chana = chana[split_here:]
            chanb = chanb[split_here:]
            zerorow = 0
            vol_state.reset()
        if len(twoch_samps) < (READBUF * sampwidth * chans):
            break
    if len(chana) > 10000:
        try:
            trackname = tracklist[j][0]
            if len(tracklist) > 9:
                trackfilename = '%s - %s - %02d - %s.wav' % (artist, album, j+1, trackname)
            else:
                trackfilename = '%s - %s - %d - %s.wav' % (artist, album, j+1, trackname)
        except IndexError:
            trackfilename = '%s_%s_%d.wav' % (artist, album, j)
            trackname = 'Track %d' % (j)
        tout = wave.open(trackfilename, 'wb')
        tout.setnchannels(2)
        tout.setsampwidth(sampwidth)
        tout.setframerate(samprate)
        tout.writeframes(b''.join((struct.pack('<hh',smpl, smpr) for smpl, smpr in zip(chana, chanb))))
        tout.close()
        tracks.append((artist, album, trackname, '%d/%d' % (j+1, len(tracklist)), trackfilename, destination))
    f.close()
    return tracks

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
    parser.add_argument('-n', '--noconv', required=False, help='Directory to move source files after conversion')
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
    if args.noconv is not None:
        try:
            os.makedirs(args.noconv)
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

