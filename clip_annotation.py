import cv2
import sys
from natsort import natsorted
import json
import os

CONFIG_FILE = "./config.json"
config = {}

if(os.path.exists(CONFIG_FILE)):
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
else: raise Exception(f"not found {CONFIG_FILE}")

VIDEO_PATH_FILE = config["video_path_file"]
TIME_FILE = config["time_file"]
MEMORY_FILE = config["memory_file"]

# 動画ファイルパスの取得
mp4list = []
with open(VIDEO_PATH_FILE, "r") as f:
    mp4list = f.readlines()
for idx in range(len(mp4list)):
    mp4list[idx] = mp4list[idx].replace("\n", "")

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
    cap.set(cv2.CAP_PROP_POS_FRAMES, (cap.get(cv2.CAP_PROP_POS_FRAMES)+n-1))%(cap.get(cv2.CAP_PROP_FRAME_COUNT))

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
    # コアタイム辞書の初期化
    if(mp4list[video_idx] not in times):
        times[mp4list[video_idx]] = {"start": -1, "end": -1}
    frame = cv2.resize(frame, (display_width, display_height), interpolation=cv2.INTER_LINEAR)
    frame = putText_japanese(frame, mp4list[video_idx].split("/")[-2] + "\n" + mp4list[video_idx].split("/")[-1], (100, 400), size=48, color=(167,127,32), thickness=2)
    frame = putText_japanese(frame, str(cap.get(cv2.CAP_PROP_POS_FRAMES)), (300,500), size=64, color=(167,127,32), thickness=2)
    frame = putText_japanese(frame, f"start={times[mp4list[video_idx]]['start']}", (600, 100), size=32, color=(255,0,0), thickness=2)
    frame = putText_japanese(frame, f"end={times[mp4list[video_idx]]['end']}", (600, 150), size=32, color=(255,0,0), thickness=2)
    # 現在フレームがコアであるなら表示
    if(times[mp4list[video_idx]]["start"] <= cap.get(cv2.CAP_PROP_POS_FRAMES) and cap.get(cv2.CAP_PROP_POS_FRAMES) <= times[mp4list[video_idx]]["end"]):
        frame = putText_japanese(frame, "CORE", (500,0), size=64, color=(0,0,255), thickness=2)
    cv2.imshow('Video', frame)
    isExit = False
    while(True):
        # キー取得
        key = cv2.waitKey(25)
        # 始点フレームのアノテーション
        if(key == ord(config["keys"]["annotate_start"])):
            times[mp4list[video_idx]]["start"] = cap.get(cv2.CAP_PROP_POS_FRAMES)
            forwardFrame(0)
            break
        # 終点フレームのアノテーション
        if(key == ord(config["keys"]["annotate_end"])):
            times[mp4list[video_idx]]["end"] = cap.get(cv2.CAP_PROP_POS_FRAMES)
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


