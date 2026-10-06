"""Live image-model catalog with a TTL cache, and request-parameter validation.

Capabilities come from OpenRouter's public model lists; no model ids are
hard-coded here.
"""

from __future__ import annotations

import asyncio
import difflib
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from .client import OpenRouterClient
from .errors import BadRequestError, CatalogUnavailableError, UnknownModelError

# Input images a chat-route model is assumed to accept when it takes images at all.
_CHAT_MAX_INPUT_IMAGES = 16
_PRICE_FIELDS = ("image_output", "image", "completion")
# Most images one tool call may ask for, whatever the model's own max n.
MAX_N = 10


@dataclass
class ModelCapabilities:
    id: str
    name: str
    description: str
    created: int
    route: Literal["images", "chat"]
    accepts_images: bool
    max_input_images: int
    aspect_ratios: list[str] | None
    resolutions: list[str] | None
    qualities: list[str] | None
    backgrounds: list[str] | None
    output_formats: list[str] | None
    max_n: int
    seed: bool
    size: bool
    is_moderated: bool | None
    pricing: dict[str, str] = field(default_factory=dict)
    min_input_images: int = 0
    pricing_lines: list[dict] = field(default_factory=list)


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _enum_values(params: dict, key: str) -> list[str] | None:
    values = _dict(params.get(key)).get("values")
    if not isinstance(values, list):
        return None
    return [str(v) for v in values]


def _range_max(params: dict, key: str, default: int) -> int:
    value = _dict(params.get(key)).get("max")
    return value if isinstance(value, int) and not isinstance(value, bool) else default


def usable_demo_image(model: ModelCapabilities) -> bool:
    """A fixed text-only tutorial needs a raster preview and no required references."""
    return (model.route == "images" and model.min_input_images == 0
            and (model.output_formats is None or any(
                value.casefold() in {"png", "jpeg", "jpg", "webp"} for value in model.output_formats)))


def _accepts_images(record: dict) -> bool:
    modalities = _dict(record.get("architecture")).get("input_modalities")
    return isinstance(modalities, list) and "image" in modalities


def _pick(primary: dict, fallback: dict, key: str, default: Any) -> Any:
    value = primary.get(key)
    if value is None:
        value = fallback.get(key)
    return default if value is None else value


def _build(model_id: str, image: dict | None, meta: dict) -> ModelCapabilities:
    source = image if image is not None else {}
    common = {
        "id": model_id,
        "name": str(_pick(source, meta, "name", model_id)),
        "description": str(_pick(source, meta, "description", "")),
        "created": int(_pick(source, meta, "created", 0)),
        "is_moderated": _dict(meta.get("top_provider")).get("is_moderated"),
        "pricing": dict(_dict(meta.get("pricing"))),
    }
    if image is None:
        accepts = _accepts_images(meta)
        return ModelCapabilities(
            **common,
            route="chat",
            accepts_images=accepts,
            max_input_images=_CHAT_MAX_INPUT_IMAGES if accepts else 0,
            aspect_ratios=None,
            resolutions=None,
            qualities=None,
            backgrounds=None,
            output_formats=None,
            max_n=1,
            seed=False,
            size=False,
        )
    params = _dict(image.get("supported_parameters"))
    minimum = _dict(params.get("input_references")).get("min", 0)
    return ModelCapabilities(
        **common,
        route="images",
        accepts_images=_accepts_images(image),
        max_input_images=_range_max(params, "input_references", 0),
        min_input_images=minimum if type(minimum) is int and minimum >= 0 else -1,
        pricing_lines=image.get("pricing") if isinstance(image.get("pricing"), list) else [],
        aspect_ratios=_enum_values(params, "aspect_ratio"),
        resolutions=_enum_values(params, "resolution"),
        qualities=_enum_values(params, "quality"),
        backgrounds=_enum_values(params, "background"),
        output_formats=_enum_values(params, "output_format"),
        max_n=_range_max(params, "n", 1),
        seed="seed" in params,
        size="size" in params,
    )


def _merge(images: list[dict], metas: list[dict]) -> list[ModelCapabilities]:
    meta_by_id = {m["id"]: m for m in metas if isinstance(m, dict) and "id" in m}
    models: list[ModelCapabilities] = []
    seen: set[str] = set()
    for record in images:
        if not isinstance(record, dict) or "id" not in record or record["id"] in seen:
            continue
        seen.add(record["id"])
        models.append(_build(record["id"], record, meta_by_id.get(record["id"], {})))
    for model_id, meta in meta_by_id.items():
        if model_id not in seen:
            models.append(_build(model_id, None, meta))
    models.sort(key=lambda m: m.created, reverse=True)
    return models


