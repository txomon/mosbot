# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

"""To have a clean architecture, here are modeled operations over the db file. This file should not import anything
else than db and config if any.

Queries to retrieve, insert or update data should be written here.
"""

import logging
from typing import List, Optional

import sqlalchemy as sa
import sqlalchemy.sql.functions as saf
from asyncio_extras import async_contextmanager
from sqlalchemy.dialects import postgresql as psa

from mosbot import db
from mosbot.db import Action, Origin, Playback, Track, User, UserAction, get_engine

logger = logging.getLogger(__name__)


@async_contextmanager
async def ensure_connection(conn):
    """
    Makes sure that the connection is active. Will be replaced in the future by something attached to an
    asyncio.Task scope, but for now let's just ignore it. The argument is the connection to the database, so
    the connection should be created when we are planning to access the database.

    Unless there is a usecase that keeps the connection open for a long time unnactively, you can just use
    this function at the usecase top function and pass the conn object down. Check existing code for examples
    """
    provided_connection = bool(conn)
    if not provided_connection:
        conn = await (await get_engine()).acquire()
    try:
        yield conn
    finally:
        if not provided_connection:
            await conn.close()


async def execute_and_first(*, query, conn=None):
    async with ensure_connection(conn) as conn:
        result_proxy = await conn.execute(query)
        if result_proxy.closed:
            raise ValueError('ResultProxy closed!?')  # TODO: DEBUG this
        data = await result_proxy.first()
        if not data:
            return {}
        return dict(data)


async def get_user(*, user_dict: dict, conn=None) -> Optional[dict]:
    """
    Retrieves a user by id, or dtid or username. id is preferred

    :param dict user_dict: Keys to define the get(), names as in the table columns
    :param conn: A connection if any open
    :return: The dict filled up with information or None
    """
    assert user_dict

    sq = sa.select([User])
    if 'id' in user_dict:
        sq = sq.where(User.c.id == user_dict['id'])
    else:
        if 'dtid' in user_dict:
            sq = sq.where(User.c.dtid == user_dict['dtid'])
        elif 'username' in user_dict:
            sq = sq.where(User.c.username == user_dict['username'])
        else:
            raise ValueError(f'Not enough parameters in select spec {user_dict}')

    return await execute_and_first(query=sq, conn=conn)


async def save_user(*, user_dict: dict, conn=None) -> dict:
    """
    Saves user, makes sure that you provide at least either username or dtid,

    :param dict user_dict: Keys to save in the database
    :param conn: A connection if any open
    :return: None if it failed to insert/update the user, or the user saved
    """
    assert 'username' in user_dict or 'dtid' in user_dict
    assert isinstance(user_dict.get('dtid', ''), str)
    assert isinstance(user_dict.get('username', ''), str)
    query = psa.insert(User) \
        .values(user_dict) \
        .returning(User) \
        .on_conflict_do_update(
        index_elements=[User.c.dtid],
        set_=user_dict
    )
    return await execute_and_first(query=query, conn=conn)


async def get_or_save_user(*, user_dict: dict, conn=None) -> dict:
    user = await get_user(user_dict=user_dict, conn=conn)
    if user:
        return user
    user = await save_user(user_dict=user_dict, conn=conn)
    if user:
        return user
    logger.error(f'Failed to save user {user_dict}')
    raise ValueError('Impossible to save the user')


async def get_track(*, track_dict: dict, conn=None) -> Optional[dict]:
    """
    Get a given track, need to either have the id or the extid (if possible with origin

    :param dict track_dict: Keys as in the table columns
    :param conn: A connection if any open
    :return: None or the track
    """
    assert 'id' in track_dict or 'extid' in track_dict
    query = sa.select([Track])

    if 'id' in track_dict:
        query = query.where(Track.c.id == track_dict['id'])
    else:
        query = query.where(Track.c.extid == track_dict['extid'])
        if 'origin' in track_dict:
            query = query.where(Track.c.origin == track_dict['origin'])

    return await execute_and_first(query=query, conn=conn)


async def save_track(*, track_dict: dict, conn=None) -> Optional[dict]:
    """
    Saves a track, updating whatever fields are given in track_dict

    :param dict track_dict: Keys as in the table columns
    :param conn: A connection if any open
    :return: None if it failed, the updated track if not
    """
    assert track_dict
    assert isinstance(track_dict.get('length'), int)
    assert isinstance(track_dict.get('origin'), (str, Origin))
    assert isinstance(track_dict.get('extid'), str)
    assert isinstance(track_dict.get('name'), str)
    query = psa.insert(Track) \
        .values(track_dict) \
        .returning(Track) \
        .on_conflict_do_update(
        index_elements=[Track.c.extid, Track.c.origin],
        set_=track_dict
    )
    return await execute_and_first(query=query, conn=conn)


