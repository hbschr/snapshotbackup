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
        'csboilerplate==0.0.4',
        'dateparser>=0.7.0',
        'python-dateutil>=2.7.2',
        'pytz>=2018.4',  # needed by `dateparser`
        'setuptools-scm>=2.0.0',
    ],
    extras_require={
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
        'Programming Language :: Python :: 3.6',
    ],
)
