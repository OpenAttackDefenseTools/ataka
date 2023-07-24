#!/bin/bash

set -e
set -u

TMPFILE="$(mktemp -d)"
trap "rm -rf '$TMPFILE'" 0               # EXIT
trap "rm -rf '$TMPFILE'; exit 1" 2       # INT
trap "rm -rf '$TMPFILE'; exit 1" 1 15    # HUP TERM

cd "$TMPFILE"
cp -r /ataka/player-cli .
cp "/ataka/ctfconfig/$CTF.py" player-cli/player_cli/ctfconfig.py
pip install -r player-cli/requirements.txt --target player-cli/
python -m zipapp --python "/usr/bin/env python3" --output /data/shared/ataka-player-cli.pyz player-cli/