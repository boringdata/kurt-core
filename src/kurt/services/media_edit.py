"""Media Edit Service - wrapper around FFmpeg and ImageMagick.

Provides a unified interface for common media editing operations:
- Image: resize, crop, rotate, format conversion, filters
- Video: trim, resize, extract audio, add audio, format conversion
- Audio: trim, convert, extract from video

Requirements:
- FFmpeg: video/audio processing (install via apt/brew/choco)
- ImageMagick: image processing (install via apt/brew/choco)

Environment variables:
- FFMPEG_PATH: Path to ffmpeg binary (default: "ffmpeg")
- MAGICK_PATH: Path to magick binary (default: "magick")
"""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class MediaFormat(str, Enum):
    """Supported output formats."""

    # Image formats
    JPEG = "jpeg"
    JPG = "jpg"
    PNG = "png"
    WEBP = "webp"
    GIF = "gif"
    AVIF = "avif"
    TIFF = "tiff"

    # Video formats
    MP4 = "mp4"
    WEBM = "webm"
    MOV = "mov"
    AVI = "avi"
    MKV = "mkv"

    # Audio formats
    MP3 = "mp3"
    WAV = "wav"
    AAC = "aac"
    OGG = "ogg"
    FLAC = "flac"


@dataclass
class EditResult:
    """Result from a media editing operation."""

    success: bool
    output_path: str | None = None
    error: str | None = None
    command: str | None = None
    stdout: str | None = None
    stderr: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MediaInfo:
    """Information about a media file."""

    path: str
    format: str | None = None
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    bitrate: int | None = None
    codec: str | None = None
    audio_codec: str | None = None
    fps: float | None = None
    size_bytes: int | None = None