async def get_or_save_track(*, track_dict: dict, conn=None) -> dict:
    track = await get_track(track_dict=track_dict, conn=conn)
    if track:
        return track
    track = await save_track(track_dict=track_dict, conn=conn)
    if track:
        return track
    logger.error(f'Failed to save track {track_dict}')
    raise ValueError('Impossible to save the track')


async def get_playback(*, playback_dict: dict, conn=None) -> Optional[dict]:
    """Retrieves a playback, given the id or the start time. Preferably id.

    This is not a query complex query, but just a way to get something you know it exists.

    :param dict playback_dict: Keys as in the table columns
    :param conn: A connection if any open
    :return: None if it doesn't exist, else the record
    """
    query = sa.select([Playback])

    if 'id' in playback_dict:
        query = query.where(Playback.c.id == playback_dict['id'])
    elif 'start' in playback_dict:
        query = query.where(Playback.c.start == playback_dict['start'])
    else:
        raise ValueError(f'Need either ID or start for getting a playback: {playback_dict}')

    return await execute_and_first(query=query, conn=conn)


async def save_playback(*, playback_dict: dict, conn=None) -> Optional[dict]:
    """Save playback instance, it can also update, and must have track_id, start and user_id.

    :param dict playback_dict: Keys as in the table columns, start is datetime, remember
    :param conn: A connection if any open
    :return: None if it failed to save, else the saved record
    """
    assert {'track_id', 'start', 'user_id'} <= set(playback_dict.keys())
    query = psa.insert(Playback) \
        .values(playback_dict) \
        .returning(Playback) \
        .on_conflict_do_update(
        index_elements=[Playback.c.start],
        set_=playback_dict
    )
    return await execute_and_first(query=query, conn=conn)


async def get_or_save_playback(*, playback_dict: dict, conn=None) -> dict:
    playback = await get_playback(playback_dict=playback_dict, conn=conn)
    if playback:
        return playback
    playback = await save_playback(playback_dict=playback_dict, conn=conn)
    if playback:
        return playback
    logger.error(f'Failed to save playback {playback_dict}')
    raise ValueError('Impossible to save the playback')


async def get_user_action(*, user_action_dict: dict, conn=None) -> Optional[dict]:
    """Get an specific user action, not querying (like multiple entries), so you need to provide the id

    :param dict user_action_dict: Key use is id, if missing it will fail
    :param conn: A connection if any open
    :return: None if it doesn't exist, else the record
    """
    query = sa.select([UserAction])

    if 'id' in user_action_dict:
        query = query.where(UserAction.c.id == user_action_dict['id'])
    else:
        raise ValueError(f'Need ID for getting a user action: {user_action_dict}')

    return await execute_and_first(query=query, conn=conn)


async def save_user_action(*, user_action_dict: dict, conn=None) -> Optional[dict]:
    """Save/Update a user action.

    :param dict user_action_dict: Keys as in table columns in the database
    :param conn: A connection if any open
    :return: None if not saved, else the saved record
    """
    assert 'playback_id' in user_action_dict
    query = psa.insert(UserAction) \
        .values(user_action_dict) \
        .returning(UserAction) \
        .on_conflict_do_update(
        index_elements=[UserAction.c.id],
        set_=user_action_dict
    )
    return await execute_and_first(query=query, conn=conn)


async def save_bot_data(key, value, *, conn=None):
    """Save some random data in the database. Accepts a json as value

    :param str key: A key of the ones specified (is not checked, up to you)
    :param value: Any json serializable value, for now not datetime, be careful
    :param conn: A connection if any open
    :return: Always None
    """
    entry = {
        'key': key,
        'value': value
    }
    query = psa.insert(db.BotData) \
        .values(entry) \
        .returning(db.BotData) \
        .on_conflict_do_update(
        index_elements=[db.BotData.c.key],
        set_=entry
    )
    res = await execute_and_first(query=query, conn=conn)
    return res.get('value')


async def load_bot_data(key, *, conn=None):
    """Retrieve a data value

    :param str key: A value in the accepted keys (if you want)
    :param conn: A connection if any open
    :return:
    """
    query = sa.select([db.BotData.c.value]).where(db.BotData.c.key == key)
    res = await execute_and_first(query=query, conn=conn)
    return res.get('value')


