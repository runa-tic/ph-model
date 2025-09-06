#!/bin/bash
cd "$(dirname "$0")/dist"
./crypto-fetch "$@"
read -p "Press Enter to close..."
