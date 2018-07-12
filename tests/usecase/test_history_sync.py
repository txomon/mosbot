import asyncio_extras
import asynctest as am
import datetime
import pytest
from unittest import mock

from mosbot.db import Action, Origin
from mosbot.usecase import save_history_songs
from mosbot.usecase.history_sync import persist_history, dubtrack_songs_since_ts, save_history_chunk, \
    update_user_actions, get_or_create_playback, get_or_create_track, get_or_create_user, history_import_skip_action

save_history_chunk = save_history_chunk.__wrapped__


@pytest.yield_fixture
def dubtrackws_mock():
    with am.patch('mosbot.usecase.history_sync.DubtrackWS') as m:
        m.return_value.initialize = am.CoroutineMock()
        m.return_value.get_history = am.CoroutineMock()
        yield m


@pytest.yield_fixture
def load_bot_data_mock():
    with am.patch('mosbot.usecase.history_sync.load_bot_data') as m:
        yield m


@pytest.yield_fixture
def dubtrack_songs_since_ts_mock():
    with am.patch('mosbot.usecase.history_sync.dubtrack_songs_since_ts') as m:
        yield m


@pytest.yield_fixture
def persist_history_mock():
    with am.patch('mosbot.usecase.history_sync.persist_history') as m:
        yield m


@pytest.yield_fixture
def get_engine_mock():
    with am.patch('mosbot.usecase.history_sync.get_engine') as m:
        m.return_value.acquire = am.CoroutineMock()
        yield m


@pytest.yield_fixture
def save_history_chunk_mock():
    with am.patch('mosbot.usecase.history_sync.save_history_chunk') as m:
        yield m


@pytest.yield_fixture
def save_bot_data_mock():
    with am.patch('mosbot.usecase.history_sync.save_bot_data') as m:
        yield m


@pytest.yield_fixture
def history_import_skip_action_mock():
    with am.patch('mosbot.usecase.history_sync.history_import_skip_action') as m:
        yield m


@pytest.yield_fixture
def get_or_create_user_mock():
    with am.patch('mosbot.usecase.history_sync.get_or_create_user') as m:
        yield m


@pytest.yield_fixture
def get_or_create_track_mock():
    with am.patch('mosbot.usecase.history_sync.get_or_create_track') as m:
        yield m


@pytest.yield_fixture
def get_or_create_playback_mock():
    with am.patch('mosbot.usecase.history_sync.get_or_create_playback') as m:
        yield m


@pytest.yield_fixture
def update_user_actions_mock():
    with am.patch('mosbot.usecase.history_sync.update_user_actions') as m:
        yield m


@pytest.yield_fixture
def query_simplified_user_actions_mock():
    with am.patch('mosbot.usecase.history_sync.query_simplified_user_actions') as m:
        yield m


@pytest.yield_fixture
def save_user_action_mock():
    with am.patch('mosbot.usecase.history_sync.save_user_action') as m:
        yield m


@pytest.yield_fixture
def get_playback_mock():
    with am.patch('mosbot.usecase.history_sync.get_playback') as m:
        yield m


@pytest.yield_fixture
def save_playback_mock():
    with am.patch('mosbot.usecase.history_sync.save_playback') as m:
        yield m


@pytest.yield_fixture
def get_track_mock():
    with am.patch('mosbot.usecase.history_sync.get_track') as m:
        yield m


@pytest.yield_fixture
def save_track_mock():
    with am.patch('mosbot.usecase.history_sync.save_track') as m:
        yield m


@pytest.yield_fixture
def get_user_mock():
    with am.patch('mosbot.usecase.history_sync.get_user') as m:
        yield m


@pytest.yield_fixture
def save_user_mock():
    with am.patch('mosbot.usecase.history_sync.save_user') as m:
        yield m


@pytest.yield_fixture
def execute_and_first_mock():
    with am.patch('mosbot.usecase.history_sync.execute_and_first') as m:
        yield m


