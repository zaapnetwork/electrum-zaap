#!/bin/bash

VERSION_STRING=(`grep ELECTRUM_VERSION lib/version.py`)
ELECTRUM_zaap_VERSION=${VERSION_STRING[2]}
ELECTRUM_zaap_VERSION=${ELECTRUM_zaap_VERSION#\'}
ELECTRUM_zaap_VERSION=${ELECTRUM_zaap_VERSION%\'}
export ELECTRUM_zaap_VERSION