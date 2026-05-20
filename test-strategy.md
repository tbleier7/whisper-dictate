# Test Strategy

## Audit findings

### Real bugs (not just untested)

- [x] **Model load failure leaves window stuck in LOADING.** `_ModelLoaderThread.run()` (`whisper_dictate/model.py:16`) has no `try/except`. If `WhisperModel(...)` raises (no CUDA, missing weights, OOM), the thread dies silently, `model_ready` never fires, hotkey never starts. There is no `loader_failed` signal.
- [x] **CUDA is hardcoded** (`whisper_dictate/model.py:8`). No CPU fallback. On a machine without CUDA the app is dead on launch.
- [x] **Language change is not persisted on the spot** (`whisper_dictate/window.py:140-146`). Only written by `closeEvent`. A force-kill drops the change.
- [x] **Working-copy `hotkey.py` swallows `KeyError` from `keyboard.unhook`** without addressing why the unhook failed. Investigate root cause (likely double-stop or `keyboard` internals already removed the hook) before keeping the patch.

### Untested seams

- [x] `HotkeyManager` press/release state machine + modifier-held check (`hotkey.py:40-51`).
- [x] `AudioRecorder` start/stop + amplitude callback (`audio.py`).
- [x] `WhisperEngine` load, transcribe, empty-segments-to-failed path (`model.py`).
- [x] `Config` load/save with corrupt or partial JSON (`config.py:25-37`) — `except Exception: pass` silently masks failures.
- [x] `FloatingWindow` flash timer + `became_idle` emission (`window.py:74-138`).
- [x] `_Controller` paths for `_on_transcription_failed`, language-cycle-during-transcription, rapid-press-while-LOADING.

## Strategy

Three layers, gated by markers.

| Layer | Marker | Speed | What it covers |
|---|---|---|---|
| Unit | (default) | <1s/test | Each module in isolation. Real Qt event loop via `qtbot`. External libs (`keyboard`, `sounddevice`, `faster_whisper`) mocked at the import boundary. |
| Integration | `@pytest.mark.slow` | ~30–60s | One end-to-end transcription: real `tiny` Whisper on CPU, fixture WAV, assert text. Skipped by default (`-m "not slow"`). |
| Manual | (markdown checklist) | minutes | Real hardware: keyboard hooks, mic, GPU, text injection into other apps. |

**Tradeoff:** mocking at the import boundary couples tests to the current libraries. Swapping `sounddevice` → `pyaudio` would rewrite the mocks. The alternative (thin adapter interfaces) is cleaner but more code now; not worth it for an app this size.

## Plan

### Phase 1 — fix the bugs the audit surfaced

- [x] Add `loader_failed` signal to `_ModelLoaderThread` and `WhisperEngine`. Wire `_Controller` to transition window to a recoverable state (FAILURE flash → IDLE? or persistent error label?). Pin with a test. — _persistent `LOAD_FAILED` state with red "ERR" label; pinned by 3 unit tests in `test_model.py` and 2 controller tests in `test_dictation_cycle.py`._
- [x] Add CPU fallback when CUDA is unavailable. Pin with a test that mocks `WhisperModel` raising on `device="cuda"` and succeeding on `device="cpu"`. — _try cuda first, fall back to cpu, fail only if both fail; pinned by 3 tests in `test_model.py`._
- [x] Persist language change immediately in `FloatingWindow._cycle_language` (call `self._config.save()`). Pin with a test. — _pinned by `test_cycle_language_persists_immediately` in `test_window.py`._
- [x] Investigate the `keyboard.unhook` `KeyError`. Either fix the root cause (don't call `stop()` twice; track hook state more carefully) or document why the swallow is correct. — _swallow is correct: KeyError means the hook is already gone from `keyboard`'s registry, which is the same end state we want. Documented inline in `hotkey.py:stop()`; pinned by `test_stop_swallows_key_error_from_unhook` in `test_hotkey.py`._

### Phase 2 — unit-test layer

- [ ] `tests/conftest.py` — shared fixtures (`config`, `qapp_args`), register `slow` marker.
- [x] `tests/test_hotkey.py` — patch `keyboard.on_press_key` / `on_release_key` / `is_pressed` / `unhook`, capture callbacks, drive them directly, assert signals via `qtbot.waitSignal`.
  - [x] press with modifiers held → `recording_started`
  - [x] press with modifiers not held → no signal
  - [x] release after press → `recording_stopped`
  - [x] release without prior press → no signal
  - [x] `stop()` removes hooks and is idempotent
  - [x] `start()` after `start()` does not double-hook
- [ ] `tests/test_audio.py` — patch `sounddevice.InputStream`.
  - [ ] `stop()` without `start()` returns zero-length array
  - [ ] callback frames concatenate in `stop()`
  - [ ] amplitude is clamped to [0, 1]
  - [ ] `amplitude_ready` is emitted from callback
- [ ] `tests/test_model.py` — patch `faster_whisper.WhisperModel`.
  - [x] `start_loading()` → `model_ready` fires
  - [x] **load failure → `loader_failed` fires** (will fail until Phase 1 lands)
  - [ ] transcribe with non-empty segments → `transcription_done(text)`
  - [ ] transcribe with empty segments → `transcription_failed`
  - [ ] transcribe raising exception → `transcription_failed`
- [ ] `tests/test_config.py` — `tmp_path`, monkeypatch `_CONFIG_PATH`.
  - [ ] missing file → defaults
  - [ ] corrupt JSON → defaults
  - [ ] partial keys → merged with defaults
  - [ ] save→load roundtrip preserves values
- [ ] `tests/test_window.py` — direct `set_state` + `qtbot`.
  - [ ] each state transition applies expected label/stack/color
  - [x] flash timer transitions SUCCESS → IDLE and emits `became_idle`
  - [x] flash timer transitions FAILURE → IDLE and emits `became_idle`
  - [x] `push_amplitude` is a no-op outside RECORDING
  - [x] `_cycle_language` only fires in IDLE
  - [x] `_cycle_language` persists immediately (after Phase 1)
- [ ] Extend `tests/test_dictation_cycle.py`:
  - [ ] failure path → flash → IDLE → hotkey restarted
  - [ ] language click during LOADING is ignored
  - [x] model-load-failure path (after Phase 1)

### Phase 3 — integration layer

- [ ] `tests/integration/test_real_whisper.py` — `@pytest.mark.slow`, loads `tiny` model on CPU, transcribes a short fixture WAV from `tests/fixtures/`, asserts expected words appear. Skip cleanly if model download fails.
- [ ] CI: run unit tests on every push, run `slow` tests nightly or pre-release.

### Phase 4 — manual checklist

- [ ] `tests/MANUAL.md` covering:
  - [ ] press hotkey, speak, release → text appears in target app
  - [ ] press hotkey while modifier dropped early → recording still ends cleanly
  - [ ] click language label → cycles, persists across restart
  - [ ] drag window → position persists across restart
  - [ ] long recording (~30s) → no crash, transcription completes
  - [ ] no CUDA → graceful CPU fallback
  - [ ] another app holding the mic → graceful error, no crash
  - [ ] hotkey-write does not re-trigger recording (regression for `8bf793b`)
