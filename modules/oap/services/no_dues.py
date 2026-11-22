"""No-Dues Clearance services for OAP (CFR-OAP-009..012, OA-UC-21..25, OA-BR-31..34)."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.oap.domain import state_machine as sm
from modules.oap.domain.errors import ActorNotAllowed, GuardFailed
from modules.oap.models import NoDuesAuthorityRecord, NoDuesRequest
from modules.oap.services import notifications


def initiate_no_dues(
    *,
    user_id: int,
    student_name: str,
    programme: str,
    department: str,
) -> NoDuesRequest:
    """Initiate no-dues clearance and dispatch in parallel to all 7 mandatory authorities (OA-BR-31, 32)."""
    with transaction.atomic():
        # A student can have only one active in-flight request
        existing = NoDuesRequest.objects.filter(
            user_id=user_id,
            status__in=[sm.NODUES_SUBMITTED, sm.NODUES_IN_PROGRESS],
        ).first()
        if existing:
            raise ConflictError(f"An active No-Dues request #{existing.id} already exists.")

        req = NoDuesRequest.objects.create(
            user_id=user_id,
            student_name=student_name,
            programme=programme,
            department=department,
            status=sm.NODUES_IN_PROGRESS,
        )

        # Create all 7 mandatory domain records in parallel
        for domain in sorted(sm.MANDATORY_NODUES_DOMAINS):
            NoDuesAuthorityRecord.objects.create(
                request=req,
                authority_domain=domain,
                status=sm.AUTHORITY_STATUS_PENDING,
            )

        notifications.enqueue(
            topic="oap.nodues.submitted",
            dedupe_key=f"oap.nodues.submitted.{req.id}",
            subject=f"No-Dues Clearance Initiated: #{req.id}",
            body="Your No-Dues clearance has been initiated across all 7 departments.",
            recipient_user_id=user_id,
        )

    return req


def record_authority_clearance(
    *,
    request_id: int,
    domain: str,
    actor_kind: str,
    verifier_user_id: int,
    status: str,
    dues_amount: Decimal | float = 0.00,
    remarks: str = "",
) -> NoDuesAuthorityRecord:
    """One authority records clearance only for its own institutional domain (OA-BR-31, 32)."""
    try:
        sm.validate_nodues_authority_action(domain, actor_kind)
    except (ActorNotAllowed, GuardFailed) as e:
        raise PermissionDeniedError(str(e)) from e

    with transaction.atomic():
        try:
            record = NoDuesAuthorityRecord.objects.select_for_update().get(
                request_id=request_id,
                authority_domain=domain,
            )
        except NoDuesAuthorityRecord.DoesNotExist as err:
            raise NotFoundError(f"No-Dues record for request #{request_id} domain {domain!r} not found.") from err

        target_status = (
            sm.AUTHORITY_STATUS_CLEARED
            if status.lower() in ("clear", "cleared")
            else sm.AUTHORITY_STATUS_DUES_PENDING
        )

        record.status = target_status
        record.verifier_user_id = verifier_user_id
        record.verified_at = timezone.now()
        record.dues_amount = Decimal(str(dues_amount))
        record.remarks = remarks
        record.save(update_fields=[
            "status", "verifier_user_id", "verified_at", "dues_amount", "remarks", "updated_at"
        ])

        notifications.enqueue(
            topic="oap.nodues.verified",
            dedupe_key=f"oap.nodues.verified.{record.id}.{target_status}",
            subject=f"No-Dues Update for {domain.title()}",
            body=f"{domain.title()} clearance has been marked {target_status}.",
            recipient_user_id=record.request.user_id,
        )

    return record


def finalize_no_dues(
    *,
    request_id: int,
    admin_user_id: int,
    actor_kind: str = sm.ACADEMIC_ADMIN,
    remarks: str = "",
) -> NoDuesRequest:
    """Academic Administrator finalizes no-dues clearance only if all 7 domains are clear (OA-BR-33)."""
    with transaction.atomic():
        try:
            req = NoDuesRequest.objects.select_for_update().get(id=request_id)
        except NoDuesRequest.DoesNotExist as err:
            raise NotFoundError(f"No-Dues request #{request_id} not found.") from err

        records = req.authority_records.all()
        domain_statuses = {r.authority_domain: r.status for r in records}

        try:
            sm.validate_nodues_finalization(domain_statuses, actor_kind)
        except ActorNotAllowed as e:
            raise PermissionDeniedError(str(e)) from e
        except GuardFailed as e:
            raise ConflictError(str(e)) from e

        req.status = sm.NODUES_CLEARED
        req.finalized_by_user_id = admin_user_id
        req.finalized_at = timezone.now()
        req.remarks = remarks
        req.save(update_fields=["status", "finalized_by_user_id", "finalized_at", "remarks", "updated_at"])

        notifications.enqueue(
            topic="oap.nodues.finalized",
            dedupe_key=f"oap.nodues.finalized.{req.id}",
            subject=f"No-Dues Clearance Finalized: #{req.id}",
            body="Your No-Dues clearance has been finalized. You may now download your certificate.",
            recipient_user_id=req.user_id,
        )

    return req


def get_downloadable_nodues_certificate_data(request_id: int, requesting_user_id: int) -> dict:
    """Download finalized no-dues certificate (OA-BR-34)."""
    try:
        req = NoDuesRequest.objects.prefetch_related("authority_records").get(id=request_id)
    except NoDuesRequest.DoesNotExist as err:
        raise NotFoundError(f"No-Dues request #{request_id} not found.") from err

    if req.user_id != requesting_user_id:
        raise PermissionDeniedError("You can only download your own No-Dues certificate.")

    if not sm.can_download_nodues_certificate(req.status):
        raise ConflictError("No-Dues certificate is only downloadable after finalization (OA-BR-34).")

    return {
        "certificate_code": req.certificate_code,
        "student_name": req.student_name,
        "programme": req.programme,
        "department": req.department,
        "finalized_at": req.finalized_at,
        "finalized_by_user_id": req.finalized_by_user_id,
        "domains": [
            {"domain": r.authority_domain, "status": r.status, "verified_at": r.verified_at}
            for r in req.authority_records.all()
        ],
    }
