# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import itertools
import time

import aiopg.sa as asa
import asyncio
import datetime
import logging
import sqlalchemy as sa
from abot.dubtrack import DubtrackWS

from mosbot.db import BotConfig, UserAction, Action, Origin, get_engine
from mosbot.query import get_dub_action, get_playback, get_track, get_user, load_bot_data, \
    query_simplified_user_actions, save_bot_data, save_playback, save_track, save_user, save_user_action, \
    execute_and_first
from mosbot.util import retries

logger = logging.getLogger(__name__)


async def save_history_songs():
    """Make sure we haven't lost a single playback.

    Gets in charge of going to dubtrack up to the previous saved history moment, and fills the database.

    It makes parallel queries and everything to maximise throughput.

    Saves previous to first unsuccessful storage, or last successful. This is, it doesn't save 5 if 4 failed."""
    last_song = await load_bot_data(BotConfig.last_saved_history)
    if not last_song:
        logger.error('There is no bot data regarding last saved playback')
        return

    history_songs = await dubtrack_songs_since_ts(last_song)

    await persist_history(history_songs)


async def persist_history(history_songs):
    engine = await get_engine()
    songs = []
    played = 0
    tasks = {}
    # Logic here: [ ][ ][s][s][ ][s][ ]
    # Groups:     \-/\-/\-------/\----/
    logger.info('Saving data chunks in database')
    for played, song in sorted(history_songs.items()):
        songs.append(song)
        if not song['skipped']:
            tasks[played] = asyncio.ensure_future(
                save_history_chunk(songs=songs, conn=await engine.acquire())
            )
            songs = []
    if songs:
        tasks[played] = asyncio.ensure_future(
            save_history_chunk(songs=songs, conn=await engine.acquire())
        )

    logger.debug('Waiting for data to be saved')
    await asyncio.wait(tasks.values())
    last_successful_song = None
    for last_song, task in sorted(tasks.items()):
        if task.exception():
            logger.error(f'Saving task failed at {last_song}')
            break
        last_successful_song = last_song
    if last_successful_song is not None:
        logger.info(f'Successfully saved until {last_successful_song}')
        await save_bot_data(BotConfig.last_saved_history, last_successful_song)
    return last_successful_song


async def dubtrack_songs_since_ts(last_song):
    dws = DubtrackWS()
    await dws.initialize()
    history_songs = {}
    found_last_song = False
    played = time.time()
    logger.info(f'Starting page retrieval until {last_song}')
    for page in itertools.count(1):  # pragma: no branch
        logger.debug(f'Retrieving page {page}, {len(history_songs)} songs, looking for {last_song} now at {played}')
        if found_last_song:
            break  # We want to do whole pages just in case...
        songs = await dws.get_history(page)
        for song in songs:
            played = song['played'] / 1000
            if played <= last_song:
                found_last_song = True
            history_songs[played] = song
    return history_songs


@retries(final_message='Failed to commit song-chunk: [{songs}]')
async def save_history_chunk(*, songs, conn: asa.SAConnection):
    """In charge of saving a chunck of continuous songs"""
    # {'__v': 0,
    #  '_id': '583bf4a9d9abb248008a698a',
    #  '_song': {
    #      '__v': 0,
    #      '_id': '5637c2cf7d7d3f2200b05659',
    #      'created': '2015-11-02T20:08:47.588Z',
    #      'fkid': 'eOwwLhMPRUE',
    #      'images': {
    #          'thumbnail': 'https://i.ytimg.com/vi/eOwwLhMPRUE/hqdefault.jpg',
    #          'youtube': {
    #              'default': {
    #                  'height': 90,
    #                  'url': 'https://i.ytimg.com/vi/eOwwLhMPRUE/default.jpg',
    #                  'width': 120
    #              },
    #              'high': {
    #                  'height': 360,
    #                  'url': 'https://i.ytimg.com/vi/eOwwLhMPRUE/hqdefault.jpg',
    #                  'width': 480
    #              },
    #              'maxres': {
    #                  'height': 720,
    #                  'url': 'https://i.ytimg.com/vi/eOwwLhMPRUE/maxresdefault.jpg',
    #                  'width': 1280
    #              },
    #              'medium': {
    #                  'height': 180,
    #                  'url': 'https://i.ytimg.com/vi/eOwwLhMPRUE/mqdefault.jpg',
    #                  'width': 320
    #              },
    #              'standard': {
    #                  'height': 480,
    #                  'url': 'https://i.ytimg.com/vi/eOwwLhMPRUE/sddefault.jpg',
    #                  'width': 640
    #              }
    #          }
    #      },
    #      'name': 'Craig Armstrong - Dream Violin',
    #      'songLength': 204000,
    #      'type': 'youtube'
    #  },
    #  '_user': {
    #      '__v': 0,
    #      '_id': '57595c7a16c34f3d00b5ea8d',
    #      'created': 1465474170519,
    #      'dubs': 0,
    #      'profileImage': {
    #          'bytes': 72094,
    #          'etag': 'fdcdd43edcaaec225a6dcd9701e62be1',
    #          'format': 'png',
    #          'height': 500,
    #          'public_id': 'user/57595c7a16c34f3d00b5ea8d',
    #          'resource_type': 'image',
    #          'secure_url':
    #              'https://res.cloudinary.com/hhberclba/image/upload/v1465474392/user'
    #              '/57595c7a16c34f3d00b5ea8d.png',
    #          'tags': [],
    #          'type': 'upload',
    #          'url': 'http://res.cloudinary.com/hhberclba/image/upload/v1465474392/user'
    #                 '/57595c7a16c34f3d00b5ea8d.png',
    #          'version': 1465474392,
    #          'width': 500
    #      },
    #      'roleid': 1,
    #      'status': 1,
    #      'username': 'masterofsoundtrack'
    #  },
    #  'created': 1480324264803,
    #  'downdubs': 0,
    #  'isActive': True,
    #  'isPlayed': True,
    #  'order': 243,
    #  'played': 1480464322618,
    #  'roomid': '561b1e59c90a9c0e00df610b',
    #  'skipped': False,
    #  'songLength': 204000,
    #  'songid': '5637c2cf7d7d3f2200b05659',
    #  'updubs': 1,
    #  'userid': '57595c7a16c34f3d00b5ea8d'
    #  }
    song_played = None
    previous_song, previous_playback_id = {}, None
    async with conn.begin():
        for song in songs:
            # Generate Action skip for the previous Playback entry
            song_played = datetime.datetime.utcfromtimestamp(song['played'] / 1000)
            if previous_song.get('skipped'):
                await history_import_skip_action(
                    previous_playback_id=previous_playback_id,
                    song_played=song_played,
                    conn=conn,
                )

            # Query or create the User for the Playback entry
            user = await get_or_create_user(song=song, conn=conn)
            user_id = user['id']

            # Query or create the Track entry for this Playback entry
            track = await get_or_create_track(song=song, conn=conn)
            track_id = track['id']

            # Query or create the Playback entry
            playback_id = await get_or_create_playback(
                song_played=song_played,
                track_id=track_id,
                user_id=user_id,
                conn=conn
            )

            # Query or create the UserAction<upvote> UserAction<downvote> entries
            await update_user_actions(
                song=song,
                song_played=song_played,
                playback_id=playback_id,
                conn=conn,
            )

            previous_song, previous_playback_id = song, playback_id
        logger.info(f'Saved songs up to {song_played}')
    await conn.close()


