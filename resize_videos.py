import os
import sys
import ffmpeg  # ffmpeg-pythonライブラリをインポート
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from natsort import natsorted

# --- 設定 ---
# 処理対象とする動画の拡張子
SUPPORTED_EXTENSIONS = [".mp4", ".avi", ".mov", ".mkv"]


# 1つの動画ファイルをリサイズする
def resize_video_worker(input_path, output_path):
    try:
        (
            ffmpeg
            .input(str(input_path))
            .filter("scale", "iw/2", -1)
            .output(str(output_path), **{"c:a": "copy"})
            .overwrite_output()
            # エラー出力をキャプチャし、成功時は何も表示しない
            .run(quiet=True, capture_stdout=False, capture_stderr=True)
        )
        return True, None
    except ffmpeg.Error as e:
        # ffmpeg-pythonがエラーを発生させた場合
        error_message = e.stderr.decode("utf8", errors="ignore").strip()
        if output_path.exists():
            os.remove(output_path)
        return False, error_message

# 指定されたディレクトリ内の動画を再帰的に、かつ並列で処理する
def process_directory(source_root, dest_root):
    source_path = Path(source_root)
    dest_path = Path(dest_root)

    if not source_path.is_dir():
        print(f"[Error] Source directory not found: {source_root}")
        return

    print(f"Source: {source_path.resolve()}")
    print(f"Destination: {dest_path.resolve()}")
    print("-" * 30)

    # 処理タスクを事前にリストアップ
    tasks = []
    print("Searching for video files...")
    for input_file in natsorted(source_path.rglob("*")):
        if input_file.is_file() and input_file.suffix.lower() in SUPPORTED_EXTENSIONS:
            relative_path = input_file.relative_to(source_path)
            output_file = dest_path / relative_path
            output_file.parent.mkdir(parents=True, exist_ok=True)
            tasks.append((input_file, output_file))

    if not tasks:
        print("No video files found to process.")
        return

    total_tasks = len(tasks)
    print(f"Found {total_tasks} videos. Starting parallel processing...")

    # タスクを並列処理
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        future_to_task = {
            executor.submit(resize_video_worker, in_path, out_path): in_path
            for in_path, out_path in tasks
        }
        processed_count = 0
        # 完了したものから順に結果を処理する
        for future in as_completed(future_to_task):
            processed_count += 1
            input_path = future_to_task[future]            
            try:
                success, error_message = future.result()
                if success:
                    print(f"[{processed_count}/{total_tasks}] Success: {input_path.name}")
                else:
                    print(f"[{processed_count}/{total_tasks}] Failed: {input_path.name}\n   Error: {error_message}")
            except Exception as e:
                print(f"[{processed_count}/{total_tasks}] An unexpected error occurred with {input_path.name}: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("使い方: python resize_videos.py <入力元ディレクトリ> <出力先ディレクトリ>")
        sys.exit(1)
        
    src_dir = sys.argv[1]
    dst_dir = sys.argv[2]
    
    process_directory(src_dir, dst_dir)
    
    print("\nAll tasks completed!")