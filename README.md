# whisper-dictate

A local, GPU-accelerated speech-to-text tool for Windows. Hold a hotkey, speak, release — and your words are typed into whatever app has focus.

No cloud. No API key. Everything runs on your machine.

---

## How It Works

1. **Hold** `Ctrl + Alt + Space` (or your configured hotkey) — recording starts
2. **Speak**
3. **Release** — transcription runs and the text is typed into the active window

A small floating window shows the current state at all times.

---

## Requirements

- Windows 10/11
- Python 3.10 or later
- NVIDIA GPU with CUDA support (tested on RTX 2070 Super)
- CUDA toolkit installed

---

## Installation

```powershell
git clone <repo-url>
cd whisper-dictate
pip install -e .
```

The Whisper model (`whisper-large-v3`) is downloaded automatically on first run.

---

## Usage

```powershell
python -m whisper_dictate.app
```

The floating window appears. On first launch, it shows `...` while loading the model into VRAM — this takes a few seconds. Once it shows a language code (e.g. `de`), it is ready.

### Controls

| Action | Result |
|---|---|
| Hold hotkey | Start recording |
| Release hotkey | Stop and transcribe |
| Click language label | Cycle to next language |
| Drag window | Reposition on screen |
| Close window | Save config and exit |

### Status Indicators

| Display | Meaning |
|---|---|
| `...` | Loading model |
| `de` / `en` / etc. | Idle, ready to record |
| Waveform bars | Recording in progress |
| Green flash | Transcription successful |
| Red flash | No speech detected or transcription failed |

---

## Configuration

Edit `config.json` in the project directory:

```json
{
  "hotkey": "ctrl+alt+space",
  "languages": ["de", "en"],
  "active_language": "de",
  "window_position": { "x": 100, "y": 100 }
}
```

| Field | Description |
|---|---|
| `hotkey` | Global hotkey to hold while speaking. Uses `+` to join keys (e.g. `ctrl+alt+space`, `shift+f12`). |
| `languages` | List of language codes to cycle through when clicking the label. |
| `active_language` | Language used for transcription on startup. |
| `window_position` | Pixel position of the floating window. Saved automatically on exit. |

Language codes follow [ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) (e.g. `de`, `en`, `fr`, `ja`, `es`).

---

## Dependencies

| Package | Purpose |
|---|---|
| `faster-whisper` | Local speech-to-text via CTranslate2 backend |
| `sounddevice` | Microphone input |
| `numpy` | Audio array processing |
| `keyboard` | Global hotkey monitoring |
| `PyQt6` | Floating window UI |

---

## Notes

- The model is loaded once on startup and kept in VRAM to minimize per-transcription latency.
- A 100 ms delay is applied before typing output to ensure modifier keys (Ctrl, Alt) have fully released — this prevents the hotkey from interfering with the typed text.
- Audio is captured at 16 kHz mono, which is the format Whisper expects.
- Window position is saved when the app closes, so it reopens in the same spot.
