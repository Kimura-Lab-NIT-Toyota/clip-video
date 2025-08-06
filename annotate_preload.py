import cv2
import sys
import json
import os
from natsort import natsorted
from pathlib import Path
from glob import glob
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import numpy as np

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

PRELOAD_AHEAD  = config["preload"]["ahead"]
PRELOAD_BEHIND = config["preload"]["behind"]
frame_cache = {}
cache_lock = threading.Lock()

# 動画を最初から最後まで読み込む
def loadVideo(video_path):
    print(f"[Backgound Task] Start Loading: {os.path.basename(video_path)}")
    start_time = time.time()
    cap = cv2.VideoCapture(video_path)
    if(not cap.isOpened):
        print(f"[Error] Failed to open {video_path}")
        return None
    compressed_frames = []
    while(True):
        ret, frame = cap.read()
        if(not ret): break
        ret, encoded_frame = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if(ret): compressed_frames.append(encoded_frame)
    cap.release()
    end_time = time.time()
    print(f"[Backgound Task] Finished loading {os.path.basename(video_path)} ({len(compressed_frames)}) in {(end_time-start_time):.2f}s.")
    return compressed_frames

# 複数動画を並列で事前読み込みし、キャッシュを管理する
class PreloadWorker:
    def __init__(self, max_workers):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_futures = {}
        self.lock = threading.Lock()
    def _on_load_complete(self, path, future):
        with self.lock:
            if(not future.cancelled()):
                frames = future.result()
                if(frames):
                    with cache_lock:
                        frame_cache[path] = frames
            self.active_futures.pop(path, None)
    def update_targets(self, new_target_paths):
        with self.lock:
            current_targets = set(self.active_futures.keys())
            cached_paths = set(frame_cache.keys())
            paths_to_load = new_target_paths - cached_paths - current_targets
            # 新しく読み込むパスを決定
            for path in paths_to_load:
                print(f"[Worker] Submitting task for {os.path.basename(path)}")
                future = self.executor.submit(loadVideo, path)
                future.add_done_callback(lambda f, p=path: self._on_load_complete(p, f))
                self.active_futures[path] = future
            # 範囲外になったキャッシュを削除
            paths_to_evict = cached_paths - new_target_paths
            with cache_lock:
                for path in paths_to_evict:
                    print(f"[Worker] Evicting from cache: {os.path.basename(path)}")
                    del frame_cache[path]
            # 範囲外になった進行中のタスクはキャンセル
            paths_to_cancel = current_targets - new_target_paths
            for path in paths_to_cancel:
                print(f"[Worker] Cancelling task for: {os.path.basename(path)}")
                self.active_futures[path].cancel()
    def stop(self):
        print("[Worker] Shutting down...")
        self.executor.shutdown(wait=True, cancel_futures=True)
    

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


frame_list = []
frame_idx = 0

# nフレーム増減させる
def forwardFrame(n):
    global frame_idx
    frame_idx = (frame_idx + n) % len(frame_list)

# 動画をn個進める
def forwardVideo(n):
    global frame_list, frame_idx, video_idx
    video_idx = (video_idx + n) % len(mp4list)
    current_video_path = mp4list[video_idx]
    print(f"\nSwitching to: {os.path.basename(current_video_path)}")
    with cache_lock:
        if(current_video_path in frame_cache):
            print("--> Found in cache! Switching instantly.")
            frame_list = frame_cache[current_video_path]
        else:
            print("--> Not in cache. Loading now...")
            frame_list = loadVideo(current_video_path)
            if(frame_list): frame_cache[current_video_path] = frame_list
    frame_idx = 0
    paths_to_keep = {current_video_path}
    for i in range(1, PRELOAD_AHEAD + 1): paths_to_keep.add(mp4list[(video_idx+i)%len(mp4list)])
    for i in range(1, PRELOAD_BEHIND + 1): paths_to_keep.add(mp4list[(video_idx-i+len(mp4list))%len(mp4list)])
    preload_worker.update_targets(paths_to_keep)
    info["index"] = video_idx
    with open(TIME_FILE, "w") as f:
        json.dump(times, f, indent=2, ensure_ascii=False)
    with open(MEMORY_FILE, "w") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)

# frame_idxに応じたフレーム画像を取得
def getFrame():
    if(not frame_list): return None
    encoded_frame = frame_list[frame_idx]
    frame = cv2.imdecode(np.frombuffer(encoded_frame, dtype=np.uint8), cv2.IMREAD_COLOR)
    return frame

preload_worker = PreloadWorker(max_workers=PRELOAD_AHEAD+PRELOAD_BEHIND)

try:
    forwardVideo(0)
    while True:
        frame = getFrame()
        if(frame is None):
            print("No frames to display. Exiting.")
            break        
        cv2.namedWindow('Video', cv2.WINDOW_NORMAL)
        # 絶対パスを相対パスに直す
        path_rel = str(Path(mp4list[video_idx]).relative_to(ROOT_DIR)).replace("\\", "/")
        # コアタイム辞書の初期化
        if(path_rel not in times):
            times[path_rel] = {"start": -1, "end": -1}
        frame = cv2.resize(frame, (display_width, display_height), interpolation=cv2.INTER_LINEAR)
        frame = putText_japanese(frame, path_rel.split("/")[-2] + "\n" + path_rel.split("/")[-1], (100, display_height-200), size=48, color=(167,127,32), thickness=2)
        frame = putText_japanese(frame, str(frame_idx), (display_width-250, display_height-150), size=100, color=(127,127,256), thickness=2)
        frame = putText_japanese(frame, f"start={times[path_rel]['start']}", (display_width-250, 100), size=48, color=(255,63,255), thickness=2)
        frame = putText_japanese(frame, f"end={times[path_rel]['end']}", (display_width-250, 175), size=48, color=(255,63,255), thickness=2)
        # 現在フレームがコアであるなら表示
        if(times[path_rel]["start"] <= frame_idx and frame_idx <= times[path_rel]["end"]):
            frame = putText_japanese(frame, "CORE", (500,0), size=64, color=(0,0,255), thickness=2)
        cv2.imshow("Video", frame)
        isExit = False
        while(True):
            # キー取得
            key = cv2.waitKey(25)
            # 始点フレームのアノテーション
            if(key == ord(config["keys"]["annotate_start"])):
                times[path_rel]["start"] = frame_idx
                break
            # 終点フレームのアノテーション
            if(key == ord(config["keys"]["annotate_end"])):
                times[path_rel]["end"] = frame_idx
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
finally:
    preload_worker.stop()
    cv2.destroyAllWindows()


