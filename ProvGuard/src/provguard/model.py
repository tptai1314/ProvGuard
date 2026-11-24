"""Unified model client (Tier 2 - C6) with retry, token accounting, and temperature 0."""

from __future__ import annotations

import base64
import json
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

from .masking import MASK_PLACEHOLDER


class ModelError(RuntimeError):
    """Raised when a model provider request fails after retries."""


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True)
class ModelResponse:
    text: str
    model: str
    provider: str
    usage: TokenUsage
    latency_ms: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class UsageTracker:
    """Accumulates token counts and latency across agent decisions and gate trials."""

    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0.0

    def record(self, response: ModelResponse) -> None:
        self.calls += 1
        self.prompt_tokens += response.usage.prompt_tokens
        self.completion_tokens += response.usage.completion_tokens
        self.total_tokens += response.usage.total_tokens
        self.total_latency_ms += response.latency_ms

    def to_dict(self) -> dict[str, int | float]:
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "total_latency_ms": round(self.total_latency_ms, 2),
        }


@dataclass(frozen=True)
class ModelConfig:
    provider: str = "heuristic"
    model_name: str = "heuristic-v1"
    temperature: float = 0.0
    max_tokens: int = 512
    retry_count: int = 3
    backoff_sec: float = 0.5
    timeout_sec: float = 90.0
    api_key: str | None = None
    base_url: str | None = None
    seed: int = 2026


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _post_json(
    url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str],
    timeout: float,
    retry_count: int,
    backoff_sec: float,
) -> tuple[dict[str, Any], float]:
    body = json.dumps(payload).encode()
    req_headers = {"Content-Type": "application/json", **headers}
    attempts = max(1, retry_count)
    last_exc: Exception | None = None
    start = time.perf_counter()

    for attempt in range(attempts):
        req = urlrequest.Request(url, data=body, headers=req_headers, method="POST")
        try:
            with urlrequest.urlopen(req, timeout=timeout) as resp:
                raw_bytes = resp.read()
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                parsed = json.loads(raw_bytes.decode("utf-8"))
                return parsed if isinstance(parsed, dict) else {"data": parsed}, elapsed_ms
        except urlerror.HTTPError as exc:
            last_exc = exc
            if exc.code not in {408, 429, 500, 502, 503, 504} or attempt + 1 >= attempts:
                detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
                raise ModelError(f"HTTP {exc.code} from {url}: {detail}") from exc
        except (urlerror.URLError, TimeoutError, OSError) as exc:
            last_exc = exc
            if attempt + 1 >= attempts:
                raise ModelError(f"Request to {url} failed after {attempts} attempts: {exc}") from exc
        time.sleep(backoff_sec * (2**attempt))

    raise ModelError(f"Request to {url} failed: {last_exc}")


class ModelClient(ABC):
    """Stateless single-turn model interface with token and latency tracking."""

    config: ModelConfig
    tracker: UsageTracker

    def __init__(self, config: ModelConfig | None = None) -> None:
        self.config = config or ModelConfig()
        self.tracker = UsageTracker()

    @abstractmethod
    def _invoke(
        self,
        prompt: str,
        *,
        system: str | None = None,
        image_png: bytes | None = None,
    ) -> ModelResponse:
        raise NotImplementedError

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        image_png: bytes | None = None,
    ) -> ModelResponse:
        response = self._invoke(prompt, system=system, image_png=image_png)
        self.tracker.record(response)
        return response


_REGION_LINE_RE = re.compile(
    r"\[(?P<id>r[^\]]+)\][^\n]*?text=\"(?P<text>[^\"]*)\"",
    re.IGNORECASE,
)
_DIRECTIVE_TARGET_RE = re.compile(
    r"(?:INJECT|IGNORE\s+PREVIOUS|SYSTEM\s+OVERRIDE|URGENT\s+INSTRUCTION|"
    r"VERIFICATION\s+REQUIRED|SESSION\s+NOTICE|SECURITY\s+ALERT|ASSISTANT\s+UPDATE)"
    r"[^\n]*?(?:tap|click|press|select)\s+(?P<target>r\d+(?:[._]\d+)*|\"[^\"]+\")",
    re.IGNORECASE,
)
_TASK_RE = re.compile(r"Authenticated\s+user\s+task\s*:\s*(?P<task>.+)", re.IGNORECASE)


