PYTHON2=`which python2.7`
PYTHON3=`which python3`
PYTHON=`which python`
VIRTUALENV=virtualenv
PIP=pip
NOSE2=nose2

DESTDIR=/
PROJECT=mediagrains
MODNAME=mediagrains

TEST_DEPS=\
	mock \
	nose2

# This is a list of URLs from which dependencies of the package which are not in pip will be fetched
REMOTE_DEPS=\
	submodules/nmos-common

VENV2=virtpython2
VENV2_ACTIVATE=$(VENV2)/bin/activate
VENV2_MODULE_DIR=$(VENV2)/lib/python2.7/site-packages
VENV2_TEST_DEPS=$(addprefix $(VENV2_MODULE_DIR)/,$(TEST_DEPS))
VENV2_INSTALLED=$(VENV2_MODULE_DIR)/$(MODNAME).egg-link
VENV2_NMOSCOMMON=$(VENV2_MODULE_DIR)/nmoscommon

VENV3=virtpython3
VENV3_ACTIVATE=$(VENV3)/bin/activate
VENV3_MODULE_DIR=$(wildcard $(VENV3)/lib/python3.*/site-packages)
VENV3_TEST_DEPS=$(addprefix $(VENV3_MODULE_DIR)/,$(TEST_DEPS))
VENV3_INSTALLED=$(VENV3_MODULE_DIR)/$(MODNAME).egg-link
VENV3_NMOSCOMMON=$(VENV3_MODULE_DIR)/nmoscommon

all:
	@echo "make source  - Create source package"
	@echo "make install - Install on local system (only during development)"
	@echo "make clean   - Get rid of scratch and byte files"
	@echo "make test2   - Test under python 2"
	@echo "make test3   - Test under python 3"
	@echo "make test    - Test under both versions"

submodules:
	git submodule init && git submodule update

source:
	$(PYTHON) setup.py sdist $(COMPILE)

install:
	$(PYTHON) setup.py install --root $(DESTDIR) $(COMPILE)

clean:
	$(PYTHON) setup.py clean || true
	rm -rf build/ MANIFEST
	rm -rf $(VENV2)
	rm -rf $(VENV3)
	find . -name '*.pyc' -delete

$(VENV2):
	$(VIRTUALENV) -p $(PYTHON2) $@

rdeps2: $(VENV2) submodules
	. $(VENV2_ACTIVATE); $(PIP) install $(REMOTE_DEPS)

$(VENV2_NMOSCOMMON): rdeps2

$(VENV2_TEST_DEPS): $(VENV2)
	. $(VENV2_ACTIVATE); $(PIP) install $(@F)

$(VENV2_INSTALLED) : $(VENV2_NMOSCOMMON)
	. $(VENV2_ACTIVATE); $(PIP) install -e .

test2: $(VENV2_TEST_DEPS) $(VENV2_INSTALLED)
	. $(VENV2_ACTIVATE); $(NOSE2) --with-coverage --coverage-report=annotate --coverage-report=term --coverage=mediagrains

$(VENV3):
	$(VIRTUALENV) -p $(PYTHON3) $@

rdeps3: $(VENV3) submodules
	. $(VENV3_ACTIVATE); $(PIP) install $(REMOTE_DEPS)

$(VENV3_NMOSCOMMON): rdeps3

$(VENV3_TEST_DEPS): $(VENV3)
	. $(VENV3_ACTIVATE); $(PIP) install $(@F)

$(VENV3_INSTALLED) : $(VENV3_NMOSCOMMON)
	. $(VENV3_ACTIVATE); $(PIP) install -e .

test3: $(VENV3_TEST_DEPS) $(VENV3_INSTALLED)
	. $(VENV3_ACTIVATE); $(NOSE2) --with-coverage --coverage-report=annotate --coverage-report=term --coverage=mediagrains

test: test2 test3

.PHONY: test test2 test3 clean install source rdeps2 rdeps3 all submodules
