PYTHON=`which python`

DESTDIR=/
PROJECT=mediagrains
VERSION=0.1.0
MODNAME=mediagrains

all:
	@echo "make source  - Create source package"
	@echo "make install - Install on local system (only during development)"
	@echo "make clean   - Get rid of scratch and byte files"
	@echo "make test    - Test under both versions"
	@echo "make deb     - Create debian package"
	@echo "make rpm     - Create rpm package"

source:
	$(PYTHON) setup.py sdist $(COMPILE)

install:
	$(PYTHON) setup.py install --root $(DESTDIR) $(COMPILE)

clean:
	$(PYTHON) setup.py clean || true
	rm -rf .tox
	rm -rf build/ MANIFEST
	rm -rf dist
	rm -rf deb_dist
	rm -rf tox-generated.ini
	find . -name '*.pyc' -delete
	find . -name '*.py,cover' -delete
	find . -name '__pycache__' -delete

test:
	tox

deb: source
	py2dsc-deb --with-python2=true --with-python3=true ./dist/$(MODNAME)-$(VERSION).tar.gz
	cp ./deb_dist/*.deb ./dist

rpm: source
	$(PYTHON) setup.py bdist_rpm

.PHONY: test test2 test3 clean install source deb rpm all
