# Bilibili 视频下载工具 (macOS)

基于 `yt-dlp` 的 Bilibili 批量视频下载脚本，支持自动重试、字幕嵌入、缩略图生成和失败重试机制。

## 功能介绍

- **批量下载**：从 `list` 文件读取多个视频链接，逐个下载
- **自动重试**：下载失败自动重试 2 次，间隔 10 秒
- **字幕嵌入**：自动下载中文自动字幕并嵌入到 MKV 视频中
- **缩略图生成**：下载完成后自动提取视频第一帧作为缩略图（.jpg）
- **ffmpeg 智能检测**：支持配置路径、PATH 环境变量、脚本同目录等多种方式查找 ffmpeg
- **文件占用等待**：下载完成后等待文件释放再生成缩略图，避免文件锁冲突
- **自动归档**：成功下载的链接归档到 `list_history_时间戳`，失败链接保留在 `list` 中方便重试

## 配置项说明

脚本顶部为配置区，共有 4 个配置项：

| 配置项 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `DOWNLOAD_DIR` | string | 是 | 视频下载保存目录 | `str(Path.home() / "bilibili")` |
| `LIST_FILE` | Path | 否 | 视频链接列表文件路径，默认为脚本同级 `list` 文件 | - |
| `FFMPEG_PATH` | string | 否 | ffmpeg 可执行文件完整路径，留空则自动从 PATH 或脚本目录查找 | `"/usr/local/bin/ffmpeg"` |
| `COOKIES_BROWSER` | string | 否 | 浏览器名称，用于从浏览器读取 Cookie 登录 B 站，留空则不使用 Cookie | `"chrome"` / `"safari"` |

## 配置示例

```python
# ==================== 配置区 ====================
DOWNLOAD_DIR = str(Path.home() / "bilibili")
LIST_FILE = Path(__file__).parent / "list"
FFMPEG_PATH = ""  # 留空则自动查找
COOKIES_BROWSER = ""  # 留空不使用 Cookie，或填 "chrome"/"safari" 等
# ===============================================
```

## 使用方法

1. 在 `list` 文件中添加要下载的视频链接（每行一个）
2. 运行脚本：
   ```bash
   python download_mac.py
   ```
3. 等待下载完成，视频保存在 `DOWNLOAD_DIR` 目录

## 流程图

```
开始
 │
 ├─► 检查 ffmpeg 可用性
 │    ├─ FFMPEG_PATH 存在？──► 使用该路径
 │    ├─ PATH 中有 ffmpeg？──► 使用该路径
 │    ├─ 脚本目录有 ffmpeg？──► 使用该路径
 │    └─ 都找不到 ──► 警告：无 ffmpeg，部分功能不可用
 │
 ├─► 创建下载目录（如不存在）
 │
 ├─► 读取 list 文件
 │    ├─ 文件不存在 ──► 创建空文件，提示用户添加链接，退出
 │    ├─ 文件为空 ──► 提示用户添加链接，退出
 │    └─ 读取成功 ──► 获取 URL 列表
 │
 ├─► 逐个下载视频 ───────────────────────────────┐
 │    │                                            │
 │    ├─► 构建 yt-dlp 命令                          │
 │    │    ├─ 最佳画质 + 最佳音质                   │
 │    │    ├─ 输出格式：MKV                        │
 │    │    ├─ 下载中文自动字幕并嵌入                │
 │    │    └─ 如配置了 Cookie，从浏览器读取          │
 │    │                                            │
 │    ├─► 执行下载（最多重试 2 次）                 │
 │    │    │                                       │
 │    │    ├─ 成功 ──► 等待文件释放（最多30s）      │
 │    │    │         ├─ 文件可用 ──► 提取缩略图     │
 │    │    │         └─ 文件仍占用 ──► 标记失败     │
 │    │    │                                       │
 │    │    └─ 失败 ──► 等待10s后重试               │
 │    │               ├─ 未超重试次数 ──► 继续重试  │
 │    │               └─ 已达最大重试 ──► 标记失败  │
 │    │                                            │
 │    └─◄─────────────────────────────────────────┘
 │
 ├─► 归档 list 文件
 │    ├─ 成功列表 ──► 保存为 list_history_时间戳
 │    ├─ 失败列表 ──► 写回 list 文件（方便下次重试）
 │    └─ 全部成功 ──► 创建空 list 文件
 │
 ├─► 输出统计信息（成功数/总数）
 │
 └─ 结束
```

