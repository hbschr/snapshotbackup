import configparser
import datetime
import pytest
from unittest.mock import patch, Mock

from snapshotbackup.cache import _get_stats_parser, get_last_run, set_last_run


@pytest.fixture
def patched_cache_dir(monkeypatch, tmpdir):
    monkeypatch.setattr('snapshotbackup.cache._CACHE_DIR', tmpdir)
    monkeypatch.setattr('snapshotbackup.cache._STAT_FILE', tmpdir / 'stat.ini')


@patch('configparser.ConfigParser', return_value=Mock())
def test_get_stats_parser(mockedConfigParser):
    assert _get_stats_parser() == mockedConfigParser()
    mockedConfigParser().read.assert_called_once()


@patch('snapshotbackup.cache._get_stats_parser', return_value=configparser.ConfigParser())
def test_get_last_run(mockedConfigParser):
    parser = mockedConfigParser()
    assert get_last_run('name') is None
    parser.add_section('name')
    assert get_last_run('name') is None
    parser.set('name', 'last_run', '1989-11-09')
    assert get_last_run('name') == datetime.datetime(1989, 11, 9)


def test_set_last_run(patched_cache_dir):
    set_last_run('name', '1989-11-09')
    assert get_last_run('name') == datetime.datetime(1989, 11, 9)


@patch('snapshotbackup.cache._get_stats_parser', return_value=configparser.ConfigParser())
def test_set_last_run_section_exists(mockedConfigParser, patched_cache_dir):
    parser = mockedConfigParser()
    parser.add_section('name')
    set_last_run('name', '1989-11-09')
    assert get_last_run('name') == datetime.datetime(1989, 11, 9)
