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
        'argcomplete>=1.11.1',
        'dateparser>=1.2.2',
        'humanfriendly>=10.0',
        'psutil>=7.2.2',
        'python-dateutil>=2.9.0.post0',
        'xdg>=6.0.0',
    ],
    extras_require={
        'dev': [
            'coverage>=7.13.2',
            'flake8>=7.3.0',
            'pytest>=9.0.2',
            'pytest-cov>=7.0.0',
            'pytest-mccabe>=2.0',
            'sphinx>=2.0.1',
            'tox>=4.34.1',
        ],
        'journald': ['systemd-python>=235'],
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
        'Programming Language :: Python :: 3.13',
    ],
)
