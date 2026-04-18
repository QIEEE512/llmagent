from __future__ import annotations

from app.services.ai import _detect_audio_format_magic


def test_detect_audio_format_magic_wav():
    # RIFF....WAVE
    b = b"RIFF" + (36).to_bytes(4, "little") + b"WAVE" + b"fmt "
    r = _detect_audio_format_magic(b)
    assert r.format == "wav"
    assert r.confidence == "high"


def test_detect_audio_format_magic_mp3_id3():
    b = b"ID3" + b"\x04\x00\x00" + b"\x00" * 32
    r = _detect_audio_format_magic(b)
    assert r.format == "mp3"


def test_detect_audio_format_magic_mp4_ftyp_m4a():
    # 4-byte size + 'ftyp' + 'M4A '
    b = b"\x00\x00\x00\x18" + b"ftyp" + b"M4A " + b"\x00\x00\x00\x00" + b"isom"
    r = _detect_audio_format_magic(b)
    assert r.format in ("m4a", "mp4")


def test_detect_audio_format_magic_fallback_to_ext_low_confidence():
    b = b"\x00\x01\x02\x03" * 16
    r = _detect_audio_format_magic(b, filename="x.ogg")
    assert r.format == "ogg"
    assert r.confidence == "low"
