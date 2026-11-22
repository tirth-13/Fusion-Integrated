"""Student leave models for OAP (CFR-OAP-003..005, OA-UC-01, OA-UC-03, OA-UC-04)."""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveApplication(TimeStampedModel, UserScopedModel):
    """Student leave application reviewed and decided by HoD (OA-BR-11)."""

    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    LEAVE_TYPES = [
        ("casual", "Casual Leave"),
        ("medical", "Medical Leave"),
        ("academic", "Academic Leave"),
        ("duty", "On Duty Leave"),
        ("other", "Other"),
    ]

    student_name = models.CharField(max_length=150, blank=True)
    programme = models.CharField(max_length=50, blank=True)
    department = models.CharField(max_length=80, blank=True)

    leave_type = models.CharField(max_length=30, choices=LEAVE_TYPES, default="casual")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    supporting_document = models.CharField(max_length=255, blank=True)  # AFR-OAP-010

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUBMITTED)
    hod_user_id = models.IntegerField(null=True, blank=True)
    decision_date = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "oap_leave_application"
        indexes = [
            models.Index(fields=["user_id", "status"]),
            models.Index(fields=["department", "status"]),
        ]

    def __str__(self) -> str:
        return f"LeaveApp {self.id} (user {self.user_id}): {self.status}"
