"""CLI commands for media generation and editing.

Commands:
- kurt media generate image: Generate images with AI
- kurt media generate video: Generate videos with AI
- kurt media edit: Edit images and videos
- kurt media convert: Convert between formats
- kurt media info: Get media file information
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


# =============================================================================
# Main Group
# =============================================================================


@click.group(name="media")
def media_group():
    """Generate and edit images, videos, and audio.

    Use AI models to generate media, or edit existing files with
    FFmpeg and ImageMagick.

    \b
    Examples:
        kurt media generate image --prompt "A cat" --model flux-dev
        kurt media edit resize image.jpg --width 800
        kurt media convert video.mp4 --format webm
    """
    pass


# =============================================================================
# Generate Commands
# =============================================================================


@media_group.group(name="generate")
def generate_group():
    """Generate images and videos using AI models.

    \b
    Supported providers:
        - fal.ai: Fast inference, Flux models (FAL_KEY)
        - Leonardo.ai: Nano Banana, Phoenix (LEONARDO_API_KEY)
        - Replicate: Large model library (REPLICATE_API_TOKEN)
        - Runway: Video generation (RUNWAY_API_KEY)

    Set the appropriate API key as an environment variable.
    """
    pass


@generate_group.command(name="image")
@click.option(
    "--prompt",
    "-p",
    required=True,
    help="Text description of the image to generate",
)
@click.option(
    "--model",
    "-m",
    default="flux/dev",
    help="Model to use (e.g., flux/dev, nano-banana, sdxl)",
)
@click.option(
    "--provider",
    type=click.Choice(["fal", "leonardo", "replicate"]),
    default="fal",
    help="AI provider to use",
)
@click.option("--width", "-w", type=int, default=1024, help="Image width in pixels")
@click.option("--height", "-h", type=int, default=1024, help="Image height in pixels")
@click.option("--num", "-n", type=int, default=1, help="Number of images to generate")
@click.option("--negative", help="Negative prompt (things to avoid)")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path (default: downloads URL)",
)
@click.option("--json", "as_json", is_flag=True, help="Output result as JSON")
def generate_image(
    prompt: str,
    model: str,
    provider: str,
    width: int,
    height: int,
    num: int,
    negative: str | None,
    output: str | None,
    as_json: bool,
):
    """Generate images using AI models.

    \b
    Examples:
        # Generate with fal.ai (default)
        kurt media generate image --prompt "A sunset over mountains"

        # Use Leonardo.ai with Nano Banana
        kurt media generate image -p "Product photo" --provider leonardo --model nano-banana

        # Generate multiple images
        kurt media generate image -p "Abstract art" --num 4 --width 512 --height 512

        # Save to file
        kurt media generate image -p "Logo design" -o logo.png
    """
    from kurt.services.ai_generation import AIGenerationService

    async def _generate():
        service = AIGenerationService()
        try:
            result = await service.generate_image(
                prompt=prompt,
                model=model,
                provider=provider,
                width=width,
                height=height,
                num_images=num,
                negative_prompt=negative,
            )
            return result
        finally:
            await service.close()

    with console.status("[bold blue]Generating image..."):
        result = asyncio.run(_generate())

    if not result.success:
        console.print(f"[red]Error:[/red] {result.error}")
        raise SystemExit(1)

    if as_json:
        click.echo(
            json.dumps(
                {
                    "success": result.success,
                    "url": result.url,
                    "urls": result.urls,
                    "provider": result.provider,
                    "model": result.model,
                },
                indent=2,
            )
        )
        return

    # Download if output path specified
    if output and result.url:
        import httpx

        console.print(f"[dim]Downloading to {output}...[/dim]")
        response = httpx.get(result.url)
        Path(output).write_bytes(response.content)
        console.print(f"[green]Saved to:[/green] {output}")
    else:
        console.print(f"[green]Generated {len(result.urls)} image(s)[/green]")
        for i, url in enumerate(result.urls, 1):
            console.print(f"  [{i}] {url}")

    console.print(f"[dim]Provider: {result.provider} | Model: {result.model}[/dim]")


@generate_group.command(name="video")
@click.option(
    "--prompt",
    "-p",
    required=True,
    help="Text description of the video motion/content",
)
@click.option(
    "--image",
    "-i",
    type=click.Path(exists=True),
    help="Source image for image-to-video",
)
@click.option(
    "--image-url",
    help="Source image URL for image-to-video",
)
@click.option(
    "--model",
    "-m",
    default=None,
    help="Model to use (e.g., gen3a_turbo, ltx-video)",
)
@click.option(
    "--provider",
    type=click.Choice(["fal", "runway", "replicate"]),
    default="fal",
    help="AI provider to use",
)
@click.option(
    "--duration",
    "-d",
    type=int,
    default=5,
    help="Video duration in seconds",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path",
)
@click.option("--json", "as_json", is_flag=True, help="Output result as JSON")
def generate_video(
    prompt: str,
    image: str | None,
    image_url: str | None,
    model: str | None,
    provider: str,
    duration: int,
    output: str | None,
    as_json: bool,
):
    """Generate videos using AI models.

    \b
    Examples:
        # Text-to-video with fal.ai
        kurt media generate video --prompt "Ocean waves crashing"

        # Image-to-video with local file
        kurt media generate video -i hero.png -p "Slow zoom in" -d 5

        # Use Runway for high quality
        kurt media generate video -p "Camera pan" --provider runway --image-url https://...

        # Save to file
        kurt media generate video -p "Particles floating" -o intro.mp4
    """
    from kurt.services.ai_generation import AIGenerationService

    # Handle local image file
    source_url = image_url
    if image and not image_url:
        # For local files, we'd need to upload first
        # For now, require URL or use a provider that accepts base64
        console.print(
            "[yellow]Note:[/yellow] Local image files require upload. "
            "Use --image-url with a hosted image URL instead."
        )
        console.print("[dim]Tip: Upload to imgur, cloudinary, or your own server[/dim]")
        raise SystemExit(1)

    async def _generate():
        service = AIGenerationService()
        try:
            result = await service.generate_video(
                prompt=prompt,
                image_url=source_url,
                model=model,
                provider=provider,
                duration=duration,
            )
            return result
        finally:
            await service.close()

    with console.status("[bold blue]Generating video (this may take a few minutes)..."):
        result = asyncio.run(_generate())

    if not result.success:
        console.print(f"[red]Error:[/red] {result.error}")
        raise SystemExit(1)

    if as_json:
        click.echo(
            json.dumps(
                {
                    "success": result.success,
                    "url": result.url,
                    "job_id": result.job_id,
                    "provider": result.provider,
                    "model": result.model,
                },
                indent=2,
            )
        )
        return

    # Download if output path specified
    if output and result.url:
        import httpx

        console.print(f"[dim]Downloading to {output}...[/dim]")
        response = httpx.get(result.url)
        Path(output).write_bytes(response.content)
        console.print(f"[green]Saved to:[/green] {output}")
    else:
        console.print(f"[green]Video generated[/green]")
        console.print(f"  URL: {result.url}")

    console.print(f"[dim]Provider: {result.provider} | Model: {result.model}[/dim]")


# =============================================================================
# Edit Commands
# =============================================================================


@media_group.group(name="edit")
def edit_group():
    """Edit images and videos using FFmpeg/ImageMagick.

    \b
    Requirements:
        - ImageMagick: apt install imagemagick (images)
        - FFmpeg: apt install ffmpeg (video/audio)
    """
    pass


@edit_group.command(name="resize")
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--width", "-w", type=int, help="Target width in pixels")
@click.option("--height", "-h", type=int, help="Target height in pixels")
@click.option("--scale", "-s", type=float, help="Scale factor (e.g., 0.5 for half)")
@click.option(
    "--preset",
    type=click.Choice(["480p", "720p", "1080p", "4k"]),
    help="Video resolution preset",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--quality", "-q", type=int, default=85, help="Output quality (1-100)")
def edit_resize(
    input_path: str,
    width: int | None,
    height: int | None,
    scale: float | None,
    preset: str | None,
    output: str | None,
    quality: int,
):
    """Resize an image or video.

    \b
    Examples:
        # Resize image to specific dimensions
        kurt media edit resize photo.jpg --width 800 --height 600

        # Scale image by factor
        kurt media edit resize photo.jpg --scale 0.5

        # Resize video to 720p
        kurt media edit resize video.mp4 --preset 720p

        # Specify output path
        kurt media edit resize photo.jpg -w 1200 -o thumbnail.jpg
    """
    from kurt.services.media_edit import MediaEditService

    service = MediaEditService()
    path = Path(input_path)

    # Determine if image or video
    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tiff", ".avif"}
    video_exts = {".mp4", ".webm", ".mov", ".avi", ".mkv"}

    async def _resize():
        if path.suffix.lower() in image_exts:
            return await service.resize_image(
                input_path,
                output_path=output,
                width=width,
                height=height,
                scale=scale,
                quality=quality,
            )
        elif path.suffix.lower() in video_exts:
            return await service.resize_video(
                input_path,
                output_path=output,
                width=width,
                height=height,
                preset=preset,
            )
        else:
            return None

    with console.status("[bold blue]Resizing..."):
        result = asyncio.run(_resize())

    if result is None:
        console.print(f"[red]Error:[/red] Unsupported file type: {path.suffix}")
        raise SystemExit(1)

    if not result.success:
        console.print(f"[red]Error:[/red] {result.error}")
        raise SystemExit(1)

    console.print(f"[green]Resized:[/green] {result.output_path}")


@edit_group.command(name="crop")
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--width", "-w", type=int, required=True, help="Crop width")
@click.option("--height", "-h", type=int, required=True, help="Crop height")
@click.option("--x", type=int, default=0, help="X offset")
@click.option("--y", type=int, default=0, help="Y offset")
@click.option(
    "--gravity",
    "-g",
    type=click.Choice(
        ["NorthWest", "North", "NorthEast", "West", "Center", "East", "SouthWest", "South", "SouthEast"]
    ),
    help="Crop from gravity point",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def edit_crop(
    input_path: str,
    width: int,
    height: int,
    x: int,
    y: int,
    gravity: str | None,
    output: str | None,
):
    """Crop an image.

    \b
    Examples:
        # Crop from top-left
        kurt media edit crop photo.jpg --width 400 --height 400

        # Crop from center
        kurt media edit crop photo.jpg -w 400 -h 400 --gravity Center

        # Crop with offset
        kurt media edit crop photo.jpg -w 200 -h 200 --x 100 --y 50
    """
    from kurt.services.media_edit import MediaEditService

    service = MediaEditService()

    with console.status("[bold blue]Cropping..."):
        result = asyncio.run(
            service.crop_image(
                input_path,
                output_path=output,
                width=width,
                height=height,
                x=x,
                y=y,
                gravity=gravity,
            )
        )

    if not result.success:
        console.print(f"[red]Error:[/red] {result.error}")
        raise SystemExit(1)

    console.print(f"[green]Cropped:[/green] {result.output_path}")


@edit_group.command(name="rotate")
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--degrees", "-d", type=float, default=90, help="Rotation angle (positive = clockwise)")
@click.option("--background", "-b", default="white", help="Background color for corners")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def edit_rotate(
    input_path: str,
    degrees: float,
    background: str,
    output: str | None,
):
    """Rotate an image.

    \b
    Examples:
        kurt media edit rotate photo.jpg --degrees 90
        kurt media edit rotate photo.jpg -d -45 --background transparent
    """
    from kurt.services.media_edit import MediaEditService

    service = MediaEditService()

    with console.status("[bold blue]Rotating..."):
        result = asyncio.run(
            service.rotate_image(
                input_path,
                output_path=output,
                degrees=degrees,
                background=background,
            )
        )

    if not result.success:
        console.print(f"[red]Error:[/red] {result.error}")
        raise SystemExit(1)

    console.print(f"[green]Rotated:[/green] {result.output_path}")


@edit_group.command(name="filter")
@click.argument("input_path", type=click.Path(exists=True))
@click.option(
    "--filter",
    "-f",
    "filter_name",
    required=True,
    type=click.Choice(
        ["grayscale", "sepia", "blur", "sharpen", "negate", "normalize", "equalize", "brightness", "contrast"]
    ),
    help="Filter to apply",
)
@click.option("--intensity", type=int, default=80, help="Filter intensity (for sepia)")
@click.option("--radius", type=float, default=3, help="Radius (for blur/sharpen)")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def edit_filter(
    input_path: str,
    filter_name: str,
    intensity: int,
    radius: float,
    output: str | None,
):
    """Apply a filter to an image.

    \b
    Examples:
        kurt media edit filter photo.jpg --filter grayscale
        kurt media edit filter photo.jpg -f blur --radius 5
        kurt media edit filter photo.jpg -f sepia --intensity 90
    """
    from kurt.services.media_edit import MediaEditService

    service = MediaEditService()

    with console.status("[bold blue]Applying filter..."):
        result = asyncio.run(
            service.apply_filter(
                input_path,
                output_path=output,
                filter_name=filter_name,
                intensity=intensity,
                radius=radius,
            )
        )

    if not result.success:
        console.print(f"[red]Error:[/red] {result.error}")
        raise SystemExit(1)

    console.print(f"[green]Filter applied:[/green] {result.output_path}")


@edit_group.command(name="trim")
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--start", "-s", help="Start time (e.g., 00:00:30 or 30)")
@click.option("--end", "-e", help="End time (e.g., 00:01:00 or 60)")
@click.option("--duration", "-d", type=float, help="Duration in seconds (alternative to --end)")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--reencode", is_flag=True, help="Re-encode for frame-accurate cuts")
def edit_trim(
    input_path: str,
    start: str | None,
    end: str | None,
    duration: float | None,
    output: str | None,
    reencode: bool,
):
    """Trim a video to a specific segment.

    \b
    Examples:
        # Trim from 30s to 1 minute
        kurt media edit trim video.mp4 --start 00:00:30 --end 00:01:00

        # Trim first 30 seconds
        kurt media edit trim video.mp4 --duration 30

        # Trim with re-encoding for precise cuts
        kurt media edit trim video.mp4 -s 10 -e 20 --reencode
    """
    from kurt.services.media_edit import MediaEditService

    service = MediaEditService()

    with console.status("[bold blue]Trimming video..."):
        result = asyncio.run(
            service.trim_video(
                input_path,
                output_path=output,
                start=start,
                end=end,
                duration=duration,
                copy_codec=not reencode,
            )
        )

    if not result.success:
        console.print(f"[red]Error:[/red] {result.error}")
        raise SystemExit(1)

    console.print(f"[green]Trimmed:[/green] {result.output_path}")


@edit_group.command(name="thumbnail")
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--time", "-t", default="00:00:01", help="Time position to capture")
@click.option("--width", "-w", type=int, default=320, help="Thumbnail width")
@click.option("--height", "-h", type=int, help="Thumbnail height (auto if not set)")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def edit_thumbnail(
    input_path: str,
    time: str,
    width: int,
    height: int | None,
    output: str | None,
):
    """Create a thumbnail from a video.

    \b
    Examples:
        kurt media edit thumbnail video.mp4 --time 5
        kurt media edit thumbnail video.mp4 -t 00:01:30 -w 640 -o thumb.jpg
    """
    from kurt.services.media_edit import MediaEditService

    service = MediaEditService()

    with console.status("[bold blue]Creating thumbnail..."):
        result = asyncio.run(
            service.create_thumbnail(
                input_path,
                output_path=output,
                time=time,
                width=width,
                height=height,
            )
        )

    if not result.success:
        console.print(f"[red]Error:[/red] {result.error}")
        raise SystemExit(1)

    console.print(f"[green]Thumbnail created:[/green] {result.output_path}")


@edit_group.command(name="extract-audio")
@click.argument("input_path", type=click.Path(exists=True))
@click.option(
    "--format",
    "-f",
    default="mp3",
    type=click.Choice(["mp3", "wav", "aac", "ogg", "flac"]),
    help="Output audio format",
)
@click.option("--bitrate", "-b", default="192k", help="Audio bitrate")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def edit_extract_audio(
    input_path: str,
    format: str,
    bitrate: str,
    output: str | None,
):
    """Extract audio from a video file.

    \b
    Examples:
        kurt media edit extract-audio video.mp4
        kurt media edit extract-audio video.mp4 --format wav --bitrate 320k
    """
    from kurt.services.media_edit import MediaEditService

    service = MediaEditService()

    with console.status("[bold blue]Extracting audio..."):
        result = asyncio.run(
            service.extract_audio(
                input_path,
                output_path=output,
                format=format,
                bitrate=bitrate,
            )
        )

    if not result.success:
        console.print(f"[red]Error:[/red] {result.error}")
        raise SystemExit(1)

    console.print(f"[green]Audio extracted:[/green] {result.output_path}")


@edit_group.command(name="add-audio")
@click.argument("video_path", type=click.Path(exists=True))
@click.argument("audio_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--mix", is_flag=True, help="Mix with existing audio instead of replacing")
@click.option("--volume", "-v", type=float, default=1.0, help="Audio volume multiplier")
def edit_add_audio(
    video_path: str,
    audio_path: str,
    output: str | None,
    mix: bool,
    volume: float,
):
    """Add or replace audio in a video.

    \b
    Examples:
        # Replace audio
        kurt media edit add-audio video.mp4 music.mp3

        # Mix with existing audio
        kurt media edit add-audio video.mp4 voiceover.mp3 --mix --volume 0.8
    """
    from kurt.services.media_edit import MediaEditService

    service = MediaEditService()

    with console.status("[bold blue]Adding audio..."):
        result = asyncio.run(
            service.add_audio(
                video_path,
                audio_path,
                output_path=output,
                replace=not mix,
                volume=volume,
            )
        )

    if not result.success:
        console.print(f"[red]Error:[/red] {result.error}")
        raise SystemExit(1)

    console.print(f"[green]Audio added:[/green] {result.output_path}")


# =============================================================================
# Convert Command
# =============================================================================


@media_group.command(name="convert")
@click.argument("input_path", type=click.Path(exists=True))
@click.option(
    "--format",
    "-f",
    required=True,
    type=click.Choice(
        [
            "jpeg",
            "jpg",
            "png",
            "webp",
            "gif",
            "avif",
            "mp4",
            "webm",
            "mov",
            "mp3",
            "wav",
            "aac",
            "ogg",
        ]
    ),
    help="Target format",
)
@click.option("--quality", "-q", type=int, default=85, help="Output quality (for lossy formats)")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def convert(
    input_path: str,
    format: str,
    quality: int,
    output: str | None,
):
    """Convert media files between formats.

    \b
    Examples:
        # Convert image to WebP
        kurt media convert photo.jpg --format webp

        # Convert video to WebM
        kurt media convert video.mp4 --format webm

        # Convert with custom quality
        kurt media convert photo.png -f jpeg -q 90 -o compressed.jpg
    """
    from kurt.services.media_edit import MediaEditService

    service = MediaEditService()

    with console.status(f"[bold blue]Converting to {format}..."):
        result = asyncio.run(
            service.convert(
                input_path,
                output_path=output,
                format=format,
                quality=quality,
            )
        )

    if not result.success:
        console.print(f"[red]Error:[/red] {result.error}")
        raise SystemExit(1)

    console.print(f"[green]Converted:[/green] {result.output_path}")


# =============================================================================
# Info Command
# =============================================================================


@media_group.command(name="info")
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def info(input_path: str, as_json: bool):
    """Get information about a media file.

    \b
    Examples:
        kurt media info video.mp4
        kurt media info photo.jpg --json
    """
    from kurt.services.media_edit import MediaEditService

    service = MediaEditService()

    result = asyncio.run(service.get_info(input_path))

    if as_json:
        click.echo(
            json.dumps(
                {
                    "path": result.path,
                    "format": result.format,
                    "width": result.width,
                    "height": result.height,
                    "duration": result.duration,
                    "fps": result.fps,
                    "size_bytes": result.size_bytes,
                },
                indent=2,
            )
        )
        return

    table = Table(title=f"Media Info: {Path(input_path).name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Path", result.path)
    table.add_row("Format", result.format or "unknown")

    if result.width and result.height:
        table.add_row("Dimensions", f"{result.width}x{result.height}")

    if result.duration:
        mins, secs = divmod(result.duration, 60)
        table.add_row("Duration", f"{int(mins)}:{secs:05.2f}")

    if result.fps:
        table.add_row("FPS", f"{result.fps:.2f}")

    if result.size_bytes:
        size_mb = result.size_bytes / (1024 * 1024)
        table.add_row("Size", f"{size_mb:.2f} MB")

    console.print(table)


# =============================================================================
# Providers Command
# =============================================================================


@media_group.command(name="providers")
def providers():
    """Show available AI providers and their status.

    Checks which providers have API keys configured.
    """
    table = Table(title="AI Generation Providers")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Env Variable")
    table.add_column("Capabilities")

    providers_info = [
        ("fal.ai", "FAL_KEY", "Image, Video"),
        ("Leonardo.ai", "LEONARDO_API_KEY", "Image"),
        ("Replicate", "REPLICATE_API_TOKEN", "Image, Video"),
        ("Runway", "RUNWAY_API_KEY", "Video"),
    ]

    for name, env_var, caps in providers_info:
        is_configured = bool(os.environ.get(env_var))
        status = "[green]Configured[/green]" if is_configured else "[dim]Not set[/dim]"
        table.add_row(name, status, env_var, caps)

    console.print(table)
    console.print()
    console.print("[dim]Set environment variables to enable providers.[/dim]")
    console.print("[dim]Example: export FAL_KEY=your_api_key[/dim]")
