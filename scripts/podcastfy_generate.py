#!/usr/bin/env python3
"""Generate a podcast MP3 from one or more URLs using podcastfy.

Goals (Clawdbot skill wrapper):
- Provide a single command that takes URLs and outputs an MP3 path.
- Use Gemini for transcript generation via GEMINI_API_KEY.
- Use Edge TTS (podcastfy's built-in edge support) for audio.

This script:
- Ensures a local venv exists and installs podcastfy.
- Writes a temporary conversation config that sets Edge voices + output dirs.
- Runs Podcastfy via the Python API.
- Verifies the produced MP3 is playable (non-trivial size + ffprobe duration).
- If the MP3 is invalid/truncated, re-synthesizes audio from the latest transcript
  using edge-tts as a fallback.

Usage:
  ./podcastfy_generate.py --url https://example.com/article
  ./podcastfy_generate.py --url https://a --url https://b --longform

Env:
  GEMINI_API_KEY (required)
  PODCASTFY_LLM_MODEL (optional; default: gemini-1.5-flash)
  PODCASTFY_EDGE_VOICE_Q (optional; default: en-US-JennyNeural)
  PODCASTFY_EDGE_VOICE_A (optional; default: en-US-EricNeural)

Notes:
- Requires ffmpeg available on PATH (also used by podcastfy).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SKILL_DIR = BASE_DIR.parent
VENV_DIR = SKILL_DIR / ".venv"
PY = VENV_DIR / "bin" / "python"
PIP = VENV_DIR / "bin" / "pip"
EDGE_TTS = VENV_DIR / "bin" / "edge-tts"


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg"):
        return
    raise SystemExit(
        "ffmpeg not found on PATH. Install it first (Ubuntu/Debian): sudo apt-get update && sudo apt-get install -y ffmpeg"
    )


def ensure_venv() -> None:
    if PY.exists() and PIP.exists():
        return

    subprocess.run(["python3", "-m", "venv", str(VENV_DIR)], check=True)
    subprocess.run([str(PIP), "install", "--upgrade", "pip"], check=True)


def ensure_deps() -> None:
    # Pin loosely; let pip resolve compatible versions.
    subprocess.run([str(PIP), "install", "-U", "podcastfy", "playwright"], check=True)

    # Podcastfy's website extractor may use Playwright. Ensure a browser is installed.
    try:
        subprocess.run([str(PY), "-m", "playwright", "install", "chromium"], check=True)
    except Exception as e:
        raise SystemExit(f"Failed to install Playwright Chromium: {e}")


def write_conversation_config(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "audio").mkdir(parents=True, exist_ok=True)
    (out_dir / "transcripts").mkdir(parents=True, exist_ok=True)

    voice_q = os.getenv("PODCASTFY_EDGE_VOICE_Q", "en-US-JennyNeural")
    voice_a = os.getenv("PODCASTFY_EDGE_VOICE_A", "en-US-EricNeural")

    cfg = f"""conversation_style:\n  - engaging\n  - fast-paced\n  - enthusiastic\nroles_person1: main summarizer\nroles_person2: questioner/clarifier\ndialogue_structure:\n  - Introduction\n  - Main Content Summary\n  - Conclusion\npodcast_name: Podcastfy\npodcast_tagline: Your Personal Generative AI Podcast\noutput_language: English\ncreativity: 1\nuser_instructions: ""\n\ntext_to_speech:\n  default_tts_model: edge\n  output_directories:\n    transcripts: \"{(out_dir / 'transcripts').as_posix()}\"\n    audio: \"{(out_dir / 'audio').as_posix()}\"\n  edge:\n    default_voices:\n      question: \"{voice_q}\"\n      answer: \"{voice_a}\"\n  audio_format: mp3\n  temp_audio_dir: \"{(out_dir / 'tmp').as_posix()}/\"\n  ending_message: See You Next Time!\n"""

    path = out_dir / "conversation_config.yaml"
    path.write_text(cfg, encoding="utf-8")
    return path


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--url", action="append", dest="urls", default=[], help="URL to include (repeatable)")
    p.add_argument("--longform", action="store_true", help="Generate long-form content")
    p.add_argument("--out", default=str(SKILL_DIR / "output"), help="Output directory")
    return p.parse_args(argv)


