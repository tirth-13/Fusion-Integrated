"""Pure Python business rule evaluators for OAP (OA-BR-01 through OA-BR-63).

Independent of database and HTTP.
"""
from __future__ import annotations

import datetime

from modules.oap.domain.errors import IneligibleStudent, OAPDomainError


def validate_student_for_leave(student_standing: dict) -> None:
    """Validate student can submit leave."""
    if not student_standing.get("is_active", True):
        raise IneligibleStudent("Inactive students cannot apply for leave.")


def validate_leave_dates(start_date: datetime.date, end_date: datetime.date) -> None:
    """Validate leave date range."""
    if end_date < start_date:
        raise OAPDomainError("Leave end date cannot be earlier than start date.")


def validate_pg_student_eligibility(programme: str) -> None:
    """OA-BR-41 & OA-BR-61: Only PG students can submit assistantship claims and seminar requests."""
    prog = (programme or "").strip().upper()
    # PG programmes include M.Tech, M.Des, Ph.D, PhD, MTech, MDes
    pg_indicators = ("M.TECH", "MTECH", "M.DES", "MDES", "PH.D", "PHD", "PG")
    is_pg = any(indicator in prog for indicator in pg_indicators)
    if not is_pg and prog != "":
        raise IneligibleStudent("Only PG students (M.Tech/M.Des/Ph.D) are eligible for this procedure.")


def validate_ta_assignment_targets(
    course_code: str = "",
    faculty_user_id: int | None = None,
) -> None:
    """OA-BR-51: TA assignment associates a PG student with a course/subject, a faculty member, or both."""
    if not course_code and faculty_user_id is None:
        raise OAPDomainError("TA assignment must associate a course/subject, a faculty member, or both.")
