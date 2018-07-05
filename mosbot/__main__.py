# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import click

from mosbot.command import botcli, botcmd

main = click.CommandCollection(sources=[botcli, botcmd])
"""This is groups all the commands under one so that we can have them together, regardless of the implementation"""

if __name__ == '__main__':  # pragma: no cover
    main()
