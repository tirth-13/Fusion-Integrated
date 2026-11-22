"""Bonafide certificate services for OAP (CFR-OAP-006..008, OA-UC-11..13, OA-BR-21, 22)."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.oap.domain import state_machine as sm
from modules.oap.domain.errors import ActorNotAllowed, InvalidTransition
from modules.oap.models import BonafideRequest
from modules.oap.services import notifications


def request_bonafide(
    *,
    user_id: int,
    student_name: str,
    programme: str,
    department: str,
    purpose: str,
) -> BonafideRequest:
    """Submit a bonafide certificate request."""
    with transaction.atomic():
        req = BonafideRequest.objects.create(
            user_id=user_id,
            student_name=student_name,
            programme=programme,
            department=department,
            purpose=purpose,
            status=sm.BONAFIDE_SUBMITTED,
        )

        notifications.enqueue(
            topic="oap.bonafide.submitted",
            dedupe_key=f"oap.bonafide.submitted.{req.id}",
            subject=f"Bonafide Request Submitted: #{req.id}",
            body=f"Your bonafide certificate request for '{purpose}' has been submitted.",
            recipient_user_id=user_id,
        )

    return req


def decide_bonafide(
    *,
    request_id: int,
    admin_user_id: int,
    decision: str,
    remarks: str = "",
) -> BonafideRequest:
    """Academic Administrator verifies and decides a bonafide request (OA-BR-21)."""
    with transaction.atomic():
        try:
            req = BonafideRequest.objects.select_for_update().get(id=request_id)
        except BonafideRequest.DoesNotExist as err:
            raise NotFoundError(f"Bonafide request #{request_id} not found.") from err

        target_status = sm.BONAFIDE_APPROVED if decision.lower() in ("approve", "approved") else sm.BONAFIDE_REJECTED

        try:
            sm.validate_bonafide_transition(req.status, target_status, sm.ACADEMIC_ADMIN)
        except ActorNotAllowed as e:
            raise PermissionDeniedError(str(e)) from e
        except InvalidTransition as e:
            raise ConflictError(str(e)) from e

        req.status = target_status
        req.verified_by_user_id = admin_user_id
        req.decision_date = timezone.now()
        req.remarks = remarks
        req.save(update_fields=["status", "verified_by_user_id", "decision_date", "remarks", "updated_at"])

        topic = "oap.bonafide.approved" if target_status == sm.BONAFIDE_APPROVED else "oap.bonafide.rejected"
        notifications.enqueue(
            topic=topic,
            dedupe_key=f"{topic}.{req.id}",
            subject=f"Bonafide Request #{req.id} {target_status.title()}",
            body=f"Your bonafide request #{req.id} was {target_status} by the Academic Administrator.",
            recipient_user_id=req.user_id,
        )

    return req


def get_downloadable_certificate_data(request_id: int, requesting_user_id: int) -> dict:
    """Download an approved bonafide certificate (OA-BR-22)."""
    try:
        req = BonafideRequest.objects.get(id=request_id)
    except BonafideRequest.DoesNotExist as err:
        raise NotFoundError(f"Bonafide request #{request_id} not found.") from err

    if req.user_id != requesting_user_id:
        raise PermissionDeniedError("You can only download your own bonafide certificate.")

    if not sm.can_download_bonafide(req.status):
        raise ConflictError("Bonafide certificate is only downloadable after approval (OA-BR-22).")

    return {
        "certificate_code": req.certificate_code,
        "student_name": req.student_name,
        "programme": req.programme,
        "department": req.department,
        "purpose": req.purpose,
        "decision_date": req.decision_date,
        "verified_by_user_id": req.verified_by_user_id,
    }
