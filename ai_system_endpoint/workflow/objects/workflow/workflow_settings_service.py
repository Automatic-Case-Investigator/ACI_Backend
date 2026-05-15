from __future__ import annotations

from ACI_Backend.utils.workflow_utils import now_iso, to_int, trim_text
from ai_system_endpoint.models import WorkflowRun, WorkflowSettings
from siem_endpoint.models import SIEMInfo
from soar_endpoint.models import SOARInfo


class WorkflowSettingsService:
    def get_singleton(self) -> WorkflowSettings:
        settings_obj = WorkflowSettings.objects.order_by("created_at").first()
        if settings_obj is None:
            settings_obj = WorkflowSettings.objects.create()
        return settings_obj

    def serialize(self, settings_obj: WorkflowSettings) -> dict:
        return {
            "enabled": settings_obj.enabled,
            "max_concurrent_workflows": settings_obj.max_concurrent_workflows,
            "webhook": {
                "bearer_key": settings_obj.webhook_bearer_key,
            },
            "soar_id": str(settings_obj.soar_id) if settings_obj.soar_id else None,
            "siem_id": str(settings_obj.siem_id) if settings_obj.siem_id else None,
            "task_generation": {
                "enabled": settings_obj.task_generation_enabled,
                "use_web_search": settings_obj.task_generation_use_web_search,
                "additional_notes": settings_obj.task_generation_additional_notes,
            },
            "activity_generation": {
                "enabled": settings_obj.activity_generation_enabled,
                "use_web_search": settings_obj.activity_generation_use_web_search,
                "additional_notes": settings_obj.activity_generation_additional_notes,
            },
            "investigation": {
                "enabled": settings_obj.investigation_enabled,
                "use_web_search": settings_obj.investigation_use_web_search,
                "additional_notes": settings_obj.investigation_additional_notes,
                "earliest_magnitude": settings_obj.investigation_earliest_magnitude,
                "earliest_unit": settings_obj.investigation_earliest_unit,
                "vicinity_magnitude": settings_obj.investigation_vicinity_magnitude,
                "vicinity_unit": settings_obj.investigation_vicinity_unit,
                "max_iterations": settings_obj.investigation_max_iterations,
                "max_queries_per_iteration": settings_obj.investigation_max_queries_per_iteration,
            },
            "report_generation": {
                "enabled": settings_obj.report_generation_enabled,
                "use_web_search": settings_obj.report_generation_use_web_search,
                "additional_notes": settings_obj.report_generation_additional_notes,
                "report_template_id": settings_obj.report_generation_report_template_id,
            },
        }

    def build_snapshot(self, settings_obj: WorkflowSettings) -> dict:
        snapshot = self.serialize(settings_obj)
        snapshot["updated_at"] = (
            now_iso()
            if settings_obj.updated_at is None
            else settings_obj.updated_at.isoformat().replace("+00:00", "Z")
        )
        return snapshot

    def normalize_payload(self, payload: dict) -> tuple[dict | None, dict | None]:
        raw_settings = payload.get("settings", payload)
        if not isinstance(raw_settings, dict):
            return None, {"settings": ["Must be an object"]}

        normalized = {
            "enabled": bool(raw_settings.get("enabled", False)),
            "max_concurrent_workflows": 3,
            "webhook": {
                "bearer_key": None,
            },
            "soar_id": None,
            "siem_id": None,
            "task_generation": {
                "enabled": False,
                "use_web_search": False,
                "additional_notes": "",
            },
            "activity_generation": {
                "enabled": False,
                "use_web_search": False,
                "additional_notes": "",
            },
            "investigation": {
                "enabled": False,
                "use_web_search": False,
                "additional_notes": "",
                "earliest_magnitude": 1,
                "earliest_unit": "years",
                "vicinity_magnitude": 1,
                "vicinity_unit": "hours",
                "max_iterations": 3,
                "max_queries_per_iteration": 5,
            },
            "report_generation": {
                "enabled": False,
                "use_web_search": False,
                "additional_notes": "",
                "report_template_id": "",
            },
        }
        details: dict[str, list[str]] = {}

        max_concurrent = to_int(raw_settings.get("max_concurrent_workflows"))
        if max_concurrent is None or not 1 <= max_concurrent <= 50:
            details["settings.max_concurrent_workflows"] = [
                "Must be an integer between 1 and 50"
            ]
        else:
            normalized["max_concurrent_workflows"] = max_concurrent

        webhook_section = raw_settings.get("webhook")
        if webhook_section is not None:
            if not isinstance(webhook_section, dict):
                details["settings.webhook"] = ["Must be an object"]
            else:
                bearer_key = webhook_section.get("bearer_key", "")
                if bearer_key is None:
                    bearer_key = ""
                if not isinstance(bearer_key, str):
                    details["settings.webhook.bearer_key"] = ["Must be a string"]
                else:
                    normalized["webhook"]["bearer_key"] = trim_text(
                        bearer_key, limit=256
                    )

        soar_id = to_int(raw_settings.get("soar_id"))
        if soar_id is None:
            details["settings.soar_id"] = [
                "Must reference an existing active SOAR integration"
            ]
        else:
            soar_obj = SOARInfo.objects.filter(id=soar_id).first()
            if soar_obj is None:
                details["settings.soar_id"] = ["SOAR integration not found"]
            elif not soar_obj.is_active:
                details["settings.soar_id"] = ["SOAR integration is inactive"]
            else:
                normalized["soar_id"] = soar_obj.id

        siem_id = raw_settings.get("siem_id")
        if siem_id is not None:
            parsed_siem_id = to_int(siem_id)
            if (
                parsed_siem_id is None
                or SIEMInfo.objects.filter(id=parsed_siem_id).first() is None
            ):
                details["settings.siem_id"] = ["SIEM integration not found"]
            else:
                normalized["siem_id"] = parsed_siem_id

        def parse_step(section_name: str, allowed_keys: tuple[str, ...]) -> dict:
            section = raw_settings.get(section_name, {})
            if section is None:
                section = {}
            if not isinstance(section, dict):
                details[f"settings.{section_name}"] = ["Must be an object"]
                return normalized[section_name]

            parsed = dict(normalized[section_name])
            enabled_value = section.get("enabled")
            if isinstance(enabled_value, bool):
                parsed["enabled"] = enabled_value

            web_search_value = section.get("use_web_search")
            if isinstance(web_search_value, bool):
                parsed["use_web_search"] = web_search_value

            notes_value = section.get("additional_notes")
            if notes_value is not None:
                if not isinstance(notes_value, str):
                    details[f"settings.{section_name}.additional_notes"] = [
                        "Must be a string"
                    ]
                else:
                    parsed["additional_notes"] = trim_text(notes_value)

            for key in allowed_keys:
                if key not in section:
                    continue
                value = section.get(key)
                if key.endswith("_unit") or key == "report_template_id":
                    if not isinstance(value, str):
                        details[f"settings.{section_name}.{key}"] = ["Must be a string"]
                    else:
                        parsed[key] = value.strip() if key == "report_template_id" else value
                    continue
                numeric_value = to_int(value)
                if numeric_value is None:
                    details[f"settings.{section_name}.{key}"] = ["Must be an integer"]
                else:
                    parsed[key] = numeric_value

            return parsed

        normalized["task_generation"] = parse_step("task_generation", ())
        normalized["activity_generation"] = parse_step("activity_generation", ())
        normalized["investigation"] = parse_step(
            "investigation",
            (
                "earliest_magnitude",
                "earliest_unit",
                "vicinity_magnitude",
                "vicinity_unit",
                "max_iterations",
                "max_queries_per_iteration",
            ),
        )
        normalized["report_generation"] = parse_step(
            "report_generation", ("report_template_id",)
        )

        for section_name in (
            "task_generation",
            "activity_generation",
            "investigation",
            "report_generation",
        ):
            normalized[section_name]["additional_notes"] = trim_text(
                normalized[section_name].get("additional_notes", "")
            )

        investigation = normalized["investigation"]
        if investigation["earliest_unit"] not in {
            "minutes",
            "hours",
            "days",
            "weeks",
            "months",
            "years",
        }:
            details["settings.investigation.earliest_unit"] = ["Must be a valid unit"]
        if investigation["vicinity_unit"] not in {"minutes", "hours", "days"}:
            details["settings.investigation.vicinity_unit"] = ["Must be a valid unit"]

        for key in (
            "earliest_magnitude",
            "vicinity_magnitude",
            "max_iterations",
            "max_queries_per_iteration",
        ):
            value = investigation[key]
            if not 1 <= int(value) <= 20:
                details[f"settings.investigation.{key}"] = ["Must be between 1 and 20"]

        if (
            normalized["report_generation"]["enabled"]
            and not normalized["report_generation"]["report_template_id"]
        ):
            details["settings.report_generation.report_template_id"] = [
                "Required when report generation is enabled"
            ]

        if details:
            return None, details

        if not normalized["task_generation"]["enabled"]:
            normalized["activity_generation"]["enabled"] = False
            normalized["investigation"]["enabled"] = False
            normalized["report_generation"]["enabled"] = False
        elif not normalized["activity_generation"]["enabled"]:
            normalized["investigation"]["enabled"] = False
            normalized["report_generation"]["enabled"] = False
        elif not normalized["investigation"]["enabled"]:
            normalized["report_generation"]["enabled"] = False

        return normalized, None

    def save(self, settings_obj: WorkflowSettings, normalized: dict, updated_by=None) -> WorkflowSettings:
        settings_obj.enabled = normalized["enabled"]
        settings_obj.max_concurrent_workflows = normalized["max_concurrent_workflows"]
        if normalized["webhook"]["bearer_key"] is not None:
            settings_obj.webhook_bearer_key = normalized["webhook"]["bearer_key"]
        settings_obj.soar = SOARInfo.objects.filter(id=normalized["soar_id"]).first()
        settings_obj.siem = (
            SIEMInfo.objects.filter(id=normalized["siem_id"]).first()
            if normalized["siem_id"]
            else settings_obj.siem
        )

        settings_obj.task_generation_enabled = normalized["task_generation"]["enabled"]
        settings_obj.task_generation_use_web_search = normalized["task_generation"][
            "use_web_search"
        ]
        settings_obj.task_generation_additional_notes = normalized["task_generation"][
            "additional_notes"
        ]

        settings_obj.activity_generation_enabled = normalized["activity_generation"][
            "enabled"
        ]
        settings_obj.activity_generation_use_web_search = normalized[
            "activity_generation"
        ]["use_web_search"]
        settings_obj.activity_generation_additional_notes = normalized[
            "activity_generation"
        ]["additional_notes"]

        settings_obj.investigation_enabled = normalized["investigation"]["enabled"]
        settings_obj.investigation_use_web_search = normalized["investigation"][
            "use_web_search"
        ]
        settings_obj.investigation_additional_notes = normalized["investigation"][
            "additional_notes"
        ]
        settings_obj.investigation_earliest_magnitude = normalized["investigation"][
            "earliest_magnitude"
        ]
        settings_obj.investigation_earliest_unit = normalized["investigation"][
            "earliest_unit"
        ]
        settings_obj.investigation_vicinity_magnitude = normalized["investigation"][
            "vicinity_magnitude"
        ]
        settings_obj.investigation_vicinity_unit = normalized["investigation"][
            "vicinity_unit"
        ]
        settings_obj.investigation_max_iterations = normalized["investigation"][
            "max_iterations"
        ]
        settings_obj.investigation_max_queries_per_iteration = normalized[
            "investigation"
        ]["max_queries_per_iteration"]

        settings_obj.report_generation_enabled = normalized["report_generation"]["enabled"]
        settings_obj.report_generation_use_web_search = normalized["report_generation"][
            "use_web_search"
        ]
        settings_obj.report_generation_additional_notes = normalized[
            "report_generation"
        ]["additional_notes"]
        settings_obj.report_generation_report_template_id = normalized[
            "report_generation"
        ]["report_template_id"]

        if updated_by is not None:
            settings_obj.updated_by = updated_by

        settings_obj.save()
        return settings_obj

    def build_step_input_payload(self, normalized: dict, step_name: str) -> dict:
        if step_name == WorkflowRun.StepName.TASK_GENERATION:
            return {
                "use_web_search": normalized["task_generation"]["use_web_search"],
                "additional_notes": normalized["task_generation"]["additional_notes"],
            }
        if step_name == WorkflowRun.StepName.ACTIVITY_GENERATION:
            return {
                "use_web_search": normalized["activity_generation"]["use_web_search"],
                "additional_notes": normalized["activity_generation"]["additional_notes"],
            }
        if step_name == WorkflowRun.StepName.INVESTIGATION:
            return {
                "use_web_search": normalized["investigation"]["use_web_search"],
                "additional_notes": normalized["investigation"]["additional_notes"],
                "earliest_magnitude": normalized["investigation"]["earliest_magnitude"],
                "earliest_unit": normalized["investigation"]["earliest_unit"],
                "vicinity_magnitude": normalized["investigation"]["vicinity_magnitude"],
                "vicinity_unit": normalized["investigation"]["vicinity_unit"],
                "max_iterations": normalized["investigation"]["max_iterations"],
                "max_queries_per_iteration": normalized["investigation"][
                    "max_queries_per_iteration"
                ],
            }
        if step_name == WorkflowRun.StepName.REPORT_GENERATION:
            return {
                "use_web_search": normalized["report_generation"]["use_web_search"],
                "additional_notes": normalized["report_generation"]["additional_notes"],
                "report_template_id": normalized["report_generation"][
                    "report_template_id"
                ],
            }
        return {}
