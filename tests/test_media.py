import pytest

from app.media.store import MAX_MEDIA_BYTES, MediaTooLargeError, save_media


async def test_media_over_5mb_is_rejected_before_db():
    with pytest.raises(MediaTooLargeError):
        await save_media(None, "photo", "image/jpeg", b"x" * (MAX_MEDIA_BYTES + 1))


def test_app_imports():
    import app.main  # noqa: F401
