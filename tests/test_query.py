# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import datetime
import pytest
from sqlalchemy.dialects import postgresql as psa

from mosbot.db import Origin, User
from mosbot.query import get_user, save_user, save_track, execute_and_first, get_track, get_playback, save_playback, \
    get_user_action, save_user_action, save_bot_data, load_bot_data


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
    'not_autogen_not_nullable_value',
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
@pytest.mark.parametrize('user_dict, raises_exception', (
        ({'id': 1}, False),
        ({'username': 'Username 1'}, False),
        ({'dtid': '00000001-0001-0001-0001-0000000001'}, False),
        ({'country': 'Country 1'}, ValueError),
), ids=['by_id', 'by_usernam', 'by_dtid', 'failing_by_country'])
async def test_get_user(db_conn, user_generator, user_dict, raises_exception):
    user = await user_generator()
    if raises_exception:
        with pytest.raises(raises_exception):
            await get_user(user_dict=user_dict, conn=db_conn)
    else:
        retrieved_user = await get_user(user_dict=user_dict, conn=db_conn)
        assert retrieved_user == user


@pytest.mark.parametrize('user_dict, raises_exception', (
        ({}, False),  # TODO
))
@pytest.mark.asyncio
async def test_save_user(db_conn, user_dict, raises_exception):
    # empty user
    with pytest.raises(AssertionError):
        await save_user(user_dict={})

    # correct user
    user_dict = {'username': 'The User', 'dtid': '0123456789theuser'}
    actual_result = await save_user(user_dict=user_dict, conn=db_conn)
    expected_result = dict(id=1, country=None, **user_dict)
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


@pytest.mark.parametrize('track_dict, raises_exception', (
        ({'id': 1}, False),
        ({'extid': 'Extid 1'}, False),
        ({'origin': 'youtube'}, AssertionError),
        ({'length': 120}, AssertionError),
        ({'extid': 'Extid 1', 'origin': 'youtube'}, False),
), ids=['by_id', 'by_extid', 'by_origin', 'by_length', 'by_extid+origin'], )
@pytest.mark.asyncio
async def test_get_track(db_conn, track_generator, track_dict, raises_exception):
    track = await track_generator()
    if raises_exception:
        with pytest.raises(raises_exception):
            await get_track(track_dict=track_dict, conn=db_conn)
    else:
        retrieved_track = await get_track(track_dict=track_dict, conn=db_conn)
        assert retrieved_track == track


@pytest.mark.parametrize("track_dict, raises_exception", [
    ({'extid': 'ab12', 'origin': 'youtube', 'length': 120, 'name': 'One name'}, None),
    ({'extid': 'ab12', 'origin': Origin.youtube, 'length': 120, 'name': 'One name'}, None),
    ({'extid': 12345, 'origin': 'youtube', 'length': 120, 'name': 'One name'}, AssertionError),
    ({'extid': 'ab12', 'origin': 'youtube', 'length': '120', 'name': 'One name'}, AssertionError),
    ({'extid': 'ab12', 'origin': (1, 2), 'length': 120, 'name': 'One name'}, AssertionError),
    ({'extid': 'ab12', 'origin': 'youtube', 'length': 120, 'name': 12345}, AssertionError),
    ({}, AssertionError),
], ids=['good_with_string', 'good_with_enum', 'bad_with_int', 'bad_with_string', 'bad_with_tuple', 'bad_with_int_name',
        'bad_no_data'])
@pytest.mark.asyncio
async def test_save_track(db_conn, track_dict, raises_exception):
    if raises_exception:
        with pytest.raises(raises_exception):
            await save_track(track_dict=track_dict, conn=db_conn)
    else:
        actual_result = await save_track(track_dict=track_dict, conn=db_conn)
        expected_result = dict(id=1, **track_dict)
        expected_result['origin'] = Origin.youtube
        assert actual_result == expected_result


@pytest.mark.parametrize('playback_dict, raises_exception', (
        ({'id': 1}, False),
        ({'start': datetime.datetime(year=1, month=1, day=1)}, False),
        ({'track_id': 1}, ValueError),
        ({'user_id': 1}, ValueError),
), ids=['by_id', 'by_start', 'by_track_id', 'by_user_id'], )
@pytest.mark.asyncio
async def test_get_playback(
        db_conn,
        track_generator,
        user_generator,
        playback_generator,
        playback_dict,
        raises_exception,
):
    track = await track_generator()
    user = await user_generator()
    playback = await playback_generator(user=user, track=track)
    if raises_exception:
        with pytest.raises(raises_exception):
            await get_playback(playback_dict=playback_dict, conn=db_conn)
    else:
        retrieved_playback = await get_playback(playback_dict=playback_dict, conn=db_conn)
        assert retrieved_playback == playback


