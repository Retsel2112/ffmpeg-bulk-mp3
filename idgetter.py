
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
    artist = ''
    album = ''
    nameparts = bulky.split('(')
    if len(nameparts) == 1:
        firstsplit = bulky.split('-')
        if len(firstsplit) == 2:
            # Only took off the hyphen in the ytdlvidid. Let's check for a title in quotes.
            secondsplit = firstsplit[0].split("'")
            if len(secondsplit) == 3:
                #or is that supposed to be two...
                artist = secondsplit[0]
                album = secondsplit[1]
            if len(secondsplit) > 3:
                #there was some other quote, too.
                thirdsplit = "'".join(secondsplit[:-1]).split(" '")
                if len(thirdsplit) == 2:
                    artist, album = thirdsplit
        if len(firstsplit) > 2:
            #going to assume the file was artist - album-ytdlvidid
            #get rid of the youtubedl video id
            secondsplit = '-'.join(firstsplit[:-1]).split(' - ')
            if len(secondsplit) >= 2:
                artist, album = firstsplit[0:2]
    else:
        namepart = nameparts[0]
        #check if splitting on a hyphen gets us two parts
        firstsplit = namepart.split('-')
        if len(firstsplit) == 2:
            #going to assume the file was artist - album (unnecessary text)
            artist, album = firstsplit
        elif len(firstsplit) > 2:
            #going to assume the file was artist - album-ytdlvidid
            #get rid of the youtubedl video id
            secondsplit = '-'.join(firstsplit[:-1]).split(' - ')
            if len(secondsplit) >= 2:
                artist, album = firstsplit[0:2]
        else:
            #maybe the title was in quotes.
            firstsplit = namepart.split("'")
            if len(firstsplit) == 3:
                #or is that supposed to be two...
                artist = firstsplit[0]
                album = firstsplit[1]
            if len(firstsplit) > 3:
                #there was some other quote, too.
                secondsplit = "'".join(firstsplit[:-1]).split(" '")
                if len(secondsplit) == 2:
                    artist, album = secondsplit
    return (artist.strip(), album.strip())

def get_track_list(yttitle):
    artist, album = mangle_title(yttitle)
    search_string = mangle_title(yttitle)
    artist_res = mb.search_artists(artist=artist, type='group', strict=True)
    try:
        correctness = artist_res['artist-list'][0]['ext:score']
        if int(correctness) > 97:
            artist_id = artist_res['artist-list'][0]['id']
            release_res = mb.search_releases(arid=artist_id, release=album)
            albcorrectness = release_res['release-list'][0]['ext:score']
            if int(albcorrectness) > 97:
                album_id = release_res['release-list'][0]['id']
                rel = mb.get_release_by_id(album_id, includes=['recordings'])
                return artist, album, [c['recording']['title'] for c in rel['release']['medium-list'][0]['track-list']]
    except IndexError:
        # No hits.
        pass
    return None, None, None

def get_media_paths(folder):
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
