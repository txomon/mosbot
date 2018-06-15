# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import pytest

from mosbot.query import get_user, save_user, save_track


@pytest.mark.asyncio
async def test_get_user(db_conn, user_generator):
    user = await user_generator()
    retrieved_user = await get_user(user_dict={'id': 1}, conn=db_conn)
    assert retrieved_user == user

    retrieved_user = await get_user(user_dict={'username': 'Username 1'}, conn=db_conn)
    assert retrieved_user == user


@pytest.mark.asyncio
async def test_save_user(db_conn):
    # empty user
    with pytest.raises(AssertionError):
        await save_user(user_dict={})

    # correct user
    user_dict = {'username': 'The User', 'dtid': '0123456789theuser'}
    actual_result = await save_user(user_dict=user_dict, conn=db_conn)
    expected_result = dict(id=1, **user_dict)
    assert expected_result == actual_result

    # duplicated user
    actual_result = await save_user(user_dict=user_dict, conn=db_conn)
    assert expected_result == actual_result

    # corrupted user.username (should be a string)
    user_dict = {'username': 1982, 'dtid': '0123456789theuser'}
    with pytest.raises(Exception):
        await save_user(user_dict=user_dict, conn=db_conn)

    # corrupted user.dtid (should be a string)
    user_dict = {'username': '1982', 'dtid': 123456789}
    with pytest.raises(Exception):
        await save_user(user_dict=user_dict, conn=db_conn)


@pytest.mark.asyncio
async def test_save_track(db_conn):
    # empty track_dict
    with pytest.raises(AssertionError):
        await save_track(track_dict={}, conn=db_conn)

    # correct track_dict
    track_dict = {'extid': 'one external id', 'origin': 'youtube', 'length': 100, 'name': 'One name'}
    result = await save_track(track_dict=track_dict, conn=db_conn)
