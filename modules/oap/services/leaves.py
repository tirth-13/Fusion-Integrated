"""Leave application services for OAP (CFR-OAP-003..005, OA-UC-01, 03, OA-BR-11)."""
from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.oap.domain import rules, state_machine as sm
from modules.oap.domain.errors import ActorNotAllowed, InvalidTransition, OAPDomainError
from modules.oap.models import LeaveApplication
from modules.oap.services import notifications


def submit_leave(
    *,
    user_id: int,
    student_name: str,
    programme: str,
    department: str,
    leave_type: str,
    start_date: datetime.date,
    end_date: datetime.date,
    reason: str,
    supporting_document: str = "",
) -> LeaveApplication:
    """Submit a student leave application."""
    try:
        rules.validate_leave_dates(start_date, end_date)
    except OAPDomainError as e:
        raise ConflictError(str(e)) from e

    with transaction.atomic():
        app = LeaveApplication.objects.create(
            user_id=user_id,
            student_name=student_name,
            programme=programme,
            department=department,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            supporting_document=supporting_document,
            status=sm.LEAVE_SUBMITTED,
        )

        notifications.enqueue(
            topic="oap.leave.submitted",
            dedupe_key=f"oap.leave.submitted.{app.id}",
            subject=f"Leave Application Submitted: #{app.id}",
            body=f"Your leave request from {start_date} to {end_date} has been submitted to the HoD.",
            recipient_user_id=user_id,
        )

    return app


def decide_leave(
    *,
    leave_id: int,
    hod_user_id: int,
    decision: str,
    remarks: str = "",
) -> LeaveApplication:
    """HoD approves or rejects a student leave application (OA-BR-11)."""
    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().get(id=leave_id)
        except LeaveApplication.DoesNotExist as err:
            raise NotFoundError(f"Leave application #{leave_id} not found.") from err

        target_status = sm.LEAVE_APPROVED if decision.lower() in ("approve", "approved") else sm.LEAVE_REJECTED

        try:
            sm.validate_leave_transition(app.status, target_status, sm.HOD)
        except ActorNotAllowed as e:
            raise PermissionDeniedError(str(e)) from e
        except InvalidTransition as e:
            raise ConflictError(str(e)) from e

        app.status = target_status
        app.hod_user_id = hod_user_id
        app.decision_date = timezone.now()
        app.remarks = remarks
        app.save(update_fields=["status", "hod_user_id", "decision_date", "remarks", "updated_at"])

        topic = "oap.leave.approved" if target_status == sm.LEAVE_APPROVED else "oap.leave.rejected"
        notifications.enqueue(
            topic=topic,
            dedupe_key=f"{topic}.{app.id}",
            subject=f"Leave Application #{app.id} {target_status.title()}",
            body=f"Your leave application #{app.id} was {target_status} by the HoD.",
            recipient_user_id=app.user_id,
        )

    return app
