import click

from mosbot.__main__ import main


def test_main_module():
    assert isinstance(main, click.CommandCollection)
