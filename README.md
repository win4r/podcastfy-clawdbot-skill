# [🚀观看我的哔哩哔哩视频](https://space.bilibili.com/3493277319825652)

# podcastfy-clawdbot-skill

A Clawdbot skill that generates a podcast-style MP3 from one or more URLs using the open-source **Podcastfy** project.

It is designed to be used inside a Clawdbot deployment and provides a wrapper script that:

- Creates/uses a local Python venv
- Installs/updates `podcastfy`
- Uses **Gemini** for script generation (LLM)
- Uses **Edge TTS** for speech synthesis (no paid TTS API required)

> Note: This repository intentionally does **not** include any generated audio/transcripts or any secrets.

---

## Features

- Generate a single MP3 from a single article URL
- Generate one MP3 from multiple URLs (e.g., 3 articles → 1 combined episode)
- Compatible with Clawdbot scheduled jobs (cron)
- Safer defaults: `.env`, `.venv`, and `output/` are ignored

---

## Requirements

- Linux/macOS (tested in Linux)
- Python 3.10+ (tested with Python 3.12)
- `ffmpeg`
- A valid `GEMINI_API_KEY` (Gemini API)

Install ffmpeg (Ubuntu/Debian):

```bash
sudo apt-get update && sudo apt-get install -y ffmpeg
```

---

## Setup

### 1) Create a `.env`

Create a `.env` file in the skill directory:

```bash
GEMINI_API_KEY=YOUR_KEY_HERE
PODCASTFY_LLM_MODEL=gemini-2.5-flash
```

Optional (Edge TTS voices):

```bash
PODCASTFY_EDGE_VOICE_Q=en-US-JennyNeural
PODCASTFY_EDGE_VOICE_A=en-US-EricNeural
```

### 2) Run

Single URL:

```bash
cd skills/podcastfy-clawdbot
./scripts/podcastfy_generate.py --url "https://example.com/article"
```

Multiple URLs:

```bash
cd skills/podcastfy-clawdbot
PODCASTFY_LLM_MODEL=gemini-2.5-flash \
  ./scripts/podcastfy_generate.py \
  --url "https://example.com/a" \
  --url "https://example.com/b" \
  --url "https://example.com/c"
```

---

## Output

On success, the script prints the generated MP3 path.

Typical output locations:

- `output/audio/*.mp3`
- `output/transcripts/*.txt`

---

## Notes / Troubleshooting

- If Gemini returns `429` with `limit: 0`, it usually means your project/key has **no usable quota** (billing/quota not enabled or free-tier not available). Check your Gemini API rate-limit page.
- Some websites keep connections open and can cause Playwright timeouts; the wrapper/config is tuned to be more tolerant, but some pages may still fail.

---

## License

Add a license if you plan to publish/redistribute.

---

# 中文说明（Chinese)

这是一个用于 **Clawdbot** 的技能（skill），可以把一个或多个网页链接生成「播客风格」的 **MP3**。

该仓库提供一个包装脚本，主要功能：

- 自动创建/使用 Python 虚拟环境
- 安装/更新 `podcastfy`
- 使用 **Gemini** 生成播客对话稿（LLM）
- 使用 **Edge TTS** 合成语音（无需付费 TTS API）

> 注意：本仓库不会提交任何密钥、`.env`、虚拟环境、以及生成的音频/转写文件。

---

## 功能

- 单链接生成一条 MP3
- 多链接合并生成一条 MP3（例如 3 篇文章合成 1 期播客）
- 可配合 Clawdbot 的定时任务（cron）每日自动生成并推送
- 默认做安全清理：忽略 `.env` / `.venv` / `output/`

---

## 环境要求

- Linux/macOS（主要在 Linux 测试）
- Python 3.10+（测试环境为 Python 3.12）
- `ffmpeg`
- 可用的 `GEMINI_API_KEY`

Ubuntu/Debian 安装 ffmpeg：

```bash
sudo apt-get update && sudo apt-get install -y ffmpeg
```

---

## 配置与运行

### 1）创建 `.env`

在 skill 目录创建 `.env`：

```bash
GEMINI_API_KEY=你的Key
PODCASTFY_LLM_MODEL=gemini-2.5-flash
```

可选：指定 Edge TTS 声音：

```bash
PODCASTFY_EDGE_VOICE_Q=en-US-JennyNeural
PODCASTFY_EDGE_VOICE_A=en-US-EricNeural
```

### 2）运行

单链接：

```bash
cd skills/podcastfy-clawdbot
./scripts/podcastfy_generate.py --url "https://example.com/article"
```

多链接（合并生成一条播客）：

```bash
cd skills/podcastfy-clawdbot
PODCASTFY_LLM_MODEL=gemini-2.5-flash \
  ./scripts/podcastfy_generate.py \
  --url "https://example.com/a" \
  --url "https://example.com/b" \
  --url "https://example.com/c"
```

---

## 输出

成功后脚本会打印 MP3 输出路径，通常在：

- `output/audio/*.mp3`
- `output/transcripts/*.txt`

---

## 常见问题

- 如果 Gemini 报错 `429` 且包含 `limit: 0`，通常是因为该项目/Key 当前没有可用配额（未启用计费或 free-tier 不可用）。请到 Gemini API 的 rate limit 页面确认配额状态。
- 某些网站会让 Playwright 一直等待（网络连接不断开），可能导致抓取超时；此仓库已做一定容错，但仍可能遇到个别页面失败。
