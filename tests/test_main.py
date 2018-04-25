import btrfsbackup


def test_main():
    assert 'make_backup' in dir(btrfsbackup)
