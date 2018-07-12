# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import asynctest as am
import datetime
import pytest
from sqlalchemy.dialects import postgresql as psa
from unittest import mock

from mosbot.db import Origin, User, Action
from mosbot.query import get_user, save_user, save_track, execute_and_first, get_track, get_playback, save_playback, \
    get_user_action, save_user_action, save_bot_data, load_bot_data, get_last_playback, get_user_user_actions, \
    get_user_dub_user_actions, get_dub_action, get_opposite_dub_action, query_simplified_user_actions, \
    get_or_save_track, get_or_save_user, get_or_save_playback, ensure_connection


@pytest.yield_fixture
def get_user_mock():
    with am.patch('mosbot.query.get_user') as m:
        yield m


@pytest.yield_fixture
def save_user_mock():
    with am.patch('mosbot.query.save_user') as m:
        yield m


@pytest.yield_fixture
def get_track_mock():
    with am.patch('mosbot.query.get_track') as m:
        yield m


@pytest.yield_fixture
def save_track_mock():
    with am.patch('mosbot.query.save_track') as m:
        yield m


@pytest.yield_fixture
def get_playback_mock():
    with am.patch('mosbot.query.get_playback') as m:
        yield m


@pytest.yield_fixture
def save_playback_mock():
    with am.patch('mosbot.query.save_playback') as m:
        yield m


@pytest.yield_fixture
def get_engine_mock():
    with am.patch('mosbot.query.get_engine') as m:
        get_engine = m.return_value = am.CoroutineMock()
        engine_object = get_engine.acquire = am.CoroutineMock()
        engine_object.return_value.close = am.CoroutineMock()
        yield m


@pytest.mark.parametrize('connection', (True, False))
@pytest.mark.asyncio
async def test_ensure_connection(
        get_engine_mock,
        connection,
):
    engine_object = get_engine_mock.return_value
    connection_object = engine_object.acquire.return_value
    async with ensure_connection(conn=connection) as conn:
        if connection:
            assert conn is True
        else:
            assert connection_object == conn
    if not connection:
        get_engine_mock.assert_awaited_once_with()
        engine_object.acquire.assert_awaited_once_with()
        connection_object.close.assert_awaited_once_with()
    else:
        get_engine_mock.assert_not_awaited()
        engine_object.acquire.assert_not_awaited()
        connection_object.close.assert_not_awaited()


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
        ({}, False),
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


@pytest.mark.parametrize('get_user_returns', ({}, {'id': 1}))
@pytest.mark.parametrize('save_user_returns', ({}, {'id': 2}))
@pytest.mark.asyncio
async def test_get_or_save_user(
        get_user_mock,
        save_user_mock,
        get_user_returns,
        save_user_returns,
):
    get_user_mock.return_value = get_user_returns
    save_user_mock.return_value = save_user_returns
    conn = mock.Mock()
    user_dict = mock.Mock()
    result = (get_user_returns or save_user_returns)

    if not result:
        with pytest.raises(ValueError):
            await get_or_save_user(conn=conn, user_dict=user_dict)
    else:
        returns = await get_or_save_user(conn=conn, user_dict=user_dict)
        assert returns == result

    get_user_mock.assert_awaited_once_with(user_dict=user_dict, conn=conn)

    if get_user_returns:
        save_user_mock.assert_not_awaited()
    else:
        save_user_mock.assert_awaited_once_with(user_dict=user_dict, conn=conn)


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


@pytest.mark.parametrize('get_track_returns', ({}, {'id': 1}))
@pytest.mark.parametrize('save_track_returns', ({}, {'id': 2}))
@pytest.mark.asyncio
async def test_get_or_save_track(
        get_track_mock,
        save_track_mock,
        get_track_returns,
        save_track_returns,
):
    get_track_mock.return_value = get_track_returns
    save_track_mock.return_value = save_track_returns
    conn = mock.Mock()
    track_dict = mock.Mock()
    result = (get_track_returns or save_track_returns)

    if not result:
        with pytest.raises(ValueError):
            await get_or_save_track(conn=conn, track_dict=track_dict)
    else:
        returns = await get_or_save_track(conn=conn, track_dict=track_dict)
        assert returns == result

    get_track_mock.assert_awaited_once_with(track_dict=track_dict, conn=conn)

    if get_track_returns:
        save_track_mock.assert_not_awaited()
    else:
        save_track_mock.assert_awaited_once_with(track_dict=track_dict, conn=conn)


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


