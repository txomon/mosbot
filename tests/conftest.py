# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import itertools

import datetime
import pytest
from aiopg import Connection
from alembic.command import downgrade, upgrade
from alembic.config import Config

from mosbot.db import get_engine
from mosbot.query import save_user, save_track, save_playback

config = Config('alembic.ini')


@pytest.yield_fixture(scope='session', autouse=True)
def database():
    upgrade(config, 'head')
    yield
    downgrade(config, 'base')


@pytest.yield_fixture()
@pytest.mark.asyncio
async def db_conn():
    """
    Global patch of ensure_connection, as when used with integration tests, we
    need to make sure there isn't any function calling the real one.

    Parallelization should run on processes, not threads, as this is a global
    replace

    :return: connection to do the stuff on
    """
    import mosbot.query
    from asyncio_extras import async_contextmanager

    await mosbot.db.get_engine(True)

    async with mosbot.query.ensure_connection(None) as roll_conn:
        @async_contextmanager
        async def ensure_connection(conn=None):
            provided_connection = bool(conn)
            if not provided_connection:
                conn = roll_conn
            try:
                yield conn
            finally:
                if not provided_connection:
                    pass

        mosbot.query.ensure_connection, old_ensure = ensure_connection, mosbot.query.ensure_connection

        trans: Connection = await roll_conn.begin()

        # Restart all sequences to avoid id changes
        sequences = await roll_conn.execute("SELECT c.relname FROM pg_class c WHERE c.relkind = 'S';")
        sequences = (s[0] for s in await sequences.fetchall())

        restart_sequences = ";".join(f'alter sequence {seq} restart' for seq in sequences)

        await roll_conn.execute(restart_sequences)

        yield roll_conn

        await trans.rollback()
        await roll_conn.close()
        # This four lines are required to close the engine properly
        engine = await get_engine()
        engine.close()
        await engine.wait_closed()

        mosbot.query.ensure_connection = old_ensure


def infinite_iterable():
    while True:
        yield None


def int_generator():
    for num in itertools.count(start=1):
        yield num


def str_generator(name_format='{num}'):
    for num in itertools.count(start=1):
        yield name_format.format(num=num)


def datetime_generator(timedelta=None):
    if timedelta is None:
        timedelta = datetime.timedelta(seconds=1)
    for num in itertools.count(start=1):
        yield datetime.datetime(year=0, month=1, day=1) + timedelta * num


@pytest.fixture
def user_generator(db_conn):
    id_generator = int_generator()
    username_generator = str_generator('Username {num}')
    dtid_generator = str_generator('{num:08}-{num:04}-{num:04}-{num:04}-{num:010}')
    country_generator = str_generator('Country {num}')

    async def generate_user(*, id=None, username=None, dtid=None, country=None):
        if id is None:
            id = next(id_generator)
        if username is None:
            username = next(username_generator)
        if dtid is None:
            dtid = next(dtid_generator)
        if country is None:
            country = next(country_generator)
        user_dict = {
            'id': id,
            'username': username,
            'dtid': dtid,
            'country': country,
        }
        user_dict = await save_user(user_dict=user_dict, conn=db_conn)
        return user_dict

    return generate_user


@pytest.fixture
def track_generator(db_conn):
    id_generator = int_generator()
    length_generator = itertools.repeat(120)
    origin_generator = itertools.cycle(['youtube', 'soundcloud'])
    extid_generator = str_generator('Extid {num}')
    name_generator = str_generator('Name {num}')

    async def generate_track(id=None, length=None, origin=None, extid=None,
                             name=None):
        if id is None:
            id = next(id_generator)
        if length is None:
            length = next(length_generator)
        if origin is None:
            origin = next(origin_generator)
        if extid is None:
            extid = next(extid_generator)
        if name is None:
            name = next(name_generator)
        track_dict = {
            'id': id,
            'length': length,
            'origin': origin,
            'extid': extid,
            'name': name,
        }
        track_dict = await save_track(track_dict=track_dict, conn=db_conn)
        return track_dict

    return generate_track


@pytest.fixture
def playback_generator(db_conn):
    id_generator = int_generator()
    start_generator = datetime_generator(datetime.timedelta(seconds=120))

    async def generate_playback(*, id=None, start=None, user_id, track_id):
        if id is None:
            id = next(id_generator)
        if start is None:
            start = next(start_generator)
        playback_dict = {
            'id': id,
            'track_id': track_id,
            'user_id': user_id,
            'start': start,
        }
        playback_dict = await save_playback(playback_dict=playback_dict,
                                            conn=db_conn)
        return playback_dict

    return generate_playback
