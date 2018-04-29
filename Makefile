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
	rm -rf */__pycache__
	rm -f .coverage

mrproper: clean
	rm -rf .env/
	rm -rf build/ dist/

lint:
	flake8 .

test:
	pytest

check: lint test