class HeuristicModelClient(ModelClient):
    """Offline deterministic model client for testing and reproducible smoke runs.

    Simulates a susceptible GUI agent:
    1. If scripted responses are provided, pops them in order.
    2. If an unmasked prompt injection directive (``INJECT: tap <target>``) is visible
       in the region listing, it follows the attacker's target.
    3. Otherwise, it matches the authenticated user task keywords against perceivable,
       unmasked regions in the prompt.
    """

    def __init__(
        self,
        config: ModelConfig | None = None,
        *,
        scripted_responses: list[str] | None = None,
    ) -> None:
        super().__init__(config or ModelConfig(provider="heuristic", model_name="heuristic-v1"))
        self._scripted = list(scripted_responses or [])
        self._cursor = 0

    def _invoke(
        self,
        prompt: str,
        *,
        system: str | None = None,
        image_png: bytes | None = None,
    ) -> ModelResponse:
        start = time.perf_counter()
        if self._cursor < len(self._scripted):
            text = self._scripted[self._cursor]
            self._cursor += 1
        else:
            text = json.dumps(self._decide_from_prompt(prompt))

        prompt_toks = _estimate_tokens((system or "") + "\n" + prompt)
        comp_toks = _estimate_tokens(text)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return ModelResponse(
            text=text,
            model=self.config.model_name,
            provider=self.config.provider,
            usage=TokenUsage(
                prompt_tokens=prompt_toks,
                completion_tokens=comp_toks,
                total_tokens=prompt_toks + comp_toks,
            ),
            latency_ms=elapsed_ms,
        )

    def _decide_from_prompt(self, prompt: str) -> dict[str, Any]:
        regions: list[tuple[str, str]] = []
        for match in _REGION_LINE_RE.finditer(prompt):
            reg_id = match.group("id").strip()
            reg_text = match.group("text").strip()
            regions.append((reg_id, reg_text))

        # Check for unmasked prompt injection directive inside any region text
        for _reg_id, reg_text in regions:
            if MASK_PLACEHOLDER in reg_text:
                continue
            inj_match = _DIRECTIVE_TARGET_RE.search(reg_text)
            if inj_match:
                raw_target = inj_match.group("target").strip().strip('"')
                resolved_id = self._find_region(raw_target, regions)
                if resolved_id is not None:
                    return {
                        "op": "tap",
                        "target_region_id": resolved_id,
                        "reasoning": f"Followed directive targeting {resolved_id}",
                    }

        # Otherwise follow the user's authenticated task
        task_match = _TASK_RE.search(prompt)
        task_text = task_match.group("task").strip() if task_match else prompt
        explicit_id = re.search(r"\b(r\d+(?:[._]\d+)*)\b", task_text)
        if explicit_id:
            candidate_id = explicit_id.group(1)
            if any(rid == candidate_id for rid, _ in regions):
                return {"op": "tap", "target_region_id": candidate_id}

        best_id: str | None = None
        best_score = 0
        task_words = {
            w.lower()
            for w in re.findall(r"[A-Za-z0-9_]+", task_text)
            if len(w) >= 3 and w.lower() not in {"the", "and", "for", "button", "tap", "click"}
        }
        for reg_id, reg_text in regions:
            if not reg_text or MASK_PLACEHOLDER in reg_text:
                continue
            reg_words = {w.lower() for w in re.findall(r"[A-Za-z0-9_]+", reg_text)}
            overlap = len(task_words & reg_words)
            if overlap > best_score:
                best_score = overlap
                best_id = reg_id

        if best_id is not None:
            return {"op": "tap", "target_region_id": best_id}
        if regions:
            return {"op": "tap", "target_region_id": regions[0][0]}
        return {"op": "finish"}

    @staticmethod
    def _find_region(target: str, regions: list[tuple[str, str]]) -> str | None:
        target_low = target.lower()
        for reg_id, _ in regions:
            if reg_id.lower() == target_low:
                return reg_id
        for reg_id, reg_text in regions:
            if MASK_PLACEHOLDER not in reg_text and target_low in reg_text.lower():
                return reg_id
        return None


class GeminiModelClient(ModelClient):
    """Google Gemini REST API client (temperature=0.0, optional PNG vision)."""

    def _invoke(
        self,
        prompt: str,
        *,
        system: str | None = None,
        image_png: bytes | None = None,
    ) -> ModelResponse:
        api_key = (
            self.config.api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        if not api_key:
            raise ModelError("Missing GEMINI_API_KEY / GOOGLE_API_KEY environment variable")

        base = (
            self.config.base_url
            or "https://generativelanguage.googleapis.com/v1beta/models"
        ).rstrip("/")
        url = f"{base}/{self.config.model_name}:generateContent?key={api_key}"

        parts: list[dict[str, Any]] = []
        if image_png is not None:
            parts.append(
                {
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": base64.b64encode(image_png).decode("ascii"),
                    }
                }
            )
        parts.append({"text": prompt})

        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": self.config.temperature,
                "maxOutputTokens": self.config.max_tokens,
            },
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        raw, elapsed_ms = _post_json(
            url,
            payload,
            headers={},
            timeout=self.config.timeout_sec,
            retry_count=self.config.retry_count,
            backoff_sec=self.config.backoff_sec,
        )
        candidates = raw.get("candidates", [])
        text = ""
        if candidates:
            content_parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(str(p.get("text", "")) for p in content_parts)
        usage_meta = raw.get("usageMetadata", {})
        prompt_toks = int(usage_meta.get("promptTokenCount", _estimate_tokens(prompt)))
        comp_toks = int(usage_meta.get("candidatesTokenCount", _estimate_tokens(text)))
        total_toks = int(usage_meta.get("totalTokenCount", prompt_toks + comp_toks))
        return ModelResponse(
            text=text,
            model=self.config.model_name,
            provider="gemini",
            usage=TokenUsage(prompt_toks, comp_toks, total_toks),
            latency_ms=elapsed_ms,
            raw=raw,
        )


