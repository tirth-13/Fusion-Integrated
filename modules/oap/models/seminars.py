"""Graduate Seminar scheduling models for OAP (CFR-OAP-020..022, OA-UC-51, 53, 54, OA-BR-61..63)."""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class GraduateSeminarRequest(TimeStampedModel, UserScopedModel):
    """Seminar request initiated by PG student and scheduled by Department Administrator."""

    STATUS_REQUESTED = "requested"
    STATUS_SCHEDULED = "scheduled"

    STATUS_CHOICES = [
        (STATUS_REQUESTED, "Requested"),
        (STATUS_SCHEDULED, "Scheduled"),
    ]

    student_name = models.CharField(max_length=150, blank=True)
    programme = models.CharField(max_length=50, default="PG")
    department = models.CharField(max_length=80, blank=True)

    topic = models.CharField(max_length=255)
    abstract = models.TextField(blank=True)
    proposed_date = models.DateField()

    # Scheduled fields (filled by Dept Admin)
    scheduled_date = models.DateTimeField(null=True, blank=True)
    venue = models.CharField(max_length=150, blank=True)
    scheduled_by_user_id = models.IntegerField(null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_REQUESTED)

    class Meta:
        db_table = "oap_seminar_request"
        indexes = [
            models.Index(fields=["user_id", "status"]),
            models.Index(fields=["department", "status"]),
            models.Index(fields=["scheduled_date"]),
        ]

    def __str__(self) -> str:
        return f"SeminarRequest {self.id} (user {self.user_id}): {self.topic[:30]} ({self.status})"


class SeminarScheduleLog(TimeStampedModel):
    """History and audit trail of graduate seminar scheduling actions (AFR-OAP-048)."""

    seminar_request = models.ForeignKey(
        GraduateSeminarRequest,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    action = models.CharField(max_length=60)
    actor_user_id = models.IntegerField()
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "oap_seminar_log"
        indexes = [
            models.Index(fields=["seminar_request", "action"]),
        ]

    def __str__(self) -> str:
        return f"SeminarLog req={self.seminar_request_id} action={self.action} actor={self.actor_user_id}"
