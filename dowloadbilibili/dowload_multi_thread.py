import subprocess
import sys
import shutil
import os
import argparse
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

# ==================== 配置区 ====================
DOWNLOAD_DIR = r"E:\bilibili"
LIST_FILE = Path(__file__).parent / "list"
# 这里填入了你之前查到的 ffmpeg 路径
FFMPEG_PATH = r"C:\Users\she_donot_like\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe"
# 留空不使用 Cookie，避免报错
COOKIES_BROWSER = "" 
# 最大并发线程数（保守限制，避免触发网站反爬）
MAX_THREADS = 3
# ===============================================

def check_ffmpeg():
    """检查 ffmpeg 是否可用，返回 ffmpeg 路径或 None"""
    if FFMPEG_PATH and Path(FFMPEG_PATH).exists():
        return FFMPEG_PATH

    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path

    script_dir = Path(__file__).parent
    local_ffmpeg = script_dir / "ffmpeg.exe"
    if local_ffmpeg.exists():
        return str(local_ffmpeg)

    try:
        result = subprocess.run(
            ["where", "ffmpeg"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0].strip()
    except Exception:
        pass

    print("警告: 未检测到 ffmpeg！这将导致视频和音频分离，无法合并。")
    print("请在配置区设置 FFMPEG_PATH 或将 ffmpeg.exe 放在脚本同目录。")
    print("-" * 50)
    return None

def print_ffmpeg_info(ffmpeg_path):
    """打印 ffmpeg 信息"""
    if ffmpeg_path:
        print(f"ffmpeg 路径: {ffmpeg_path}")
    else:
        print("ffmpeg: 未找到")

def parse_thread_count(user_threads=None):
    """解析并校验线程数"""
    import multiprocessing
    
    default_threads = max(1, multiprocessing.cpu_count() // 2)
    
    if user_threads is not None:
        if user_threads < 1:
            print(f"警告: 线程数必须 >= 1，使用默认值 {default_threads}")
            return default_threads
        if user_threads > MAX_THREADS:
            print(f"警告: 线程数 {user_threads} 超过最大限制 {MAX_THREADS}，使用最大值 {MAX_THREADS}")
            return MAX_THREADS
        return user_threads
    
    calculated = min(default_threads, MAX_THREADS)
    print(f"使用默认线程数: {calculated} (CPU核心数的一半，最大不超过 {MAX_THREADS})")
    return calculated

def download_video(url, ffmpeg_path=None, use_cookies=True, retries=2, thread_id=1):
    """下载单个视频，支持重试"""
    cmd = [
        sys.executable, "-m", "yt_dlp",
    ]
    
    if ffmpeg_path:
        cmd.extend(["--ffmpeg-location", ffmpeg_path])

    cmd.extend([
        "-P", DOWNLOAD_DIR,
        "-f", "bestvideo+bestaudio/best",
        "--merge-output-format", "mkv",
        "--no-mtime",
        "--write-auto-sub",
        "--sub-langs", "zh.*,zh-Hans",
        "--embed-subs",
        "--sub-format", "srt",
        "--write-thumbnail",
    ])

    if use_cookies and COOKIES_BROWSER:
        cmd.extend(["--cookies-from-browser", COOKIES_BROWSER])

    cmd.append(url)

    env = os.environ.copy()
    if ffmpeg_path:
        ffmpeg_dir = str(Path(ffmpeg_path).parent)
        env["PATH"] = ffmpeg_dir + os.pathsep + env.get("PATH", "")

    for attempt in range(1, retries + 1):
        print(f"\n[线程{thread_id}] 正在下载: {url} (尝试 {attempt}/{retries})")
        print("-" * 50)
        
        result = subprocess.run(cmd, env=env)
        
        if result.returncode == 0:
            print(f"\n[线程{thread_id}] 下载完成: {url}")
            return True
        else:
            print(f"\n[线程{thread_id}] 下载失败 (尝试 {attempt}/{retries}): {url}")
            if attempt < retries:
                print(f"[线程{thread_id}] 等待 10 秒后重试...")
                import time
                time.sleep(10)
            
    return False

def archive_list_files(success_urls, failed_urls):
    """归档 list 文件：成功的放 list_history，失败的保留在新 list"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if success_urls:
        history_name = f"list_history_{timestamp}"
        history_path = LIST_FILE.parent / history_name
        history_path.write_text("\n".join(success_urls) + "\n", encoding="utf-8")
        print(f"已归档成功下载列表: {history_name} ({len(success_urls)} 个)")

    if failed_urls:
        LIST_FILE.write_text("\n".join(failed_urls) + "\n", encoding="utf-8")
        print(f"下载失败的 {len(failed_urls)} 个链接已保留在 list 文件中")
    else:
        LIST_FILE.write_text("", encoding="utf-8")
        print("所有视频下载成功，已创建空 list 文件")

def read_list_file():
    """读取 list 文件，返回链接列表"""
    if not LIST_FILE.exists():
        print(f"list 文件不存在: {LIST_FILE}")
        print("正在创建空的 list 文件...")
        LIST_FILE.write_text("", encoding="utf-8")
        print("请在 list 文件中添加要下载的视频链接（每行一个），然后重新运行脚本。")
        return None

    content = LIST_FILE.read_text(encoding="utf-8").strip()
    if not content:
        print(f"list 文件为空: {LIST_FILE}")
        print("请在 list 文件中添加要下载的视频链接（每行一个），然后重新运行脚本。")
        return None

    urls = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]
    if not urls:
        print("list 文件中没有找到有效的链接（# 开头的行为注释）。")
        print("请添加要下载的视频链接，然后重新运行脚本。")
        return None

    return urls

def main():
    parser = argparse.ArgumentParser(description="Bilibili 视频批量下载工具 (Windows 多线程版)")
    parser.add_argument("-threads", type=int, default=None,
                       help=f"并发线程数 (1-{MAX_THREADS})，默认为 CPU 核心数的一半（最大不超过 {MAX_THREADS}）")
    args = parser.parse_args()

    thread_count = parse_thread_count(args.threads)

    print("=" * 50)
    print("Bilibili 视频下载工具 (Windows 多线程版)")
    print(f"下载目录: {DOWNLOAD_DIR}")
    print(f"列表文件: {LIST_FILE}")
    print(f"并发线程: {thread_count}")
    print("=" * 50)

    ffmpeg_path = check_ffmpeg()
    print_ffmpeg_info(ffmpeg_path)

    Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)

    urls = read_list_file()
    if urls is None:
        return

    print(f"\n共 {len(urls)} 个视频待下载")

    if thread_count > 1:
        print("注意: 多线程模式下已自动禁用 Cookie 读取，以避免浏览器锁冲突")

    success_urls = []
    failed_urls = []
    results = {}

    use_cookies = thread_count == 1

    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        future_to_url = {
            executor.submit(download_video, url, ffmpeg_path, use_cookies, thread_id=i+1): url
            for i, url in enumerate(urls)
        }

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                if future.result():
                    success_urls.append(url)
                else:
                    failed_urls.append(url)
            except Exception as e:
                print(f"\n[异常] 处理 {url} 时出错: {e}")
                failed_urls.append(url)

    archive_list_files(success_urls, failed_urls)

    print(f"\n{'=' * 50}")
    print(f"全部完成！成功 {len(success_urls)}/{len(urls)}")
    print(f"文件位置: {DOWNLOAD_DIR}")

    if failed_urls:
        print(f"\n以下链接下载失败，已保留在 list 文件中:")
        for url in failed_urls:
            print(f"  - {url}")

if __name__ == "__main__":
    main()
