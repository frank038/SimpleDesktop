#!/bin/bash
thisdir=$(dirname "$0")
cd $thisdir
./qt5desktop.py &
cd $HOME
