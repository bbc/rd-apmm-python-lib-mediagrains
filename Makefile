PYTHON=`which python`

DESTDIR=/
PROJECT=mediagrains
MODNAME=mediagrains

all:
	@echo "make source  - Create source package"
	@echo "make install - Install on local system (only during development)"
	@echo "make clean   - Get rid of scratch and byte files"
	@echo "make test    - Test under both versions"

source:
	$(PYTHON) setup.py sdist $(COMPILE)

install:
	$(PYTHON) setup.py install --root $(DESTDIR) $(COMPILE)

clean:
	$(PYTHON) setup.py clean || true
	rm -rf build/ MANIFEST
	rm -rf dist
	rm -rf tox-generated.ini
	find . -name '*.pyc' -delete
	find . -name '*.py,cover' -delete

test:
	tox

.PHONY: test test2 test3 clean install source all