class Catalog:
    def __init__(
        self,
        client: OpenRouterClient,
        ttl_s: float = 600,
        stale_ok_s: float = 86400,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client
        self._ttl_s = ttl_s
        self._stale_ok_s = stale_ok_s
        self._clock = clock
        self._lock = asyncio.Lock()
        self._models: list[ModelCapabilities] | None = None
        self._fetched_at = 0.0
        self._endpoints: dict[str, tuple[float, list[dict]]] = {}
        self._endpoints_lock = asyncio.Lock()

    async def all(self) -> list[ModelCapabilities]:
        """All image models, newest first. Falls back to a stale cache when offline."""
        async with self._lock:
            now = self._clock()
            if self._models is not None and now - self._fetched_at < self._ttl_s:
                return list(self._models)
            results = await asyncio.gather(
                self._client.image_models(),
                self._client.image_models_meta(),
                return_exceptions=True,
            )
            failure = next((r for r in results if isinstance(r, BaseException)), None)
            if failure is not None:
                if (
                    isinstance(failure, CatalogUnavailableError)
                    and self._models is not None
                    and now - self._fetched_at <= self._stale_ok_s
                ):
                    return list(self._models)
                raise failure
            images, metas = results
            self._models = _merge(images, metas)
            self._fetched_at = now
            return list(self._models)

    async def get(self, model_id: str) -> ModelCapabilities:
        models = await self.all()
        for model in models:
            if model.id == model_id:
                return model
        ids = [m.id for m in models]
        raise UnknownModelError(
            model_id, difflib.get_close_matches(model_id, ids, n=3, cutoff=0.6)
        )

    async def endpoints(self, model_id: str) -> list[dict]:
        await self.get(model_id)  # raises UnknownModelError / CatalogUnavailableError
        async with self._endpoints_lock:
            now = self._clock()
            cached = self._endpoints.get(model_id)
            if cached is not None and now - cached[0] < self._ttl_s:
                return list(cached[1])
            try:
                data = await self._client.image_model_endpoints(model_id)
            except CatalogUnavailableError:
                if cached is not None and now - cached[0] <= self._stale_ok_s:
                    return list(cached[1])
                raise
            self._endpoints[model_id] = (now, data)
            return list(data)


def price_key(m: ModelCapabilities) -> float:
    """Sort key: per-image price if known, else per-image/completion, else last.

    Negative values (the router models report "-1" for variable pricing) are
    treated as unknown rather than as the cheapest model.
    """
    for name in _PRICE_FIELDS:
        try:
            value = float(m.pricing[name])
        except (KeyError, TypeError, ValueError):
            continue
        if value >= 0:
            return value
    return float("inf")


def _unsupported(m: ModelCapabilities, param: str) -> BadRequestError:
    return BadRequestError(f"{m.id} does not support {param}")


def validate_params(
    m: ModelCapabilities,
    *,
    n: int | None,
    aspect_ratio: str | None,
    resolution: str | None,
    quality: str | None,
    background: str | None,
    output_format: str | None,
    seed: int | None,
    size: str | None,
    input_count: int,
) -> list[str]:
    """Validate request parameters against the model's capabilities.

    Returns human-readable notes; raises ``BadRequestError`` on invalid input.
    """
    if m.route == "chat":
        # Chat-route models take only aspect_ratio, and it passes through unvalidated.
        given = {
            "resolution": resolution,
            "quality": quality,
            "background": background,
            "output_format": output_format,
            "seed": seed,
            "size": size,
        }
        for param, value in given.items():
            if value is not None:
                raise BadRequestError(
                    f"{param} is not supported for {m.id}; this model only supports aspect_ratio"
                )
    else:
        enums = {
            "aspect_ratio": (aspect_ratio, m.aspect_ratios),
            "resolution": (resolution, m.resolutions),
            "quality": (quality, m.qualities),
            "background": (background, m.backgrounds),
            "output_format": (output_format, m.output_formats),
        }
        for param, (value, allowed) in enums.items():
            if value is None:
                continue
            if allowed is None:
                raise _unsupported(m, param)
            if value not in allowed:
                raise BadRequestError(
                    f"{param} '{value}' is not supported by {m.id}. Allowed: {', '.join(allowed)}"
                )
        if seed is not None and not m.seed:
            raise _unsupported(m, "seed")
        if size is not None and not m.size:
            raise _unsupported(m, "size")

    if input_count > 0 and not m.accepts_images:
        raise BadRequestError(f"{m.id} does not accept input images")
    if input_count > m.max_input_images:
        raise BadRequestError(
            f"{m.id} accepts at most {m.max_input_images} input images (got {input_count})"
        )

    notes: list[str] = []
    count = 1 if n is None else n
    if not 1 <= count <= MAX_N:
        raise BadRequestError(f"n must be between 1 and {MAX_N} (got {count})")
    if count > m.max_n:
        notes.append(f"model max n is {m.max_n}; will make {len(batch_sizes(count, m.max_n))} calls")
    return notes


def batch_sizes(n: int, max_n: int) -> list[int]:
    """Split `n` images into calls of at most `max_n`; the last call gets the remainder."""
    per_call = max(1, max_n)
    full, rest = divmod(n, per_call)
    return [per_call] * full + ([rest] if rest else [])
