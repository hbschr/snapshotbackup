#!/usr/bin/env python3
"""A setuptools based setup module.

"""

from setuptools import setup

setup(
    name='snapshotbackup',
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    description='A sample Python project',
    packages=('snapshotbackup',),
    install_requires=[
        'dateparser>=0.7.0',
        'python-dateutil>=2.7.2',
        'pytz>=2018.4',  # needed by `dateparser`
    ],
    entry_points={
        'console_scripts': [
            'snapshotbackup=snapshotbackup:main',
        ],
    },
)
