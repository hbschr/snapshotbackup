doc: doctest apidoc
	sphinx-build -b html doc doc/build

doctest:
	sphinx-build -b doctest doc doc/doctest

apidoc:
	sphinx-apidoc -f snapshotbackup -o doc/api

clean-doc:
	rm -rf doc/api doc/build doc/doctest

clean: clean-doc
	rm -rf *.egg-info/ .pytest_cache .tox/
	rm -f .coverage

mrproper: clean
	rm -rf .env/

lint:
	flake8 .

test:
	ENV=testing pytest

check: lint test
