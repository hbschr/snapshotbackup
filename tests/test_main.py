import btrfsbackup


def test_main():
    assert 'main' in dir(btrfsbackup)
    assert btrfsbackup.main()
