# whisper-dictate

A local speech-to-text tool for Windows. Tap a hotkey, speak, tap again — and your words are typed into whatever app has focus.

No cloud. No API key. Everything runs on your machine.

---

## How It Works

1. **Tap** `right Ctrl + right Shift` — recording starts
2. **Speak**
3. **Tap** `right Ctrl + right Shift` again — transcription runs and the text is typed into the active window

A small floating window shows the current state at all times.

---

## Requirements

- Windows 10/11
- Python 3.10 or later
- A microphone
- *(Optional)* an NVIDIA GPU with CUDA for fast transcription (tested on RTX 2070 Super). Without one, the app falls back to CPU automatically — slower, but functional.

---

## Installation

```powershell
git clone https://github.com/tbleier7/whisper-dictate.git
cd whisper-dictate

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -e .          # add ".[test]" to include the test dependencies
```

You can also install straight from GitHub without cloning:

```powershell
pip install "git+https://github.com/tbleier7/whisper-dictate.git"
```

The Whisper model (`whisper-large-v3`, several GB) is downloaded automatically from Hugging Face on first run, so the initial startup needs network access and may take a while.

---

## Usage

Launch via the installed console script or as a module:

```powershell
whisper-dictate
# or
python -m whisper_dictate
```

The floating window appears. On first launch, it shows `...` while loading the model into memory — this takes a few seconds. Once it shows a language code (e.g. `de`), it is ready.

> **Tip:** because the `keyboard` library installs a global keyboard hook, some systems require running the terminal **as Administrator** for the hotkey to register.

### Controls

| Action | Result |
|---|---|
| Tap hotkey | Start recording |
| Tap hotkey again | Stop and transcribe |
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

Configuration lives in a per-user file, created on first exit:

- **Windows:** `%APPDATA%\whisper-dictate\config.json`
- **macOS:** `~/Library/Application Support/whisper-dictate/config.json`
- **Linux:** `$XDG_CONFIG_HOME/whisper-dictate/config.json` (or `~/.config/...`)

If a `config.json` from an older install still sits in the project root, it is
read once and migrated to the per-user location the next time the app exits.

```json
{
  "languages": ["de", "en"],
  "active_language": "de",
  "window_position": { "x": 100, "y": 100 }
}
```

| Field | Description |
|---|---|
| `languages` | List of language codes to cycle through when clicking the label. |
| `active_language` | Language used for transcription on startup. |
| `window_position` | Pixel position of the floating window. Saved automatically on exit. |

The activation chord is fixed at `right Ctrl + right Shift` and is not configurable. It must be "clean": pressing any other key while the modifiers are held cancels the toggle, so combinations like `Ctrl+Shift+T` still pass through to the focused app.

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

- The model is loaded once on startup and kept in memory to minimize per-transcription latency.
- A 100 ms delay is applied before typing output to ensure the held modifier keys have fully released — this prevents the hotkey from interfering with the typed text.
- Audio is captured at 16 kHz mono, which is the format Whisper expects.
- Window position is saved when the app closes, so it reopens in the same spot.
- Runtime logs are written to `~/.whisper-dictate/app.log` — useful when debugging the hotkey or model loading.

---

## License

Released under the [MIT License](LICENSE). © 2026 Tobias Bleier.
