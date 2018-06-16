# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import pytest
from sqlalchemy.dialects import postgresql as psa

from mosbot.db import Origin, User
from mosbot.query import get_user, save_user, save_track, execute_and_first


@pytest.mark.parametrize('data_dict,expected_result', (
        (
                {'id': 1, 'dtid': '1234', 'username': 'username', 'country': 'ES'},
                {'id': 1, 'dtid': '1234', 'username': 'username', 'country': 'ES'},
        ),
        (
                {'id': 1, 'dtid': '1234', 'username': 'username', 'country': None},
                {'id': 1, 'dtid': '1234', 'username': 'username', 'country': None},
        ),
        (
                {'id': 1, 'dtid': '1234', 'username': 'username'},
                {'id': 1, 'dtid': '1234', 'username': 'username', 'country': None},
        ),
        (
                {'dtid': '1234', 'username': 'username'},
                {'id': 1, 'dtid': '1234', 'username': 'username', 'country': None},
        ),
), ids=[
    'all_values',
    'all_values_with_null',
    'not_nullable_value',
    'not_autogen_not_nullable_value'
])
@pytest.mark.asyncio
async def test_execute_and_first(db_conn, data_dict, expected_result):
    # We use user table because it's the one with 3 tipes of fields:
    # * Unique not nullable
    # * Not nullable
    # * Nullable
    query = psa.insert(User) \
        .values(data_dict) \
        .returning(User) \
        .on_conflict_do_update(
        index_elements=[User.c.dtid],
        set_=data_dict
    )
    ret = await execute_and_first(query=query, conn=db_conn)
    rp = await db_conn.execute('select * from "user";')
    select_result = dict(await rp.fetchone())
    assert select_result == ret
    assert expected_result == ret


@pytest.mark.asyncio
async def test_get_user(db_conn, user_generator):
    user = await user_generator()
    retrieved_user = await get_user(user_dict={'id': 1}, conn=db_conn)
    assert retrieved_user == user

    retrieved_user = await get_user(user_dict={'username': 'Username 1'}, conn=db_conn)
    assert retrieved_user == user


@pytest.mark.parametrize('user_dict, raises_exception', (
        ({}, False), # TODO
))
@pytest.mark.asyncio
async def test_save_user(db_conn, user_dict, raises_exception):
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


@pytest.mark.parametrize("track_dict, raises_exception", [
    ({'extid': 'ab12', 'origin': 'youtube', 'length': 120, 'name': 'One name'}, False),
    ({'extid': 'ab12', 'origin': Origin.youtube, 'length': 120, 'name': 'One name'}, False),
    ({'extid': 12345, 'origin': 'youtube', 'length': 120, 'name': 'One name'}, True),
    ({'extid': 'ab12', 'origin': 'youtube', 'length': '120', 'name': 'One name'}, True),
    ({'extid': 'ab12', 'origin': (1, 2), 'length': 120, 'name': 'One name'}, True),
    ({'extid': 'ab12', 'origin': 'youtube', 'length': 120, 'name': 12345}, True),
    ({}, True),
])
@pytest.mark.asyncio
async def test_save_track(db_conn, track_dict, raises_exception):
    if raises_exception:
        with pytest.raises(AssertionError):
            await save_track(track_dict=track_dict, conn=db_conn)
    else:
        actual_result = await save_track(track_dict=track_dict, conn=db_conn)
        expected_result = dict(id=1, **track_dict)
        expected_result['origin'] = Origin.youtube
        assert actual_result == expected_result
