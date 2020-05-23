
import lyricsgenius
import praw
import shutil
import time
import json
import os
import database as d
from pprint import pprint


def main():
    reddit = praw.Reddit(
        "rapgeniusbot", user_agent="rapgeniusbot v1.0 by /u/killuminati07")

    genius_token = os.environ.get('GENIUS_TOKEN')

    genius = lyricsgenius.Genius(genius_token)

    me = str(reddit.user.me())

    subreddit = reddit.subreddit("lukerken")
    for comment in subreddit.stream.comments():
        if not is_added(comment):
            if me in comment.body:
                comment_list = comment.body.split(',')
                artist_name = comment_list[1].strip().lower()
                song_name = comment_list[2].strip().lower()
                option = comment_list[3].strip().lower()

                new_artist_name = artist_name.replace(" ", "")
                new_song_name = song_name.replace(" ", "")

                filename = f"lyrics_{new_artist_name}_{new_song_name}.json"

                dest = os.path.abspath(f"lyrics/{filename}")

                if os.path.isfile(dest):
                    with open(dest) as f:
                        data = json.load(f)
                        comment.reply(data['lyrics'])
                        add_entry(comment)
                        print('posted')
                        break

                else:
                    genius.search_song(song_name,
                                       artist=artist_name, get_full_info=True).save_lyrics()

                    shutil.move(filename, dest)

                    with open(dest) as f:
                        data = json.load(f)
                        comment.reply(data['lyrics'])
                        add_entry(comment)
                        print('posted')
                        break


def is_added(comment_id):
    try:
        comments1 = d.Comments.get(d.Comments.cid == comment_id)
        return True
    except:
        return False


def add_entry(comment_id):
    if not is_added(comment_id):
        print(f"Adding {comment_id}")
        d.Comments(cid=comment_id).save()


def flush_db():
    coms = d.Comments.select()
    for com in coms:
        com.delete_instance()


if __name__ == "__main__":
    main()
