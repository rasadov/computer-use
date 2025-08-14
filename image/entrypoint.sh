#!/bin/bash
set -e

./start_all.sh
./novnc_startup.sh

tail -f /dev/null
