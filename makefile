doc: apidoc doctest
	sphinx-build -b html doc doc/build

doctest: apidoc
	sphinx-build -b doctest doc doc/doctest

apidoc:
	sphinx-apidoc -f snapshotbackup -o doc/api

lint:
	flake8 .

test:
	pytest

check: lint test doc
	$(MAKE) demo

.PHONY: demo
demo:
	$(MAKE) -f makefile.demo clean
	$(MAKE) -f makefile.demo test

clean-doc:
	rm -rf doc/api doc/build doc/doctest

clean: clean-doc
	rm -rf __pycache__ */__pycache__
	rm -rf .pytest_cache/ .tox/ .eggs/
	rm -f .coverage
	rm -rf build/ dist/

distclean: clean
	rm -rf *.egg-info/
	rm -rf .env/
