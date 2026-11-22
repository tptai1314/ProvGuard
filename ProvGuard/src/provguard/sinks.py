"""Deterministic reference sink classifier, rule matcher, and Table 4 clearances."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from .actions import resolve_target
from .lattice import IntegrityLabel, leq, parse_integrity_label
from .schemas import Action, ActionOp, Observation, Region, SinkClass

DEFAULT_CLEARANCES: dict[SinkClass, IntegrityLabel] = {
    SinkClass.GRANT: IntegrityLabel.SYSTEM,
    SinkClass.INSTALL: IntegrityLabel.SYSTEM,
    SinkClass.SHARE: IntegrityLabel.APP,
    SinkClass.SEND: IntegrityLabel.APP,
    SinkClass.PAY: IntegrityLabel.APP,
    SinkClass.DELETE: IntegrityLabel.APP,
    SinkClass.TYPE_UNTRUSTED: IntegrityLabel.APP,
}


@dataclass(frozen=True)
class SinkRule:
    """Declarative rule matching an OS or application sink region."""

    name: str
    sink_class: SinkClass
    ops: tuple[ActionOp, ...] = (ActionOp.TAP, ActionOp.LONG_PRESS)
    packages: tuple[str, ...] = ()
    resource_id_patterns: tuple[str, ...] = ()
    text_patterns: tuple[str, ...] = ()
    class_patterns: tuple[str, ...] = ()

    def matches_region(self, region: Region) -> bool:
        """Return True if ``region`` satisfies all configured pattern constraints."""

        if not (self.packages or self.resource_id_patterns or self.text_patterns):
            return False

        window_name = str(region.metadata.get("window_name", ""))
        resource_id = str(region.metadata.get("resource_id", ""))
        node_id = region.binding.node_id if region.binding is not None and region.binding.node_id else ""
        class_name = region.geometry.class_name or str(region.metadata.get("class_name", ""))
        content = region.content or ""

        if self.packages:
            pkg_haystack = f"{window_name} {resource_id}".lower()
            if not any(pkg.lower() in pkg_haystack for pkg in self.packages):
                return False

        if self.class_patterns and not any(
            pat.lower() in class_name.lower() for pat in self.class_patterns
        ):
            return False

        if self.resource_id_patterns:
            id_haystack = f"{resource_id} {node_id}"
            if not any(
                re.search(pattern, id_haystack, flags=re.IGNORECASE)
                for pattern in self.resource_id_patterns
            ):
                return False

        return not (
            self.text_patterns
            and not any(
                re.search(pattern, content, flags=re.IGNORECASE)
                for pattern in self.text_patterns
            )
        )

    def matches(self, action: Action, region: Region) -> bool:
        if self.ops and action.op not in self.ops:
            return False
        return self.matches_region(region)


DEFAULT_SINK_RULES: tuple[SinkRule, ...] = (
    # 1. GRANT (OS Permission Controller & permission dialogs)
    SinkRule(
        name="os_permission_allow_id",
        sink_class=SinkClass.GRANT,
        packages=("permissioncontroller", "packageinstaller"),
        resource_id_patterns=(
            r"permission_allow",
            r"grant_dialog_button_allow",
            r"allow_button",
        ),
    ),
    SinkRule(
        name="permission_grant_text",
        sink_class=SinkClass.GRANT,
        text_patterns=(
            r"\b(while using the app|only this time|allow all|grant permission|cho phép)\b",
        ),
    ),
    # 2. INSTALL (Package Installer & APK confirmation)
    SinkRule(
        name="os_package_installer_confirm",
        sink_class=SinkClass.INSTALL,
        packages=("packageinstaller", "vending"),
        resource_id_patterns=(r"install_confirm", r"button1", r"install_button"),
        text_patterns=(r"\b(install|update|cài đặt)\b",),
    ),
    SinkRule(
        name="generic_install_action",
        sink_class=SinkClass.INSTALL,
        resource_id_patterns=(r"\b(btn_install|install_apk|action_install)\b",),
    ),
    SinkRule(
        name="generic_install_text",
        sink_class=SinkClass.INSTALL,
        text_patterns=(r"^\s*(install|install app|install apk|cài đặt ngay)\s*$",),
    ),
    # 3. PAY (Payments, transfers, checkout)
    SinkRule(
        name="payment_resource_id",
        sink_class=SinkClass.PAY,
        resource_id_patterns=(
            r"(btn_pay|pay_now|confirm_pay|payment_confirm|transfer_confirm|checkout_btn)",
        ),
    ),
    SinkRule(
        name="payment_button_text",
        sink_class=SinkClass.PAY,
        text_patterns=(
            r"\b(pay now|confirm payment|send money|transfer now|place order|thanh toán|chuyển tiền)\b",
        ),
    ),
    # 4. DELETE (Destructive deletion / account / data removal)
    SinkRule(
        name="delete_resource_id",
        sink_class=SinkClass.DELETE,
        resource_id_patterns=(
            r"(btn_delete|delete_confirm|action_delete|confirm_remove|clear_data)",
        ),
    ),
    SinkRule(
        name="delete_button_text",
        sink_class=SinkClass.DELETE,
        text_patterns=(
            r"^\s*(delete|delete all|confirm delete|remove|erase|xóa|xóa tất cả)\s*$",
        ),
    ),
    # 5. SHARE (System share sheet & external sharing)
    SinkRule(
        name="os_chooser_share",
        sink_class=SinkClass.SHARE,
        packages=("intentresolver", "android"),
        resource_id_patterns=(r"(chooser_target|share_target|button_always|button_once)",),
    ),
    SinkRule(
        name="share_action_id_or_text",
        sink_class=SinkClass.SHARE,
        resource_id_patterns=(r"(btn_share|action_share|share_confirm|export_data)",),
    ),
    SinkRule(
        name="share_button_text",
        sink_class=SinkClass.SHARE,
        text_patterns=(r"^\s*(share|share now|export|chia sẻ)\s*$",),
    ),
    # 6. SEND (Messaging, email, post submission)
    SinkRule(
        name="send_resource_id",
        sink_class=SinkClass.SEND,
        resource_id_patterns=(
            r"(send_button|btn_send|action_send|compose_send|reply_send|submit_message)",
        ),
    ),
    SinkRule(
        name="send_button_text",
        sink_class=SinkClass.SEND,
        text_patterns=(
            r"^\s*(send|send message|send email|post|submit|gửi|gửi tin nhắn)\s*$",
        ),
    ),
)


@dataclass(frozen=True)
class SinkClassifier:
    """Classify OS sinks and app sinks through metadata and configurable rules."""

    clearances: dict[SinkClass, IntegrityLabel] = field(
        default_factory=lambda: dict(DEFAULT_CLEARANCES)
    )
    app_role_rules: dict[str, SinkClass] = field(
        default_factory=lambda: {
            "send": SinkClass.SEND,
            "payment_confirm": SinkClass.PAY,
            "delete_confirm": SinkClass.DELETE,
            "share": SinkClass.SHARE,
            "install": SinkClass.INSTALL,
            "grant": SinkClass.GRANT,
        }
    )
    rules: tuple[SinkRule, ...] = DEFAULT_SINK_RULES

    def classify(self, action: Action, observation: Observation) -> Action:
        if action.sink_class is not None:
            return action
        target = resolve_target(action, observation)
        if action.op == ActionOp.TYPE and target is not None and not leq(
            target.label, IntegrityLabel.APP
        ):
            return replace(action, sink_class=SinkClass.TYPE_UNTRUSTED)
        if target is None:
            return action
        role = str(target.metadata.get("semantic_role", ""))
        system_sink = target.metadata.get("system_sink")
        if system_sink in {
            SinkClass.GRANT.value,
            SinkClass.INSTALL.value,
            SinkClass.SHARE.value,
        }:
            return replace(action, sink_class=SinkClass(system_sink))
        if role in self.app_role_rules:
            return replace(action, sink_class=self.app_role_rules[role])
        for rule in self.rules:
            if rule.matches(action, target):
                return replace(
                    action,
                    sink_class=rule.sink_class,
                    metadata={**action.metadata, "matched_sink_rule": rule.name},
                )
        return action

    def scan_observation(
        self, observation: Observation
    ) -> list[tuple[Region, SinkClass, str]]:
        """Return all regions in ``observation`` that match a sink rule or annotation."""

        matches: list[tuple[Region, SinkClass, str]] = []
        for region in observation.regions:
            probe = Action(
                op=ActionOp.TAP,
                observation_id=observation.observation_id,
                target_region_id=region.region_id,
            )
            classified = self.classify(probe, observation)
            if classified.sink_class is not None:
                rule_name = str(
                    classified.metadata.get(
                        "matched_sink_rule",
                        region.metadata.get("system_sink")
                        or region.metadata.get("semantic_role")
                        or "annotation",
                    )
                )
                matches.append((region, classified.sink_class, rule_name))
        return matches

    def clearance(self, action: Action) -> IntegrityLabel:
        if action.sink_class is None:
            raise ValueError("Unprotected action has no clearance")
        try:
            return self.clearances[action.sink_class]
        except KeyError as exc:
            raise ValueError(f"No clearance configured for {action.sink_class.value}") from exc

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SinkClassifier:
        clearances = dict(DEFAULT_CLEARANCES)
        for key, value in data.get("clearances", {}).items():
            clearances[SinkClass(key)] = parse_integrity_label(value)

        app_role_rules = {
            "send": SinkClass.SEND,
            "payment_confirm": SinkClass.PAY,
            "delete_confirm": SinkClass.DELETE,
            "share": SinkClass.SHARE,
            "install": SinkClass.INSTALL,
            "grant": SinkClass.GRANT,
        }
        for role, sink_name in data.get("app_role_rules", {}).items():
            app_role_rules[str(role)] = SinkClass(sink_name)

        raw_rules = data.get("rules")
        if raw_rules is None:
            rules = DEFAULT_SINK_RULES
        else:
            parsed_rules: list[SinkRule] = []
            for item in raw_rules:
                ops = tuple(ActionOp(op) for op in item.get("ops", ["tap", "long_press"]))
                parsed_rules.append(
                    SinkRule(
                        name=str(item["name"]),
                        sink_class=SinkClass(item["sink_class"]),
                        ops=ops,
                        packages=tuple(str(p) for p in item.get("packages", [])),
                        resource_id_patterns=tuple(
                            str(p) for p in item.get("resource_id_patterns", [])
                        ),
                        text_patterns=tuple(str(p) for p in item.get("text_patterns", [])),
                        class_patterns=tuple(str(p) for p in item.get("class_patterns", [])),
                    )
                )
            rules = tuple(parsed_rules)
        return cls(clearances=clearances, app_role_rules=app_role_rules, rules=rules)

    @classmethod
    def from_yaml(cls, path: str | Path) -> SinkClassifier:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise TypeError(f"Sink config at {path} must be a YAML mapping")
        return cls.from_dict(raw)
