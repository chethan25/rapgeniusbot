# -*- coding: utf-8 -*-
"""
Module to stream reddit comments and reply with song
lyrics, metadata when triggered.
"""
import os
import re
import time
import json
import shutil
import logging

import praw
import lyricsgenius
import praw.exceptions
import prawcore.exceptions

import database as db


def main():
    """
    The main function.

    Configures praw and authorizes genius api, gets latest comments from the
    subreddits, filters out comments that have already been replied. Parses
    comment for artist name, song name, option and the specified options
    function is called.
    """
    # Configuring PRAW.
    reddit = praw.Reddit(
        'rapgeniusbot', user_agent='rapgeniusbot v1.0 by /u/killuminati07')

    # Authorize access to the genius api using client access token.
    genius = lyricsgenius.Genius(os.environ.get('GENIUS_TOKEN'))

    # Configure logger
    logging.basicConfig(filename='bot.log', filemode='w',
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    logging.info('logging in')

    # Get the latest comments from the subreddit.
    for comment in reddit.subreddit('lukerken').stream.comments(skip_existing=True):
        # Check if bot has already replied to the comment.
        if not is_added(comment):
            # Check if bots username is present in the comment.
            if str(reddit.user.me()) in comment.body:
                # Parse comments for song name, artist name and option.
                comment_list = comment.body.split(',')
                try:
                    artist_name = comment_list[1].strip().lower()
                    song_name = comment_list[2].strip().lower()
                    option = comment_list[3].strip().lower()
                    option_list = ['lyrics', 'short info',
                                   'long info', 'relations']
                    if option not in option_list:
                        logging.info('Invalid Option')
                        print('Invalid Option')
                        continue
                except IndexError:
                    logging.info('Invalid comment format')
                    print('Invalid comment format')
                    continue

                new_artist_name = artist_name.replace(
                    " ", "").replace("'", "").replace("-", "").replace('"', "")
                new_song_name = song_name.replace(" ", "").replace(
                    "'", "").replace("(", "").replace(")", "").replace("&", "")

                # Construct the json filename.
                filename = f"lyrics_{new_artist_name}_{new_song_name}.json"

                # Find the absolute path to json file.
                dest_path = os.path.abspath(f"lyrics/{filename}")

                # Check if the json file is present in the lyrics directory.
                if os.path.isfile(dest_path):
                    if option == 'lyrics':
                        post_lyrics(dest_path, comment)
                    elif option == 'short info':
                        post_short_song_info(dest_path, comment)
                    elif option == 'long info':
                        post_long_song_info(dest_path, comment)
                    elif option == 'relations':
                        post_song_relations(dest_path, comment)
                else:
                    try:
                        # Search Genius.com for the specified song
                        # and save songs json file.
                        genius.search_song(song_name,
                                           artist=artist_name,
                                           get_full_info=True).save_lyrics()
                    except AttributeError:
                        logging.info("Invalid Song Request")
                        print('Invalid Song Request')
                        continue
                    else:
                        for filename in os.listdir('.'):
                            if filename[-4:] == 'json':
                                filename_list = re.split(r'[_]', filename)

                        artist_name = filename_list[1]
                        old_song_name = filename_list[2]
                        song_name = old_song_name[:-5]

                        # Construct the json filename.
                        filename = f"lyrics_{artist_name}_{song_name}.json"

                        # Find the absolute path to json file.
                        dest_path = os.path.abspath(f"lyrics/{filename}")

                        try:
                            # Move json file to lyrics directory.
                            shutil.move(filename, dest_path)
                        except FileNotFoundError:
                            logging.info('Invalid Song Request')
                            print('Invalid Song Request')
                            continue

                        if option == 'lyrics':
                            post_lyrics(dest_path, comment)
                        elif option == 'short info':
                            post_short_song_info(dest_path, comment)
                        elif option == 'long info':
                            post_long_song_info(dest_path, comment)
                        elif option == 'relations':
                            post_song_relations(dest_path, comment)


def post_lyrics(d_path, comment):
    """Parses json file for songs lyrics and replies lyrics to the comment."""
    try:
        with open(d_path) as f:
            data = json.load(f)
            comment.reply(f"**\"{data.get('title').upper()}\"** **LYRICS**\
                    \n\n---\n\n{data.get('lyrics', 'Lyrics Unavailable')}")
            add_entry(comment)
            logging.info('posted')
            print('posted')
    except Exception:
        logging.exception('Exception occurred')


def post_short_song_info(d_path, comment):
    """Parses json file for songs metadata and replies short song info to the comment."""
    try:
        with open(d_path) as f:
            data = json.load(f)

        title = data.get('title', '')

        primary_artist = data['primary_artist']['name']

        featured_artists_list = []
        for artist in data['featured_artists']:
            featured_artists_list.append(artist['name'])
        featured_artists = ", ".join(featured_artists_list)

        try:
            album = data['album']['name']
        except:
            album = ''

        release_date = data['release_date_for_display']
        if release_date is None:
            release_date = ''

        producer_artists_list = []
        for artist in data['producer_artists']:
            producer_artists_list.append(artist['name'])
        producer_artists = ", ".join(producer_artists_list)

        description = data['description']['plain']
        if description == '?':
            description = ''

        comment.reply(
            f"**\"{data.get('title').upper()}\"** **TRACK INFO**\
                \n\n---\n\n**Song** - {title}\
                \n\n**Artist** - {primary_artist}\
                \n\n**Featured Artist(s)** - {featured_artists}\
                \n\n**Album** - {album}\n\n**Release Date** - {release_date}\
                \n\n**Produced by** - {producer_artists}\
                \n\n**Description** - {description}")
        add_entry(comment)
        logging.info('posted')
        print('posted')
    except Exception:
        logging.exception('Exception occurred')


def post_long_song_info(d_path, comment):
    """Parses json file for songs metadata and replies long info to the comment."""
    try:
        with open(d_path) as f:
            data = json.load(f)

        writer_artists_list = []
        wa_list = data.get('writer_artists')
        for wa in wa_list:
            writer_artists_list.append(wa.get('name'))
            writer_artists = ", ".join(writer_artists_list)

        custom_performances_dict = {}
        custom_performances_list = data.get('custom_performances')
        for custom_performance in custom_performances_list:
            artists_list = custom_performance.get('artists')
            for artist in artists_list:
                custom_performances_dict.setdefault(
                    custom_performance.get('label'), []).append(artist.get('name'))

        custom_performance_str = ''
        for key, value in custom_performances_dict.items():
            custom_performance_str += f"**{key}** - {', '.join(value)}" + \
                '\n\n'

        recorded_at = data.get('recording_location')
        if recorded_at is None:
            recorded_at = ""

        comment.reply(
            f"**\"{data.get('title').upper()}\"** **TRACK INFO**\
                \n\n---\n\n**Writer Artists** - {writer_artists}\
                \n\n{custom_performance_str}\n\n**Recorded At** - {recorded_at}")
        add_entry(comment)
        logging.info('posted')
        print('posted')
    except Exception:
        logging.exception('Exception occurred')


def post_song_relations(d_path, comment):
    """Parses json file for song relationships and replies the same to the comment."""
    try:
        with open(d_path) as f:
            data = json.load(f)

        song_relationships_dict = {}
        song_relationships_list = data.get('song_relationships')
        for song_relationship in song_relationships_list:
            song_relationship.get('type')
            song_list = song_relationship.get('songs')
            for song in song_list:
                song_relationships_dict.setdefault(song_relationship.get(
                    'type'), []).append(song.get('full_title'))
        song_relationships_str = ''
        for key, value in song_relationships_dict.items():
            song_relationships_str += \
                f"**{key.title().replace('_', ' ')}** - {', '.join(value)}" + '\n\n'

        comment.reply(
            f"**\"{data.get('title').upper()}\"** **TRACK RELATIONSHPS**\
                \n\n---\n\n{song_relationships_str}")
        add_entry(comment)
        logging.info('posted')
        print('posted')
    except Exception:
        logging.exception('Exception occurred')


def is_added(comment_id):
    """Checks if comment id is present in the database."""
    try:
        comments1 = db.Comments.get(db.Comments.cid == comment_id)
        return True
    except:
        return False


def add_entry(comment_id):
    """Adds comment id to the database if it wasn't already in the database."""
    if not is_added(comment_id):
        logging.info(f"Adding {comment_id}")
        print(f"Adding {comment_id}")
        db.Comments(cid=comment_id).save()


def flush_db():
    """Deletes all comment ids from the database."""
    coms = db.Comments.select()
    for com in coms:
        com.delete_instance()


if __name__ == "__main__":
    while True:
        try:
            main()
        except prawcore.exceptions.RequestException:
            logging.error("Error with the incomplete HTTP request")
            print("Error with the incomplete HTTP request")
        except prawcore.exceptions.ResponseException:
            logging.error("Error with the completed HTTP request")
            print("Error with the completed HTTP request")
        except prawcore.exceptions.OAuthException:
            logging.error("OAuth2 related error with the request")
            print("OAuth2 related error with the request")
        except praw.exceptions.RedditAPIException as exception:
            logging.error(exception)
            print(exception)
        except Exception as err:
            logging.error(err)
            print(err)

        logging.info("Retrying in 5 minutes")
        time.sleep(60 * 5)
