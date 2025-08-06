import cv2
import sys
import json
import os
from natsort import natsorted
from pathlib import Path
from glob import glob

CONFIG_FILE = "./config.json"
config = {}

if(os.path.exists(CONFIG_FILE)):
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
else: raise Exception(f"not found {CONFIG_FILE}")

VIDEO_PATH_FILE = config["video_path_file"]
TIME_FILE = config["time_file"]
MEMORY_FILE = config["memory_file"]
ROOT_DIR = config["root_dir"]

# 動画ファイルパスの取得
mp4list = []
with open(VIDEO_PATH_FILE, "r") as f:
    lines = f.readlines()
    # configのroot_dirをカレントディレクトリにした相対パスを取得
    for line in lines:
        mp4list += [path.replace("\\", "/") for path in (glob(line.replace("\n", ""), recursive=True, root_dir=ROOT_DIR))]
    # 相対パスを絶対パスに直す
    mp4list = natsorted([os.path.join(ROOT_DIR, path) for path in mp4list])
for path in mp4list:
    if(os.path.splitext(path)[1].lower() not in [".mp4", ".avi"]):
        raise Exception(f"{path} is not video!")

# スタートのmp4ファイル番号を読み込み、なければ新規生成
video_idx = 0
if(os.path.exists(MEMORY_FILE)):
    with open(MEMORY_FILE, "r") as f:
        info = json.load(f)
    video_idx = info["index"]
else:
    with open(MEMORY_FILE, "w") as f:
        json.dump({"index": 0}, f, indent=2, ensure_ascii=False)
print("start at: " + mp4list[video_idx])

# アノテーション情報ファイルを読み込み、なければ新規生成
times = {}
if(os.path.exists(TIME_FILE)):
    with open(TIME_FILE, "r") as f:
        times = json.load(f)
else:
    with open(TIME_FILE, "w") as f:
        json.dump({}, f, indent=2, ensure_ascii=False)

# cv2で動画読み込み
cap = cv2.VideoCapture(mp4list[video_idx])
if(not cap.isOpened()):
    print("ファイルオープンに失敗しました")
    sys.exit(0)

# ディスプレイサイズの取得
display_width = config["display"]["width"]
display_height = config["display"]["height"]


def forwardVideo(n):
    global video_idx, info, times
    video_idx = ((video_idx + n)%len(mp4list))
    info["index"] = video_idx
    with open(TIME_FILE, "w") as f:
        json.dump(times, f, indent=2, ensure_ascii=False)
    with open(MEMORY_FILE, "w") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)

def putText_japanese(img, text, point, size, color, thickness):
    from PIL import ImageFont, ImageDraw, Image
    import numpy as np
    #Notoフォントとする
    font = ImageFont.truetype("SourceHanSansJP-Medium.otf", size)
    #imgをndarrayからPILに変換
    img_pil = Image.fromarray(img)
    #drawインスタンス生成
    draw = ImageDraw.Draw(img_pil)
    #テキスト描画
    draw.text(point, text, fill=color, font=font, thickness=thickness)
    #PILからndarrayに変換して返す
    return np.array(img_pil)

# nフレーム増減させる
def forwardFrame(n):
    # cap.read実行時に自動で1進むため、フレーム数を-1している
    next_frame = (cap.get(cv2.CAP_PROP_POS_FRAMES)+cap.get(cv2.CAP_PROP_FRAME_COUNT)+n-1)%(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, next_frame)

pre_idx = video_idx
while(cap.isOpened()):
    cv2.namedWindow('Video', cv2.WINDOW_NORMAL)
    if(pre_idx != video_idx):
        cap = cv2.VideoCapture(mp4list[video_idx])
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        pre_idx = video_idx
    ret, frame = cap.read()
    # 動画終了時
    if(not ret):
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        continue
    # 絶対パスを相対パスに直す
    path_rel = str(Path(mp4list[video_idx]).relative_to(ROOT_DIR)).replace("\\", "/")
    # コアタイム辞書の初期化
    if(path_rel not in times):
        times[path_rel] = {"start": -1, "end": -1}
    frame = cv2.resize(frame, (display_width, display_height), interpolation=cv2.INTER_LINEAR)
    frame = putText_japanese(frame, path_rel.split("/")[-2] + "\n" + path_rel.split("/")[-1], (100, display_height-200), size=48, color=(167,127,32), thickness=2)
    frame = putText_japanese(frame, str(int(cap.get(cv2.CAP_PROP_POS_FRAMES))-1), (display_width-250, display_height-150), size=100, color=(127,127,256), thickness=2)
    frame = putText_japanese(frame, f"start={times[path_rel]['start']}", (display_width-250, 100), size=48, color=(255,63,255), thickness=2)
    frame = putText_japanese(frame, f"end={times[path_rel]['end']}", (display_width-250, 175), size=48, color=(255,63,255), thickness=2)
    # 現在フレームがコアであるなら表示
    if(times[path_rel]["start"] <= cap.get(cv2.CAP_PROP_POS_FRAMES) and cap.get(cv2.CAP_PROP_POS_FRAMES) <= times[path_rel]["end"]):
        frame = putText_japanese(frame, "CORE", (500,0), size=64, color=(0,0,255), thickness=2)
    cv2.imshow('Video', frame)
    isExit = False
    while(True):
        # キー取得
        key = cv2.waitKey(25)
        # 始点フレームのアノテーション
        if(key == ord(config["keys"]["annotate_start"])):
            times[path_rel]["start"] = int(cap.get(cv2.CAP_PROP_POS_FRAMES))-1
            forwardFrame(0)
            break
        # 終点フレームのアノテーション
        if(key == ord(config["keys"]["annotate_end"])):
            times[path_rel]["end"] = int(cap.get(cv2.CAP_PROP_POS_FRAMES))-1
            forwardFrame(0)
            break
        # 次フレーム
        if(key == ord(config["keys"]["next_frame"])):
            forwardFrame(1)
            break
        # 前フレーム
        if(key == ord(config["keys"]["pre_frame"])):
            forwardFrame(-1)
            break
        # 次の動画
        if(key == ord(config["keys"]["next_video"])):
            forwardVideo(1)
            break
        # 前の動画
        if(key == ord(config["keys"]["pre_video"])):
            forwardVideo(-1)
            break
        # Escで終了
        if(key & 0xFF == 27):
            isExit = True
            break
    if(isExit): break

cap.release()
cv2.destroyAllWindows()


