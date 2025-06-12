# clip-video

## Overview
動画データを切り取るPythonプログラム。  
動画の始終フレームをアノテーションする`clip_annotation.py`と、  
アノテーションを元に動画を切り取る`clip.py`から構成されています。  

## Requirements
- Python3
  - opencv-python
  - ffmpeg-python
  - natsort
- ffmpeg
- GUI表示可能な環境

## Usage
1. `paths.txt`に、アノテーション対象の動画パスを改行区切りで列挙
    - [paths_example.txt](/paths_example.txt)に記述例
    - 絶対パス相対パスどちらも可能
    - 空行は入れないこと
    - ワイルドカード使用可
      - 内部的にはglobモジュールを使用
      - `*`で任意の文字列
        - [paths_example.txt](/paths_example.txt)の6行目では、`./videos/500160-色/`内にある`.mp4`拡張子の動画ファイルを全選択
      - `**`で任意のディレクトリ構成
        - [paths_example.txt](/paths_example.txt)の7行目では、`/home/user/videos/`内にある、サブディレクトリ含めた`.avi`拡張子の動画ファイルを全選択
      - 参考: [「Pythonで条件を満たすパスの一覧を再帰的に取得するglobの使い方」](https://note.nkmk.me/python-glob-usage/)
    - ファイル構成は`**/<動画の分類名>/<動画名>`にすること
      - **は任意のディレクトリ構成
      - 出力時のディレクトリ構成に使用
    - 対応拡張子はmp4とaviの2種類
2. [annotate.py](/annotate.py)を実行し、アノテーションを行う
    - `paths.txt`から動画を読み込む
    - 操作法
      - qキーで動画の始フレームをアノテーション
      - eキーで動画の終フレームをアノテーション
      - dキーで動画を1フレーム進める
      - aキーで動画を1フレーム戻す
      - cキーで次の動画に移動
      - zキーで前の動画に移動
      - Escキーで終了
    - 画面に表示されているフレームがアノテーションされたフレームの間であれば、"CORE"が表示されます
3. [clip.py](/clip.py)で、アノテーション情報を元に動画をクリップ
    - クリップされた動画は`clipped_videos`ディレクトリに配置
    - アノテーション情報が不正な値である場合や、出力先に同名ファイルがある場合には処理を飛ばす

ファイル名やキー設定などは`config.json`から変更できます。

