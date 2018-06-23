doc: apidoc doctest
	sphinx-build -b html doc doc/build

doctest: apidoc
	sphinx-build -b doctest doc doc/doctest

apidoc:
	sphinx-apidoc -f snapshotbackup -o doc/api

clean-doc:
	rm -rf doc/api doc/build doc/doctest

clean: clean-doc
	rm -rf */__pycache__
	rm -rf .pytest_cache/ .tox/ .eggs/
	rm -f .coverage
	rm -rf build/ dist/

mrproper: clean
	find . -type f -name "*.orig"
	rm -rf *.egg-info/
	rm -rf .env/

lint:
	flake8 .

test:
	pytest

check: lint test