class MediaEditService:
    """Service for editing media files using FFmpeg and ImageMagick.

    Example:
        service = MediaEditService()

        # Resize image
        result = await service.resize_image(
            "input.jpg",
            output_path="output.jpg",
            width=800,
            height=600,
        )

        # Trim video
        result = await service.trim_video(
            "input.mp4",
            output_path="output.mp4",
            start="00:00:30",
            end="00:01:00",
        )

        # Convert format
        result = await service.convert(
            "input.png",
            output_path="output.webp",
            format=MediaFormat.WEBP,
        )
    """

    def __init__(
        self,
        ffmpeg_path: str | None = None,
        magick_path: str | None = None,
    ):
        """Initialize the media edit service.

        Args:
            ffmpeg_path: Path to ffmpeg binary (or FFMPEG_PATH env var)
            magick_path: Path to magick binary (or MAGICK_PATH env var)
        """
        self.ffmpeg_path = ffmpeg_path or os.environ.get("FFMPEG_PATH", "ffmpeg")
        self.magick_path = magick_path or os.environ.get("MAGICK_PATH", "magick")

    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available."""
        return shutil.which(self.ffmpeg_path) is not None

    def _check_imagemagick(self) -> bool:
        """Check if ImageMagick is available."""
        return shutil.which(self.magick_path) is not None

    async def _run_command(
        self,
        cmd: list[str],
        check: bool = True,
    ) -> tuple[int, str, str]:
        """Run a command asynchronously.

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return (
            process.returncode or 0,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )

    def _ensure_output_path(
        self,
        input_path: str,
        output_path: str | None,
        suffix: str | None = None,
    ) -> str:
        """Generate output path if not provided."""
        if output_path:
            return output_path

        input_p = Path(input_path)
        if suffix:
            return str(input_p.parent / f"{input_p.stem}_edited{suffix}")
        return str(input_p.parent / f"{input_p.stem}_edited{input_p.suffix}")

    # -------------------------------------------------------------------------
    # Image Operations (ImageMagick)
    # -------------------------------------------------------------------------

    async def resize_image(
        self,
        input_path: str,
        output_path: str | None = None,
        width: int | None = None,
        height: int | None = None,
        scale: float | None = None,
        maintain_aspect: bool = True,
        quality: int = 85,
    ) -> EditResult:
        """Resize an image.

        Args:
            input_path: Path to input image
            output_path: Path for output (auto-generated if not provided)
            width: Target width in pixels
            height: Target height in pixels
            scale: Scale factor (e.g., 0.5 for half size)
            maintain_aspect: Keep aspect ratio (default True)
            quality: Output quality 1-100 (for JPEG/WebP)

        Returns:
            EditResult with output path
        """
        if not self._check_imagemagick():
            return EditResult(
                success=False,
                error="ImageMagick not found. Install with: apt install imagemagick",
            )

        output_path = self._ensure_output_path(input_path, output_path)
        cmd = [self.magick_path, input_path]

        if scale:
            cmd.extend(["-resize", f"{int(scale * 100)}%"])
        elif width and height:
            resize_op = f"{width}x{height}" if maintain_aspect else f"{width}x{height}!"
            cmd.extend(["-resize", resize_op])
        elif width:
            cmd.extend(["-resize", f"{width}x"])
        elif height:
            cmd.extend(["-resize", f"x{height}"])

        cmd.extend(["-quality", str(quality)])
        cmd.append(output_path)

        returncode, stdout, stderr = await self._run_command(cmd)

        return EditResult(
            success=returncode == 0,
            output_path=output_path if returncode == 0 else None,
            error=stderr if returncode != 0 else None,
            command=" ".join(cmd),
            stdout=stdout,
            stderr=stderr,
        )

    async def crop_image(
        self,
        input_path: str,
        output_path: str | None = None,
        width: int | None = None,
        height: int | None = None,
        x: int = 0,
        y: int = 0,
        gravity: str | None = None,
    ) -> EditResult:
        """Crop an image.

        Args:
            input_path: Path to input image
            output_path: Path for output
            width: Crop width
            height: Crop height
            x: X offset from left (or from gravity point)
            y: Y offset from top (or from gravity point)
            gravity: Gravity point (Center, North, South, East, West, etc.)

        Returns:
            EditResult with output path
        """
        if not self._check_imagemagick():
            return EditResult(
                success=False,
                error="ImageMagick not found",
            )

        output_path = self._ensure_output_path(input_path, output_path)
        cmd = [self.magick_path, input_path]

        if gravity:
            cmd.extend(["-gravity", gravity])

        crop_spec = f"{width}x{height}+{x}+{y}"
        cmd.extend(["-crop", crop_spec, "+repage"])
        cmd.append(output_path)

        returncode, stdout, stderr = await self._run_command(cmd)

        return EditResult(
            success=returncode == 0,
            output_path=output_path if returncode == 0 else None,
            error=stderr if returncode != 0 else None,
            command=" ".join(cmd),
        )

    async def rotate_image(
        self,
        input_path: str,
        output_path: str | None = None,
        degrees: float = 90,
        background: str = "white",
    ) -> EditResult:
        """Rotate an image.

        Args:
            input_path: Path to input image
            output_path: Path for output
            degrees: Rotation angle (positive = clockwise)
            background: Background color for corners

        Returns:
            EditResult with output path
        """
        if not self._check_imagemagick():
            return EditResult(success=False, error="ImageMagick not found")

        output_path = self._ensure_output_path(input_path, output_path)
        cmd = [
            self.magick_path,
            input_path,
            "-background",
            background,
            "-rotate",
            str(degrees),
            output_path,
        ]

        returncode, stdout, stderr = await self._run_command(cmd)

        return EditResult(
            success=returncode == 0,
            output_path=output_path if returncode == 0 else None,
            error=stderr if returncode != 0 else None,
            command=" ".join(cmd),
        )

    async def apply_filter(
        self,
        input_path: str,
        output_path: str | None = None,
        filter_name: str = "grayscale",
        **kwargs: Any,
    ) -> EditResult:
        """Apply a filter to an image.

        Args:
            input_path: Path to input image
            output_path: Path for output
            filter_name: Filter to apply (grayscale, blur, sharpen, etc.)
            **kwargs: Filter-specific parameters

        Returns:
            EditResult with output path
        """
        if not self._check_imagemagick():
            return EditResult(success=False, error="ImageMagick not found")

        output_path = self._ensure_output_path(input_path, output_path)
        cmd = [self.magick_path, input_path]

        # Map filter names to ImageMagick operations
        filter_ops = {
            "grayscale": ["-colorspace", "Gray"],
            "sepia": ["-sepia-tone", str(kwargs.get("intensity", 80)) + "%"],
            "blur": ["-blur", f"0x{kwargs.get('radius', 3)}"],
            "sharpen": ["-sharpen", f"0x{kwargs.get('radius', 1)}"],
            "negate": ["-negate"],
            "normalize": ["-normalize"],
            "equalize": ["-equalize"],
            "brightness": [
                "-modulate",
                f"{kwargs.get('brightness', 100)},{kwargs.get('saturation', 100)}",
            ],
            "contrast": ["-contrast-stretch", f"{kwargs.get('black', 0)}x{kwargs.get('white', 0)}%"],
        }

        if filter_name in filter_ops:
            cmd.extend(filter_ops[filter_name])
        else:
            return EditResult(
                success=False,
                error=f"Unknown filter: {filter_name}. Available: {list(filter_ops.keys())}",
            )

        cmd.append(output_path)

        returncode, stdout, stderr = await self._run_command(cmd)

        return EditResult(
            success=returncode == 0,
            output_path=output_path if returncode == 0 else None,
            error=stderr if returncode != 0 else None,
            command=" ".join(cmd),
        )

    async def composite_images(
        self,
        background_path: str,
        overlay_path: str,
        output_path: str | None = None,
        x: int = 0,
        y: int = 0,
        gravity: str = "NorthWest",
        opacity: float = 1.0,
    ) -> EditResult:
        """Composite two images (overlay one on another).

        Args:
            background_path: Path to background image
            overlay_path: Path to overlay image
            output_path: Path for output
            x: X offset
            y: Y offset
            gravity: Placement gravity
            opacity: Overlay opacity (0.0-1.0)

        Returns:
            EditResult with output path
        """
        if not self._check_imagemagick():
            return EditResult(success=False, error="ImageMagick not found")

        output_path = self._ensure_output_path(background_path, output_path, "_composite.png")

        # Build composite command
        cmd = [
            self.magick_path,
            background_path,
            "(",
            overlay_path,
            "-alpha",
            "set",
            "-channel",
            "A",
            "-evaluate",
            "multiply",
            str(opacity),
            "+channel",
            ")",
            "-gravity",
            gravity,
            "-geometry",
            f"+{x}+{y}",
            "-composite",
            output_path,
        ]

        returncode, stdout, stderr = await self._run_command(cmd)

        return EditResult(
            success=returncode == 0,
            output_path=output_path if returncode == 0 else None,
            error=stderr if returncode != 0 else None,
            command=" ".join(cmd),
        )

    # -------------------------------------------------------------------------
    # Video Operations (FFmpeg)
    # -------------------------------------------------------------------------

    async def trim_video(
        self,
        input_path: str,
        output_path: str | None = None,
        start: str | float | None = None,
        end: str | float | None = None,
        duration: float | None = None,
        copy_codec: bool = True,
    ) -> EditResult:
        """Trim a video to a specific segment.

        Args:
            input_path: Path to input video
            output_path: Path for output
            start: Start time (e.g., "00:00:30" or 30.0)
            end: End time (e.g., "00:01:00" or 60.0)
            duration: Duration in seconds (alternative to end)
            copy_codec: Copy codecs without re-encoding (fast but less precise)

        Returns:
            EditResult with output path
        """
        if not self._check_ffmpeg():
            return EditResult(
                success=False,
                error="FFmpeg not found. Install with: apt install ffmpeg",
            )

        output_path = self._ensure_output_path(input_path, output_path, "_trimmed.mp4")
        cmd = [self.ffmpeg_path, "-y"]

        if start:
            cmd.extend(["-ss", str(start)])

        cmd.extend(["-i", input_path])

        if end:
            cmd.extend(["-to", str(end)])
        elif duration:
            cmd.extend(["-t", str(duration)])

        if copy_codec:
            cmd.extend(["-c", "copy"])

        cmd.append(output_path)

        returncode, stdout, stderr = await self._run_command(cmd)

        return EditResult(
            success=returncode == 0,
            output_path=output_path if returncode == 0 else None,
            error=stderr if returncode != 0 else None,
            command=" ".join(cmd),
            stderr=stderr,
        )

    async def resize_video(
        self,
        input_path: str,
        output_path: str | None = None,
        width: int | None = None,
        height: int | None = None,
        scale: str | None = None,
        preset: str | None = None,
    ) -> EditResult:
        """Resize a video.

        Args:
            input_path: Path to input video
            output_path: Path for output
            width: Target width (use -1 for auto based on height)
            height: Target height (use -1 for auto based on width)
            scale: FFmpeg scale filter (e.g., "1280:720", "iw/2:ih/2")
            preset: Preset resolution ("480p", "720p", "1080p", "4k")

        Returns:
            EditResult with output path
        """
        if not self._check_ffmpeg():
            return EditResult(success=False, error="FFmpeg not found")

        output_path = self._ensure_output_path(input_path, output_path, "_resized.mp4")

        # Handle presets
        presets = {
            "480p": "854:480",
            "720p": "1280:720",
            "1080p": "1920:1080",
            "4k": "3840:2160",
        }

        if preset:
            scale = presets.get(preset, scale)
        elif width and height:
            scale = f"{width}:{height}"
        elif width:
            scale = f"{width}:-2"
        elif height:
            scale = f"-2:{height}"

        if not scale:
            return EditResult(success=False, error="Must specify width, height, scale, or preset")

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i",
            input_path,
            "-vf",
            f"scale={scale}",
            "-c:a",
            "copy",
            output_path,
        ]

        returncode, stdout, stderr = await self._run_command(cmd)

        return EditResult(
            success=returncode == 0,
            output_path=output_path if returncode == 0 else None,
            error=stderr if returncode != 0 else None,
            command=" ".join(cmd),
        )

    async def extract_audio(
        self,
        input_path: str,
        output_path: str | None = None,
        format: str = "mp3",
        bitrate: str = "192k",
    ) -> EditResult:
        """Extract audio track from video.

        Args:
            input_path: Path to input video
            output_path: Path for output audio
            format: Output format (mp3, wav, aac, etc.)
            bitrate: Audio bitrate

        Returns:
            EditResult with output path
        """
        if not self._check_ffmpeg():
            return EditResult(success=False, error="FFmpeg not found")

        output_path = self._ensure_output_path(input_path, output_path, f".{format}")

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i",
            input_path,
            "-vn",
            "-acodec",
            "libmp3lame" if format == "mp3" else "copy",
            "-ab",
            bitrate,
            output_path,
        ]

        returncode, stdout, stderr = await self._run_command(cmd)

        return EditResult(
            success=returncode == 0,
            output_path=output_path if returncode == 0 else None,
            error=stderr if returncode != 0 else None,
            command=" ".join(cmd),
        )

    async def add_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str | None = None,
        replace: bool = True,
        volume: float = 1.0,
    ) -> EditResult:
        """Add or replace audio in a video.

        Args:
            video_path: Path to input video
            audio_path: Path to audio file
            output_path: Path for output
            replace: Replace existing audio (True) or mix (False)
            volume: Audio volume multiplier

        Returns:
            EditResult with output path
        """
        if not self._check_ffmpeg():
            return EditResult(success=False, error="FFmpeg not found")

        output_path = self._ensure_output_path(video_path, output_path, "_audio.mp4")

        if replace:
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i",
                video_path,
                "-i",
                audio_path,
                "-c:v",
                "copy",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-shortest",
                output_path,
            ]
        else:
            # Mix audio
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i",
                video_path,
                "-i",
                audio_path,
                "-c:v",
                "copy",
                "-filter_complex",
                f"[0:a][1:a]amerge=inputs=2,volume={volume}[a]",
                "-map",
                "0:v",
                "-map",
                "[a]",
                "-shortest",
                output_path,
            ]

        returncode, stdout, stderr = await self._run_command(cmd)

        return EditResult(
            success=returncode == 0,
            output_path=output_path if returncode == 0 else None,
            error=stderr if returncode != 0 else None,
            command=" ".join(cmd),
        )

    async def extract_frames(
        self,
        input_path: str,
        output_dir: str | None = None,
        fps: float = 1.0,
        format: str = "jpg",
        quality: int = 2,
    ) -> EditResult:
        """Extract frames from video as images.

        Args:
            input_path: Path to input video
            output_dir: Directory for output frames
            fps: Frames per second to extract
            format: Output image format
            quality: JPEG quality (2-31, lower is better)

        Returns:
            EditResult with output directory
        """
        if not self._check_ffmpeg():
            return EditResult(success=False, error="FFmpeg not found")

        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="frames_")
        else:
            os.makedirs(output_dir, exist_ok=True)

        output_pattern = os.path.join(output_dir, f"frame_%04d.{format}")

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i",
            input_path,
            "-vf",
            f"fps={fps}",
            "-q:v",
            str(quality),
            output_pattern,
        ]

        returncode, stdout, stderr = await self._run_command(cmd)

        return EditResult(
            success=returncode == 0,
            output_path=output_dir if returncode == 0 else None,
            error=stderr if returncode != 0 else None,
            command=" ".join(cmd),
            metadata={"pattern": output_pattern},
        )

    async def create_thumbnail(
        self,
        input_path: str,
        output_path: str | None = None,
        time: str | float = "00:00:01",
        width: int = 320,
        height: int | None = None,
    ) -> EditResult:
        """Create a thumbnail from video.

        Args:
            input_path: Path to input video
            output_path: Path for output image
            time: Time position to capture
            width: Thumbnail width
            height: Thumbnail height (auto if not specified)

        Returns:
            EditResult with output path
        """
        if not self._check_ffmpeg():
            return EditResult(success=False, error="FFmpeg not found")

        output_path = self._ensure_output_path(input_path, output_path, "_thumb.jpg")

        scale = f"{width}:-1" if height is None else f"{width}:{height}"

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-ss",
            str(time),
            "-i",
            input_path,
            "-vframes",
            "1",
            "-vf",
            f"scale={scale}",
            output_path,
        ]

        returncode, stdout, stderr = await self._run_command(cmd)

        return EditResult(
            success=returncode == 0,
            output_path=output_path if returncode == 0 else None,
            error=stderr if returncode != 0 else None,
            command=" ".join(cmd),
        )

    # -------------------------------------------------------------------------
    # Format Conversion
    # -------------------------------------------------------------------------

    async def convert(
        self,
        input_path: str,
        output_path: str | None = None,
        format: MediaFormat | str | None = None,
        quality: int = 85,
        **kwargs: Any,
    ) -> EditResult:
        """Convert media to different format.

        Args:
            input_path: Path to input file
            output_path: Path for output (format inferred from extension)
            format: Target format
            quality: Quality setting (for lossy formats)
            **kwargs: Additional format-specific options

        Returns:
            EditResult with output path
        """
        if format is None and output_path:
            format = Path(output_path).suffix.lstrip(".")

        if format is None:
            return EditResult(success=False, error="Must specify format or output_path with extension")

        if isinstance(format, MediaFormat):
            format = format.value

        # Determine if it's an image or video format
        image_formats = {"jpeg", "jpg", "png", "webp", "gif", "avif", "tiff"}
        video_formats = {"mp4", "webm", "mov", "avi", "mkv"}
        audio_formats = {"mp3", "wav", "aac", "ogg", "flac"}

        if format in image_formats:
            return await self._convert_image(input_path, output_path, format, quality)
        elif format in video_formats:
            return await self._convert_video(input_path, output_path, format, **kwargs)
        elif format in audio_formats:
            return await self._convert_audio(input_path, output_path, format, **kwargs)
        else:
            return EditResult(success=False, error=f"Unsupported format: {format}")

    async def _convert_image(
        self,
        input_path: str,
        output_path: str | None,
        format: str,
        quality: int,
    ) -> EditResult:
        """Convert image format using ImageMagick."""
        if not self._check_imagemagick():
            return EditResult(success=False, error="ImageMagick not found")

        output_path = self._ensure_output_path(input_path, output_path, f".{format}")

        cmd = [
            self.magick_path,
            input_path,
            "-quality",
            str(quality),
            output_path,
        ]

        returncode, stdout, stderr = await self._run_command(cmd)

        return EditResult(
            success=returncode == 0,
            output_path=output_path if returncode == 0 else None,
            error=stderr if returncode != 0 else None,
            command=" ".join(cmd),
        )

    async def _convert_video(
        self,
        input_path: str,
        output_path: str | None,
        format: str,
        **kwargs: Any,
    ) -> EditResult:
        """Convert video format using FFmpeg."""
        if not self._check_ffmpeg():
            return EditResult(success=False, error="FFmpeg not found")

        output_path = self._ensure_output_path(input_path, output_path, f".{format}")

        cmd = [self.ffmpeg_path, "-y", "-i", input_path]

        # Add codec options based on format
        if format == "webm":
            cmd.extend(["-c:v", "libvpx-vp9", "-c:a", "libopus"])
        elif format == "mp4":
            cmd.extend(["-c:v", "libx264", "-c:a", "aac"])

        # Add any additional options
        crf = kwargs.get("crf", 23)
        cmd.extend(["-crf", str(crf)])

        cmd.append(output_path)

        returncode, stdout, stderr = await self._run_command(cmd)

        return EditResult(
            success=returncode == 0,
            output_path=output_path if returncode == 0 else None,
            error=stderr if returncode != 0 else None,
            command=" ".join(cmd),
        )

    async def _convert_audio(
        self,
        input_path: str,
        output_path: str | None,
        format: str,
        **kwargs: Any,
    ) -> EditResult:
        """Convert audio format using FFmpeg."""
        if not self._check_ffmpeg():
            return EditResult(success=False, error="FFmpeg not found")

        output_path = self._ensure_output_path(input_path, output_path, f".{format}")

        cmd = [self.ffmpeg_path, "-y", "-i", input_path]

        bitrate = kwargs.get("bitrate", "192k")
        cmd.extend(["-ab", bitrate])

        cmd.append(output_path)

        returncode, stdout, stderr = await self._run_command(cmd)

        return EditResult(
            success=returncode == 0,
            output_path=output_path if returncode == 0 else None,
            error=stderr if returncode != 0 else None,
            command=" ".join(cmd),
        )

    # -------------------------------------------------------------------------
    # Media Information
    # -------------------------------------------------------------------------

    async def get_info(self, input_path: str) -> MediaInfo:
        """Get information about a media file.

        Args:
            input_path: Path to media file

        Returns:
            MediaInfo with file details
        """
        if not self._check_ffmpeg():
            # Fallback to basic info
            path = Path(input_path)
            return MediaInfo(
                path=input_path,
                format=path.suffix.lstrip("."),
                size_bytes=path.stat().st_size if path.exists() else None,
            )

        cmd = [
            self.ffmpeg_path,
            "-i",
            input_path,
            "-hide_banner",
        ]

        returncode, stdout, stderr = await self._run_command(cmd)

        # FFmpeg outputs info to stderr
        info = MediaInfo(path=input_path)

        # Parse format
        path = Path(input_path)
        info.format = path.suffix.lstrip(".")
        if path.exists():
            info.size_bytes = path.stat().st_size

        # Parse dimensions (from "Stream #0:0: Video: ... 1920x1080")
        import re

        dimension_match = re.search(r"(\d{2,5})x(\d{2,5})", stderr)
        if dimension_match:
            info.width = int(dimension_match.group(1))
            info.height = int(dimension_match.group(2))

        # Parse duration
        duration_match = re.search(r"Duration: (\d+):(\d+):(\d+)\.(\d+)", stderr)
        if duration_match:
            h, m, s, ms = duration_match.groups()
            info.duration = int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 100

        # Parse FPS
        fps_match = re.search(r"(\d+(?:\.\d+)?)\s*fps", stderr)
        if fps_match:
            info.fps = float(fps_match.group(1))

        return info


# Convenience functions for synchronous usage
def resize_image_sync(input_path: str, **kwargs: Any) -> EditResult:
    """Synchronous wrapper for image resize."""
    service = MediaEditService()
    return asyncio.run(service.resize_image(input_path, **kwargs))


def trim_video_sync(input_path: str, **kwargs: Any) -> EditResult:
    """Synchronous wrapper for video trim."""
    service = MediaEditService()
    return asyncio.run(service.trim_video(input_path, **kwargs))


def convert_sync(input_path: str, **kwargs: Any) -> EditResult:
    """Synchronous wrapper for format conversion."""
    service = MediaEditService()
    return asyncio.run(service.convert(input_path, **kwargs))
