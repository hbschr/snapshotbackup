clean:
	rm -rf btrfs_backup.egg-info/ env/ .pytest_cache/ .tox/
	rm -f .coverage

test:
	ENV=testing pytest
