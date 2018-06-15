# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import asynctest as am
import pytest

import mosbot.db as db


@pytest.yield_fixture
def engine_empty():
    engine, db.ENGINE = db.ENGINE, {}
    yield
    db.ENGINE = engine


@pytest.yield_fixture()
def create_engine_mock():
    with am.patch('mosbot.db.asa.create_engine') as m:
        m.return_value = am.CoroutineMock()()
        yield m


@pytest.mark.asyncio
async def test_get_engine(event_loop, engine_empty, create_engine_mock):
    assert not db.ENGINE

    engine = await db.get_engine()

    assert db.ENGINE[event_loop] == engine

    create_engine_mock.assert_called_once_with(db.config.DATABASE_URL, echo=False)

    assert engine == await db.get_engine()

    create_engine_mock.assert_called_once_with(db.config.DATABASE_URL, echo=False)
