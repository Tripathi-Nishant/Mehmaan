import pytest

from app.config import Settings
from app.gnani.usage import GnaniUsageLimitError, UsageGuard


def test_settings_defaults_are_safe():
    settings = Settings(_env_file=None)
    assert settings.gnani_stt_model == "prisma-v2.5"
    assert settings.gnani_tts_model == "timbre-v2.5"


def test_usage_guard_blocks_after_cap():
    UsageGuard.reset_for_tests()
    guard = UsageGuard(1)
    guard.consume()
    with pytest.raises(GnaniUsageLimitError):
        guard.consume()
