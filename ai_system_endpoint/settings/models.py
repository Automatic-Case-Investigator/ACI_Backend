from django.conf import settings
from django.db import models


class AgentSettings(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="settings",
    )
    report_templates = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user"], name="unique_user_settings")
        ]


class AutomationSettings(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="automation_settings",
    )
    soar_id = models.CharField(max_length=128)
    org_id = models.CharField(max_length=128)
    case_id = models.CharField(max_length=128)
    settings = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "soar_id", "org_id", "case_id"],
                name="unique_user_automation_settings_context",
            )
        ]