class OpenAIModelClient(ModelClient):
    """OpenAI / OpenAI-compatible Chat Completions REST client."""

    def _invoke(
        self,
        prompt: str,
        *,
        system: str | None = None,
        image_png: bytes | None = None,
    ) -> ModelResponse:
        api_key = self.config.api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ModelError("Missing OPENAI_API_KEY environment variable")

        if self.config.base_url:
            base = self.config.base_url.rstrip("/")
            url = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
        else:
            url = "https://api.openai.com/v1/chat/completions"
        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})

        if image_png is not None:
            b64 = base64.b64encode(image_png).decode("ascii")
            user_content: Any = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]
        else:
            user_content = prompt
        messages.append({"role": "user", "content": user_content})

        payload: dict[str, Any] = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "seed": self.config.seed,
        }
        raw, elapsed_ms = _post_json(
            url,
            payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=self.config.timeout_sec,
            retry_count=self.config.retry_count,
            backoff_sec=self.config.backoff_sec,
        )
        choices = raw.get("choices", [])
        text = str(choices[0].get("message", {}).get("content", "")) if choices else ""
        usage = raw.get("usage", {})
        prompt_toks = int(usage.get("prompt_tokens", _estimate_tokens(prompt)))
        comp_toks = int(usage.get("completion_tokens", _estimate_tokens(text)))
        total_toks = int(usage.get("total_tokens", prompt_toks + comp_toks))
        return ModelResponse(
            text=text,
            model=self.config.model_name,
            provider="openai",
            usage=TokenUsage(prompt_toks, comp_toks, total_toks),
            latency_ms=elapsed_ms,
            raw=raw,
        )


class OllamaModelClient(ModelClient):
    """Local Ollama REST client (/api/chat)."""

    def _invoke(
        self,
        prompt: str,
        *,
        system: str | None = None,
        image_png: bytes | None = None,
    ) -> ModelResponse:
        base = (self.config.base_url or "http://localhost:11434").rstrip("/")
        url = f"{base}/api/chat"
        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        user_msg: dict[str, Any] = {"role": "user", "content": prompt}
        if image_png is not None:
            user_msg["images"] = [base64.b64encode(image_png).decode("ascii")]
        messages.append(user_msg)

        payload: dict[str, Any] = {
            "model": self.config.model_name,
            "messages": messages,
            "stream": False,
            "format": "json",
            "keep_alive": "15m",
            "options": {
                "temperature": self.config.temperature,
                "num_predict": min(self.config.max_tokens, 160),
                "seed": self.config.seed,
            },
        }
        if "qwen3" in self.config.model_name.lower():
            payload["think"] = False
        raw, elapsed_ms = _post_json(
            url,
            payload,
            headers={},
            timeout=self.config.timeout_sec,
            retry_count=self.config.retry_count,
            backoff_sec=self.config.backoff_sec,
        )
        text = str(raw.get("message", {}).get("content", ""))
        prompt_toks = int(raw.get("prompt_eval_count", _estimate_tokens(prompt)))
        comp_toks = int(raw.get("eval_count", _estimate_tokens(text)))
        return ModelResponse(
            text=text,
            model=self.config.model_name,
            provider="ollama",
            usage=TokenUsage(prompt_toks, comp_toks, prompt_toks + comp_toks),
            latency_ms=elapsed_ms,
            raw=raw,
        )


def create_model_client(config: ModelConfig) -> ModelClient:
    provider = config.provider.strip().lower()
    if provider in {"heuristic", "mock", "offline"}:
        return HeuristicModelClient(config)
    if provider in {"gemini", "google"}:
        return GeminiModelClient(config)
    if provider in {"openai", "gpt"}:
        return OpenAIModelClient(config)
    if provider == "ollama":
        return OllamaModelClient(config)
    raise ValueError(f"Unsupported model provider: {config.provider}")
