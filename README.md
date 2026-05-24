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
- *(Optional)* an NVIDIA GPU for fast transcription (tested on RTX 2070 Super). The CUDA libraries are installed automatically with the app — you do **not** need to install the CUDA Toolkit, only a reasonably recent NVIDIA driver. Without a GPU, the app falls back to CPU automatically — slower, but functional, and it tells you when it does (see [Status Indicators](#status-indicators)).

---

## Installation

One command installs everything — including the CUDA libraries for GPU
transcription — and puts the `whisper-dictate` command on your PATH. There is no
venv to activate and no CUDA Toolkit to install separately.

The easiest way is [pipx](https://pipx.pypa.io), which keeps the app in its own
isolated environment while still exposing the command globally:

```powershell
pipx install "git+https://github.com/tbleier7/whisper-dictate.git"
whisper-dictate
```

> Don't have pipx? Install it once with `python -m pip install --user pipx` then
> `python -m pipx ensurepath` (reopen your terminal afterwards).

Prefer plain pip? Install into your user site instead:

```powershell
pip install --user "git+https://github.com/tbleier7/whisper-dictate.git"
whisper-dictate
```

For development, clone and install editable in a venv:

```powershell
git clone https://github.com/tbleier7/whisper-dictate.git
cd whisper-dictate
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[test]"        # ".[test]" adds the test dependencies
```

Whichever method you pick, the GPU libraries land in the same environment as the
app, so it finds them automatically at runtime — no PATH tweaking required.

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
| `de` / `en` / etc. (white) | Idle, ready to record — running on the **GPU** |
| `de` / `en` / etc. (amber) | Idle, but running on **CPU** (slow). Hover for why; reinstall in an environment with the NVIDIA GPU libraries to fix it. |
| Waveform bars | Recording in progress |
| Green flash | Transcription successful |
| Red flash | No speech detected or transcription failed |

Hover the window any time to see the active device in a tooltip (`Running on GPU (cuda)` or a CPU warning).

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
| `nvidia-cublas-cu12`, `nvidia-cuda-nvrtc-cu12` | CUDA GPU libraries (Windows/Linux only; installed automatically). cuDNN ships inside the `faster-whisper`/CTranslate2 wheel. |

---

## Notes

- The model is loaded once on startup and kept in memory to minimize per-transcription latency.
- A 100 ms delay is applied before typing output to ensure the held modifier keys have fully released — this prevents the hotkey from interfering with the typed text.
- Audio is captured at 16 kHz mono, which is the format Whisper expects.
- Window position is saved when the app closes, so it reopens in the same spot.
- Runtime logs are written to `~/.whisper-dictate/app.log` — useful when debugging the hotkey or model loading.

---

## Development

This repo includes an MCP test harness (`mcp_server.py`) for driving the app from
Claude Code during development — starting/stopping it, simulating the hotkey, and
screenshotting the floating window. To enable it, copy `.mcp.json.example` to
`.mcp.json` and adjust the paths to your clone if needed. The `.mcp.json` file is
git-ignored so machine-specific paths stay out of the repo.

---

## License

Released under the [MIT License](LICENSE). © 2026 Tobias Bleier.
