"""Tests for media services."""

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kurt.services.ai_generation import (
    AIGenerationService,
    GenerationResult,
    Provider,
)
from kurt.services.media_edit import (
    EditResult,
    MediaEditService,
    MediaFormat,
)


class TestAIGenerationService:
    """Tests for AIGenerationService."""

    def test_init_reads_env_vars(self, monkeypatch):
        """Test that service reads API keys from environment."""
        monkeypatch.setenv("FAL_KEY", "test-fal-key")
        monkeypatch.setenv("LEONARDO_API_KEY", "test-leonardo-key")

        service = AIGenerationService()

        assert service.fal_key == "test-fal-key"
        assert service.leonardo_key == "test-leonardo-key"

    def test_init_with_explicit_keys(self):
        """Test that explicit keys override env vars."""
        service = AIGenerationService(
            fal_key="explicit-fal",
            leonardo_key="explicit-leonardo",
        )

        assert service.fal_key == "explicit-fal"
        assert service.leonardo_key == "explicit-leonardo"

    def test_default_providers(self):
        """Test default provider settings."""
        service = AIGenerationService()

        assert service.default_image_provider == Provider.FAL
        assert service.default_video_provider == Provider.FAL

    @pytest.mark.asyncio
    async def test_generate_image_no_api_key(self):
        """Test that missing API key returns error."""
        service = AIGenerationService(fal_key=None)

        result = await service.generate_image(
            prompt="test prompt",
            provider=Provider.FAL,
        )

        assert not result.success
        assert "FAL_KEY not configured" in result.error

    @pytest.mark.asyncio
    async def test_generate_video_no_api_key(self):
        """Test that missing API key returns error for video."""
        service = AIGenerationService(runway_key=None)

        result = await service.generate_video(
            prompt="test prompt",
            provider=Provider.RUNWAY,
        )

        assert not result.success
        assert "RUNWAY_API_KEY not configured" in result.error


class TestMediaEditService:
    """Tests for MediaEditService."""

    def test_init_defaults(self):
        """Test default binary paths."""
        service = MediaEditService()

        assert service.ffmpeg_path == "ffmpeg"
        assert service.magick_path == "magick"

    def test_init_with_custom_paths(self):
        """Test custom binary paths."""
        service = MediaEditService(
            ffmpeg_path="/usr/local/bin/ffmpeg",
            magick_path="/usr/local/bin/magick",
        )

        assert service.ffmpeg_path == "/usr/local/bin/ffmpeg"
        assert service.magick_path == "/usr/local/bin/magick"

    def test_ensure_output_path_with_provided(self):
        """Test output path when explicitly provided."""
        service = MediaEditService()

        result = service._ensure_output_path(
            input_path="input.jpg",
            output_path="custom_output.jpg",
        )

        assert result == "custom_output.jpg"

    def test_ensure_output_path_auto_generated(self):
        """Test auto-generated output path."""
        service = MediaEditService()

        result = service._ensure_output_path(
            input_path="/path/to/input.jpg",
            output_path=None,
        )

        assert result == "/path/to/input_edited.jpg"

    def test_ensure_output_path_with_suffix(self):
        """Test output path with custom suffix."""
        service = MediaEditService()

        result = service._ensure_output_path(
            input_path="/path/to/video.mp4",
            output_path=None,
            suffix="_trimmed.mp4",
        )

        assert result == "/path/to/video_trimmed.mp4"

    @pytest.mark.asyncio
    async def test_resize_image_no_imagemagick(self):
        """Test resize when ImageMagick not available."""
        service = MediaEditService()

        with patch.object(service, "_check_imagemagick", return_value=False):
            result = await service.resize_image(
                "input.jpg",
                width=800,
                height=600,
            )

        assert not result.success
        assert "ImageMagick not found" in result.error

    @pytest.mark.asyncio
    async def test_trim_video_no_ffmpeg(self):
        """Test trim when FFmpeg not available."""
        service = MediaEditService()

        with patch.object(service, "_check_ffmpeg", return_value=False):
            result = await service.trim_video(
                "input.mp4",
                start="00:00:30",
                end="00:01:00",
            )

        assert not result.success
        assert "FFmpeg not found" in result.error

    @pytest.mark.asyncio
    async def test_convert_unsupported_format(self):
        """Test convert with unsupported format."""
        service = MediaEditService()

        result = await service.convert(
            "input.xyz",
            format="unsupported",
        )

        assert not result.success
        assert "Unsupported format" in result.error

    @pytest.mark.asyncio
    async def test_get_info_basic(self, tmp_path):
        """Test getting basic file info."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        service = MediaEditService()

        with patch.object(service, "_check_ffmpeg", return_value=False):
            info = await service.get_info(str(test_file))

        assert info.path == str(test_file)
        assert info.format == "txt"
        assert info.size_bytes > 0


class TestGenerationResult:
    """Tests for GenerationResult dataclass."""

    def test_primary_url_from_url(self):
        """Test primary_url when url is set."""
        result = GenerationResult(
            success=True,
            url="https://example.com/image.png",
            urls=["https://example.com/other.png"],
        )

        assert result.primary_url == "https://example.com/image.png"

    def test_primary_url_from_urls(self):
        """Test primary_url falls back to first urls entry."""
        result = GenerationResult(
            success=True,
            url=None,
            urls=["https://example.com/first.png", "https://example.com/second.png"],
        )

        assert result.primary_url == "https://example.com/first.png"

    def test_primary_url_none(self):
        """Test primary_url when nothing available."""
        result = GenerationResult(
            success=False,
            error="Some error",
        )

        assert result.primary_url is None


class TestMediaFormat:
    """Tests for MediaFormat enum."""

    def test_image_formats(self):
        """Test image format values."""
        assert MediaFormat.JPEG.value == "jpeg"
        assert MediaFormat.PNG.value == "png"
        assert MediaFormat.WEBP.value == "webp"

    def test_video_formats(self):
        """Test video format values."""
        assert MediaFormat.MP4.value == "mp4"
        assert MediaFormat.WEBM.value == "webm"

    def test_audio_formats(self):
        """Test audio format values."""
        assert MediaFormat.MP3.value == "mp3"
        assert MediaFormat.WAV.value == "wav"
