import subprocess
import sys
import shutil
from pathlib import Path
from datetime import datetime

# ==================== 配置区 ====================
DOWNLOAD_DIR = r"E:\迅雷下载"
LIST_FILE = Path(__file__).parent / "list"
# ===============================================

def check_ffmpeg():
    """检查 ffmpeg 是否可用，返回 ffmpeg 路径或 None"""
    # 方法1: shutil.which
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path

    # 方法2: 检查脚本同目录
    script_dir = Path(__file__).parent
    local_ffmpeg = script_dir / "ffmpeg.exe"
    if local_ffmpeg.exists():
        return str(local_ffmpeg)

    # 方法3: 使用 where.exe 查找 (Windows)
    try:
        result = subprocess.run(
            ["where", "ffmpeg"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode == 0:
            path = result.stdout.strip().split("\n")[0].strip()
            return path
    except Exception:
        pass

    print("警告: 未检测到 ffmpeg，可能导致视频无声音！")
    print("请将 ffmpeg.exe 放在脚本同目录或添加到系统 PATH。")
    print("-" * 50)
    return None

def print_ffmpeg_info(ffmpeg_path):
    """打印 ffmpeg 信息"""
    if ffmpeg_path:
        print(f"ffmpeg 路径: {ffmpeg_path}")
    else:
        print("ffmpeg: 未找到")

def download_video(url, ffmpeg_path=None):
    """下载单个视频"""
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-P", DOWNLOAD_DIR,
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--no-mtime",
    ]

    if ffmpeg_path:
        cmd.extend(["--ffmpeg-location", ffmpeg_path, "--embed-subs"])

    cmd.append(url)

    print(f"\n正在下载: {url}")
    print("-" * 50)
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print(f"\n下载完成: {url}")
    else:
        print(f"\n下载失败: {url}")
    return result.returncode == 0

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

def archive_list_file():
    """将 list 文件重命名为 list_history+日期时间"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"list_history_{timestamp}"
    archive_path = LIST_FILE.parent / archive_name
    shutil.move(str(LIST_FILE), str(archive_path))
    print(f"已归档 list 文件: {archive_path.name}")

def main():
    print("=" * 50)
    print("Bilibili 视频下载工具")
    print(f"下载目录: {DOWNLOAD_DIR}")
    print(f"列表文件: {LIST_FILE}")
    print("=" * 50)

    # 检查 ffmpeg
    ffmpeg_path = check_ffmpeg()
    print_ffmpeg_info(ffmpeg_path)

    # 确保下载目录存在
    Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)

    # 读取 list 文件
    urls = read_list_file()
    if urls is None:
        return

    print(f"\n共 {len(urls)} 个视频待下载")

    # 下载视频
    success = 0
    for url in urls:
        if download_video(url, ffmpeg_path):
            success += 1

    # 归档 list 文件
    archive_list_file()

    # 创建新的空 list 文件
    LIST_FILE.write_text("", encoding="utf-8")
    print(f"已创建新的空 list 文件: {LIST_FILE}")

    print(f"\n{'=' * 50}")
    print(f"全部完成！成功 {success}/{len(urls)}")
    print(f"文件位置: {DOWNLOAD_DIR}")

if __name__ == "__main__":
    main()
