from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class AutomationConditionType(str, Enum):
    STATUS_EQUALS = "status_equals"
    PRIORITY_EQUALS = "priority_equals"
    CATEGORY_EQUALS = "category_equals"
    DEPARTMENT_EQUALS = "department_equals"
    SOURCE_EQUALS = "source_equals"
    CUSTOMER_TYPE_EQUALS = "customer_type_equals"
    TITLE_CONTAINS = "title_contains"
    DESCRIPTION_CONTAINS = "description_contains"
    SLA_BREACHED = "sla_breached"


class AutomationActionType(str, Enum):
    SET_PRIORITY = "set_priority"
    SET_DEPARTMENT = "set_department"
    SET_ASSIGNEE_EMAIL = "set_assignee_email"
    ADD_TAG = "add_tag"
    ADD_INTERNAL_NOTE = "add_internal_note"
    SET_CRITICAL = "set_critical"
    SET_STATUS = "set_status"


@dataclass(slots=True)
class AutomationCondition:
    type: AutomationConditionType
    value: Any = None


@dataclass(slots=True)
class AutomationAction:
    type: AutomationActionType
    value: Any = None


@dataclass(slots=True)
class AutomationRule:
    key: str
    name: str
    enabled: bool = True
    priority: int = 100
    stop_on_match: bool = False
    conditions: List[AutomationCondition] = field(default_factory=list)
    actions: List[AutomationAction] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AutomationExecutionEntry:
    rule_key: str
    matched: bool
    applied_actions: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


def normalize_rule_payload(payload: Dict[str, Any]) -> AutomationRule:
    conditions = [
        AutomationCondition(
            type=AutomationConditionType(item["type"]),
            value=item.get("value"),
        )
        for item in payload.get("conditions", [])
    ]
    actions = [
        AutomationAction(
            type=AutomationActionType(item["type"]),
            value=item.get("value"),
        )
        for item in payload.get("actions", [])
    ]
    return AutomationRule(
        key=str(payload["key"]),
        name=str(payload.get("name") or payload["key"]),
        enabled=bool(payload.get("enabled", True)),
        priority=int(payload.get("priority", 100)),
        stop_on_match=bool(payload.get("stop_on_match", False)),
        conditions=conditions,
        actions=actions,
        meta=dict(payload.get("meta") or {}),
    )
