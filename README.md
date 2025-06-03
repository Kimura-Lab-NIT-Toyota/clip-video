# clip-video

## Overview
動画データを切り取るPythonプログラム。  
動画の始終フレームをアノテーションする`clip_annotation.py`と、  
アノテーションを元に動画を切り取る`clip.ipynb`から構成されています。  

## Requirements
- Python3
  - opencv-python
  - ffmpeg-python
  - natsort
- ffmpeg
- GUI表示可能な環境

## Usage
木村研NASに上がっている動画が対象であることが前提です。
1. `paths.txt`に、アノテーション対象の動画パスを改行区切りで列挙
2. `clip_annotation.py`を実行し、アノテーションを行う
    - `paths.txt`から動画を読み込む
    - 操作法
      - qキーで動画の始フレームをアノテーション
      - eキーで動画の終フレームをアノテーション
      - dキーで動画を1フレーム進める
      - aキーで動画を1フレーム戻す
      - cキーで次の動画に移動
      - zキーで前の動画に移動
    - 画面に表示されているフレームがアノテーションされたフレームの間であれば、"CORE"が表示されます
3. `clip.ipynb`で、アノテーション情報を元に動画をクリップ
    - クリップされた動画は`clipped_videos`ディレクトリに配置

ファイル名やキー設定などは`config.json`から変更できます。