@pytest.mark.parametrize('load_bot_data_result', (
        None,
        'last_song'
))
@pytest.mark.asyncio
async def test_save_history_songs(
        load_bot_data_mock,
        dubtrack_songs_since_ts_mock,
        persist_history_mock,
        load_bot_data_result,
):
    load_bot_data_mock.return_value = load_bot_data_result
    await save_history_songs()

    load_bot_data_mock.assert_awaited_once_with('last_saved_history')
    if load_bot_data_result is None:
        dubtrack_songs_since_ts_mock.assert_not_awaited()
        persist_history_mock.assert_not_awaited()
    else:
        dubtrack_songs_since_ts_mock.assert_awaited_once_with(load_bot_data_result)
        persist_history_mock.assert_awaited_once_with(dubtrack_songs_since_ts_mock.return_value)


@pytest.mark.parametrize('songs_input, songs_results, expected_last', (
        ({0: {'skipped': False}}, (None,), (True, 0),),
        ({0: {'skipped': False}, 1: {'skipped': False}, 2: {'skipped': False}}, (None, None, None,), (True, 2,),),
        ({0: {'skipped': False}, 1: {'skipped': True}, 2: {'skipped': False}}, (None, None,), (True, 2),),
        ({0: {'skipped': True}, 1: {'skipped': True}, 2: {'skipped': False}}, (None,), (True, 2),),
        ({0: {'skipped': True}, 1: {'skipped': True}, 2: {'skipped': True}}, (None,), (True, 2),),
        ({0: {'skipped': False}, 1: {'skipped': False}, 2: {'skipped': False}}, (None, None, ValueError,), (True, 1),),
        ({0: {'skipped': False}, 1: {'skipped': False}, 2: {'skipped': False}}, (None, ValueError, None,), (True, 0),),
        ({0: {'skipped': False}, 1: {'skipped': False}, 2: {'skipped': False}}, (ValueError, None, None,),
         (False, None),),
), ids=(
        'one_song_chunk',
        'many_one_song_chunk',
        'two_chunks',
        'many_songs_chunk',
        'many_skips_one_chunk',
        'last_chunk_failing',
        'middle_chunk_failing',
        'first_chunk_failing',
))
@pytest.mark.asyncio
async def test_persist_history(
        get_engine_mock,
        save_history_chunk_mock,
        save_bot_data_mock,
        songs_input,
        songs_results,
        expected_last,
):
    save_history_chunk_mock.side_effect = songs_results
    result = await persist_history(songs_input)

    assert get_engine_mock.return_value.acquire.await_count == len(songs_results)
    assert save_history_chunk_mock.await_count == len(songs_results)
    is_saved, expected_result = expected_last
    assert result == expected_result
    if is_saved:
        save_bot_data_mock.assert_awaited_once_with('last_saved_history', expected_result)


def get_history_song_gen(start, stop, step):
    for s in range(start, stop, step):
        yield {'played': s}


def dubtrack_songs_since_ts_result_gen(start, stop, step):
    for i in get_history_song_gen(start, stop, step):
        yield i['played'] / 1000, i


@pytest.mark.parametrize('last_song, expected_calls, expected_result', (
        (7, 2, dict(dubtrack_songs_since_ts_result_gen(15, 5, -1))),
        (11, 1, dict(dubtrack_songs_since_ts_result_gen(15, 10, -1))),
        (10, 2, dict(dubtrack_songs_since_ts_result_gen(15, 5, -1))),
))
@pytest.mark.asyncio
async def test_dubtrack_songs_since_ts(
        dubtrackws_mock,
        last_song,
        expected_calls,
        expected_result,
):
    get_history = dubtrackws_mock.return_value.get_history
    get_history.side_effect = (
        tuple(get_history_song_gen(15, 10, -1)),
        tuple(get_history_song_gen(10, 5, -1)),
        tuple(get_history_song_gen(5, 0, -1)),
        tuple(get_history_song_gen(0, -1, -1)),
    )

    result = await dubtrack_songs_since_ts(last_song / 1000)

    assert expected_result == result
    assert expected_calls == get_history.await_count


