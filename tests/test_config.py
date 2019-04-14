import os

import pytest
from pathlib import Path

from snapshotbackup.exceptions import ConfigFileNotFound
from snapshotbackup.config import _config_basepaths, _config_filename, _get_config_file


@pytest.fixture
def patched_basepaths(monkeypatch, tmpdir):
    basepaths = (tmpdir / 'path/1', tmpdir / 'path/2')
    monkeypatch.setattr('snapshotbackup.config._config_basepaths', basepaths)
    return basepaths


def test_basepaths():
    for _p in _config_basepaths:
        assert isinstance(_p, Path)


def test_config_given(tmpdir):
    configfile = tmpdir / _config_filename
    with pytest.raises(ConfigFileNotFound):
        _get_config_file(configfile)
    open(configfile, 'w').close()
    assert _get_config_file(configfile) == configfile


def test_config(patched_basepaths):
    configfile0 = patched_basepaths[0] / _config_filename
    configfile1 = patched_basepaths[1] / _config_filename
    with pytest.raises(ConfigFileNotFound):
        _get_config_file()
    os.makedirs(patched_basepaths[1], exist_ok=True)
    open(configfile1, 'w').close()
    assert _get_config_file() == configfile1
    os.makedirs(patched_basepaths[0], exist_ok=True)
    open(configfile0, 'w').close()
    assert _get_config_file() == configfile0
