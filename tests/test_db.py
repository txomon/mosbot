# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import asynctest as am
import pytest

import mosbot.db as db


@pytest.yield_fixture
def engine_empty():
    engine, db.ENGINE = db.ENGINE, None
    yield
    db.ENGINE = engine


@pytest.yield_fixture()
def create_engine_mock():
    with am.patch('mosbot.db.asa.create_engine') as m:
        m.return_value = am.CoroutineMock()()
        yield m


@pytest.mark.asyncio
async def test_get_engine(engine_empty, create_engine_mock):
    assert db.ENGINE is None

    engine = await db.get_engine()

    assert db.ENGINE == engine

    create_engine_mock.assert_called_once_with(db.config.DATABASE_URL)

    assert engine == await db.get_engine()

    create_engine_mock.assert_called_once_with(db.config.DATABASE_URL)
