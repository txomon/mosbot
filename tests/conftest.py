# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import asyncio

import logging
import pytest
import threading
from aiopg import Connection
from alembic.command import downgrade, upgrade
from alembic.config import Config
from async_generator import async_generator

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

        yield roll_conn

        await trans.rollback()
        await roll_conn.close()
        mosbot.query.ensure_connection = old_ensure
