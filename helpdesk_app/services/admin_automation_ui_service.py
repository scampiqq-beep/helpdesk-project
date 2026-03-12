from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

from flask import current_app

from helpdesk_app.models.tickets import SupportTicket
from helpdesk_app.services.admin_automation_service import AdminAutomationService
from helpdesk_app.services.automation_execution_log_service import AutomationExecutionLogService


class AdminAutomationUIService:
    STORAGE_FILENAME = "automation_rules.json"

    @staticmethod
    def storage_path() -> str:
        instance_path = current_app.instance_path
        os.makedirs(instance_path, exist_ok=True)
        return os.path.join(instance_path, AdminAutomationUIService.STORAGE_FILENAME)

    @staticmethod
    def load_rules() -> List[Dict[str, Any]]:
        path = AdminAutomationUIService.storage_path()
        if not os.path.exists(path):
            return AdminAutomationUIService._normalize_rules(AdminAutomationService.get_rule_templates())
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if isinstance(payload, list):
                return AdminAutomationUIService._normalize_rules(payload)
        except Exception:
            pass
        return AdminAutomationUIService._normalize_rules(AdminAutomationService.get_rule_templates())

    @staticmethod
    def save_rules(rules: List[Dict[str, Any]]) -> None:
        path = AdminAutomationUIService.storage_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)

    @staticmethod
    def page_context() -> Dict[str, Any]:
        builder = AdminAutomationService.get_rule_builder_context()
        rules = AdminAutomationUIService.load_rules()
        recent_tickets = (
            SupportTicket.query.order_by(SupportTicket.created_at.desc()).limit(12).all()
            if hasattr(SupportTicket, 'query') else []
        )
        return {
            **builder,
            "rules": rules,
            "rules_count": len(rules),
            "enabled_rules_count": sum(1 for rule in rules if rule.get("enabled")),
            "recent_tickets": recent_tickets,
            "execution_logs": AutomationExecutionLogService.recent_entries(12),
        }

    @staticmethod
    def create_rule(payload: Dict[str, Any]) -> Dict[str, Any]:
        rule = AdminAutomationUIService._normalize_rule(payload)
        rules = AdminAutomationUIService.load_rules()
        existing_idx = next((idx for idx, item in enumerate(rules) if item.get("key") == rule["key"]), None)
        if existing_idx is None:
            rules.append(rule)
        else:
            rules[existing_idx] = rule
        rules.sort(key=lambda item: (int(item.get("priority", 100)), str(item.get("key", ""))))
        AdminAutomationUIService.save_rules(rules)
        return rule

    @staticmethod
    def delete_rule(rule_key: str) -> bool:
        rules = AdminAutomationUIService.load_rules()
        filtered = [item for item in rules if item.get("key") != rule_key]
        if len(filtered) == len(rules):
            return False
        AdminAutomationUIService.save_rules(filtered)
        return True

    @staticmethod
    def toggle_rule(rule_key: str) -> bool:
        rules = AdminAutomationUIService.load_rules()
        changed = False
        for item in rules:
            if item.get("key") == rule_key:
                item["enabled"] = not bool(item.get("enabled", True))
                changed = True
                break
        if changed:
            AdminAutomationUIService.save_rules(rules)
        return changed

    @staticmethod
    def _normalize_rules(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        seen = set()
        for item in rules or []:
            rule = AdminAutomationUIService._normalize_rule(item)
            if rule["key"] in seen:
                continue
            seen.add(rule["key"])
            normalized.append(rule)
        normalized.sort(key=lambda item: (int(item.get("priority", 100)), str(item.get("key", ""))))
        return normalized

    @staticmethod
    def _normalize_rule(payload: Dict[str, Any]) -> Dict[str, Any]:
        raw_key = str((payload or {}).get("key") or "").strip()
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw_key).strip("-").lower()
        key = slug or "rule"
        name = str((payload or {}).get("name") or key).strip()
        try:
            priority = int((payload or {}).get("priority", 100) or 100)
        except Exception:
            priority = 100
        conditions = []
        for item in list((payload or {}).get("conditions") or []):
            item_type = str(item.get("type") or "").strip()
            if not item_type:
                continue
            conditions.append({"type": item_type, "value": item.get("value")})
        actions = []
        for item in list((payload or {}).get("actions") or []):
            item_type = str(item.get("type") or "").strip()
            if not item_type:
                continue
            actions.append({"type": item_type, "value": item.get("value")})
        if not actions:
            actions = [{"type": "add_internal_note", "value": "Создано без действия — требуется настройка"}]
        return {
            "key": key,
            "name": name,
            "enabled": bool((payload or {}).get("enabled", True)),
            "priority": priority,
            "stop_on_match": bool((payload or {}).get("stop_on_match", False)),
            "conditions": conditions,
            "actions": actions,
        }