async def get_last_playback(*, conn=None) -> dict:
    """This makes a query looking for the most recent playback in the database. It cannot assure it's still playing
    though

    :param conn: A connection if any open
    :return: The last recorded playback
    """
    query = sa.select([db.Playback]) \
        .order_by(sa.desc(db.Playback.c.start)) \
        .limit(1)
    return await execute_and_first(query=query, conn=conn)


# TODO: should be optional
async def get_user_user_actions(user_id, *, conn=None) -> List[dict]:
    """Get the user actions for a given user, no more filters than that

    :param str user_id: User id for who we want to retrieve the records for
    :param conn: A connection if any open
    :return: List of user_action items
    """
    query = sa.select([db.UserAction]) \
        .where(UserAction.c.user_id == user_id)
    result = []
    async with ensure_connection(conn) as conn:
        async for user_action in await conn.execute(query):
            result.append(dict(user_action))
        return result


# TODO: should be optional
async def get_user_dub_user_actions(user_id, *, conn=None) -> List[dict]:
    """Get the user dubs (upvote/downvote) only, not specific to a given playback

    :param str user_id: User id for who we want to retrieve the records for
    :param conn: A connection if any open
    :return: List of records
    """
    query = sa.select([db.UserAction]) \
        .where(UserAction.c.user_id == user_id) \
        .where(UserAction.c.action in [Action.upvote, Action.downvote])
    async with ensure_connection(conn) as conn:
        result = []
        async for user_action in await conn.execute(query):
            result.append(dict(user_action))
        return result


def get_dub_action(dub):
    """Transform a name received by the api into an internal action. Shouldn't really be here but it's the best place

    Skip is not supported because it's never referred as an skip by itself

    :param str dub: As the dubtrack API refers to this
    :return: :ref:`Action.upvote` or :ref:`Action.downvote`.
    """
    upvote = {'upvote', 'updub', 'updubs', }
    downvote = {'downvote', 'downdub', 'downdubs', }
    if dub in upvote:
        return Action.upvote
    elif dub in downvote:
        return Action.downvote
    else:
        logger.error(f'Tried to convert {dub} into Action')
        raise ValueError(f'Tried to convert {dub} into Action')


def get_opposite_dub_action(dub):
    """Transform a name received by the API into the opposite. Only works for up/down votes

    :param str dub: Dubtrack api name
    :return: :ref:`Action.downvote` or :ref:`Action.upvote`
    """
    upvote = {'upvote', 'updub', 'updubs', }
    downvote = {'downvote', 'downdub', 'downdubs', }
    if dub in upvote:
        return Action.downvote
    elif dub in downvote:
        return Action.upvote
    else:
        logger.error(f'Tried to convert {dub} into Action')
        raise ValueError(f'Tried to convert {dub} into Action')


async def query_simplified_user_actions(playback_id, *, conn=None) -> List[dict]:
    """Return the final output of user actions for a given playback

    We no longer delete entries, instead we support many being inserted, and we just have into account the last vote
    and the skip if any.

    :param str playback_id: The playback id we want to get the actions for
    :param conn: A connection if any open
    :return: A list of the records
    """
    sub_query = sa.select([
        db.UserAction.c.user_id,
        saf.max(db.UserAction.c.ts).label('ts'),
        db.UserAction.c.playback_id,
    ]).where(
        db.UserAction.c.playback_id == playback_id
    ).group_by(
        db.UserAction.c.user_id,
        db.UserAction.c.playback_id,
        sa.case([
            (db.UserAction.c.user_id.is_(None), db.UserAction.c.id),
        ], else_=0)
    ).alias()

    query = sa.select([
        sa.distinct(db.UserAction.c.id),
        db.UserAction.c.action,
        db.UserAction.c.playback_id,
        db.UserAction.c.ts,
        db.UserAction.c.user_id,
    ]).select_from(
        db.UserAction.join(
            sub_query,
            sa.and_(
                sub_query.c.ts == db.UserAction.c.ts,
                db.UserAction.c.playback_id == sub_query.c.playback_id,
                sa.case([
                    (sa.and_(
                        db.UserAction.c.user_id.is_(None),
                        sub_query.c.user_id.is_(None)
                    ), sa.true())
                ], else_=db.UserAction.c.user_id == sub_query.c.user_id)
            )
        )
    )
    async with ensure_connection(conn) as conn:
        result = []
        async for user_action in await conn.execute(query):
            result.append(dict(user_action))
        return result
