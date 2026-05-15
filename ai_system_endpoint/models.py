import uuid

from django.conf import settings
from django.db import models

from siem_endpoint.models import SIEMInfo
from soar_endpoint.models import SOARInfo


class WorkflowSettings(models.Model):
    UNIT_CHOICES = (
        ("minutes", "minutes"),
        ("hours", "hours"),
        ("days", "days"),
        ("weeks", "weeks"),
        ("months", "months"),
        ("years", "years"),
    )

    enabled = models.BooleanField(default=False)
    max_concurrent_workflows = models.PositiveSmallIntegerField(default=3)
    webhook_bearer_key = models.CharField(max_length=256, blank=True, default="")
    soar = models.ForeignKey(
        SOARInfo,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="workflow_settings",
    )
    siem = models.ForeignKey(
        SIEMInfo,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="workflow_settings",
    )

    task_generation_enabled = models.BooleanField(default=False)
    task_generation_use_web_search = models.BooleanField(default=False)
    task_generation_additional_notes = models.TextField(blank=True, default="")

    activity_generation_enabled = models.BooleanField(default=False)
    activity_generation_use_web_search = models.BooleanField(default=False)
    activity_generation_additional_notes = models.TextField(blank=True, default="")

    investigation_enabled = models.BooleanField(default=False)
    investigation_use_web_search = models.BooleanField(default=False)
    investigation_additional_notes = models.TextField(blank=True, default="")
    investigation_earliest_magnitude = models.PositiveSmallIntegerField(default=1)
    investigation_earliest_unit = models.CharField(
        max_length=16,
        choices=UNIT_CHOICES,
        default="years",
    )
    investigation_vicinity_magnitude = models.PositiveSmallIntegerField(default=1)
    investigation_vicinity_unit = models.CharField(
        max_length=16,
        choices=(
            ("minutes", "minutes"),
            ("hours", "hours"),
            ("days", "days"),
        ),
        default="hours",
    )
    investigation_max_iterations = models.PositiveSmallIntegerField(default=3)
    investigation_max_queries_per_iteration = models.PositiveSmallIntegerField(
        default=5
    )

    report_generation_enabled = models.BooleanField(default=False)
    report_generation_use_web_search = models.BooleanField(default=False)
    report_generation_additional_notes = models.TextField(blank=True, default="")
    report_generation_report_template_id = models.CharField(
        max_length=256,
        blank=True,
        default="",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_workflow_settings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class WorkflowRun(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "queued"
        RUNNING = "running", "running"
        SUCCEEDED = "succeeded", "succeeded"
        FAILED = "failed", "failed"
        CANCELLED = "cancelled", "cancelled"
        SKIPPED = "skipped", "skipped"

    class StepName(models.TextChoices):
        TASK_GENERATION = "task_generation", "task_generation"
        ACTIVITY_GENERATION = "activity_generation", "activity_generation"
        INVESTIGATION = "investigation", "investigation"
        REPORT_GENERATION = "report_generation", "report_generation"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    external_event_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    source = models.CharField(max_length=64)
    soar = models.ForeignKey(
        SOARInfo,
        on_delete=models.PROTECT,
        related_name="workflow_runs",
    )
    siem = models.ForeignKey(
        SIEMInfo,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="workflow_runs",
    )
    org_id = models.CharField(max_length=128)
    case_id = models.CharField(max_length=128)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    current_step = models.CharField(
        max_length=32,
        choices=StepName.choices,
        null=True,
        blank=True,
    )
    error_code = models.CharField(max_length=64, blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    correlation_id = models.CharField(max_length=128, db_index=True)
    settings_snapshot = models.JSONField(blank=True, default=dict)
    raw_payload = models.JSONField(blank=True, default=dict)
    retry_of = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="retries",
    )
    cancel_reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)


class WorkflowRunStep(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "pending"
        RUNNING = "running", "running"
        SUCCEEDED = "succeeded", "succeeded"
        FAILED = "failed", "failed"
        SKIPPED = "skipped", "skipped"
        CANCELLED = "cancelled", "cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow_run = models.ForeignKey(
        WorkflowRun,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    step_name = models.CharField(max_length=32, choices=WorkflowRun.StepName.choices)
    enabled = models.BooleanField(default=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    attempt = models.PositiveSmallIntegerField(default=0)
    input_payload = models.JSONField(blank=True, default=dict)
    output_payload = models.JSONField(blank=True, default=dict)
    error_code = models.CharField(max_length=64, blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workflow_run", "step_name"],
                name="unique_workflow_run_step",
            )
        ]


class WorkflowEvent(models.Model):
    class Level(models.TextChoices):
        DEBUG = "debug", "debug"
        INFO = "info", "info"
        WARNING = "warning", "warning"
        ERROR = "error", "error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow_run = models.ForeignKey(
        WorkflowRun,
        on_delete=models.CASCADE,
        related_name="events",
    )
    step_name = models.CharField(max_length=32, blank=True, default="")
    level = models.CharField(max_length=16, choices=Level.choices, default=Level.INFO)
    message = models.TextField()
    payload = models.JSONField(blank=True, default=dict)
    correlation_id = models.CharField(max_length=128, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