## 依赖

- Python 3.x
- yt-dlp：`pip install yt-dlp`
- ffmpeg：视频合并和缩略图生成必需

## ffmpeg 安装指南

如果脚本提示 `警告: 未检测到 ffmpeg！`，请按以下方法安装：

### 方法一：使用 Homebrew 自动安装（推荐）

1. 安装 Homebrew（如果尚未安装）：
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. 使用 Homebrew 安装 ffmpeg：
   ```bash
   brew install ffmpeg
   ```

3. 验证安装：
   ```bash
   ffmpeg -version
   ```
   如果显示版本信息，说明安装成功，脚本会自动检测到 ffmpeg。

### 方法二：手动下载安装

如果 Homebrew 安装失败，可以手动下载：

1. 访问 [ffmpeg 官方下载页](https://ffmpeg.org/download.html#build-mac)
2. 下载 macOS 版本的静态构建包（通常为 `.zip` 文件）
3. 解压下载的文件
4. 找到 `ffmpeg` 可执行文件（通常在 `bin` 目录下）
5. 记下 `ffmpeg` 文件的完整路径，例如：`/Users/yourname/ffmpeg/bin/ffmpeg`

### 配置 FFMPEG_PATH

如果你选择手动安装，或者自动安装后脚本仍然找不到 ffmpeg，需要手动配置 `FFMPEG_PATH`：

**步骤 1：获取 ffmpeg 路径**

```bash
# 如果通过 Homebrew 安装，通常路径为：
which ffmpeg
# 输出示例：/usr/local/bin/ffmpeg 或 /opt/homebrew/bin/ffmpeg

# 如果是手动安装，使用你解压后的 ffmpeg 完整路径
```

**步骤 2：修改脚本配置**

编辑 `download_mac.py`，找到配置区：

```python
# ==================== 配置区 ====================
DOWNLOAD_DIR = str(Path.home() / "bilibili")
LIST_FILE = Path(__file__).parent / "list"
FFMPEG_PATH = ""  # 在这里填入 ffmpeg 的完整路径
COOKIES_BROWSER = ""
# ===============================================
```

将 `FFMPEG_PATH` 修改为你的 ffmpeg 路径，例如：

```python
FFMPEG_PATH = "/usr/local/bin/ffmpeg"  # Homebrew 安装
# 或
FFMPEG_PATH = "/Users/yourname/ffmpeg/bin/ffmpeg"  # 手动安装
```

**步骤 3：验证配置**

保存文件后重新运行脚本：

```bash
python download_mac.py
```

如果看到 `ffmpeg 路径: /your/path/to/ffmpeg`，说明配置成功。

### 未安装 ffmpeg 的后果

- ❌ 视频和音频将分离为两个文件，无法合并为单个 MKV 文件
- ❌ 无法生成视频缩略图
- ❌ 字幕可能无法正确嵌入

## 输出文件格式

下载完成后，每个视频会生成：

- `视频标题.mkv`：合并后的视频文件（含内嵌字幕）
- `视频标题.jpg`：视频第一帧缩略图

## 失败重试机制

下载失败的链接会自动保留在 `list` 文件中，下次运行脚本时会继续尝试下载这些链接。历史成功记录会归档到 `list_history_YYYYMMDD_HHMMSS` 文件中，方便追溯。

## 需要多线程下载？

如果你需要同时下载多个视频以提升速度，请使用 **macOS 多线程版**：

👉 运行文件：`download_mac_multi_thread.py`  
📖 查看文档：[README_mac_multi_thread.md](README_mac_multi_thread.md)
