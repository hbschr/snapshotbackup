#!/usr/bin/env python3
"""A setuptools based setup module.

"""

from os.path import abspath, dirname, join
from setuptools import setup


here = abspath(dirname(__file__))
with open(join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    author='heiko huebscher',
    author_email='heiko.huebscher@gmail.com',
    name='snapshotbackup',
    description='backups with `rsync` and `btrfs` snapshots',
    keywords='backup cli commandline',
    license='MIT',
    long_description=long_description,
    long_description_content_type='text/markdown',
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    packages=('snapshotbackup',),
    url='https://github.com/hbschr/snapshotbackup',
    install_requires=[
        'dateparser>=0.7.0',
        'humanfriendly>=4.17',
        'psutil>=5.4.8',
        'python-dateutil>=2.7.2',
        'pytz>=2018.4',  # needed by `dateparser`
    ],
    extras_require={
        'dev': [
            'coverage>=4.5.2',
            'flake8>=3.6.0',
            'pytest >=4.0.1, <4.1.0',
            'pytest-cov>=2.6.0',
            'pytest-mccabe>=0.1',
            'sphinx>=1.8.2',
            'tox>=3.5.3',
        ],
        'ci': [
            'coveralls>=1.5.1',
        ],
        'journald': ['systemd-python>=234'],
    },
    entry_points={
        'console_scripts': [
            'snapshotbackup=snapshotbackup:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Topic :: System :: Archiving :: Backup',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
    ],
)
