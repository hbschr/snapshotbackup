#!/usr/bin/env python3
"""A setuptools based setup module.

"""

from setuptools import setup

setup(
    name='snapshotbackup',
    version='0.0.0',
    description='A sample Python project',
    packages=('snapshotbackup',),
    install_requires=[
        'python-dateutil>=2.7.2',
        'dateparser>=0.7.0',
    ],
)
