"""PG Assistantship and Assignment services for OAP (CFR-OAP-013..019, OA-UC-31..42, OA-BR-41..52)."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.oap.domain import rules, state_machine as sm
from modules.oap.domain.errors import (
    ActorNotAllowed,
    GuardFailed,
    IneligibleStudent,
    InvalidTransition,
    OAPDomainError,
)
from modules.oap.models import (
    AssistantshipClaim,
    SupervisorAssignment,
    TAAssignment,
)
from modules.oap.services import notifications


# ==============================================================================
# ASSIGNMENT SERVICES (OA-UC-41, 42, OA-BR-51)
# ==============================================================================

def record_thesis_supervisor_assignment(
    *,
    student_user_id: int,
    thesis_supervisor_user_id: int,
    department: str,
    assigned_by_user_id: int,
) -> SupervisorAssignment:
    """Department Administrator records thesis-supervisor assignment (OA-BR-51, AFR-OAP-043)."""
    with transaction.atomic():
        # Deactivate old active assignment if any
        SupervisorAssignment.objects.filter(
            student_user_id=student_user_id,
            is_active=True,
        ).update(is_active=False)

        assignment = SupervisorAssignment.objects.create(
            student_user_id=student_user_id,
            thesis_supervisor_user_id=thesis_supervisor_user_id,
            department=department,
            assigned_by_user_id=assigned_by_user_id,
            is_active=True,
        )

        notifications.enqueue(
            topic="oap.assistantship.verified",
            dedupe_key=f"oap.assignment.supervisor.{assignment.id}",
            subject="Thesis Supervisor Assigned",
            body=f"You have been assigned thesis supervisor {thesis_supervisor_user_id}.",
            recipient_user_id=student_user_id,
        )

    return assignment


def record_ta_assignment(
    *,
    student_user_id: int,
    department: str,
    assigned_by_user_id: int,
    course_code: str = "",
    course_name: str = "",
    ta_supervisor_user_id: int | None = None,
) -> TAAssignment:
    """Department Administrator records TA assignment (OA-BR-51, AFR-OAP-044)."""
    try:
        rules.validate_ta_assignment_targets(course_code, ta_supervisor_user_id)
    except OAPDomainError as e:
        raise ConflictError(str(e)) from e

    with transaction.atomic():
        TAAssignment.objects.filter(
            student_user_id=student_user_id,
            course_code=course_code,
            is_active=True,
        ).update(is_active=False)

        assignment = TAAssignment.objects.create(
            student_user_id=student_user_id,
            course_code=course_code,
            course_name=course_name,
            ta_supervisor_user_id=ta_supervisor_user_id,
            department=department,
            assigned_by_user_id=assigned_by_user_id,
            is_active=True,
        )

    return assignment


# ==============================================================================
# ASSISTANTSHIP CLAIM SERVICES (OA-UC-31..36, OA-BR-41..46)
# ==============================================================================

def submit_assistantship_claim(
    *,
    user_id: int,
    programme: str,
    department: str,
    claim_month: int,
    claim_year: int,
    stipend_amount: Decimal | float = 0.00,
) -> AssistantshipClaim:
    """PG student submits an assistantship claim (OA-BR-41)."""
    try:
        rules.validate_pg_student_eligibility(programme)
    except IneligibleStudent as e:
        raise PermissionDeniedError(str(e)) from e

    with transaction.atomic():
        # Duplicate check for the same month/year
        existing = AssistantshipClaim.objects.filter(
            user_id=user_id,
            claim_month=claim_month,
            claim_year=claim_year,
        ).first()
        if existing:
            raise ConflictError(f"Claim for month {claim_month}/{claim_year} already exists (#{existing.id}).")

        # Resolve supervisors
        sup = SupervisorAssignment.objects.filter(student_user_id=user_id, is_active=True).first()
        ta_asgn = TAAssignment.objects.filter(student_user_id=user_id, is_active=True).first()

        thesis_sup_id = sup.thesis_supervisor_user_id if sup else None
        ta_sup_id = ta_asgn.ta_supervisor_user_id if ta_asgn else None

        claim = AssistantshipClaim.objects.create(
            user_id=user_id,
            programme=programme,
            department=department,
            claim_month=claim_month,
            claim_year=claim_year,
            stipend_amount=Decimal(str(stipend_amount)),
            thesis_supervisor_user_id=thesis_sup_id,
            ta_supervisor_user_id=ta_sup_id,
            status=sm.CLAIM_SUBMITTED,
        )

        notifications.enqueue(
            topic="oap.assistantship.submitted",
            dedupe_key=f"oap.assistantship.submitted.{claim.id}",
            subject=f"Assistantship Claim Submitted: #{claim.id}",
            body=f"Your claim for {claim_month}/{claim_year} has been submitted for supervisor verification.",
            recipient_user_id=user_id,
        )

    return claim


def verify_supervisor_claim(
    *,
    claim_id: int,
    verifier_user_id: int,
    role_type: str,  # 'thesis' or 'ta'
    remarks: str = "",
) -> AssistantshipClaim:
    """Faculty verifies assistantship claim in thesis or TA supervisor role (OA-BR-42, 52)."""
    with transaction.atomic():
        try:
            claim = AssistantshipClaim.objects.select_for_update().get(id=claim_id)
        except AssistantshipClaim.DoesNotExist as err:
            raise NotFoundError(f"Assistantship claim #{claim_id} not found.") from err

        now = timezone.now()
        role = role_type.lower().strip()

        if role == "thesis":
            if claim.thesis_supervisor_user_id and claim.thesis_supervisor_user_id != verifier_user_id:
                raise PermissionDeniedError("You are not the assigned Thesis Supervisor for this claim.")
            claim.thesis_verified = True
            claim.thesis_verified_at = now
            claim.thesis_remarks = remarks
        elif role == "ta":
            if claim.ta_supervisor_user_id and claim.ta_supervisor_user_id != verifier_user_id:
                raise PermissionDeniedError("You are not the assigned TA Supervisor for this claim.")
            claim.ta_verified = True
            claim.ta_verified_at = now
            claim.ta_remarks = remarks
        else:
            raise ConflictError(f"Invalid verification role: {role_type!r}. Must be 'thesis' or 'ta'.")

        # Update overall status
        if claim.thesis_verified and claim.ta_verified:
            claim.status = sm.CLAIM_SUPERVISORS_VERIFIED
        elif claim.thesis_verified:
            claim.status = sm.CLAIM_THESIS_VERIFIED
        elif claim.ta_verified:
            claim.status = sm.CLAIM_TA_VERIFIED

        claim.save(update_fields=[
            "thesis_verified", "thesis_verified_at", "thesis_remarks",
            "ta_verified", "ta_verified_at", "ta_remarks",
            "status", "updated_at",
        ])

        notifications.enqueue(
            topic="oap.assistantship.verified",
            dedupe_key=f"oap.assistantship.verified.{claim.id}.{role}",
            subject=f"Assistantship Claim #{claim.id} Verified by {role.upper()} Supervisor",
            body=f"{role.upper()} verification recorded for your claim #{claim.id}.",
            recipient_user_id=claim.user_id,
        )

    return claim


def forward_claim_by_department(
    *,
    claim_id: int,
    dept_admin_user_id: int,
    remarks: str = "",
) -> AssistantshipClaim:
    """Department Administrator reviews and forwards claim to HoD (OA-BR-43)."""
    with transaction.atomic():
        try:
            claim = AssistantshipClaim.objects.select_for_update().get(id=claim_id)
        except AssistantshipClaim.DoesNotExist as err:
            raise NotFoundError(f"Assistantship claim #{claim_id} not found.") from err

        try:
            sm.validate_claim_department_forward(claim.status, sm.DEPARTMENT_ADMIN)
        except ActorNotAllowed as e:
            raise PermissionDeniedError(str(e)) from e
        except GuardFailed as e:
            raise ConflictError(str(e)) from e

        claim.dept_forwarded = True
        claim.dept_forwarded_by_user_id = dept_admin_user_id
        claim.dept_forwarded_at = timezone.now()
        claim.dept_remarks = remarks
        claim.status = sm.CLAIM_DEPARTMENT_FORWARDED
        claim.save(update_fields=[
            "dept_forwarded", "dept_forwarded_by_user_id", "dept_forwarded_at", "dept_remarks",
            "status", "updated_at",
        ])

        notifications.enqueue(
            topic="oap.assistantship.forwarded",
            dedupe_key=f"oap.assistantship.forwarded.{claim.id}",
            subject=f"Assistantship Claim #{claim.id} Forwarded to HoD",
            body=f"Your claim #{claim.id} has been reviewed by the Department and forwarded to the HoD.",
            recipient_user_id=claim.user_id,
        )

    return claim


def decide_claim_by_hod(
    *,
    claim_id: int,
    hod_user_id: int,
    decision: str,
    remarks: str = "",
) -> AssistantshipClaim:
    """HoD approves or rejects assistantship claim (OA-BR-44)."""
    with transaction.atomic():
        try:
            claim = AssistantshipClaim.objects.select_for_update().get(id=claim_id)
        except AssistantshipClaim.DoesNotExist as err:
            raise NotFoundError(f"Assistantship claim #{claim_id} not found.") from err

        target_status = sm.CLAIM_APPROVED if decision.lower() in ("approve", "approved") else sm.CLAIM_REJECTED

        try:
            sm.validate_claim_hod_decision(claim.status, sm.HOD, target_status)
        except ActorNotAllowed as e:
            raise PermissionDeniedError(str(e)) from e
        except (InvalidTransition, GuardFailed) as e:
            raise ConflictError(str(e)) from e

        claim.hod_decision = "approved" if target_status == sm.CLAIM_APPROVED else "rejected"
        claim.hod_user_id = hod_user_id
        claim.hod_decided_at = timezone.now()
        claim.hod_remarks = remarks
        claim.status = target_status
        claim.save(update_fields=[
            "hod_decision", "hod_user_id", "hod_decided_at", "hod_remarks",
            "status", "updated_at",
        ])

        topic = "oap.assistantship.approved" if target_status == sm.CLAIM_APPROVED else "oap.assistantship.rejected"
        notifications.enqueue(
            topic=topic,
            dedupe_key=f"{topic}.{claim.id}",
            subject=f"Assistantship Claim #{claim.id} {target_status.title()}",
            body=f"Your assistantship claim #{claim.id} was {target_status} by the HoD.",
            recipient_user_id=claim.user_id,
        )

    return claim


def process_stipend_disbursement(
    *,
    claim_id: int,
    admin_user_id: int,
) -> AssistantshipClaim:
    """Academic Administrator processes stipend disbursement (OA-BR-45)."""
    with transaction.atomic():
        try:
            claim = AssistantshipClaim.objects.select_for_update().get(id=claim_id)
        except AssistantshipClaim.DoesNotExist as err:
            raise NotFoundError(f"Assistantship claim #{claim_id} not found.") from err

        try:
            sm.validate_stipend_disbursement(claim.status, sm.ACADEMIC_ADMIN)
        except ActorNotAllowed as e:
            raise PermissionDeniedError(str(e)) from e
        except GuardFailed as e:
            raise ConflictError(str(e)) from e

        claim.stipend_disbursed = True
        claim.stipend_disbursed_by_user_id = admin_user_id
        claim.stipend_disbursed_at = timezone.now()
        claim.status = sm.CLAIM_DISBURSED
        claim.save(update_fields=[
            "stipend_disbursed", "stipend_disbursed_by_user_id", "stipend_disbursed_at",
            "status", "updated_at",
        ])

        notifications.enqueue(
            topic="oap.assistantship.disbursed",
            dedupe_key=f"oap.assistantship.disbursed.{claim.id}",
            subject=f"Stipend Disbursed: Claim #{claim.id}",
            body=f"Stipend disbursement processed for claim #{claim.id} ({claim.claim_month}/{claim.claim_year}).",
            recipient_user_id=claim.user_id,
        )

    return claim
