# rd-apmm-python-lib-mediagrains

A python library for handling grain-based media in a python-native
style. Please read the poydoc documentation for more details.

Provides constructor functions for various types of grains and classes
that nicely wrap those grains, as well as a full deserialisation
library for GSF format.

## Installing with Python and make

To run the installer run

> make install

to create a redistributable source tarball call

> make source

## Running tests

To run the tests for python2 run

> make test2

to run the tests for python3 run

> make test3

to run both run

> make test

All tests are run inside a virtual environment so as to avoid
polluting the global python environment.

## submodules

This repo currently uses two git submodules. Their checkout is
automated by the Makefile.


submodules/rd-ips-core-lib-cog2

is used to get a header file for processing to make a python file
containing certain enumerated types needed for compatibility with our
C++ implementations.


submodules/nmos-common

is the nmoscommon library used to provide the Timestamp class which is
needed during testing.

