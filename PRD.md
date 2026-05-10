# Whisper Dictate — Product Requirements Document

## Overview

A personal Windows desktop utility that converts speech to text locally using OpenAI Whisper, with no cloud dependency. Triggered by a global hotkey, it transcribes speech and types the result directly into whatever app has focus.

---

## Functional Requirements

### 1. Global Hotkey — Hold to Record
- Default hotkey: `Ctrl + Alt + Space`
- **Hold** the hotkey to record, **release** to stop recording and begin transcription
- Recording is captured for the entire duration the hotkey is held
- Hotkey must be configurable via config file (no code change required)

### 2. Transcription Output
- Transcribed text is auto-typed into the currently focused application at the cursor position
- Uses keyboard simulation (as if the user typed it)
- No clipboard involvement

### 3. Language Support
- Default languages: German (`de`) and English (`en`)
- Additional languages (e.g., Japanese `ja`) can be added via config file
- Active language is displayed in the floating window at all times
- Clicking the language label cycles through the configured language list

### 4. Whisper Model
- Model: `whisper-large-v3` (multilingual)
- Backend: `faster-whisper` with CTranslate2
- Quantization: `int8` to reduce VRAM usage
- Device: CUDA (NVIDIA GPU required; RTX 2070 Super is the reference hardware)
- Model loads on application startup — the floating window shows a "Loading..." state until ready

---

## UI Requirements

### Floating Window
- Always visible on screen (always-on-top)
- Frameless, minimal, unobtrusive
- Draggable — user can reposition it anywhere on screen
- Window position is saved to config on close and restored on next launch
- Built with PyQt6

### Idle State
- Shows the active language label (e.g., `DE`, `EN`, `JA`)
- Language label is clickable — each click cycles to the next configured language

### Loading State
- Shown on startup while the Whisper model is loading into VRAM
- Displays a "Loading..." indicator; hotkey is disabled during this state

### Recording State
- Shown while the hotkey is held
- Displays a live audio waveform animation (volume-driven amplitude visualization)

### Feedback on Transcription Complete
- **Success:** Window briefly flashes green (~500ms)
- **Failure / silence detected:** Window briefly flashes red (~500ms)

---

## Configuration

A single `config.json` file in the project root stores all user-configurable settings:

```json
{
  "hotkey": "ctrl+alt+space",
  "languages": ["de", "en"],
  "active_language": "de",
  "window_position": { "x": 100, "y": 100 }
}
```

- Config is read on startup and written on clean exit (to persist window position and active language)

---

## Installation & Launch

- Installed as an editable Python package via `pip install -e .`
- Console entry point: `whisper-dictate`
- Runnable from any terminal: `whisper-dictate`
- Requires Python 3.10+, CUDA-capable NVIDIA GPU, and CUDA toolkit installed

---

## Tech Stack

| Concern | Library |
|---|---|
| Speech recognition | `faster-whisper` |
| Audio capture | `sounddevice` + `numpy` |
| Global hotkey | `keyboard` |
| UI | `PyQt6` |
| Packaging | `setuptools` with `pyproject.toml` |

---

## Out of Scope

- Cloud/API-based transcription
- Speaker diarization or word-level timestamps
- Multi-monitor window management beyond dragging
- Packaging as a standalone `.exe`
- Any form of text editing or post-processing of transcription output
