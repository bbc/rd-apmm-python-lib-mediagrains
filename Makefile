PYTHON=`which python`
DESTDIR=/
PROJECT=mediagrains
MODNAME=mediagrains

TEST_DEPS=\
	mock

# This is a list of URLs from which dependencies of the package which are not in pip will be fetched
REMOTE_DEPS=\
	git+https://github.com/bbc/nmos-common/

VENV=virtpython
VENV_ACTIVATE=$(VENV)/bin/activate
VENV_MODULE_DIR=$(VENV)/lib/python2.7/site-packages
VENV_TEST_DEPS=$(addprefix $(VENV_MODULE_DIR)/,$(TEST_DEPS))
VENV_INSTALLED=$(VENV_MODULE_DIR)/$(MODNAME).egg-link

all:
	@echo "make source  - Create source package"
	@echo "make install - Install on local system (only during development)"
	@echo "make clean   - Get rid of scratch and byte files"
	@echo "make test    - Tests are nice"

source:
	$(PYTHON) setup.py sdist $(COMPILE)

install:
	$(PYTHON) setup.py install --root $(DESTDIR) $(COMPILE)

clean:
	$(PYTHON) setup.py clean
	rm -rf build/ MANIFEST
	rm -rf $(VENV)
	find . -name '*.pyc' -delete

$(VENV):
	virtualenv $@

rdeps: $(VENV)
	. $(VENV_ACTIVATE); pip install $(REMOTE_DEPS)

$(VENV_TEST_DEPS): $(VENV)
	. $(VENV_ACTIVATE); pip install $(@F)

$(VENV_INSTALLED) : $(VENV) rdeps
	. $(VENV_ACTIVATE); pip install -e .

test: $(VENV_TEST_DEPS) $(VENV_INSTALLED)
	. $(VENV_ACTIVATE); python -m unittest discover -s .

.PHONY: test clean install source rdeps all