async def update_user_actions(conn, playback_id, song, song_played):
    user_actions = await query_simplified_user_actions(playback_id, conn=conn)
    for dubkey in ('updubs', 'downdubs'):
        # if no updubs/downdubs
        votes = song[dubkey]
        action = get_dub_action(dubkey)

        if not votes:
            continue

        action_user_actions = [a for a in user_actions if a['action'] == action]
        action_count = len(action_user_actions)
        if action_count == votes:
            continue
        if action_count > votes:
            logger.error(f'Playback {playback_id} votes: real {dubkey} > {action_count} db')
            continue
        # There are less than they should
        for _ in range(votes - action_count):
            user_action = await save_user_action(user_action_dict={
                'ts': song_played,
                'playback_id': playback_id,
                'action': action,
            }, conn=conn)
            if not user_action:
                logger.error(
                    f'\tError UserAction<vote>#{user_action.get("id")} {playback_id}('
                    f'{song_played})')
                raise ValueError(
                    f'\tCollision UserAction<skip>#{user_action.get("id")}'
                    f'{playback_id}({song_played})')


async def get_or_create_playback(conn, song_played, track_id, user_id):
    entry = {
        'track_id': track_id,
        'user_id': user_id,
        'start': song_played,
    }
    playback = await get_playback(playback_dict=entry, conn=conn)
    if not playback:
        playback = await save_playback(playback_dict=entry, conn=conn)
        if not playback:
            logger.error(f'Error Playback#{playback.get("id")} '
                         f'track:{track_id} user_id:{user_id} '
                         f'start:{song_played}')
            raise ValueError(f'Error generating Playback track:{track_id} user_id:{user_id} start:{song_played}')
    playback_id = playback['id']
    return playback_id


async def get_or_create_track(conn, song):
    origin = getattr(Origin, song['_song']['type'])
    length = song['_song']['songLength']
    name = song['_song']['name']
    fkid = song['_song']['fkid']
    entry = {
        'length': length / 1000,
        'name': name,
        'origin': origin,
        'extid': fkid,
    }
    track = await get_track(track_dict=entry, conn=conn)
    if not track:
        track = await save_track(track_dict=entry, conn=conn)
        if not track:
            logger.error(f'Error Track#{track.get("id")} {origin}#{fkid} by {name}')
            raise ValueError(f'Error generating Track {origin}#{fkid} for {name}')
    return track


async def get_or_create_user(conn, song):
    user_dict = {
        'dtid': song['userid'],
        'username': song['_user']['username'],
    }
    user = await get_user(user_dict=user_dict, conn=conn)
    if not user:
        user = await save_user(user_dict=user_dict, conn=conn)
        if not user:
            raise ValueError('Impossible to create/save the user')
    return user


async def history_import_skip_action(conn, previous_playback_id, song_played):
    query = sa.select([UserAction.c.id]) \
        .where(UserAction.c.action == Action.skip) \
        .where(UserAction.c.playback_id == previous_playback_id)
    user_action = await execute_and_first(query=query, conn=conn)
    if not user_action:
        user_action = await save_user_action(user_action_dict={
            'ts': song_played,
            'playback_id': previous_playback_id,
            'action': Action.skip,
        }, conn=conn)
        if not user_action:
            logger.error(
                f'Error UserAction<skip> {previous_playback_id}({song_played})')
            raise ValueError(
                f'\tCollision UserAction<skip> {previous_playback_id}({song_played})')
