"""Bonafide certificate models for OAP (CFR-OAP-006..008, OA-UC-11..14, OA-BR-21, 22)."""
import uuid

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class BonafideRequest(TimeStampedModel, UserScopedModel):
    """Bonafide certificate request verified and decided by Academic Administrator."""

    STATUS_SUBMITTED = "submitted"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    student_name = models.CharField(max_length=150, blank=True)
    programme = models.CharField(max_length=50, blank=True)
    department = models.CharField(max_length=80, blank=True)
    purpose = models.TextField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUBMITTED)
    verified_by_user_id = models.IntegerField(null=True, blank=True)
    decision_date = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    certificate_code = models.CharField(max_length=64, unique=True, default=uuid.uuid4)

    class Meta:
        db_table = "oap_bonafide_request"
        indexes = [
            models.Index(fields=["user_id", "status"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"BonafideRequest {self.id} (user {self.user_id}): {self.status}"
