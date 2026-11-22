"""OAP notification outbox model (CFR-OAP-002, OA-BR-03, OA-UC-91, 92).

Enables reliable atomic delivery of system alerts and emails.
"""
from django.db import models

from core.db.mixins import TimeStampedModel


class NotificationOutbox(TimeStampedModel):
    """Queued notifications (system alerts and emails) emitted during OAP events."""

    topic = models.CharField(max_length=80, db_index=True)
    dedupe_key = models.CharField(max_length=160, unique=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    recipient_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    recipient_email = models.EmailField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "oap_notification_outbox"
        indexes = [
            models.Index(fields=["recipient_user_id", "sent_at"]),
        ]

    def __str__(self) -> str:
        return f"Notification {self.topic} to user={self.recipient_user_id} dedupe={self.dedupe_key}"
