#!/bin/bash
set -e
cd "$(dirname "$0")"

if [ ! -x ".venv-beta/bin/python" ]; then
  python3 -m venv .venv-beta
  .venv-beta/bin/python -m pip install -r requirements.txt
fi

exec .venv-beta/bin/python png_black_converter/app.py
