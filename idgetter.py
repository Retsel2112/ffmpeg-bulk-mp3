
import argparse
import os
import os.path
import re
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
    artist_res = mb.search_artists(artist=artist, type='group', strict=True)
    try:
        release_res = mb.search_releases(release=album)
    except ValueError:
        # It is likely that the mangle_title wasn't able to find an artist/album split.
        print('Unable to split: %s' % (yttitle))
        return (None, None, None)
    artists = []
    arids = []
    albums = dict()
    try:
        alb_i = 0
        for a in artist_res['artist-list']:
            correctness = a['ext:score']
            if int(correctness) < 97:
                break
            artists.append(a)
            arids.append(a['id'])
        for i, r in enumerate(release_res['release-list']):
            correctness = r['ext:score']
            if int(correctness) < 97:
                break
            if r['artist-credit'][0]['artist']['id'] in arids:
                rel = mb.get_release_by_id(r['id'], includes=['recordings'])
                albums[i] = rel
                if rel['release']['country'] in ('XW', 'US'):
                    alb_i = i
                    if r['release-group']['type'] == 'Album':
                        break
        return (release_res['release-list'][alb_i]['artist-credit'][0]['artist']['name'],
                release_res['release-list'][alb_i]['title'],
                [(re.sub(r'[\/:*?"><|]','',c['recording']['title']), int(c['recording'].get('length', 0))) for c in albums[alb_i]['release']['medium-list'][0]['track-list']])
    except IndexError:
        # No hits.
        print("Err A")
        pass
    except KeyError:
        # No hits.
        print("Err B")
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
            tracklist = get_track_list(m)
            print(tracklist)
            if tracklist[2] is not None:
                for n,t in tracklist[2]:
                    seconds=(t/1000)%60
                    minutes=(t/(1000*60))%60
                    hours=(t/(1000*60*60))%24
                    print("%s %02d:%02d" % (n, minutes,seconds))
            time.sleep(15)
