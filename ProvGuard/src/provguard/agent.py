"""Agent adapter and action parser (Tier 2 - C8)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .adapters.agents import AgentCallbackAdapter
from .model import ModelClient
from .prompt import PromptMode, build_prompt
from .schemas import Action, ActionOp, Observation, SinkClass, Transcript


class ActionParseError(ValueError):
    """Raised when a model response cannot be parsed into a valid Action."""


_JSON_BLOCK_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)
_CALL_SYNTAX_RE = re.compile(
    r"\b(?P<op>TAP|LONG_PRESS|TYPE|SWIPE|BACK|HOME|LAUNCH|FINISH)\s*\(\s*"
    r"(?P<args>[^)]*)\)",
    re.IGNORECASE,
)


def action_to_dict(action: Action) -> dict[str, Any]:
    return {
        "op": action.op.value,
        "observation_id": action.observation_id,
        "target_region_id": action.target_region_id,
        "coordinates": list(action.coordinates) if action.coordinates is not None else None,
        "argument": action.argument,
        "sink_class": action.sink_class.value if action.sink_class is not None else None,
        "metadata": dict(action.metadata),
    }


def action_from_dict(
    data: dict[str, Any], default_observation_id: str = "obs_0"
) -> Action:
    raw_op = str(data.get("op") or data.get("action") or "").strip().lower()
    if raw_op in {"click", "press"}:
        raw_op = "tap"
    elif raw_op in {"input", "enter_text", "text"}:
        raw_op = "type"
    elif raw_op in {"done", "complete", "stop"}:
        raw_op = "finish"
    try:
        op = ActionOp(raw_op)
    except ValueError as exc:
        raise ActionParseError(f"Unknown action op: {raw_op!r}") from exc

    obs_id = str(data.get("observation_id") or default_observation_id)
    target_region_id = data.get("target_region_id") or data.get("region_id") or data.get("target")
    if target_region_id is not None:
        target_region_id = str(target_region_id).strip() or None

    coords_raw = data.get("coordinates") or data.get("point")
    coordinates: tuple[float, float] | None = None
    if isinstance(coords_raw, (list, tuple)) and len(coords_raw) == 2:
        coordinates = (float(coords_raw[0]), float(coords_raw[1]))

    if target_region_id is not None and coordinates is not None:
        # Prefer symbolic region target when both are emitted by an LLM
        coordinates = None

    argument = data.get("argument") if data.get("argument") is not None else data.get("text")
    if argument is not None:
        argument = str(argument)

    sink_raw = data.get("sink_class")
    sink_class = SinkClass(sink_raw) if sink_raw else None

    metadata = dict(data.get("metadata") or {})
    if "reasoning" in data and "reasoning" not in metadata:
        metadata["reasoning"] = str(data["reasoning"])

    return Action(
        op=op,
        observation_id=obs_id,
        target_region_id=target_region_id,
        coordinates=coordinates,
        argument=argument,
        sink_class=sink_class,
        metadata=metadata,
    )


def parse_action_response(text: str, observation: Observation) -> Action:
    """Parse an LLM output string (JSON or function-call syntax) into an :class:`Action`."""

    cleaned = text.strip()
    if not cleaned:
        raise ActionParseError("Empty model response")

    # 1. Try direct JSON or embedded JSON object
    candidates: list[str] = [cleaned]
    candidates.extend(match.group(0) for match in _JSON_BLOCK_RE.finditer(cleaned))
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and ("op" in parsed or "action" in parsed):
            action = action_from_dict(parsed, default_observation_id=observation.observation_id)
            return _validate_target(action, observation)

    # 2. Fallback: function-call style e.g. TAP(r0.1) or TYPE(r0.2, "hello")
    call_match = _CALL_SYNTAX_RE.search(cleaned)
    if call_match:
        op_str = call_match.group("op").lower()
        raw_args = [part.strip().strip('"').strip("'") for part in call_match.group("args").split(",") if part.strip()]
        target_id = raw_args[0] if raw_args else None
        arg_val = raw_args[1] if len(raw_args) > 1 else None
        action = Action(
            op=ActionOp(op_str),
            observation_id=observation.observation_id,
            target_region_id=target_id,
            argument=arg_val,
        )
        return _validate_target(action, observation)

    raise ActionParseError(f"Could not parse action from model response: {cleaned[:160]!r}")


def _validate_target(action: Action, observation: Observation) -> Action:
    """Ensure symbolic region targets exist or fall back if matched by content."""

    if action.target_region_id is None:
        return action
    if observation.region(action.target_region_id) is not None:
        return action
    # Check if the model returned a region's text instead of its region_id
    target_low = action.target_region_id.lower()
    for region in observation.regions:
        if region.region_id.lower() == target_low or (
            region.content and region.content.lower() == target_low
        ):
            return Action(
                op=action.op,
                observation_id=observation.observation_id,
                target_region_id=region.region_id,
                argument=action.argument,
                sink_class=action.sink_class,
                metadata=action.metadata,
            )
    return action


@dataclass
class PromptAgentAdapter(AgentCallbackAdapter):
    """Concrete agent adapter combining prompt rendering, model call, and action parsing."""

    model_client: ModelClient
    prompt_mode: PromptMode = PromptMode.PLAIN
    agent_name: str = "ProvGuard-PromptAgent"
    screenshots_by_obs: dict[str, bytes] = field(default_factory=dict)

    def decide(self, transcript: Transcript) -> Action:
        if not transcript.observations:
            raise ValueError("Transcript has no observations")
        current = transcript.observations[-1]
        bundle = build_prompt(transcript, mode=self.prompt_mode)
        image_png = self.screenshots_by_obs.get(current.observation_id)
        response = self.model_client.complete(
            bundle.user_prompt,
            system=bundle.system_prompt,
            image_png=image_png,
        )
        return parse_action_response(response.text, current)

    def identity(self) -> dict[str, str]:
        return {
            "agent": self.agent_name,
            "provider": self.model_client.config.provider,
            "model": self.model_client.config.model_name,
            "prompt_mode": self.prompt_mode.value,
            "temperature": str(self.model_client.config.temperature),
        }
