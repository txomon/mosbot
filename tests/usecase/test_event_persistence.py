import asynctest as am
import pytest
from unittest import mock

from mosbot.db import Origin, Action
from mosbot.usecase import ensure_dubtrack_skip
from mosbot.usecase.event_persistence import ensure_dubtrack_entity, ensure_dubtrack_playing, ensure_dubtrack_dub


@pytest.yield_fixture
def get_or_save_user_mock():
    with am.patch('mosbot.usecase.event_persistence.get_or_save_user') as m:
        yield m


@pytest.yield_fixture
def ensure_dubtrack_entity_mock():
    with am.patch('mosbot.usecase.event_persistence.ensure_dubtrack_entity') as m:
        yield m


@pytest.yield_fixture
def get_or_save_track_mock():
    with am.patch('mosbot.usecase.event_persistence.get_or_save_track') as m:
        yield m


@pytest.yield_fixture
def get_or_save_playback_mock():
    with am.patch('mosbot.usecase.event_persistence.get_or_save_playback') as m:
        yield m


@pytest.yield_fixture
def get_last_playback_mock():
    with am.patch('mosbot.usecase.event_persistence.get_last_playback') as m:
        yield m


@pytest.yield_fixture
def save_user_action_mock():
    with am.patch('mosbot.usecase.event_persistence.save_user_action') as m:
        yield m


@pytest.fixture
def datetime_mock(mocker):
    return mocker.patch('mosbot.usecase.event_persistence.datetime')


@pytest.fixture
def get_dub_action_mock(mocker):
    return mocker.patch('mosbot.usecase.event_persistence.get_dub_action')


@pytest.mark.asyncio
async def test_ensure_dubtrack_entity(
        get_or_save_user_mock,
):
    conn = mock.Mock()

    de = mock.Mock()
    user_dict = {'dtid': de.id, 'username': de.username}

    returns = await ensure_dubtrack_entity(user=de, conn=conn)
    assert returns == get_or_save_user_mock.return_value

    get_or_save_user_mock.assert_awaited_once_with(user_dict=user_dict, conn=conn)


@pytest.mark.asyncio
async def test_ensure_dubtrack_playing(
        ensure_dubtrack_entity_mock,
        get_or_save_track_mock,
        get_or_save_playback_mock,
):
    ensure_dubtrack_entity_mock.return_value = {'id': 1}
    get_or_save_track_mock.return_value = {'id': 2}

    dp = mock.Mock()
    dp.song_type = 'youtube'
    conn = mock.Mock()
    await ensure_dubtrack_playing(event=dp, conn=conn)

    ensure_dubtrack_entity_mock.assert_awaited_once_with(user=dp.sender, conn=conn)
    get_or_save_track_mock.assert_awaited_once_with(track_dict={
        'length': dp.length.total_seconds.return_value,
        'origin': Origin.youtube,
        'extid': dp.song_external_id,
        'name': dp.song_name,
    }, conn=conn)
    get_or_save_playback_mock.assert_awaited_once_with(playback_dict={
        'user_id': 1,
        'track_id': 2,
        'start': dp.played,
    }, conn=conn)


@pytest.mark.asyncio
async def test_ensure_dubtrack_skip(
        get_last_playback_mock,
        ensure_dubtrack_entity_mock,
        save_user_action_mock,
        datetime_mock,
):
    get_last_playback_mock.return_value = {'id': 1}
    ensure_dubtrack_entity_mock.return_value = {'id': 2}

    ds = mock.Mock()
    conn = mock.Mock()
    await ensure_dubtrack_skip(event=ds, conn=conn)

    get_last_playback_mock.assert_awaited_once_with(conn=conn)
    ensure_dubtrack_entity_mock.assert_awaited_once_with(user=ds.sender, conn=conn)
    save_user_action_mock.assert_awaited_once_with(user_action_dict={
        'playback_id': 1,
        'user_id': 2,
        'action': Action.skip,
        'ts': datetime_mock.datetime.utcnow.return_value,
    }, conn=conn)


@pytest.mark.parametrize('event_played', (1, False))
@pytest.mark.asyncio
async def test_ensure_dubtrack_dub(
        get_last_playback_mock,
        ensure_dubtrack_entity_mock,
        get_dub_action_mock,
        save_user_action_mock,
        datetime_mock,
        event_played,
):
    dd = mock.Mock()
    dd.played = event_played
    conn = mock.Mock()
    get_last_playback_mock.return_value = {'id': 1, 'start': 1}
    ensure_dubtrack_entity_mock.return_value = {'id': 2}

    await ensure_dubtrack_dub(event=dd, conn=conn)

    if event_played:
        get_last_playback_mock.assert_awaited_once_with(conn=conn)
        ensure_dubtrack_entity_mock.assert_awaited_once_with(user=dd.sender, conn=conn)
        get_dub_action_mock.assert_called_once_with(dd.dubtype)
        save_user_action_mock.assert_awaited_once_with(user_action_dict={
            'ts': datetime_mock.datetime.utcnow.return_value,
            'playback_id': 1,
            'user_id': 2,
            'action': get_dub_action_mock.return_value,
        }, conn=conn)
    else:
        get_last_playback_mock.assert_awaited_once_with(conn=conn)
        ensure_dubtrack_entity_mock.assert_not_awaited()
        get_dub_action_mock.assert_not_called()
        save_user_action_mock.assert_not_awaited()
