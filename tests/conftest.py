# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import pytest
from aiopg import Connection
from alembic.command import downgrade, upgrade
from alembic.config import Config

config = Config('alembic.ini')


@pytest.yield_fixture(scope='session', autouse=True)
def database():
    upgrade(config, 'head')
    yield
    downgrade(config, 'base')


@pytest.yield_fixture()
async def db_conn():
    import mosbot.query
    from asyncio_extras import async_contextmanager

    async with mosbot.query.ensure_connection() as roll_conn:
        @async_contextmanager
        async def ensure_connection(conn):
            provided_connection = bool(conn)
            if not provided_connection:
                conn = roll_conn
            try:
                yield conn
            finally:
                if not provided_connection:
                    pass

        mosbot.query.ensure_connection = ensure_connection

        trans: Connection = await roll_conn.begin()

        yield roll_conn

        await trans.rollback()
        await roll_conn.close()
