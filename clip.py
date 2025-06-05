import ffmpeg
import json
import cv2
import os
import tqdm

CONFIG_FILE = "./config.json"
config = {}
if(os.path.exists(CONFIG_FILE)):
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
else: raise Exception(f"not found {CONFIG_FILE}")

skip_path = set()

# コアとなる時間を記したjsonを読み込む
with open(config["time_file"], "r") as f:
    coretimes = json.load(f)
# 未記入のパスがないかの確認
for path in list(coretimes.keys()):
    if(coretimes[path]["start"] == -1 or coretimes[path]["end"] == -1 or coretimes[path]["start"] > coretimes[path]["end"]):
        print(f"Skip {path}")
        skip_path.add(path)

if(not os.path.exists(config["clipped_directory"])):
    os.mkdir(config["clipped_directory"])
for path in tqdm.tqdm(list(coretimes.keys())):
    # 改行文字を消去
    path = path.replace("\n", "").replace("\r", "")
    if(path in skip_path): continue
    # 動画ファイルのフレームレートを取得
    cap = cv2.VideoCapture(path)
    # 保存先となるディレクトリ、なければ作成
    dir_path = f"{config['clipped_directory']}/{path.split('/')[-2]}"
    if (not os.path.isdir(dir_path)):
          os.mkdir(dir_path)
    # フレームレートと始終フレームから開始時間と動画長さを計算
    stream = ffmpeg.input(
        path,
        ss=coretimes[path]["start"]/cap.get(cv2.CAP_PROP_FPS),
        t =(coretimes[path]["end"] - coretimes[path]["start"]) / cap.get(cv2.CAP_PROP_FPS),
    ).output(f"{dir_path}/{path.split('/')[-1]}")
    # 保存
    ffmpeg.run(stream, quiet=True)

