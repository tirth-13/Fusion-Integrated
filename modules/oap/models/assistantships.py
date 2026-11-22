"""PG Assistantship and Assignment models for OAP (CFR-OAP-013..019, OA-UC-31..42, OA-BR-41..52)."""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class SupervisorAssignment(TimeStampedModel):
    """Department Administrator records thesis supervisor assignment (AFR-OAP-043, OA-BR-51)."""

    student_user_id = models.IntegerField(db_index=True)
    thesis_supervisor_user_id = models.IntegerField(db_index=True)
    department = models.CharField(max_length=80)
    assigned_by_user_id = models.IntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "oap_supervisor_assignment"
        indexes = [
            models.Index(fields=["student_user_id", "is_active"]),
            models.Index(fields=["thesis_supervisor_user_id", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"SupervisorAssignment student={self.student_user_id} supervisor={self.thesis_supervisor_user_id}"


class TAAssignment(TimeStampedModel):
    """Department Administrator records TA assignment (AFR-OAP-044, OA-BR-51).

    Associates a PG student with a course/subject, a faculty member, or both.
    """

    student_user_id = models.IntegerField(db_index=True)
    course_code = models.CharField(max_length=40, blank=True)
    course_name = models.CharField(max_length=120, blank=True)
    ta_supervisor_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    department = models.CharField(max_length=80)
    assigned_by_user_id = models.IntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "oap_ta_assignment"
        indexes = [
            models.Index(fields=["student_user_id", "is_active"]),
            models.Index(fields=["ta_supervisor_user_id", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"TAAssignment student={self.student_user_id} course={self.course_code} ta_sup={self.ta_supervisor_user_id}"


class AssistantshipClaim(TimeStampedModel, UserScopedModel):
    """Monthly assistantship claim submitted by PG student and verified along the chain."""

    STATUS_SUBMITTED = "submitted"
    STATUS_THESIS_VERIFIED = "thesis_verified"
    STATUS_TA_VERIFIED = "ta_verified"
    STATUS_SUPERVISORS_VERIFIED = "supervisors_verified"
    STATUS_DEPARTMENT_FORWARDED = "department_forwarded"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_DISBURSED = "disbursed"

    STATUS_CHOICES = [
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_THESIS_VERIFIED, "Thesis Supervisor Verified"),
        (STATUS_TA_VERIFIED, "TA Supervisor Verified"),
        (STATUS_SUPERVISORS_VERIFIED, "Both Supervisors Verified"),
        (STATUS_DEPARTMENT_FORWARDED, "Department Forwarded"),
        (STATUS_APPROVED, "Approved by HoD"),
        (STATUS_REJECTED, "Rejected by HoD"),
        (STATUS_DISBURSED, "Stipend Disbursed"),
    ]

    programme = models.CharField(max_length=50, default="PG")
    department = models.CharField(max_length=80, blank=True)
    claim_month = models.PositiveSmallIntegerField()
    claim_year = models.PositiveSmallIntegerField()
    stipend_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Assigned Supervisors
    thesis_supervisor_user_id = models.IntegerField(null=True, blank=True)
    ta_supervisor_user_id = models.IntegerField(null=True, blank=True)

    # 1. Dual Supervisor Verification
    thesis_verified = models.BooleanField(default=False)
    thesis_verified_at = models.DateTimeField(null=True, blank=True)
    thesis_remarks = models.TextField(blank=True)

    ta_verified = models.BooleanField(default=False)
    ta_verified_at = models.DateTimeField(null=True, blank=True)
    ta_remarks = models.TextField(blank=True)

    # 2. Department Admin Review & Forward
    dept_forwarded = models.BooleanField(default=False)
    dept_forwarded_by_user_id = models.IntegerField(null=True, blank=True)
    dept_forwarded_at = models.DateTimeField(null=True, blank=True)
    dept_remarks = models.TextField(blank=True)

    # 3. HoD Decision
    hod_decision = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
        default="pending",
    )
    hod_user_id = models.IntegerField(null=True, blank=True)
    hod_decided_at = models.DateTimeField(null=True, blank=True)
    hod_remarks = models.TextField(blank=True)

    # 4. Academic Admin Stipend Disbursement
    stipend_disbursed = models.BooleanField(default=False)
    stipend_disbursed_by_user_id = models.IntegerField(null=True, blank=True)
    stipend_disbursed_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_SUBMITTED)

    class Meta:
        db_table = "oap_assistantship_claim"
        indexes = [
            models.Index(fields=["user_id", "status"]),
            models.Index(fields=["department", "status"]),
            models.Index(fields=["thesis_supervisor_user_id", "thesis_verified"]),
            models.Index(fields=["ta_supervisor_user_id", "ta_verified"]),
        ]

    def __str__(self) -> str:
        return f"AssistantshipClaim {self.id} (user {self.user_id}, {self.claim_month}/{self.claim_year}): {self.status}"
