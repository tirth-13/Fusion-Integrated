"""OAP notification services (CFR-OAP-002, OA-BR-03, OA-UC-91, 92).

Atomic notification outbox enqueueing with deduplication.
"""
from __future__ import annotations

import logging

from django.db import IntegrityError, transaction

from modules.oap.models import NotificationOutbox

log = logging.getLogger("fusion.oap.notify")

TOPICS = {
    "oap.leave.submitted",
    "oap.leave.approved",
    "oap.leave.rejected",
    "oap.bonafide.submitted",
    "oap.bonafide.approved",
    "oap.bonafide.rejected",
    "oap.nodues.submitted",
    "oap.nodues.verified",
    "oap.nodues.finalized",
    "oap.nodues.rejected",
    "oap.assistantship.submitted",
    "oap.assistantship.verified",
    "oap.assistantship.forwarded",
    "oap.assistantship.approved",
    "oap.assistantship.rejected",
    "oap.assistantship.disbursed",
    "oap.seminar.requested",
    "oap.seminar.scheduled",
    "oap.reminder.pending_action",
}


def enqueue(
    *,
    topic: str,
    dedupe_key: str,
    subject: str,
    body: str,
    recipient_user_id: int | None = None,
    recipient_email: str = "",
    payload: dict | None = None,
) -> NotificationOutbox | None:
    """Queue one notification inside the caller's transaction. Returns None if duplicate."""
    if topic not in TOPICS:
        raise ValueError(f"Unknown OAP notification topic: {topic!r}")
    if recipient_user_id is None and not recipient_email:
        raise ValueError("A notification needs a recipient user ID or email.")

    try:
        with transaction.atomic():
            return NotificationOutbox.objects.create(
                topic=topic,
                dedupe_key=dedupe_key,
                subject=subject,
                body=body,
                recipient_user_id=recipient_user_id,
                recipient_email=recipient_email,
                payload=payload or {},
            )
    except IntegrityError:
        log.debug("oap.notify.duplicate key=%s", dedupe_key)
        return None


def enqueue_many(rows: list[dict]) -> int:
    return sum(1 for r in rows if enqueue(**r) is not None)
