from __future__ import annotations

from whisper_dictate.window import AppState

from ..drivers.calibration_driver import CalibrationDriver


class CalibrationDsl:
    """Domain-language surface for calibration acceptance tests.

    Every method name is drawn from the user's vocabulary; no widget
    handles, signal names, or implementation details appear here.
    """

    def __init__(self, driver: CalibrationDriver) -> None:
        self._driver = driver

    def launch_idle(self) -> None:
        """The dictation tool is running and idle — model loaded, hotkey active."""
        # config is already built; driver was pre-constructed by the fixture
        pass

    def switch_to_recording(self) -> None:
        """Transition the app into recording state (simulates hotkey press mid-recording)."""
        self._driver.set_app_state(AppState.RECORDING)

    def click_gear_button(self) -> None:
        """The user clicks the gear button on the dictation overlay."""
        self._driver.click_gear_button()

    def assert_calibration_window_is_open(self) -> None:
        assert self._driver.calibration_window_is_visible(), (
            "Expected the calibration window to be visible, but it was not."
        )

    def assert_calibration_window_is_not_open(self) -> None:
        assert not self._driver.calibration_window_is_visible(), (
            "Expected no calibration window, but one was visible."
        )

    def assert_global_hotkey_is_disabled(self) -> None:
        assert self._driver.hotkey_stop_was_called(), (
            "Expected the global hotkey to be suspended while calibration is open, "
            "but hotkey.stop() was not called."
        )

    def assert_global_hotkey_is_enabled(self) -> None:
        assert self._driver.hotkey_start_was_called(), (
            "Expected the global hotkey to resume after calibration closed, "
            "but hotkey.start() was not called."
        )

    def close_calibration(self) -> None:
        """The user closes the calibration window."""
        self._driver.close_calibration_window()

    def deliver_transcription_result(self, text: str) -> None:
        """The transcription engine returns a result to the calibration window."""
        self._driver.deliver_transcription_to_calibration(text)

    def set_hotwords(self, text: str) -> None:
        """The user types words into the hotwords field."""
        self._driver.set_hotwords_in_calibration(text)

    def enable_vad(self) -> None:
        """The user checks the VAD filter checkbox."""
        self._driver.enable_vad_in_calibration()

    def enable_normalize(self) -> None:
        """The user checks the Normalize audio checkbox."""
        self._driver.enable_normalize_in_calibration()

    def click_save(self) -> None:
        """The user clicks Save to persist the current calibration settings."""
        self._driver.click_save_in_calibration()

    def assert_wer_score_is_displayed(self) -> None:
        assert self._driver.wer_is_shown_in_result_panel(), (
            "Expected the WER score to be shown in the calibration result panel, "
            "but 'WER' was not found in the result label."
        )

    def assert_config_hotwords_for(self, lang: str, expected: str) -> None:
        actual = self._driver.config_hotwords_for(lang)
        assert actual == expected, (
            f"Expected config hotwords[{lang!r}] = {expected!r}, got {actual!r}"
        )

    def assert_config_vad_filter(self, expected: bool) -> None:
        actual = self._driver.config_vad_filter()
        assert actual == expected, (
            f"Expected config.vad_filter = {expected}, got {actual}"
        )

    def assert_config_normalize_audio(self, expected: bool) -> None:
        actual = self._driver.config_normalize_audio()
        assert actual == expected, (
            f"Expected config.normalize_audio = {expected}, got {actual}"
        )

    def assert_main_window_is_still_running(self) -> None:
        assert self._driver.main_window_is_visible(), (
            "Expected the main floating window to still be visible after closing "
            "the calibration window, but it was not."
        )
