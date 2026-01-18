"""Media workflow - AI-powered image and video generation and editing.

This module provides:
- AI image generation via fal.ai, Leonardo.ai, Replicate
- AI video generation via Runway, fal.ai, Replicate
- Media editing via FFmpeg and ImageMagick

CLI Usage:
    # Generate images
    kurt media generate image --prompt "A sunset over mountains" --model flux-dev

    # Generate video from image
    kurt media generate video --image hero.png --prompt "Slow zoom" --duration 5

    # Edit images
    kurt media edit resize input.jpg --width 800 --height 600
    kurt media edit crop input.jpg --width 400 --height 400 --gravity center
    kurt media edit filter input.jpg --filter grayscale

    # Edit videos
    kurt media edit trim video.mp4 --start 00:00:30 --end 00:01:00
    kurt media edit resize video.mp4 --preset 720p
    kurt media edit thumbnail video.mp4 --time 5

    # Convert formats
    kurt media convert input.png --format webp
    kurt media convert video.mp4 --format webm

Programmatic Usage:
    from kurt.services import AIGenerationService, MediaEditService

    # Generate image
    service = AIGenerationService()
    result = await service.generate_image(prompt="...", model="flux-dev")

    # Edit video
    editor = MediaEditService()
    result = await editor.trim_video("input.mp4", start="00:00:30", duration=30)
"""

from kurt.services.ai_generation import (
    AIGenerationService,
    GenerationResult,
    MediaType,
    Provider,
    generate_image_sync,
    generate_video_sync,
)
from kurt.services.media_edit import (
    EditResult,
    MediaEditService,
    MediaFormat,
    MediaInfo,
    convert_sync,
    resize_image_sync,
    trim_video_sync,
)

__all__ = [
    # AI Generation
    "AIGenerationService",
    "GenerationResult",
    "Provider",
    "MediaType",
    "generate_image_sync",
    "generate_video_sync",
    # Media Editing
    "MediaEditService",
    "EditResult",
    "MediaFormat",
    "MediaInfo",
    "resize_image_sync",
    "trim_video_sync",
    "convert_sync",
]
