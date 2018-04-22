doc: doctest apidoc
	sphinx-build -b html doc doc/build

doctest:
	ENV=testing sphinx-build -b doctest doc doc/doctest

apidoc:
	sphinx-apidoc -f btrfsbackup -o doc/api

clean-doc:
	rm -rf doc/api doc/build doc/doctest

clean: clean-doc
	rm -rf btrfs_backup.egg-info/ env/ .pytest_cache/ .tox/
	rm -f .coverage

test:
	ENV=testing pytest