@pytest.mark.parametrize('get_playback_returns', ({}, {'id': 1}))
@pytest.mark.parametrize('save_playback_returns', ({}, {'id': 2}))
@pytest.mark.asyncio
async def test_get_or_save_playback(
        get_playback_mock,
        save_playback_mock,
        get_playback_returns,
        save_playback_returns,
):
    get_playback_mock.return_value = get_playback_returns
    save_playback_mock.return_value = save_playback_returns
    conn = mock.Mock()
    playback_dict = mock.Mock()
    result = (get_playback_returns or save_playback_returns)

    if not result:
        with pytest.raises(ValueError):
            await get_or_save_playback(conn=conn, playback_dict=playback_dict)
    else:
        returns = await get_or_save_playback(conn=conn, playback_dict=playback_dict)
        assert returns == result

    get_playback_mock.assert_awaited_once_with(playback_dict=playback_dict, conn=conn)

    if get_playback_returns:
        save_playback_mock.assert_not_awaited()
    else:
        save_playback_mock.assert_awaited_once_with(playback_dict=playback_dict, conn=conn)


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
    assert None is await load_bot_data(key=key, conn=db_conn)
    if raises_exception:
        with pytest.raises(raises_exception):
            await save_bot_data(key=key, value=value, conn=db_conn)
            await load_bot_data(key=key, conn=db_conn)
    else:
        await save_bot_data(key=key, value=value, conn=db_conn)
        retrieved_bot_data = await load_bot_data(key=key, conn=db_conn)
        assert retrieved_bot_data == value


@pytest.mark.asyncio
async def test_get_last_playback(
        db_conn,
        track_generator,
        user_generator,
        playback_generator,
):
    track = await track_generator()
    user = await user_generator()
    for _ in range(6):
        expected_playback = await playback_generator(user=user, track=track)
    playback = await get_last_playback(conn=db_conn)
    assert expected_playback == playback


@pytest.mark.asyncio
async def test_get_user_user_actions(
        db_conn,
        track_generator,
        user_generator,
        playback_generator,
        user_action_generator,
):
    track = await track_generator()
    user = await user_generator()
    expected_user_actions = set()
    for _ in range(6):
        playback = await playback_generator(user=user, track=track)
        for _ in range(6):
            user_action = await user_action_generator(user=user, playback=playback)
            expected_user_actions.add(tuple(sorted(user_action.items())))

    user_actions = await get_user_user_actions(user_id=user['id'], conn=db_conn)
    user_actions = {tuple(sorted(ua.items())) for ua in user_actions}

    assert user_actions == expected_user_actions


@pytest.mark.asyncio
async def test_user_dub_user_actions(
        db_conn,
        track_generator,
        user_generator,
        playback_generator,
        user_action_generator,
):
    track = await track_generator()
    user = await user_generator()
    expected_user_actions = set()
    for _ in range(6):
        playback = await playback_generator(user=user, track=track)
        for _ in range(6):
            user_action = await user_action_generator(user=user, playback=playback)
            if user_action['action'] not in [Action.upvote, Action.downvote]:
                continue
            expected_user_actions.add(tuple(sorted(user_action.items())))

    user_actions = await get_user_dub_user_actions(user_id=user['id'], conn=db_conn)
    assert user_actions
    user_actions = {tuple(sorted(ua.items())) for ua in user_actions}

    assert expected_user_actions
    assert user_actions == expected_user_actions


@pytest.mark.parametrize('input,output', (
        ('upvote', Action.upvote),
        ('updub', Action.upvote),
        ('updubs', Action.upvote),
        ('downvote', Action.downvote),
        ('downdub', Action.downvote),
        ('downdubs', Action.downvote),
        ('none', None),
))
def test_get_dub_action(input, output):
    if output is None:
        with pytest.raises(ValueError):
            get_dub_action(input)
    else:
        assert output == get_dub_action(input)


@pytest.mark.parametrize('input,output', (
        ('upvote', Action.downvote),
        ('updub', Action.downvote),
        ('updubs', Action.downvote),
        ('downvote', Action.upvote),
        ('downdub', Action.upvote),
        ('downdubs', Action.upvote),
        ('none', None),
))
def test_get_opposite_dub_action(input, output):
    if output is None:
        with pytest.raises(ValueError):
            get_opposite_dub_action(input)
    else:
        assert output == get_opposite_dub_action(input)


@pytest.mark.parametrize('loops, output', (
        (1, {Action.upvote, }),
        (2, {Action.downvote, }),
        (3, {Action.upvote, }),
        pytest.param(4, {Action.upvote, Action.skip}, marks=pytest.mark.xfail(
            reason='The query is not complete enough to only aggregate upvotes and downvotes')),
))
@pytest.mark.asyncio
async def test_query_simplified_user_actions(
        db_conn,
        track_generator,
        user_generator,
        playback_generator,
        user_action_generator,
        loops,
        output
):
    actions = ['upvote', 'downvote', 'upvote', 'skip']
    track = await track_generator()
    user = await user_generator()
    playback = await playback_generator(user=user, track=track)
    for _, action in zip(range(loops), actions):
        await user_action_generator(user=user, playback=playback, action=action)

    user_actions = await query_simplified_user_actions(playback_id=playback['id'], conn=db_conn)
    result = {ua['action'] for ua in user_actions}
    assert result == output
