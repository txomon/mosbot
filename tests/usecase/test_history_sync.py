import asynctest as am
import pytest

from mosbot.usecase import save_history_songs
from mosbot.usecase.history_sync import persist_history


@pytest.yield_fixture
def dubtrackws_mock():
    with am.patch('mosbot.usecase.history_sync.DubtrackWS') as m:
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
        mmm = m.return_value.acquire = am.CoroutineMock()
        print(mmm)
        yield m


@pytest.yield_fixture
def save_history_chunk_mock():
    with am.patch('mosbot.usecase.history_sync.save_history_chunk') as m:
        yield m


@pytest.yield_fixture
def save_bot_data_mock():
    with am.patch('mosbot.usecase.history_sync.save_bot_data') as m:
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
