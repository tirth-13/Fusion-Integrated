"""OAP public contract surface.

All functions are plural by signature (takes Sequence[int]) per
ops/checks/contracts_are_plural.py.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import datetime

from modules.oap.models import (
    AssistantshipClaim,
    LeaveApplication,
    NoDuesRequest,
    SupervisorAssignment,
    TAAssignment,
)


@dataclass(frozen=True)
class NoDuesStatusDTO:
    user_id: int
    is_cleared: bool
    status: str
    certificate_code: str = ""
    finalized_at: datetime.datetime | None = None


@dataclass(frozen=True)
class StudentLeaveDTO:
    leave_id: int
    user_id: int
    leave_type: str
    start_date: datetime.date
    end_date: datetime.date
    status: str


@dataclass(frozen=True)
class StudentSupervisorsDTO:
    user_id: int
    thesis_supervisor_user_id: int | None
    ta_supervisor_user_id: int | None


def get_student_no_dues_status(user_ids: Sequence[int]) -> dict[int, NoDuesStatusDTO]:
    """Check no-dues status for a cohort of students."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    reqs = NoDuesRequest.objects.filter(user_id__in=ids)
    mapping: dict[int, NoDuesStatusDTO] = {}
    for r in reqs:
        mapping[r.user_id] = NoDuesStatusDTO(
            user_id=r.user_id,
            is_cleared=(r.status == "cleared"),
            status=r.status,
            certificate_code=r.certificate_code if r.status == "cleared" else "",
            finalized_at=r.finalized_at,
        )

    # Defaults for users without a request
    for uid in ids:
        if uid not in mapping:
            mapping[uid] = NoDuesStatusDTO(
                user_id=uid,
                is_cleared=False,
                status="none",
            )
    return mapping


def get_student_leaves(user_ids: Sequence[int]) -> dict[int, list[StudentLeaveDTO]]:
    """Get active/approved leaves for given students."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    rows = LeaveApplication.objects.filter(user_id__in=ids).order_by("-start_date")
    result: dict[int, list[StudentLeaveDTO]] = {uid: [] for uid in ids}
    for r in rows:
        result[r.user_id].append(
            StudentLeaveDTO(
                leave_id=r.id,
                user_id=r.user_id,
                leave_type=r.leave_type,
                start_date=r.start_date,
                end_date=r.end_date,
                status=r.status,
            )
        )
    return result


def get_student_supervisors(user_ids: Sequence[int]) -> dict[int, StudentSupervisorsDTO]:
    """Get assigned Thesis and TA supervisors for PG students."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    sup_map = {
        s.student_user_id: s.thesis_supervisor_user_id
        for s in SupervisorAssignment.objects.filter(student_user_id__in=ids, is_active=True)
    }
    ta_map = {
        t.student_user_id: t.ta_supervisor_user_id
        for t in TAAssignment.objects.filter(student_user_id__in=ids, is_active=True)
    }

    return {
        uid: StudentSupervisorsDTO(
            user_id=uid,
            thesis_supervisor_user_id=sup_map.get(uid),
            ta_supervisor_user_id=ta_map.get(uid),
        )
        for uid in ids
    }
