
import argparse
import os
import os.path
import struct
import subprocess
import string
import time

import musicbrainzngs as mb

mb.set_useragent("Zed Track Splitter", "0.1", "http://gitgud.malvager.net/zed")
okchars = string.ascii_letters + string.digits + string.whitespace

def mangle_title(bulky):
    nameparts = bulky.split('(')
    if len(nameparts) == 1:
        namepart = ''.join(bulky.split('-')[:-1])
    else:
        namepart = nameparts[0]
    boring = ''.join((c for c in namepart if c in okchars))
    return boring

def get_track_list(yttitle):
    search_string = mangle_title(yttitle)
    searchidres = mb.search_release_groups(search_string)
    correctness = searchidres['release-group-list'][0]['ext:score']
    album = searchidres['release-group-list'][0]['title']
    artist = searchidres['release-group-list'][0]['artist-credit'][0]['artist']['name']
    if int(correctness) > 97:
        brlid = searchidres['release-group-list'][0]['release-list'][0]['id']
        rel = mb.get_release_by_id(brlid, includes=['recordings'])
        return artist, album, [c['recording']['title'] for c in rel['release']['medium-list'][0]['track-list']]
    else:
        return None, None, None

def get_media_paths(folder):
  print(os.listdir(folder))
  return [f
        for f in os.listdir(folder)
              if os.path.splitext(f)[1] in ('.mp3', '.mp4', '.m4a')]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert media to media')
    parser.add_argument('-d', '--directory', required=True, help='Source directory containing mp4 or webm files')
    parser.add_argument('-a', '--actuallyrun', action='store_true')
    args = parser.parse_args()
    folder = os.path.abspath(args.directory)
    media = get_media_paths(folder)
    for m in media:
        print(mangle_title(m))
        if args.actuallyrun:
            print(get_track_list(m))
            time.sleep(15)
