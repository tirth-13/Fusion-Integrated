"""No-Dues Clearance models for OAP (CFR-OAP-009..012, OA-UC-21..25, OA-BR-31..34)."""
import uuid

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class NoDuesRequest(TimeStampedModel, UserScopedModel):
    """Central No-Dues Clearance record for a student."""

    STATUS_SUBMITTED = "submitted"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_CLEARED = "cleared"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_CLEARED, "Cleared"),
        (STATUS_REJECTED, "Rejected"),
    ]

    student_name = models.CharField(max_length=150, blank=True)
    programme = models.CharField(max_length=50, blank=True)
    department = models.CharField(max_length=80, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUBMITTED)
    finalized_by_user_id = models.IntegerField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    certificate_code = models.CharField(max_length=64, unique=True, default=uuid.uuid4)

    class Meta:
        db_table = "oap_no_dues_request"
        indexes = [
            models.Index(fields=["user_id", "status"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"NoDuesRequest {self.id} (user {self.user_id}): {self.status}"


class NoDuesAuthorityRecord(TimeStampedModel):
    """Domain-specific clearance by each of the 7 mandatory authorities (OA-BR-31, 32)."""

    STATUS_PENDING = "pending"
    STATUS_CLEARED = "cleared"
    STATUS_DUES_PENDING = "dues_pending"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CLEARED, "Cleared"),
        (STATUS_DUES_PENDING, "Dues Pending"),
    ]

    DOMAIN_CHOICES = [
        ("library", "Library"),
        ("hostel", "Hostel"),
        ("mess", "Mess"),
        ("department", "Respective Department"),
        ("lab", "Lab"),
        ("academic", "Academic Section"),
        ("student_section", "Student Section"),
    ]

    request = models.ForeignKey(
        NoDuesRequest,
        on_delete=models.CASCADE,
        related_name="authority_records",
    )
    authority_domain = models.CharField(max_length=40, choices=DOMAIN_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    verifier_user_id = models.IntegerField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    dues_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "oap_no_dues_authority_record"
        constraints = [
            models.UniqueConstraint(
                fields=["request", "authority_domain"],
                name="oap_nodues_unique_domain_per_request",
            )
        ]
        indexes = [
            models.Index(fields=["authority_domain", "status"]),
        ]

    def __str__(self) -> str:
        return f"NoDuesRecord req={self.request_id} domain={self.authority_domain}: {self.status}"
