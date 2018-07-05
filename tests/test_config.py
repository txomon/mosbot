import os
import pytest

from mosbot.config import get_config


@pytest.yield_fixture
def clean_environ():
    os.environ, saved = {}, os.environ
    yield os.environ
    os.environ = saved


@pytest.yield_fixture
def clean_workdir(tmpdir):
    old_dir = os.getcwd()
    os.chdir(tmpdir)
    yield tmpdir
    os.chdir(old_dir)


@pytest.mark.parametrize('file_content, file_result', (
        (None, EnvironmentError),
        ('', EnvironmentError),
        ('{}', EnvironmentError),
        ('{"variable": "123}', EnvironmentError),
        ('{"variable": null}', None),
        ('{"variable": 123}', 123),
        ('{"variable": 123, "other": "aa"}', 123),
        ('{"variable": "123"}', '123'),
        ('{"variable": "asdf"}', 'asdf'),
        ('{"variable": {"a": "123"}}', {'a': '123'}),
        ('{"variable": ["a", "123"]}', ['a', '123']),
        ('{"variable": ["a", 123]}', ['a', 123]),
), ids=(
        'file__no_file',
        'file__empty_file',
        'file__empty_object',
        'file__malformed_json',
        'file__null',
        'file__number',
        'file__number_and_more',
        'file__number_string',
        'file__string',
        'file__dict',
        'file__list',
        'file__list_varied',
))
@pytest.mark.parametrize('environ_content, environ_result', (
        ({}, EnvironmentError),
        ({'VARIABLE': ''}, ''),
        ({'VARIABLE': 'null'}, None),
        ({'VARIABLE': '123'}, 123),
        ({'VARIABLE': '"123"'}, '123'),
        ({'VARIABLE': 'asdf'}, 'asdf'),
        ({'VARIABLE': '{"a": "123"}'}, {"a": "123"}),
        ({'VARIABLE': '["a", "123"]'}, ["a", "123"]),
        ({'VARIABLE': '["a", 123]'}, ["a", 123]),
), ids=(
        'environ__not_set',
        'environ__empty_string',
        'environ__null',
        'environ__number',
        'environ__number_string',
        'environ__string',
        'environ__dict',
        'environ__list',
        'environ__list_varied',
))
@pytest.mark.parametrize('args_content, args_result', (
        (tuple(), EnvironmentError),
        ((None,), None),
        ((123,), 123),
        (('asdf',), 'asdf'),
        (({"a": "123"},), {"a": "123"}),
        ((["a", "123"],), ["a", "123"]),
        ((["a", 123],), ["a", 123]),
), ids=(
        'args__no_default',
        'args__none',
        'args__number',
        'args__string',
        'args__dict',
        'args__list',
        'args__list_varied'
))
def test_get_config(
        clean_environ,
        clean_workdir,
        file_content,
        file_result,
        environ_content,
        environ_result,
        args_content,
        args_result,
):
    if file_content is not None:
        config_file = clean_workdir.join('config.json')
        config_file.write(file_content)
    clean_environ.update(environ_content)

    result = environ_result
    if result == EnvironmentError:
        result = file_result
        if result == EnvironmentError:
            result = args_result

    if isinstance(result, type) and issubclass(result, Exception):
        with pytest.raises(result):
            get_config('VARIABLE', *args_content)
    else:
        assert result == get_config('VARIABLE', *args_content)