@pytest.mark.parametrize("playback_dict, raises_exception", [
    ({'start': datetime.datetime(1, 1, 1), 'user_id': 1, 'track_id': 1}, None),
    ({'start': '0001-01-01', 'user_id': 1, 'track_id': 1}, None),
    ({'start': datetime.datetime(1, 1, 1), 'user_id': '1', 'track_id': 1}, None),
    ({'start': datetime.datetime(1, 1, 1), 'user_id': 1, 'track_id': '1'}, None),
    ({}, AssertionError),
], ids=['good', 'bad_with_date_string', 'bad_with_uid_string', 'bad_with_tid_string', 'bad_no_data'])
@pytest.mark.asyncio
async def test_save_playback(
        db_conn,
        track_generator,
        user_generator,
        playback_dict,
        raises_exception,
):
    await track_generator()
    await user_generator()
    if raises_exception:
        with pytest.raises(raises_exception):
            await save_playback(playback_dict=playback_dict, conn=db_conn)
    else:
        actual_result = await save_playback(playback_dict=playback_dict, conn=db_conn)
        db_data = await get_playback(playback_dict={'id': 1}, conn=db_conn)
        assert db_data == actual_result


@pytest.mark.parametrize('user_action_dict, raises_exception', (
        ({'id': 1}, False),
        ({'ts': datetime.datetime(year=1, month=1, day=1)}, ValueError),
        ({'track_id': 1}, ValueError),
        ({'user_id': 1}, ValueError),
), ids=['by_id', 'by_start', 'by_track_id', 'by_user_id'], )
@pytest.mark.asyncio
async def test_get_user_action(
        db_conn,
        track_generator,
        user_generator,
        playback_generator,
        user_action_generator,
        user_action_dict,
        raises_exception,
):
    track = await track_generator()
    user = await user_generator()
    playback = await playback_generator(user=user, track=track)
    user_action = await user_action_generator(user=user, playback=playback)
    if raises_exception:
        with pytest.raises(raises_exception):
            await get_user_action(user_action_dict=user_action_dict, conn=db_conn)
    else:
        retrieved_user_action = await get_user_action(
            user_action_dict=user_action_dict,
            conn=db_conn,
        )
        assert retrieved_user_action == user_action


@pytest.mark.parametrize("user_action_dict, raises_exception", [
    ({'ts': datetime.datetime(1, 1, 1), 'action': 'upvote', 'user_id': 1, 'playback_id': 1}, None),
    ({'ts': '0001-01-01', 'user_id': 1, 'action': 'upvote', 'playback_id': 1}, None),
    ({'ts': datetime.datetime(1, 1, 1), 'action': 'upvote', 'user_id': '1', 'playback_id': 1}, None),
    ({'ts': datetime.datetime(1, 1, 1), 'action': 'upvote', 'user_id': 1, 'playback_id': '1'}, None),
    ({'ts': datetime.datetime(1, 1, 1), 'action': 'upvote', 'user_id': 1, 'track_id': 1}, AssertionError),
    ({}, AssertionError),
], ids=[
    'good',
    'bad_with_date_string',
    'bad_with_uid_string',
    'bad_with_tid_string',
    'bad_with_track',
    'bad_no_data'
])
@pytest.mark.asyncio
async def test_save_user_action(
        db_conn,
        track_generator,
        user_generator,
        playback_generator,
        user_action_dict,
        raises_exception,
):
    track = await track_generator()
    user = await user_generator()
    await playback_generator(user=user, track=track)
    if raises_exception:
        with pytest.raises(raises_exception):
            await save_user_action(user_action_dict=user_action_dict, conn=db_conn)
    else:
        actual_result = await save_user_action(user_action_dict=user_action_dict, conn=db_conn)
        db_data = await get_user_action(user_action_dict={'id': 1}, conn=db_conn)
        assert db_data == actual_result


@pytest.mark.parametrize('bot_data, raises_exception', (
        (('id', 1), False),
        (('extid', 'Extid 1'), False),
        (('origin', {'a': 1, 'b': 2}), False),
        (('length', {1, 2, 3, 120}), TypeError),
        (('other', [1, 2, 3, 120]), False),
        (('extid', None), False),
), ids=['number', 'string', 'dict', 'set', 'list', 'null'], )
@pytest.mark.asyncio
async def test_bot_data(db_conn, bot_data, raises_exception):
    key, value = bot_data
    if raises_exception:
        with pytest.raises(raises_exception):
            await save_bot_data(key=key, value=value, conn=db_conn)
            await load_bot_data(key=key, conn=db_conn)
    else:
        await save_bot_data(key=key, value=value, conn=db_conn)
        retrieved_bot_data = await load_bot_data(key=key, conn=db_conn)
        assert retrieved_bot_data == value


@pytest.mark.asyncio
async def test_bot_data_duplicate_insert(db_conn):
    bot_data = await load_bot_data(key='id', conn=db_conn)
    assert bot_data is None

    await save_bot_data(key='id', value=123, conn=db_conn)
    bot_data = await load_bot_data(key='id', conn=db_conn)
    assert bot_data == 123

    await save_bot_data(key='id', value='val', conn=db_conn)
    bot_data = await load_bot_data(key='id', conn=db_conn)
    assert bot_data == 'val'
