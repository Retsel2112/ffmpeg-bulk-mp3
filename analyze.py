
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

import fsm

READBUF = int(44100 / 10)
SILENCE_LEVEL = 300
LOUD_LEVEL = 2000
SILENCE_DURATION = 10000
BLIND_SILENCE_DURATION = 40000
SPLIT_EPSILON = 3 # seconds of leeway around musicbrainz track length and track silence location

def reached(a, b, rate = 44100):
    if a > b:
        print("checked %d vs %d" % (a/rate, b/rate))
        return True
    return False
    if abs(a - b) < SPLIT_EPSILON * rate:
        return True
    return False

def analyze(packarg):
    filename = packarg
    with tempfile.NamedTemporaryFile(dir='tmp', suffix='.wav', delete=False) as tmpfile:
        tmp_file_name = tmpfile.name
    print(' '.join(['ffmpeg', '-i', filename, '-codec:a', 'pcm_s16le', tmp_file_name]))
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
    split_now = False
    vol_state = fsm.fsm()
    vol_state.set_verbose(True)
    while True:
        twoch_samps = f.readframes(READBUF)
        for twoch_samp in range(0,len(twoch_samps),sampwidth*chans):
            l,r = struct.unpack('<2h', twoch_samps[twoch_samp:twoch_samp+(sampwidth*chans)])
            chana.append(l)
            chanb.append(r)
        avga = sum((abs(s) for s in chana)) / READBUF
        avgb = sum((abs(s) for s in chanb)) / READBUF
        chana = []
        chanb = []
        vol_state.add_sample(avga + avgb)
        print("%d\t%d\t%d\t%s\t%d (%d)" % (j, avga, avgb, vol_state.get_state(), vol_state.should_split(), vol_state.last_quiet()))
        if vol_state.should_split():
            vol_state.reset()
        j += 0.1
        if len(twoch_samps) < (READBUF * sampwidth * chans):
            break
    f.close()
    os.remove(tmp_file_name)
    print("And that's it")
    return


if __name__ == '__main__':
    #multiprocessing.freeze_support()
    parser = argparse.ArgumentParser(description='Convert media to media')
    parser.add_argument('-s', '--source', required=True, help='Source directory containing mp4 or webm files')
    args = parser.parse_args()
    args.source = os.path.abspath(args.source)

    analyze(args.source)
