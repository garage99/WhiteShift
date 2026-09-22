#!/bin/bash
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  osascript -e 'display alert "Python 3が見つかりません" message "Python 3.10以上をインストールしてください。"'
  exit 1
fi

if [ ! -x ".venv-build/bin/python" ]; then
  python3 -m venv .venv-build
fi

. .venv-build/bin/activate
export PYINSTALLER_CONFIG_DIR="$PWD/work/pyinstaller"
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --clean PNGWhiteConverter-macOS.spec

open dist
osascript -e 'display notification "distフォルダに完成しました" with title "WhiteShift"'