def newest_file(path: Path, pattern: str) -> Path | None:
    files = list(path.glob(pattern))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def mp3_is_valid(mp3_path: Path) -> bool:
    # Quick size sanity check: broken files we saw were ~261 bytes.
    try:
        if mp3_path.stat().st_size < 10_000:
            return False
    except FileNotFoundError:
        return False

    # Duration sanity check.
    try:
        p = subprocess.run(
            [
                "ffprobe",
                "-hide_banner",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1",
                str(mp3_path),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        if p.returncode != 0:
            return False
        # Expect line like: duration=735.144000
        dur_line = next((ln for ln in p.stdout.splitlines() if ln.startswith("duration=")), "")
        if not dur_line:
            return False
        duration = float(dur_line.split("=", 1)[1])
        return duration >= 1.0
    except Exception:
        return False


def edge_tts_from_transcript(transcript_path: Path, out_mp3_path: Path) -> None:
    if not EDGE_TTS.exists():
        raise SystemExit("edge-tts not found in venv; expected at: " + str(EDGE_TTS))

    out_mp3_path.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            str(EDGE_TTS),
            "-f",
            str(transcript_path),
            "--write-media",
            str(out_mp3_path),
        ],
        check=True,
    )


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if not args.urls:
        raise SystemExit("Provide at least one --url")

    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("Missing GEMINI_API_KEY environment variable")

    ensure_ffmpeg()
    ensure_venv()
    ensure_deps()

    out_dir = Path(args.out).resolve()
    conv_cfg = write_conversation_config(out_dir)

    # Typer/Click compatibility can break the CLI in some environments.
    # Use the Python API instead of `python -m podcastfy.client ...`.
    code = r'''
import os
import yaml
from podcastfy.client import generate_podcast

urls = os.environ["_PODCASTFY_URLS"].split("\n")
longform = os.environ.get("_PODCASTFY_LONGFORM","0") == "1"
llm_model = os.environ.get("PODCASTFY_LLM_MODEL", "gemini-1.5-flash")

with open(os.environ["_PODCASTFY_CONV_CFG"], "r", encoding="utf-8") as f:
    conv = yaml.safe_load(f)

cfg = None
cfg_path = os.environ.get("_PODCASTFY_CFG")
if cfg_path:
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

out = generate_podcast(
    urls=urls,
    tts_model="edge",
    llm_model_name=llm_model,
    api_key_label="GEMINI_API_KEY",
    config=cfg,
    conversation_config=conv,
    longform=longform,
)
print(out)
'''

    env = os.environ.copy()
    env["_PODCASTFY_URLS"] = "\n".join(args.urls)
    env["_PODCASTFY_LONGFORM"] = "1" if args.longform else "0"
    env["_PODCASTFY_CONV_CFG"] = str(conv_cfg)

    # Optional base config overrides (e.g., website_extractor timeout)
    cfg_path = SKILL_DIR / "config.yaml"
    if cfg_path.exists():
        env["_PODCASTFY_CFG"] = str(cfg_path)

    proc = subprocess.run([str(PY), "-c", code], env=env, text=True)
    if proc.returncode != 0:
        return proc.returncode

    # Find newest outputs and validate.
    audio_dir = out_dir / "audio"
    tx_dir = out_dir / "transcripts"

    mp3 = newest_file(audio_dir, "*.mp3")
    if not mp3:
        raise SystemExit(f"No MP3 produced under: {audio_dir}")

    if mp3_is_valid(mp3):
        print(str(mp3))
        return 0

    # Fallback: re-synthesize from newest transcript.
    tx = newest_file(tx_dir, "*.txt")
    if not tx:
        raise SystemExit(f"MP3 appears invalid and no transcript found under: {tx_dir}")

    fixed = audio_dir / (mp3.stem + "_fixed.mp3")
    edge_tts_from_transcript(tx, fixed)

    if not mp3_is_valid(fixed):
        raise SystemExit(f"Fallback edge-tts MP3 still invalid: {fixed}")

    print(str(fixed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
