"""AI Generation Service - unified interface to image/video generation APIs.

Supported providers:
- fal.ai: Fast inference, Flux models, video generation
- Leonardo.ai: Nano Banana, Phoenix, commercial-grade
- Replicate: Huge model library, pay-per-use
- Runway: Video generation (Gen-3, Gen-4)

Environment variables:
- FAL_KEY: fal.ai API key
- LEONARDO_API_KEY: Leonardo.ai API key
- REPLICATE_API_TOKEN: Replicate API token
- RUNWAY_API_KEY: Runway API key
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx


class Provider(str, Enum):
    """Supported AI generation providers."""

    FAL = "fal"
    LEONARDO = "leonardo"
    REPLICATE = "replicate"
    RUNWAY = "runway"


class MediaType(str, Enum):
    """Type of media to generate."""

    IMAGE = "image"
    VIDEO = "video"


@dataclass
class GenerationResult:
    """Result from an AI generation request."""

    success: bool
    url: str | None = None
    urls: list[str] = field(default_factory=list)
    job_id: str | None = None
    provider: str | None = None
    model: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def primary_url(self) -> str | None:
        """Get the primary output URL."""
        return self.url or (self.urls[0] if self.urls else None)


class AIGenerationService:
    """Unified interface to AI generation APIs.

    Example:
        service = AIGenerationService()

        # Generate image
        result = await service.generate_image(
            prompt="A futuristic city at sunset",
            model="flux-dev",
        )
        print(result.url)

        # Generate video from image
        result = await service.generate_video(
            image_url=result.url,
            prompt="Slow zoom in with particles floating",
            duration=5,
        )
        print(result.url)
    """

    # Default models for each provider
    DEFAULT_MODELS = {
        Provider.FAL: {
            MediaType.IMAGE: "flux/dev",
            MediaType.VIDEO: "ltx-video/image-to-video",
        },
        Provider.LEONARDO: {
            MediaType.IMAGE: "phoenix",
        },
        Provider.REPLICATE: {
            MediaType.IMAGE: "stability-ai/sdxl",
            MediaType.VIDEO: "stability-ai/stable-video-diffusion",
        },
        Provider.RUNWAY: {
            MediaType.VIDEO: "gen3a_turbo",
        },
    }

    def __init__(
        self,
        fal_key: str | None = None,
        leonardo_key: str | None = None,
        replicate_token: str | None = None,
        runway_key: str | None = None,
        default_image_provider: Provider = Provider.FAL,
        default_video_provider: Provider = Provider.FAL,
    ):
        """Initialize the AI generation service.

        Args:
            fal_key: fal.ai API key (or FAL_KEY env var)
            leonardo_key: Leonardo.ai API key (or LEONARDO_API_KEY env var)
            replicate_token: Replicate token (or REPLICATE_API_TOKEN env var)
            runway_key: Runway API key (or RUNWAY_API_KEY env var)
            default_image_provider: Default provider for image generation
            default_video_provider: Default provider for video generation
        """
        self.fal_key = fal_key or os.environ.get("FAL_KEY")
        self.leonardo_key = leonardo_key or os.environ.get("LEONARDO_API_KEY")
        self.replicate_token = replicate_token or os.environ.get("REPLICATE_API_TOKEN")
        self.runway_key = runway_key or os.environ.get("RUNWAY_API_KEY")

        self.default_image_provider = default_image_provider
        self.default_video_provider = default_video_provider

        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=300.0)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _get_provider_key(self, provider: Provider) -> str | None:
        """Get the API key for a provider."""
        return {
            Provider.FAL: self.fal_key,
            Provider.LEONARDO: self.leonardo_key,
            Provider.REPLICATE: self.replicate_token,
            Provider.RUNWAY: self.runway_key,
        }.get(provider)

    async def generate_image(
        self,
        prompt: str,
        model: str | None = None,
        provider: Provider | str | None = None,
        width: int = 1024,
        height: int = 1024,
        num_images: int = 1,
        negative_prompt: str | None = None,
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate an image using AI.

        Args:
            prompt: Text description of the image to generate
            model: Model identifier (provider-specific)
            provider: Provider to use (fal, leonardo, replicate)
            width: Image width in pixels
            height: Image height in pixels
            num_images: Number of images to generate
            negative_prompt: Things to avoid in the image
            **kwargs: Additional provider-specific parameters

        Returns:
            GenerationResult with URL(s) of generated images
        """
        if provider is None:
            provider = self.default_image_provider
        elif isinstance(provider, str):
            provider = Provider(provider)

        if model is None:
            model = self.DEFAULT_MODELS.get(provider, {}).get(MediaType.IMAGE)

        if provider == Provider.FAL:
            return await self._fal_generate_image(
                prompt=prompt,
                model=model,
                width=width,
                height=height,
                num_images=num_images,
                negative_prompt=negative_prompt,
                **kwargs,
            )
        elif provider == Provider.LEONARDO:
            return await self._leonardo_generate_image(
                prompt=prompt,
                model=model,
                width=width,
                height=height,
                num_images=num_images,
                negative_prompt=negative_prompt,
                **kwargs,
            )
        elif provider == Provider.REPLICATE:
            return await self._replicate_generate_image(
                prompt=prompt,
                model=model,
                width=width,
                height=height,
                num_images=num_images,
                negative_prompt=negative_prompt,
                **kwargs,
            )
        else:
            return GenerationResult(
                success=False,
                error=f"Provider {provider} does not support image generation",
            )

    async def generate_video(
        self,
        prompt: str,
        image_url: str | None = None,
        model: str | None = None,
        provider: Provider | str | None = None,
        duration: int = 5,
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate a video using AI.

        Args:
            prompt: Text description of the video motion/content
            image_url: Source image URL (for image-to-video)
            model: Model identifier (provider-specific)
            provider: Provider to use (fal, runway, replicate)
            duration: Video duration in seconds
            **kwargs: Additional provider-specific parameters

        Returns:
            GenerationResult with URL of generated video
        """
        if provider is None:
            provider = self.default_video_provider
        elif isinstance(provider, str):
            provider = Provider(provider)

        if model is None:
            model = self.DEFAULT_MODELS.get(provider, {}).get(MediaType.VIDEO)

        if provider == Provider.FAL:
            return await self._fal_generate_video(
                prompt=prompt,
                image_url=image_url,
                model=model,
                duration=duration,
                **kwargs,
            )
        elif provider == Provider.RUNWAY:
            return await self._runway_generate_video(
                prompt=prompt,
                image_url=image_url,
                model=model,
                duration=duration,
                **kwargs,
            )
        elif provider == Provider.REPLICATE:
            return await self._replicate_generate_video(
                prompt=prompt,
                image_url=image_url,
                model=model,
                **kwargs,
            )
        else:
            return GenerationResult(
                success=False,
                error=f"Provider {provider} does not support video generation",
            )

    # -------------------------------------------------------------------------
    # fal.ai Implementation
    # -------------------------------------------------------------------------

    async def _fal_generate_image(
        self,
        prompt: str,
        model: str,
        width: int,
        height: int,
        num_images: int,
        negative_prompt: str | None,
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate image via fal.ai."""
        if not self.fal_key:
            return GenerationResult(
                success=False,
                error="FAL_KEY not configured",
            )

        # fal.ai uses model paths like "fal-ai/flux/dev"
        if not model.startswith("fal-ai/"):
            model = f"fal-ai/{model}"

        url = f"https://fal.run/{model}"

        payload: dict[str, Any] = {
            "prompt": prompt,
            "image_size": {"width": width, "height": height},
            "num_images": num_images,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        payload.update(kwargs)

        try:
            response = await self.client.post(
                url,
                headers={
                    "Authorization": f"Key {self.fal_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            images = data.get("images", [])
            urls = [img.get("url") for img in images if img.get("url")]

            return GenerationResult(
                success=True,
                url=urls[0] if urls else None,
                urls=urls,
                provider="fal",
                model=model,
                metadata={"seed": data.get("seed")},
            )
        except httpx.HTTPStatusError as e:
            return GenerationResult(
                success=False,
                error=f"fal.ai API error: {e.response.status_code} - {e.response.text}",
                provider="fal",
            )
        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"fal.ai request failed: {e}",
                provider="fal",
            )

    async def _fal_generate_video(
        self,
        prompt: str,
        image_url: str | None,
        model: str,
        duration: int,
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate video via fal.ai."""
        if not self.fal_key:
            return GenerationResult(
                success=False,
                error="FAL_KEY not configured",
            )

        if not model.startswith("fal-ai/"):
            model = f"fal-ai/{model}"

        url = f"https://fal.run/{model}"

        payload: dict[str, Any] = {"prompt": prompt}
        if image_url:
            payload["image_url"] = image_url
        if "num_frames" not in kwargs:
            # Approximate frames from duration (assuming ~24fps output)
            payload["num_frames"] = min(duration * 24, 257)
        payload.update(kwargs)

        try:
            response = await self.client.post(
                url,
                headers={
                    "Authorization": f"Key {self.fal_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            video_url = data.get("video", {}).get("url")

            return GenerationResult(
                success=True,
                url=video_url,
                provider="fal",
                model=model,
                metadata=data,
            )
        except httpx.HTTPStatusError as e:
            return GenerationResult(
                success=False,
                error=f"fal.ai API error: {e.response.status_code} - {e.response.text}",
                provider="fal",
            )
        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"fal.ai request failed: {e}",
                provider="fal",
            )

    # -------------------------------------------------------------------------
    # Leonardo.ai Implementation
    # -------------------------------------------------------------------------

    async def _leonardo_generate_image(
        self,
        prompt: str,
        model: str,
        width: int,
        height: int,
        num_images: int,
        negative_prompt: str | None,
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate image via Leonardo.ai."""
        if not self.leonardo_key:
            return GenerationResult(
                success=False,
                error="LEONARDO_API_KEY not configured",
            )

        base_url = "https://cloud.leonardo.ai/api/rest/v1"

        # Model name to ID mapping (common models)
        model_ids = {
            "phoenix": "6b645e3a-d64f-4341-a6d8-7a3690fbf042",
            "nano-banana": "aa77f04e-3eec-4034-9c07-d0f619684628",
            "nano-banana-pro": "faf3e8d3-6d19-4e98-8c3a-5c17e9f67a28",
            "sdxl": "1e60896f-3c26-4296-8ecc-53e2afecc132",
        }

        model_id = model_ids.get(model, model)

        payload: dict[str, Any] = {
            "prompt": prompt,
            "modelId": model_id,
            "width": width,
            "height": height,
            "num_images": num_images,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        payload.update(kwargs)

        try:
            # Start generation
            response = await self.client.post(
                f"{base_url}/generations",
                headers={
                    "Authorization": f"Bearer {self.leonardo_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            generation_id = data.get("sdGenerationJob", {}).get("generationId")
            if not generation_id:
                return GenerationResult(
                    success=False,
                    error="No generation ID returned",
                    provider="leonardo",
                )

            # Poll for completion
            urls = await self._leonardo_poll_generation(generation_id)

            return GenerationResult(
                success=True,
                url=urls[0] if urls else None,
                urls=urls,
                job_id=generation_id,
                provider="leonardo",
                model=model,
            )
        except httpx.HTTPStatusError as e:
            return GenerationResult(
                success=False,
                error=f"Leonardo API error: {e.response.status_code} - {e.response.text}",
                provider="leonardo",
            )
        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"Leonardo request failed: {e}",
                provider="leonardo",
            )

    async def _leonardo_poll_generation(
        self,
        generation_id: str,
        max_wait: int = 120,
        poll_interval: float = 2.0,
    ) -> list[str]:
        """Poll Leonardo.ai for generation completion."""
        base_url = "https://cloud.leonardo.ai/api/rest/v1"
        start_time = time.time()

        while time.time() - start_time < max_wait:
            response = await self.client.get(
                f"{base_url}/generations/{generation_id}",
                headers={"Authorization": f"Bearer {self.leonardo_key}"},
            )
            response.raise_for_status()
            data = response.json()

            generation = data.get("generations_by_pk", {})
            status = generation.get("status")

            if status == "COMPLETE":
                images = generation.get("generated_images", [])
                return [img.get("url") for img in images if img.get("url")]
            elif status == "FAILED":
                raise Exception("Generation failed")

            await asyncio.sleep(poll_interval)

        raise Exception("Generation timed out")

    # -------------------------------------------------------------------------
    # Replicate Implementation
    # -------------------------------------------------------------------------

    async def _replicate_generate_image(
        self,
        prompt: str,
        model: str,
        width: int,
        height: int,
        num_images: int,
        negative_prompt: str | None,
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate image via Replicate."""
        if not self.replicate_token:
            return GenerationResult(
                success=False,
                error="REPLICATE_API_TOKEN not configured",
            )

        base_url = "https://api.replicate.com/v1"

        # Build input based on model
        input_data: dict[str, Any] = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_outputs": num_images,
        }
        if negative_prompt:
            input_data["negative_prompt"] = negative_prompt
        input_data.update(kwargs)

        try:
            # Start prediction
            response = await self.client.post(
                f"{base_url}/predictions",
                headers={
                    "Authorization": f"Token {self.replicate_token}",
                    "Content-Type": "application/json",
                },
                json={"version": model, "input": input_data},
            )
            response.raise_for_status()
            data = response.json()

            prediction_id = data.get("id")
            if not prediction_id:
                return GenerationResult(
                    success=False,
                    error="No prediction ID returned",
                    provider="replicate",
                )

            # Poll for completion
            urls = await self._replicate_poll_prediction(prediction_id)

            return GenerationResult(
                success=True,
                url=urls[0] if urls else None,
                urls=urls,
                job_id=prediction_id,
                provider="replicate",
                model=model,
            )
        except httpx.HTTPStatusError as e:
            return GenerationResult(
                success=False,
                error=f"Replicate API error: {e.response.status_code} - {e.response.text}",
                provider="replicate",
            )
        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"Replicate request failed: {e}",
                provider="replicate",
            )

    async def _replicate_poll_prediction(
        self,
        prediction_id: str,
        max_wait: int = 300,
        poll_interval: float = 2.0,
    ) -> list[str]:
        """Poll Replicate for prediction completion."""
        base_url = "https://api.replicate.com/v1"
        start_time = time.time()

        while time.time() - start_time < max_wait:
            response = await self.client.get(
                f"{base_url}/predictions/{prediction_id}",
                headers={"Authorization": f"Token {self.replicate_token}"},
            )
            response.raise_for_status()
            data = response.json()

            status = data.get("status")

            if status == "succeeded":
                output = data.get("output", [])
                if isinstance(output, list):
                    return output
                return [output] if output else []
            elif status in ("failed", "canceled"):
                raise Exception(f"Prediction {status}: {data.get('error')}")

            await asyncio.sleep(poll_interval)

        raise Exception("Prediction timed out")

    async def _replicate_generate_video(
        self,
        prompt: str,
        image_url: str | None,
        model: str,
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate video via Replicate."""
        if not self.replicate_token:
            return GenerationResult(
                success=False,
                error="REPLICATE_API_TOKEN not configured",
            )

        base_url = "https://api.replicate.com/v1"

        input_data: dict[str, Any] = {}
        if image_url:
            input_data["image"] = image_url
        if prompt:
            input_data["prompt"] = prompt
        input_data.update(kwargs)

        try:
            response = await self.client.post(
                f"{base_url}/predictions",
                headers={
                    "Authorization": f"Token {self.replicate_token}",
                    "Content-Type": "application/json",
                },
                json={"version": model, "input": input_data},
            )
            response.raise_for_status()
            data = response.json()

            prediction_id = data.get("id")
            if not prediction_id:
                return GenerationResult(
                    success=False,
                    error="No prediction ID returned",
                    provider="replicate",
                )

            urls = await self._replicate_poll_prediction(prediction_id)

            return GenerationResult(
                success=True,
                url=urls[0] if urls else None,
                urls=urls,
                job_id=prediction_id,
                provider="replicate",
                model=model,
            )
        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"Replicate request failed: {e}",
                provider="replicate",
            )

    # -------------------------------------------------------------------------
    # Runway Implementation
    # -------------------------------------------------------------------------

    async def _runway_generate_video(
        self,
        prompt: str,
        image_url: str | None,
        model: str,
        duration: int,
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate video via Runway."""
        if not self.runway_key:
            return GenerationResult(
                success=False,
                error="RUNWAY_API_KEY not configured",
            )

        base_url = "https://api.dev.runwayml.com/v1"

        payload: dict[str, Any] = {
            "model": model,
            "promptText": prompt,
            "duration": duration,
        }
        if image_url:
            payload["promptImage"] = image_url
        payload.update(kwargs)

        try:
            # Start generation
            response = await self.client.post(
                f"{base_url}/image_to_video" if image_url else f"{base_url}/text_to_video",
                headers={
                    "Authorization": f"Bearer {self.runway_key}",
                    "Content-Type": "application/json",
                    "X-Runway-Version": "2024-11-06",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            task_id = data.get("id")
            if not task_id:
                return GenerationResult(
                    success=False,
                    error="No task ID returned",
                    provider="runway",
                )

            # Poll for completion
            video_url = await self._runway_poll_task(task_id)

            return GenerationResult(
                success=True,
                url=video_url,
                job_id=task_id,
                provider="runway",
                model=model,
            )
        except httpx.HTTPStatusError as e:
            return GenerationResult(
                success=False,
                error=f"Runway API error: {e.response.status_code} - {e.response.text}",
                provider="runway",
            )
        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"Runway request failed: {e}",
                provider="runway",
            )

    async def _runway_poll_task(
        self,
        task_id: str,
        max_wait: int = 600,
        poll_interval: float = 5.0,
    ) -> str:
        """Poll Runway for task completion."""
        base_url = "https://api.dev.runwayml.com/v1"
        start_time = time.time()

        while time.time() - start_time < max_wait:
            response = await self.client.get(
                f"{base_url}/tasks/{task_id}",
                headers={
                    "Authorization": f"Bearer {self.runway_key}",
                    "X-Runway-Version": "2024-11-06",
                },
            )
            response.raise_for_status()
            data = response.json()

            status = data.get("status")

            if status == "SUCCEEDED":
                output = data.get("output", [])
                if output:
                    return output[0]
                raise Exception("No output URL in completed task")
            elif status == "FAILED":
                raise Exception(f"Task failed: {data.get('failure')}")

            await asyncio.sleep(poll_interval)

        raise Exception("Task timed out")


# Convenience function for synchronous usage
def generate_image_sync(
    prompt: str,
    model: str | None = None,
    provider: str | None = None,
    **kwargs: Any,
) -> GenerationResult:
    """Synchronous wrapper for image generation."""
    service = AIGenerationService()
    return asyncio.run(
        service.generate_image(prompt=prompt, model=model, provider=provider, **kwargs)
    )


def generate_video_sync(
    prompt: str,
    image_url: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    **kwargs: Any,
) -> GenerationResult:
    """Synchronous wrapper for video generation."""
    service = AIGenerationService()
    return asyncio.run(
        service.generate_video(
            prompt=prompt, image_url=image_url, model=model, provider=provider, **kwargs
        )
    )
