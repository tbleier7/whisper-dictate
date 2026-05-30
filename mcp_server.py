#!/usr/bin/env python3
"""MCP server for interacting with the whisper-dictate app."""
from __future__ import annotations

import io
import json
import subprocess
import time
import urllib.request
from pathlib import Path

import keyboard
from mcp.server.fastmcp import FastMCP, Image
from PIL import ImageGrab

ROOT = Path(__file__).parent
VENV_PYTHON = str(ROOT / ".venv" / "Scripts" / "python.exe")
STATE_URL = "http://127.0.0.1:19876/state"
CONFIG_PATH = ROOT / "config.json"
WINDOW_W = 96
WINDOW_H = 38
SCREENSHOT_PAD = 40

_app_process: subprocess.Popen | None = None

mcp = FastMCP("whisper-dictate")


@mcp.tool()
def app_start() -> str:
    """Start the whisper-dictate application. Model load takes ~10-30 seconds."""
    global _app_process
    if _app_process is not None and _app_process.poll() is None:
        return "App is already running"
    _app_process = subprocess.Popen(
        [VENV_PYTHON, "-m", "whisper_dictate"],
        cwd=str(ROOT),
    )
    return f"App started (PID {_app_process.pid}). Poll app_get_state until it returns 'idle'."


@mcp.tool()
def app_stop() -> str:
    """Stop the whisper-dictate application."""
    global _app_process
    if _app_process is None or _app_process.poll() is not None:
        return "App is not running"
    _app_process.terminate()
    _app_process = None
    return "App stopped"


@mcp.tool()
def app_get_state() -> str:
    """Return current app state: loading | idle | recording | success | failure | load_failed | unreachable"""
    try:
        with urllib.request.urlopen(STATE_URL, timeout=2) as r:
            return json.loads(r.read())["state"]
    except Exception as e:
        return f"unreachable ({e})"


@mcp.tool()
def hotkey_press() -> str:
    """Simulate the Right Ctrl + Right Shift chord to toggle recording on/off."""
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:19876/trigger", data=b"", method="POST"
        )
        with urllib.request.urlopen(req, timeout=2):
            pass
        return "Chord sent"
    except Exception as e:
        return f"Failed to trigger: {e}"


CAL_BASE = "http://127.0.0.1:19876/calibrate"


def _cal_post(path: str) -> None:
    req = urllib.request.Request(f"{CAL_BASE}/{path}", data=b"", method="POST")
    with urllib.request.urlopen(req, timeout=2):
        pass


def _cal_get(path: str) -> dict:
    with urllib.request.urlopen(f"{CAL_BASE}/{path}", timeout=2) as r:
        return json.loads(r.read())


@mcp.tool()
def calibrate_open() -> str:
    """Open the calibration window. Returns the reference passage the user should read aloud.
    App must be idle before calling this."""
    _cal_post("open")
    data = _cal_get("passage")
    return f"Calibration window opened. Read this passage aloud:\n\n{data['passage']}"


@mcp.tool()
def calibrate_record(duration_seconds: int = 10) -> str:
    """Record audio for calibration, then transcribe and score it.

    Starts recording, waits duration_seconds, stops, and returns the WER result.
    Call calibrate_open() first. duration_seconds should be long enough to read the full passage.
    """
    _cal_post("record_start")
    time.sleep(duration_seconds)
    _cal_post("record_stop")
    # Poll until transcription finishes (up to 60 s)
    for _ in range(60):
        time.sleep(1)
        data = _cal_get("state")
        if data["state"] == "result":
            break
    result = _cal_get("result")
    if "error" in result:
        return f"Calibration failed: {result['error']}"
    return (
        f"WER: {result['wer_pct']}%\n"
        f"Transcription: {result['transcription']}"
    )


@mcp.tool()
def calibrate_get_result() -> str:
    """Return the most recent calibration result (WER and transcription)."""
    result = _cal_get("result")
    if "error" in result:
        return result["error"]
    return (
        f"WER: {result['wer_pct']}%\n"
        f"Transcription: {result['transcription']}"
    )


@mcp.tool()
def screenshot() -> Image:
    """Capture the floating window. Reads window position from config.json and adds padding."""
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        x = cfg["window_position"]["x"]
        y = cfg["window_position"]["y"]
        bbox = (x - SCREENSHOT_PAD, y - SCREENSHOT_PAD,
                x + WINDOW_W + SCREENSHOT_PAD, y + WINDOW_H + SCREENSHOT_PAD)
    except Exception:
        bbox = None  # full screenshot fallback

    img = ImageGrab.grab(bbox)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Image(data=buf.getvalue(), format="png")


if __name__ == "__main__":
    mcp.run()
