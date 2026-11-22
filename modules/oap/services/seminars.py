"""Graduate Seminar scheduling services for OAP (CFR-OAP-020..022, OA-UC-51, 53, OA-BR-61..63)."""
from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.oap.domain import rules, state_machine as sm
from modules.oap.domain.errors import ActorNotAllowed, IneligibleStudent, InvalidTransition
from modules.oap.models import GraduateSeminarRequest, SeminarScheduleLog
from modules.oap.services import notifications


def request_seminar(
    *,
    user_id: int,
    student_name: str,
    programme: str,
    department: str,
    topic: str,
    proposed_date: datetime.date,
    abstract: str = "",
) -> GraduateSeminarRequest:
    """PG student requests graduate seminar scheduling (OA-BR-61)."""
    try:
        rules.validate_pg_student_eligibility(programme)
    except IneligibleStudent as e:
        raise PermissionDeniedError(str(e)) from e

    with transaction.atomic():
        req = GraduateSeminarRequest.objects.create(
            user_id=user_id,
            student_name=student_name,
            programme=programme,
            department=department,
            topic=topic,
            abstract=abstract,
            proposed_date=proposed_date,
            status=sm.SEMINAR_REQUESTED,
        )

        SeminarScheduleLog.objects.create(
            seminar_request=req,
            action="requested",
            actor_user_id=user_id,
            details={"topic": topic, "proposed_date": str(proposed_date)},
        )

        notifications.enqueue(
            topic="oap.seminar.requested",
            dedupe_key=f"oap.seminar.requested.{req.id}",
            subject=f"Graduate Seminar Scheduling Requested: #{req.id}",
            body=f"Your seminar request on '{topic}' has been submitted for scheduling.",
            recipient_user_id=user_id,
        )

    return req


def schedule_seminar(
    *,
    seminar_id: int,
    dept_admin_user_id: int,
    scheduled_date: datetime.datetime,
    venue: str,
) -> GraduateSeminarRequest:
    """Department Administrator schedules a graduate seminar (OA-BR-62)."""
    with transaction.atomic():
        try:
            req = GraduateSeminarRequest.objects.select_for_update().get(id=seminar_id)
        except GraduateSeminarRequest.DoesNotExist as err:
            raise NotFoundError(f"Seminar request #{seminar_id} not found.") from err

        try:
            sm.validate_seminar_schedule(req.status, sm.DEPARTMENT_ADMIN)
        except ActorNotAllowed as e:
            raise PermissionDeniedError(str(e)) from e
        except InvalidTransition as e:
            raise ConflictError(str(e)) from e

        req.scheduled_date = scheduled_date
        req.venue = venue
        req.scheduled_by_user_id = dept_admin_user_id
        req.scheduled_at = timezone.now()
        req.status = sm.SEMINAR_SCHEDULED
        req.save(update_fields=[
            "scheduled_date", "venue", "scheduled_by_user_id", "scheduled_at",
            "status", "updated_at",
        ])

        SeminarScheduleLog.objects.create(
            seminar_request=req,
            action="scheduled",
            actor_user_id=dept_admin_user_id,
            details={"scheduled_date": str(scheduled_date), "venue": venue},
        )

        notifications.enqueue(
            topic="oap.seminar.scheduled",
            dedupe_key=f"oap.seminar.scheduled.{req.id}",
            subject=f"Graduate Seminar Scheduled: #{req.id}",
            body=f"Your seminar on '{req.topic}' has been scheduled for {scheduled_date} at {venue}.",
            recipient_user_id=req.user_id,
        )

    return req
