# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

from setuptools import find_packages, setup

setup(
    name='mosbot',
    version='0.0.1',
    description='Mos bot',
    long_description=open('README.rst').read(),
    url='https://github.com/txomon/mosbot',
    author='Javier Domingo Cansino',
    author_email='javierdo1@gmail.com',
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
    ],
    packages=find_packages(),
    python_requires='>=3.6',
    include_package_data=True,
    zip_safe=False,
    keywords=['dubtrack', 'bot', 'mos', 'master-of-soundtrack'],
    entry_points={
        'console_scripts': [
            'bot=mosbot.__main__:main'
        ]
    },
    install_requires=[
        'abot >= 0.0.1a1.dev15',
        'aiopg',
        'alembic',
        'asyncio-extras',
        'click',
        'sqlalchemy',
    ]
)
