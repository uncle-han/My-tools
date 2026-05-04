import subprocess
import sys
import shutil
import os
import time
from pathlib import Path
from datetime import datetime

# ==================== 配置区 ====================
DOWNLOAD_DIR = str(Path.home() / "bilibili")
LIST_FILE = Path(__file__).parent / "list"
FFMPEG_PATH = ""
COOKIES_BROWSER = ""
# ===============================================

def check_ffmpeg():
    """检查 ffmpeg 是否可用，返回 ffmpeg 路径或 None"""
    if FFMPEG_PATH and Path(FFMPEG_PATH).exists():
        return FFMPEG_PATH

    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path

    script_dir = Path(__file__).parent
    local_ffmpeg = script_dir / "ffmpeg"
    if local_ffmpeg.exists():
        return str(local_ffmpeg)

    print("=" * 60)
    print("⚠️  警告: 未检测到 ffmpeg！")
    print("=" * 60)
    print("未安装 ffmpeg 将导致：")
    print("  - 视频和音频分离，无法合并为单个文件")
    print("  - 无法生成缩略图")
    print("")
    print("📖 请查看 README_mac.md 文件获取安装帮助：")
    print("   1. 自动安装方法（推荐）")
    print("   2. 手动安装方法")
    print("   3. 如何配置 FFMPEG_PATH")
    print("=" * 60)
    return None

def print_ffmpeg_info(ffmpeg_path):
    """打印 ffmpeg 信息"""
    if ffmpeg_path:
        print(f"ffmpeg 路径: {ffmpeg_path}")
    else:
        print("ffmpeg: 未找到")

def wait_for_file_unlock(file_path, max_wait=30, check_interval=1):
    """等待文件不再被系统占用，最多等待max_wait秒，每隔check_interval秒检查一次"""
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"文件不存在: {file_path}")
        return False

    for i in range(max_wait):
        try:
            # macOS 和 Linux 上尝试以读写方式打开文件来检查是否被占用
            with open(file_path, 'r+b') as f:
                f.seek(0, 2)
            return True
        except (PermissionError, OSError, IOError) as e:
            if i == 0:
                print(f"文件被占用，等待释放: {file_path.name}")
            else:
                print(f"等待中... ({i+1}/{max_wait}s)")
            time.sleep(check_interval)

    print(f"超时: 文件 {file_path.name} 在 {max_wait}s 后仍被占用")
    return False

def extract_thumbnail(video_path, ffmpeg_path, output_path=None):
    """从视频第一帧提取缩略图"""
    if output_path is None:
        output_path = str(Path(video_path).with_suffix(".jpg"))

    cmd = [
        ffmpeg_path,
        "-ss", "00:00:00",
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        "-y",
        output_path,
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if result.returncode == 0:
        print(f"缩略图已生成: {output_path}")
        return output_path
    else:
        print(f"生成缩略图失败: {result.stderr.decode('utf-8', errors='ignore')}")
        return None

def get_latest_video():
    """获取下载目录中最新的视频文件"""
    video_dir = Path(DOWNLOAD_DIR)
    # 支持常见视频格式
    video_extensions = ["*.mkv", "*.mp4", "*.webm", "*.m4a", "*.mov", "*.avi"]
    video_files = []
    for ext in video_extensions:
        video_files.extend(video_dir.glob(ext))
    
    if not video_files:
        return None
    return max(video_files, key=lambda f: f.stat().st_mtime)

def download_video(url, ffmpeg_path=None, retries=2):
    """下载单个视频，支持重试"""
    cmd = [
        sys.executable, "-m", "yt_dlp",
    ]

    if ffmpeg_path:
        cmd.extend(["--ffmpeg-location", ffmpeg_path])

    cmd.extend([
        "-P", DOWNLOAD_DIR,
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
        "--merge-output-format", "mkv",
        "--no-mtime",
        "--write-auto-sub",
        "--sub-langs", "zh.*,zh-Hans",
        "--embed-subs",
        "--sub-format", "srt/ass/vtt",
    ])

    if COOKIES_BROWSER:
        cmd.extend(["--cookies-from-browser", COOKIES_BROWSER])

    cmd.append(url)

    env = os.environ.copy()
    if ffmpeg_path:
        ffmpeg_dir = str(Path(ffmpeg_path).parent)
        env["PATH"] = ffmpeg_dir + os.pathsep + env.get("PATH", "")

    for attempt in range(1, retries + 1):
        print(f"\n正在下载: {url} (尝试 {attempt}/{retries})")
        print("-" * 50)

        result = subprocess.run(cmd, env=env)

        if result.returncode == 0:
            print(f"\n下载完成: {url}")

            if ffmpeg_path:
                latest_video = get_latest_video()
                if latest_video:
                    print(f"正在检查文件可用性: {latest_video.name}")
                    if wait_for_file_unlock(str(latest_video), max_wait=30):
                        print(f"文件可用，正在提取缩略图...")
                        extract_thumbnail(str(latest_video), ffmpeg_path)
                    else:
                        print(f"文件仍被占用，跳过缩略图生成，当前视频视为失败")
                        return False

            return True
        else:
            print(f"\n下载失败 (尝试 {attempt}/{retries}): {url}")
            if attempt < retries:
                print(f"等待 10 秒后重试...")
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
    print("=" * 50)
    print("Bilibili 视频下载工具")
    print(f"下载目录: {DOWNLOAD_DIR}")
    print(f"列表文件: {LIST_FILE}")
    print("=" * 50)

    ffmpeg_path = check_ffmpeg()
    print_ffmpeg_info(ffmpeg_path)

    Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)

    urls = read_list_file()
    if urls is None:
        return

    print(f"\n共 {len(urls)} 个视频待下载")

    success_urls = []
    failed_urls = []

    for url in urls:
        if download_video(url, ffmpeg_path):
            success_urls.append(url)
        else:
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
