import asynctest as am
import pytest

from mosbot.usecase import save_history_songs
from mosbot.usecase.history_sync import persist_history, dubtrack_songs_since_ts


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
def insert_history_skip_action_mock():
    with am.patch('mosbot.usecase.history_sync.insert_history_skip_action') as m:
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


@pytest.mark.asyncio
async def test_save_history_chunk(

):
    pass
