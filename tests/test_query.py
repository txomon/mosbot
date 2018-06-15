# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import pytest

from mosbot.query import save_user, save_track


@pytest.mark.asyncio
async def test_get_user(db_conn):
    pass


@pytest.mark.asyncio
async def test_save_user(db_conn):
    # empty user
    with pytest.raises(AssertionError):
        await save_user(user_dict={})

    # correct user
    user_dict = {'username': 'The User', 'dtid': '0123456789theuser'}
    result = await save_user(user_dict=user_dict, conn=db_conn)
    assert dict(id=1, **user_dict) == result

    # duplicated user
    result = await save_user(user_dict=user_dict, conn=db_conn)
    assert user_dict == result

    # corrupted user
    user_dict = {'username': 1982, 'dtid': '0123456789theuser'}
    result = await save_user(user_dict=user_dict, conn=db_conn)
    assert user_dict == result


@pytest.mark.asyncio
async def test_save_track(db_conn):
    # empty track_dict
    result = await save_track(track_dict={}, conn=db_conn)
    assert result is None

    # correct track_dict
    track_dict = {'extid': '???', 'origin': '???'}
