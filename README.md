# WhiteShift

Mimaki RasterLinkで白版を生成する際、完全な白と重なった箇所の白版抜けを防ぐデスクトップアプリです。PNG/JPEG内の RGB `#FFFFFF` または `#FEFEFE` を `#FCFCFC` に変換します。透明・半透明を含む alpha 値は変更しません。

PSDは8bit RGB/CMYKに対応します。表示結果を1枚の「統合画像」レイヤーへまとめ、RGBは `#FFFFFF` と `#FEFEFE` を `#FCFCFC`、CMYKはそれらに相当する白を `C0 M0 Y0 K1%` に変換します。透明度はalphaチャンネルとして保持します。16bit/32bit PSDはベータ版では読み込みません。

## 主な機能

- PNG/JPEG/PSDのドラッグ＆ドロップ／ファイル選択（複数対応・ウィンドウ全体で受付）
- JPEG入力は色を完全一致で保持できるRGB PNGへ変換して保存
- 出力はRGB（PNG）またはCMYK（PSD）を選択可能
- RGBからCMYKへの変換は選択したICCプロファイルを使用し、PSDへ埋め込み
- macOS/Windowsの標準カラープロファイルフォルダからCMYK ICCを自動検出
- 元画像と処理後画像の左右プレビュー（72 dpi相当の表示、ウィンドウにフィット）
- 実際の変更対象をシアンで確認できる表示モード（保存画像には反映されません）
- 変換ピクセル数の表示と一括書き出し
- `sample.png` を `sample-.png` として保存
- `sample.jpg` を `sample-.png` として保存
- 前回の保存先をOS標準設定に記憶
- ICCプロファイル、dpi、PNGテキスト情報を可能な範囲で保持
- 元画像および既存の出力ファイルを上書きしない安全設計

## 動作環境

- 64-bit Python 3.11以上を推奨
- macOS / Windows

## セットアップと起動

ターミナル（WindowsではPowerShell）でこのフォルダへ移動し、仮想環境を作成します。

### macOS

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python png_black_converter/app.py
```

### Windows

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python png_black_converter\app.py
```

一覧へPNGを追加し、必要に応じてシアン確認表示を切り替えます。「書き出し」で保存先フォルダを選ぶと、一覧の全画像を書き出します。同名ファイルが既にある場合は一括処理を中止し、上書きしません。

## テスト

```sh
python -m unittest test_core.py
```

## Windows版 `.exe` の作成

PyInstallerは別OS向けのクロスビルドに対応しないため、Windows 10/11上で作成してください。64-bit Python 3.11以上をインストールしたWindows PCで `build_windows.bat` をダブルクリックします。

```bat
build_windows.bat
```

必要なビルド環境は `.venv-build` に自動作成され、完成品は次の場所に生成されます。

```text
dist\WhiteShift.exe
```

これはコンソール画面を表示しない単一ファイルのGUI実行形式です。CMYKプロファイルはWindowsの `%WINDIR%\System32\spool\drivers\color` から自動検出し、見つからない場合はアプリ画面から `.icc` / `.icm` を選択します。Windows SmartScreenやウイルス対策ソフトの警告を抑えて第三者へ配布する場合は、別途コード署名証明書による署名を推奨します。

## Mac版 `.app` の作成と起動

完成済みの `WhiteShift.app` はFinderでダブルクリックして起動できます。自分で再ビルドする場合は、`build_macos.command` をダブルクリックしてください。初回のみ、右クリックして「開く」が必要になる場合があります。必要な環境は `.venv-build` に作られ、完成品は `dist/WhiteShift.app` に生成されます。

署名していないアプリを別のMacへ配布した場合、受け取った側でも初回は右クリックして「開く」が必要です。通常のダブルクリックだけで警告なく配布するには、Apple Developer IDによるコード署名と公証が必要です。

## Macベータ版をアプリ化せずに試す

`run_beta_macos.command` をダブルクリックします。初回だけ必要なライブラリを自動導入するため、インターネット接続が必要です。macOSに止められた場合は、ファイルを右クリックして「開く」を選択してください。シアン確認表示は初期状態でONです。

注意: PNGを安全にRGBAへ展開して保存するため、元画像がパレット形式などの場合、ピクセルの見た目と alpha は維持されますが、内部のカラーモードはRGBAになります。未知の独自PNGチャンクまで完全に複製するものではありません。
