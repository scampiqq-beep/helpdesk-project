from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Iterable, List

from helpdesk_app.domain.automation import (
    AutomationActionType,
    AutomationConditionType,
    AutomationExecutionEntry,
    AutomationRule,
    normalize_rule_payload,
)


class AutomationService:
    """Безопасный foundation-layer для правил автоматизации.

    В этом шаге сервис работает поверх уже существующего тикета
    и не требует миграции БД. Правила можно передавать как список dict.
    """

    @staticmethod
    def evaluate_rules(ticket: Any, rules: Iterable[AutomationRule | Dict[str, Any]]) -> Dict[str, Any]:
        normalized_rules: List[AutomationRule] = [
            rule if isinstance(rule, AutomationRule) else normalize_rule_payload(rule)
            for rule in rules
        ]
        normalized_rules.sort(key=lambda r: (r.priority, r.key))

        execution_log: List[AutomationExecutionEntry] = []
        mutations: Dict[str, Any] = {
            "priority": getattr(ticket, "priority", None),
            "department": getattr(ticket, "department", None),
            "status": getattr(ticket, "status", None),
            "is_critical": getattr(ticket, "is_critical", False),
            "tags_to_add": [],
            "internal_notes": [],
            "assignee_email": None,
        }

        for rule in normalized_rules:
            if not rule.enabled:
                execution_log.append(
                    AutomationExecutionEntry(rule_key=rule.key, matched=False, notes=["disabled"])
                )
                continue

            matched = all(AutomationService._match_condition(ticket, cond) for cond in rule.conditions)
            entry = AutomationExecutionEntry(rule_key=rule.key, matched=matched)

            if matched:
                for action in rule.actions:
                    applied = AutomationService._apply_action(mutations, action)
                    entry.applied_actions.append(applied)
                if rule.stop_on_match:
                    entry.notes.append("stop_on_match")
                    execution_log.append(entry)
                    break

            execution_log.append(entry)

        return {
            "matched_rules": [e.rule_key for e in execution_log if e.matched],
            "mutations": mutations,
            "execution_log": [asdict(item) for item in execution_log],
        }

    @staticmethod
    def preview(ticket: Any, rules: Iterable[AutomationRule | Dict[str, Any]]) -> Dict[str, Any]:
        return AutomationService.evaluate_rules(ticket, rules)

    @staticmethod
    def _match_condition(ticket: Any, condition) -> bool:
        raw_value = condition.value

        if condition.type == AutomationConditionType.STATUS_EQUALS:
            return (getattr(ticket, "status", None) or "") == (raw_value or "")
        if condition.type == AutomationConditionType.PRIORITY_EQUALS:
            return (getattr(ticket, "priority", None) or "") == (raw_value or "")
        if condition.type == AutomationConditionType.CATEGORY_EQUALS:
            return (getattr(ticket, "category", None) or "") == (raw_value or "")
        if condition.type == AutomationConditionType.DEPARTMENT_EQUALS:
            return (getattr(ticket, "department", None) or "") == (raw_value or "")
        if condition.type == AutomationConditionType.SOURCE_EQUALS:
            return (getattr(ticket, "source", None) or "") == (raw_value or "")
        if condition.type == AutomationConditionType.CUSTOMER_TYPE_EQUALS:
            return (getattr(ticket, "customer_type", None) or "") == (raw_value or "")
        if condition.type == AutomationConditionType.TITLE_CONTAINS:
            return str(raw_value or "").lower() in str(getattr(ticket, "title", "") or "").lower()
        if condition.type == AutomationConditionType.DESCRIPTION_CONTAINS:
            return str(raw_value or "").lower() in str(getattr(ticket, "description", "") or "").lower()
        if condition.type == AutomationConditionType.SLA_BREACHED:
            return bool(getattr(ticket, "sla_breached", False))
        return False

    @staticmethod
    def _apply_action(mutations: Dict[str, Any], action) -> str:
        if action.type == AutomationActionType.SET_PRIORITY:
            mutations["priority"] = action.value
            return f"set_priority:{action.value}"
        if action.type == AutomationActionType.SET_DEPARTMENT:
            mutations["department"] = action.value
            return f"set_department:{action.value}"
        if action.type == AutomationActionType.SET_ASSIGNEE_EMAIL:
            mutations["assignee_email"] = action.value
            return f"set_assignee_email:{action.value}"
        if action.type == AutomationActionType.ADD_TAG:
            mutations["tags_to_add"].append(action.value)
            return f"add_tag:{action.value}"
        if action.type == AutomationActionType.ADD_INTERNAL_NOTE:
            mutations["internal_notes"].append(action.value)
            return "add_internal_note"
        if action.type == AutomationActionType.SET_CRITICAL:
            mutations["is_critical"] = bool(action.value)
            return f"set_critical:{bool(action.value)}"
        if action.type == AutomationActionType.SET_STATUS:
            mutations["status"] = action.value
            return f"set_status:{action.value}"
        return "noop"

    @staticmethod
    def default_rule_templates() -> List[Dict[str, Any]]:
        return [
            {
                "key": "vip-high-priority",
                "name": "VIP → высокий приоритет",
                "priority": 10,
                "conditions": [
                    {"type": "customer_type_equals", "value": "VIP"},
                ],
                "actions": [
                    {"type": "set_priority", "value": "Высокий"},
                    {"type": "set_critical", "value": True},
                ],
            },
            {
                "key": "category-1c-to-department",
                "name": "Категория 1С → отдел 1С",
                "priority": 20,
                "conditions": [
                    {"type": "category_equals", "value": "1С"},
                ],
                "actions": [
                    {"type": "set_department", "value": "Сопровождение 1С"},
                ],
            },
            {
                "key": "sla-breach-note",
                "name": "SLA breach → внутренняя заметка",
                "priority": 90,
                "conditions": [
                    {"type": "sla_breached", "value": True},
                ],
                "actions": [
                    {"type": "add_internal_note", "value": "SLA нарушен, нужна эскалация"},
                ],
            },
        ]
