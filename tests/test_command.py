import asynctest as am
import pytest
from click.testing import CliRunner
from unittest import mock

from mosbot import config
from mosbot.__main__ import main
from mosbot.command import BotConfigValueType
from mosbot.handler import history_handler, availability_handler


@pytest.fixture
def check_alembic_in_latest_version_mock(mocker):
    return mocker.patch('mosbot.command.check_alembic_in_latest_version')


@pytest.fixture
def setup_logging_mock(mocker):
    return mocker.patch('mosbot.command.setup_logging')


@pytest.yield_fixture
def save_history_songs_mock():
    with am.patch('mosbot.command.save_history_songs') as m:
        yield m


@pytest.yield_fixture
def save_bot_data_mock():
    with am.patch('mosbot.command.save_bot_data') as m:
        yield m


@pytest.yield_fixture
def load_bot_data_mock():
    with am.patch('mosbot.command.load_bot_data') as m:
        yield m


@pytest.fixture
def bot_mock(mocker):
    return mocker.patch('mosbot.command.Bot')


@pytest.fixture
def dubtrackbotbackend_mock(mocker):
    return mocker.patch('mosbot.command.DubtrackBotBackend')


@pytest.fixture
def asyncio_mock(mocker):
    return mocker.patch('mosbot.command.asyncio')


@pytest.mark.parametrize('input,expected_output', (
        ('{}', {}),
        ('a1', 'a1'),
        ('1', 1),
        ('-1.1', -1.1),
))
def test_botconfigvaluetype(input, expected_output):
    bcvt = BotConfigValueType()
    result = bcvt.convert(input, None, None)
    assert result == expected_output


def test_atest(event_loop):
    runner = CliRunner()

    result = runner.invoke(main, ['atest'])

    assert result.exit_code == 0
    assert result.output.strip() == 'aTest'


@pytest.mark.parametrize('debug_arg,debug', (
        ('--debug', True),
        ('-d', True),
        ('--no-debug', False),
        ('', False),
))
def test_history_sync(
        event_loop,
        check_alembic_in_latest_version_mock,
        setup_logging_mock,
        save_history_songs_mock,
        debug_arg,
        debug
):
    runner = CliRunner()
    args = ['history_sync']
    if debug_arg:
        args.append(debug_arg)

    result = runner.invoke(main, args)

    assert result.exit_code == 0
    assert result.output.strip() == ''

    check_alembic_in_latest_version_mock.assert_called_once_with()
    setup_logging_mock.assert_called_once_with(debug)
    save_history_songs_mock.assert_awaited_once_with()


@pytest.mark.parametrize('args,exit_code,key,value', (
        ([], 2, False, False),
        (['some_key'], 2, False, False),
        (['last_saved_history'], 0, 'last_saved_history', False),
        (['last_saved_history', '-v', '1234'], 0, 'last_saved_history', 1234),
))
def test_config(
        event_loop,
        save_bot_data_mock,
        load_bot_data_mock,
        args,
        exit_code,
        key,
        value,
):
    load_bot_data_mock.return_value = {}
    runner = CliRunner()
    full_args = ['config']
    full_args.extend(args)

    result = runner.invoke(main, full_args)

    assert result.exit_code == exit_code, result.output

    if exit_code:
        save_bot_data_mock.assert_not_awaited()
        load_bot_data_mock.assert_not_awaited()
    elif value:
        save_bot_data_mock.assert_awaited_once_with(key, value)
        load_bot_data_mock.assert_not_awaited()
    else:
        save_bot_data_mock.assert_not_awaited()
        load_bot_data_mock.assert_awaited_once_with(key)


def test_test(
        event_loop,
):
    runner = CliRunner()

    result = runner.invoke(main, ['test'])

    assert result.exit_code == 0


@pytest.mark.parametrize('debug_arg,debug', (
        ('', False),
        ('-d', True),
        ('--no-debug', False),
        ('--debug', True),
))
def test_run(
        event_loop,
        check_alembic_in_latest_version_mock,
        setup_logging_mock,
        bot_mock,
        dubtrackbotbackend_mock,
        asyncio_mock,
        debug_arg,
        debug,
):
    runner = CliRunner()
    args = ['run']
    if debug_arg:
        args.append(debug_arg)

    result = runner.invoke(main, args)

    assert result.exit_code == 0

    check_alembic_in_latest_version_mock.assert_called_once_with()
    setup_logging_mock.assert_called_once_with(debug)

    bot_mock.assert_called_once_with()
    bot_object = bot_mock.return_value

    dubtrackbotbackend_mock.assert_called_once_with(room='master-of-soundtrack')
    dubtrack_backend_object = dubtrackbotbackend_mock.return_value
    dubtrack_backend_object.configure.assert_called_once_with(
        username=config.DUBTRACK_USERNAME,
        password=config.DUBTRACK_PASSWORD,
    )
    bot_object.attach_backend.assert_called_once_with(
        backend=dubtrack_backend_object
    )
    assert bot_object.add_event_handler.mock_calls == [
        mock.call(func=history_handler),
        mock.call(func=availability_handler),
    ]

    asyncio_mock.get_event_loop.assert_called_once_with()
    loop_object = asyncio_mock.get_event_loop.return_value
    loop_object.run_until_complete.assert_called_once_with(
        bot_object.run_forever.return_value
    )