@pytest.mark.parametrize((
        'input_songs',
        'history_import_skip_action_calls',
        'whole_flow_calls',
), (
        (({'played': 1},), [], 1),
        (({'played': 1, 'skipped': True}, {'played': 2}), [
            {'song_played': datetime.datetime.utcfromtimestamp(2 / 1000)},
        ], 2),
), ids=(
        'one_song',
        'one_skip_one_normal',
))
@pytest.mark.asyncio
async def test_save_history_chunk(
        history_import_skip_action_mock,
        get_or_create_user_mock,
        get_or_create_track_mock,
        get_or_create_playback_mock,
        update_user_actions_mock,
        input_songs,
        history_import_skip_action_calls,
        whole_flow_calls,
):
    conn = mock.MagicMock()

    @asyncio_extras.async_contextmanager
    async def mock_manager(*a, **kw):
        yield

    conn.begin = mock_manager
    conn.close = am.CoroutineMock()

    await save_history_chunk(songs=input_songs, conn=conn)
    if len(history_import_skip_action_calls):
        last_call = history_import_skip_action_calls[-1]

        history_import_skip_action_mock.assert_awaited_with(
            **last_call,
            previous_playback_id=get_or_create_playback_mock.return_value,
            conn=conn
        )
        print('MOCK CALLS', history_import_skip_action_mock.await_args_list)

        for call in history_import_skip_action_calls:
            history_import_skip_action_mock.assert_any_await(
                **call,
                previous_playback_id=get_or_create_playback_mock.return_value,
                conn=conn
            )
    assert get_or_create_user_mock.await_count == whole_flow_calls
    assert get_or_create_track_mock.await_count == whole_flow_calls
    assert get_or_create_playback_mock.await_count == whole_flow_calls
    assert update_user_actions_mock.await_count == whole_flow_calls


@pytest.mark.parametrize('input_song,user_actions,expected_actions,save_user_action_returns,raises_exception', (
        ({'updubs': 3, 'downdubs': 2}, (3, 2), (0, 0), True, False),
        ({'updubs': 0, 'downdubs': 2}, (0, 2), (0, 0), True, False),
        ({'updubs': 3, 'downdubs': 0}, (3, 0), (0, 0), True, False),
        ({'updubs': 1, 'downdubs': 2}, (3, 2), (0, 0), True, False),
        ({'updubs': 3, 'downdubs': 1}, (3, 2), (0, 0), True, False),
        ({'updubs': 3, 'downdubs': 2}, (1, 2), (2, 0), True, False),
        ({'updubs': 3, 'downdubs': 2}, (3, 0), (0, 2), True, False),
        ({'updubs': 3, 'downdubs': 2}, (1, 0), (2, 2), True, False),
        ({'updubs': 3, 'downdubs': 2}, (2, 2), (1, 0), {}, ValueError),
), ids=(
        'no_changes',
        'no_updubs',
        'no_downdubs',
        'extra_updubs',
        'extra_downdubs',
        'missing_upvote',
        'missing_downvote',
        'missing_both',
        'impossible_saving',
))
@pytest.mark.asyncio
async def test_update_user_actions(
        query_simplified_user_actions_mock,
        save_user_action_mock,
        input_song,
        user_actions,
        expected_actions,
        save_user_action_returns,
        raises_exception,
):
    upvotes, downvotes = user_actions

    actions = [{'action': Action.upvote} for _ in range(upvotes)]
    actions.extend([{'action': Action.downvote} for _ in range(downvotes)])
    query_simplified_user_actions_mock.return_value = actions

    conn = mock.Mock()

    if raises_exception:
        save_user_action_mock.return_value = save_user_action_returns
        with pytest.raises(raises_exception):
            await update_user_actions(conn=conn, playback_id=1, song=input_song, song_played=1)
    else:
        await update_user_actions(conn=conn, playback_id=1, song=input_song, song_played=1)

    for action, action_num in zip([Action.upvote, Action.downvote], expected_actions):
        save_user_action_mock.assert_has_awaits([
            mock.call(user_action_dict={'ts': 1, 'playback_id': 1, 'action': action}, conn=conn)
            for _ in range(action_num)
        ])

    assert sum(expected_actions) == save_user_action_mock.await_count


