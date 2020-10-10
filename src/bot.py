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
        'rapgeniusbot', user_agent='rapgenius v1.0 by /u/killuminati07')

    # Authorize access to the genius api using client access token.
    genius = lyricsgenius.Genius(os.environ.get('GENIUS_TOKEN'))

    # Configure logger
    logging.basicConfig(filename='bot.log',
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    logging.info('logging in')

    # Get the latest comments from the subreddit.
    for comment in reddit.subreddit('Eminem+Tupac+hiphop101+hiphop+hiphopheads').stream.comments():
        # Check if bot has already replied to the comment.
        if not is_added(comment):
            # Parse comments for song name, artist name and option.
            comment_list = comment.body.split(',')
            # Check if bots username is present in the comment.
            if comment_list[0].strip().lower() == 'geniusbot':
                try:
                    artist_name = comment_list[1].strip().lower()
                    song_name = comment_list[2].strip().lower()
                    option = comment_list[3].strip().lower()
                    option_list = ['lyrics', 'short info',
                                   'long info', 'relations']
                    if option not in option_list:
                        logging.info('Invalid Option')
                        continue

                    lyrics_suboptions = ''
                    try:
                        if option == 'lyrics':
                            lyrics_suboptions = comment_list[4].strip(
                            ).lower().split()
                            suboptions_list = ['intro', 'outro', 'verse1',
                                               'verse2', 'verse3', 'verse4',
                                               'verse5', 'verse6', 'verse7',
                                               'verse8', 'verse9', 'verse10',
                                               'verse11', 'verse12', 'verse13',
                                               'interlude', 'bridge', 'chorus',
                                               'hook', 'pre-chorus', 'break',
                                               'refrain', 'post-chorus', 'collision']
                            flag = False
                            for suboption in lyrics_suboptions:
                                if suboption not in suboptions_list:
                                    logging.info('Invalid Suboption (Section)')
                                    flag = True
                                    break
                            if flag == True:
                                continue

                            beg = ''
                            end = ''
                            if comment_list[5]:
                                bar_suboptions = comment_list[5].split()
                                if bar_suboptions[0]:
                                    beg = bar_suboptions[0]
                                if bar_suboptions[1]:
                                    end = bar_suboptions[1]
                    except IndexError:
                        pass

                except IndexError:
                    logging.info('Invalid comment format')
                    continue

                new_artist_name = artist_name.replace(
                    " ", "").replace("'", "").replace("-", "").replace('"', "").replace("&", "")
                new_song_name = song_name.replace(" ", "").replace(
                    "'", "").replace("(", "").replace(")", "").replace("&", "")

                # Construct the json filename.
                filename = f"lyrics_{new_artist_name}_{new_song_name}.json"

                # Find the absolute path to json file.
                dest_path = os.path.abspath(f"lyrics/{filename}")

                # Check if the json file is present in the lyrics directory.
                if os.path.isfile(dest_path):
                    if option == 'lyrics':
                        if not lyrics_suboptions:
                            post_lyrics(dest_path, comment)
                        else:
                            post_sub_lyrics(dest_path, comment,
                                            lyrics_suboptions, beg, end)
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
                            continue

                        if option == 'lyrics':
                            if not lyrics_suboptions:
                                post_lyrics(dest_path, comment)
                            else:
                                post_sub_lyrics(dest_path, comment,
                                                lyrics_suboptions, beg, end)
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
            time.sleep(10)
    except Exception:
        logging.exception('Exception occurred')


def post_sub_lyrics(d_path, comment, section, beg, end):
    """Parses json file for songs lyrics and replies part of lyrics to the comment."""
    try:
        with open(d_path) as f:
            data = json.load(f)
            lyrics = data.get('lyrics', 'Lyrics Unavailable')
            lyrics_list = lyrics.split('\n\n')

            Intro = ''
            if 'intro' in section:
                for sub_lyrics in lyrics_list:
                    if 'Intro' in sub_lyrics:
                        Intro = sub_lyrics
            Verse_1 = ''
            if 'verse1' in section:
                for sub_lyrics in lyrics_list:
                    if 'Verse 1' in sub_lyrics:
                        Verse_1 = sub_lyrics
                if beg != '':
                    beg = int(beg)
                    if end == '':
                        emp_end_1 = None
                        bars_list = Verse_1.split('\n')
                        Verse_1 = bars_list[beg:emp_end_1]
                        Verse_1 = bars_list[0] + ' ' + '\n\n'.join(Verse_1)
                    else:
                        end = int(end)
                        new_end_1 = end + 1
                        bars_list = Verse_1.split('\n')
                        Verse_1 = bars_list[beg:new_end_1]
                        Verse_1 = bars_list[0] + ' ' + '\n\n'.join(Verse_1)

            Verse_2 = ''
            if 'verse2' in section:
                for sub_lyrics in lyrics_list:
                    if 'Verse 2' in sub_lyrics:
                        Verse_2 = sub_lyrics
                if beg != '':
                    beg = int(beg)
                    if end == '':
                        emp_end_2 = None
                        bars_list = Verse_2.split('\n')
                        Verse_2 = bars_list[beg:emp_end_2]
                        Verse_2 = bars_list[0] + ' ' + '\n\n'.join(Verse_2)
                    else:
                        end = int(end)
                        new_end_2 = end + 1
                        bars_list = Verse_2.split('\n')
                        Verse_2 = bars_list[beg:new_end_2]
                        Verse_2 = bars_list[0] + ' ' + '\n\n'.join(Verse_2)
            Verse_3 = ''
            if 'verse3' in section:
                for sub_lyrics in lyrics_list:
                    if 'Verse 3' in sub_lyrics:
                        Verse_3 = sub_lyrics
                if beg != '':
                    beg = int(beg)
                    if end == '':
                        emp_end_3 = None
                        bars_list = Verse_3.split('\n')
                        Verse_3 = bars_list[beg:emp_end_3]
                        Verse_3 = bars_list[0] + ' ' + '\n\n'.join(Verse_3)
                    else:
                        end = int(end)
                        new_end_3 = end + 1
                        bars_list = Verse_3.split('\n')
                        Verse_3 = bars_list[beg:new_end_3]
                        Verse_3 = bars_list[0] + ' ' + '\n\n'.join(Verse_3)
            Verse_4 = ''
            if 'verse4' in section:
                for sub_lyrics in lyrics_list:
                    if 'Verse 4' in sub_lyrics:
                        Verse_4 = sub_lyrics
                if beg != '':
                    beg = int(beg)
                    if end == '':
                        emp_end_4 = None
                        bars_list = Verse_4.split('\n')
                        Verse_4 = bars_list[beg:emp_end_4]
                        Verse_4 = bars_list[0] + ' ' + '\n\n'.join(Verse_4)
                    else:
                        end = int(end)
                        new_end_4 = end + 1
                        bars_list = Verse_4.split('\n')
                        Verse_4 = bars_list[beg:new_end_4]
                        Verse_4 = bars_list[0] + ' ' + '\n\n'.join(Verse_4)
            Verse_5 = ''
            if 'verse5' in section:
                for sub_lyrics in lyrics_list:
                    if 'Verse 5' in sub_lyrics:
                        Verse_5 = sub_lyrics
                if beg != '':
                    beg = int(beg)
                    if end == '':
                        emp_end_5 = None
                        bars_list = Verse_5.split('\n')
                        Verse_5 = bars_list[beg:emp_end_5]
                        Verse_5 = bars_list[0] + ' ' + '\n\n'.join(Verse_5)
                    else:
                        end = int(end)
                        new_end_5 = end + 1
                        bars_list = Verse_5.split('\n')
                        Verse_5 = bars_list[beg:new_end_5]
                        Verse_5 = bars_list[0] + ' ' + '\n\n'.join(Verse_5)
            Verse_6 = ''
            if 'verse6' in section:
                for sub_lyrics in lyrics_list:
                    if 'Verse 6' in sub_lyrics:
                        Verse_6 = sub_lyrics
                if beg != '':
                    beg = int(beg)
                    if end == '':
                        emp_end_6 = None
                        bars_list = Verse_6.split('\n')
                        Verse_6 = bars_list[beg:emp_end_6]
                        Verse_6 = bars_list[0] + ' ' + '\n\n'.join(Verse_6)
                    else:
                        end = int(end)
                        new_end_6 = end + 1
                        bars_list = Verse_6.split('\n')
                        Verse_6 = bars_list[beg:new_end_6]
                        Verse_6 = bars_list[0] + ' ' + '\n\n'.join(Verse_6)
            Verse_7 = ''
            if 'verse7' in section:
                for sub_lyrics in lyrics_list:
                    if 'Verse 7' in sub_lyrics:
                        Verse_7 = sub_lyrics
                if beg != '':
                    beg = int(beg)
                    if end == '':
                        emp_end_7 = None
                        bars_list = Verse_7.split('\n')
                        Verse_7 = bars_list[beg:emp_end_7]
                        Verse_7 = bars_list[0] + ' ' + '\n\n'.join(Verse_7)
                    else:
                        end = int(end)
                        new_end_7 = end + 1
                        bars_list = Verse_7.split('\n')
                        Verse_7 = bars_list[beg:new_end_7]
                        Verse_7 = bars_list[0] + ' ' + '\n\n'.join(Verse_7)
            Verse_8 = ''
            if 'verse8' in section:
                for sub_lyrics in lyrics_list:
                    if 'Verse 8' in sub_lyrics:
                        Verse_8 = sub_lyrics
                if beg != '':
                    beg = int(beg)
                    if end == '':
                        emp_end_8 = None
                        bars_list = Verse_8.split('\n')
                        Verse_8 = bars_list[beg:emp_end_8]
                        Verse_8 = bars_list[0] + ' ' + '\n\n'.join(Verse_8)
                    else:
                        end = int(end)
                        new_end_8 = end + 1
                        bars_list = Verse_8.split('\n')
                        Verse_8 = bars_list[beg:new_end_8]
                        Verse_8 = bars_list[0] + ' ' + '\n\n'.join(Verse_8)
            Verse_9 = ''
            if 'verse9' in section:
                for sub_lyrics in lyrics_list:
                    if 'Verse 9' in sub_lyrics:
                        Verse_9 = sub_lyrics
                if beg != '':
                    beg = int(beg)
                    if end == '':
                        emp_end_9 = None
                        bars_list = Verse_9.split('\n')
                        Verse_9 = bars_list[beg:emp_end_9]
                        Verse_9 = bars_list[0] + ' ' + '\n\n'.join(Verse_9)
                    else:
                        end = int(end)
                        new_end_9 = end + 1
                        bars_list = Verse_9.split('\n')
                        Verse_9 = bars_list[beg:new_end_9]
                        Verse_9 = bars_list[0] + ' ' + '\n\n'.join(Verse_9)
            Verse_10 = ''
            if 'verse10' in section:
                for sub_lyrics in lyrics_list:
                    if 'Verse 10' in sub_lyrics:
                        Verse_10 = sub_lyrics
                if beg != '':
                    beg = int(beg)
                    if end == '':
                        emp_end_10 = None
                        bars_list = Verse_10.split('\n')
                        Verse_10 = bars_list[beg:emp_end_10]
                        Verse_10 = bars_list[0] + ' ' + '\n\n'.join(Verse_10)
                    else:
                        end = int(end)
                        new_end_10 = end + 1
                        bars_list = Verse_10.split('\n')
                        Verse_10 = bars_list[beg:new_end_10]
                        Verse_10 = bars_list[0] + ' ' + '\n\n'.join(Verse_10)
            Verse_11 = ''
            if 'verse11' in section:
                for sub_lyrics in lyrics_list:
                    if 'Verse 11' in sub_lyrics:
                        Verse_11 = sub_lyrics
                if beg != '':
                    beg = int(beg)
                    if end == '':
                        emp_end_11 = None
                        bars_list = Verse_11.split('\n')
                        Verse_11 = bars_list[beg:emp_end_11]
                        Verse_11 = bars_list[0] + ' ' + '\n\n'.join(Verse_11)
                    else:
                        end = int(end)
                        new_end_11 = end + 1
                        bars_list = Verse_11.split('\n')
                        Verse_11 = bars_list[beg:new_end_11]
                        Verse_11 = bars_list[0] + ' ' + '\n\n'.join(Verse_11)
            Verse_12 = ''
            if 'verse12' in section:
                for sub_lyrics in lyrics_list:
                    if 'Verse 12' in sub_lyrics:
                        Verse_12 = sub_lyrics
                if beg != '':
                    beg = int(beg)
                    if end == '':
                        emp_end_12 = None
                        bars_list = Verse_12.split('\n')
                        Verse_12 = bars_list[beg:emp_end_12]
                        Verse_12 = bars_list[0] + ' ' + '\n\n'.join(Verse_12)
                    else:
                        end = int(end)
                        new_end_12 = end + 1
                        bars_list = Verse_12.split('\n')
                        Verse_12 = bars_list[beg:new_end_12]
                        Verse_12 = bars_list[0] + ' ' + '\n\n'.join(Verse_12)
            Verse_13 = ''
            if 'verse13' in section:
                for sub_lyrics in lyrics_list:
                    if 'Verse 13' in sub_lyrics:
                        Verse_13 = sub_lyrics
                if beg != '':
                    beg = int(beg)
                    if end == '':
                        emp_end_13 = None
                        bars_list = Verse_13.split('\n')
                        Verse_13 = bars_list[beg:emp_end_13]
                        Verse_13 = bars_list[0] + ' ' + '\n\n'.join(Verse_13)
                    else:
                        end = int(end)
                        new_end_13 = end + 1
                        bars_list = Verse_13.split('\n')
                        Verse_13 = bars_list[beg:new_end_13]
                        Verse_13 = bars_list[0] + ' ' + '\n\n'.join(Verse_13)
            Pre_Chorus = ''
            if 'pre-chorus' in section:
                for sub_lyrics in lyrics_list:
                    if 'Pre-Chorus' in sub_lyrics:
                        Pre_Chorus = sub_lyrics
                        break
            Chorus = ''
            if 'chorus' in section:
                for sub_lyrics in lyrics_list:
                    if 'Chorus' in sub_lyrics:
                        Chorus = sub_lyrics
                        break
            Post_Chorus = ''
            if 'post-chorus' in section:
                for sub_lyrics in lyrics_list:
                    if 'Post-Chorus' in sub_lyrics:
                        Post_Chorus = sub_lyrics
                        break
            Refrain = ''
            if 'refrain' in section:
                for sub_lyrics in lyrics_list:
                    if 'Refrain' in sub_lyrics:
                        Refrain = sub_lyrics
                        break
            Collision = ''
            if 'collision' in section:
                for sub_lyrics in lyrics_list:
                    if 'Collision' in sub_lyrics:
                        Collision = sub_lyrics
                        break
            Hook = ''
            if 'hook' in section:
                for sub_lyrics in lyrics_list:
                    if 'Hook' in sub_lyrics:
                        Hook = sub_lyrics
                        break
            Interlude = ''
            if 'interlude' in section:
                for sub_lyrics in lyrics_list:
                    if 'Interlude' in sub_lyrics:
                        Interlude = sub_lyrics
                        break
            Bridge = ''
            if 'bridge' in section:
                for sub_lyrics in lyrics_list:
                    if 'Bridge' in sub_lyrics:
                        Bridge = sub_lyrics
                        break
            Break = ''
            if 'break' in section:
                for sub_lyrics in lyrics_list:
                    if 'Break' in sub_lyrics:
                        Break = sub_lyrics
                        break
            Outro = ''
            if 'outro' in section:
                for sub_lyrics in lyrics_list:
                    if 'Outro' in sub_lyrics:
                        Outro = sub_lyrics

            comment.reply(f"**\"{data.get('title').upper()}\"** **LYRICS**\
                \n\n---\n\n{Intro}\n\n{Verse_1}\n\n{Pre_Chorus}\n\n{Chorus}\
                \n\n{Post_Chorus}\n\n{Hook}\n\n{Refrain}\n\n{Collision}\
                \n\n{Bridge}\
                \n\n{Break}\n\n{Interlude}\n\n{Verse_2}\n\n{Verse_3}\
                \n\n{Verse_4}\n\n{Verse_5}\n\n{Verse_6}\n\n{Verse_7}\
                \n\n{Verse_8}\n\n{Verse_9}\n\n{Verse_10}\n\n{Verse_11}\
                \n\n{Verse_12}\n\n{Verse_13}\n\n{Outro}")

            add_entry(comment)
            logging.info('posted')
            time.sleep(10)
    except ValueError:
        logging.info('Invalid Suboption (Bar)')
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
        time.sleep(10)
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
        time.sleep(10)
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
        time.sleep(10)
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
        except prawcore.exceptions.ResponseException:
            logging.error("Error with the completed HTTP request")
        except prawcore.exceptions.OAuthException:
            logging.error("OAuth2 related error with the request")
        except prawcore.exceptions.PrawcoreException as prawcoreerr:
            logging.error(prawcoreerr)
        except praw.exceptions.RedditAPIException as exception:
            logging.error(exception)
        except praw.exceptions.ClientException as clienterr:
            logging.error(clienterr)
        except praw.exceptions.PRAWException as prawerr:
            logging.error(prawerr)
        except Exception as err:
            logging.error(err)

        logging.info("Retrying in 5 minutes")
        time.sleep(60 * 5)