@pytest.mark.parametrize('get_playback_returns', ({}, {'id': 1}))
@pytest.mark.parametrize('save_playback_returns', ({}, {'id': 1}))
@pytest.mark.asyncio
async def test_get_or_create_playback(
        get_playback_mock,
        save_playback_mock,
        get_playback_returns,
        save_playback_returns,
):
    get_playback_mock.return_value = get_playback_returns
    save_playback_mock.return_value = save_playback_returns
    conn = mock.Mock()

    if not (get_playback_returns or save_playback_returns):
        with pytest.raises(ValueError):
            await get_or_create_playback(conn=conn, song_played=1, track_id=1, user_id=1)
    else:
        returns = await get_or_create_playback(conn=conn, song_played=1, track_id=1, user_id=1)
        assert returns == 1

    playback_dict = {'track_id': 1, 'user_id': 1, 'start': 1}
    get_playback_mock.assert_awaited_once_with(playback_dict=playback_dict, conn=conn)
    if not get_playback_returns:
        save_playback_mock.assert_awaited_once_with(playback_dict=playback_dict, conn=conn)


@pytest.mark.parametrize('get_track_returns', ({}, {'id': 1}))
@pytest.mark.parametrize('save_track_returns', ({}, {'id': 1}))
@pytest.mark.asyncio
async def test_get_or_create_track(
        get_track_mock,
        save_track_mock,
        get_track_returns,
        save_track_returns,
):
    get_track_mock.return_value = get_track_returns
    save_track_mock.return_value = save_track_returns
    conn = mock.Mock()

    song = {'_song': {'type': 'youtube', 'songLength': 1000, 'name': 'Song 1', 'fkid': '123asd'}}
    track_dict = {'length': 1, 'name': 'Song 1', 'origin': Origin.youtube, 'extid': '123asd', }

    if not (get_track_returns or save_track_returns):
        with pytest.raises(ValueError):
            await get_or_create_track(conn=conn, song=song)
    else:
        returns = await get_or_create_track(conn=conn, song=song)
        assert returns == {'id': 1}

    get_track_mock.assert_awaited_once_with(track_dict=track_dict, conn=conn)
    if not get_track_returns:
        save_track_mock.assert_awaited_once_with(track_dict=track_dict, conn=conn)


@pytest.mark.parametrize('get_user_returns', ({}, {'id': 1}))
@pytest.mark.parametrize('save_user_returns', ({}, {'id': 1}))
@pytest.mark.asyncio
async def test_get_or_create_user(
        get_user_mock,
        save_user_mock,
        get_user_returns,
        save_user_returns,
):
    get_user_mock.return_value = get_user_returns
    save_user_mock.return_value = save_user_returns
    conn = mock.Mock()

    song = {'userid': 'DubtrackId 1', '_user': {'username': 'Dubtrack Username 1'}}
    user_dict = {'dtid': 'DubtrackId 1', 'username': 'Dubtrack Username 1'}

    if not (get_user_returns or save_user_returns):
        with pytest.raises(ValueError):
            await get_or_create_user(conn=conn, song=song)
    else:
        returns = await get_or_create_user(conn=conn, song=song)
        assert returns == {'id': 1}

    get_user_mock.assert_awaited_once_with(user_dict=user_dict, conn=conn)
    if not get_user_returns:
        save_user_mock.assert_awaited_once_with(user_dict=user_dict, conn=conn)


@pytest.mark.parametrize('execute_and_first_returns', ({}, {'id': 1}))
@pytest.mark.parametrize('save_user_action_returns', ({}, {'id': 1}))
@pytest.mark.asyncio
async def test_history_import_skip_action(
        execute_and_first_mock,
        save_user_action_mock,
        execute_and_first_returns,
        save_user_action_returns,
):
    execute_and_first_mock.return_value = execute_and_first_returns
    save_user_action_mock.return_value = save_user_action_returns
    conn = mock.Mock()

    user_action_dict = {'ts': 1, 'playback_id': 1, 'action': Action.skip, }

    if not (execute_and_first_returns or save_user_action_returns):
        with pytest.raises(ValueError):
            await history_import_skip_action(conn=conn, previous_playback_id=1, song_played=1)
    else:
        returns = await history_import_skip_action(conn=conn, previous_playback_id=1, song_played=1)
        assert returns is None

    execute_and_first_mock.assert_awaited_once()
    if not execute_and_first_returns:
        save_user_action_mock.assert_awaited_once_with(user_action_dict=user_action_dict, conn=conn)
