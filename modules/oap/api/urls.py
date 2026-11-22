"""OAP URL configuration."""
from django.urls import path

from modules.oap.api import views as v

urlpatterns = [
    # Leaves (CFR-OAP-003..005, OA-UC-01, 03, 04)
    path("leaves", v.LeaveListView.as_view(), name="oap-leaves"),
    path("leaves/<int:pk>", v.LeaveDetailView.as_view(), name="oap-leave-detail"),
    path("leaves/<int:pk>/decide", v.LeaveDecisionView.as_view(), name="oap-leave-decide"),

    # Bonafide (CFR-OAP-006..008, OA-UC-11..14)
    path("bonafide", v.BonafideListView.as_view(), name="oap-bonafide-list"),
    path("bonafide/<int:pk>", v.BonafideDetailView.as_view(), name="oap-bonafide-detail"),
    path("bonafide/<int:pk>/decide", v.BonafideDecisionView.as_view(), name="oap-bonafide-decide"),
    path("bonafide/<int:pk>/download", v.BonafideDownloadView.as_view(), name="oap-bonafide-download"),

    # No-Dues (CFR-OAP-009..012, OA-UC-21..25)
    path("no-dues", v.NoDuesListView.as_view(), name="oap-nodues-list"),
    path("no-dues/<int:pk>", v.NoDuesDetailView.as_view(), name="oap-nodues-detail"),
    path("no-dues/<int:pk>/verify", v.NoDuesAuthorityVerifyView.as_view(), name="oap-nodues-verify"),
    path("no-dues/<int:pk>/finalize", v.NoDuesFinalizeView.as_view(), name="oap-nodues-finalize"),
    path("no-dues/<int:pk>/download", v.NoDuesDownloadView.as_view(), name="oap-nodues-download"),

    # Assistantships (CFR-OAP-013..018, OA-UC-31..37)
    path("assistantships", v.AssistantshipClaimListView.as_view(), name="oap-assistantships-list"),
    path("assistantships/<int:pk>", v.AssistantshipClaimDetailView.as_view(), name="oap-assistantship-detail"),
    path("assistantships/<int:pk>/verify", v.AssistantshipVerifyView.as_view(), name="oap-assistantship-verify"),
    path("assistantships/<int:pk>/forward", v.AssistantshipForwardView.as_view(), name="oap-assistantship-forward"),
    path("assistantships/<int:pk>/decide", v.AssistantshipHoDDecisionView.as_view(), name="oap-assistantship-decide"),
    path("assistantships/<int:pk>/disburse", v.AssistantshipDisburseView.as_view(), name="oap-assistantship-disburse"),

    # Assignments (CFR-OAP-019, OA-UC-41, 42)
    path("assignments/supervisors", v.SupervisorAssignmentListView.as_view(), name="oap-assignments-supervisors"),
    path("assignments/tas", v.TAAssignmentListView.as_view(), name="oap-assignments-tas"),

    # Graduate Seminars (CFR-OAP-020..022, OA-UC-51, 53, 54)
    path("seminars", v.SeminarListView.as_view(), name="oap-seminars-list"),
    path("seminars/<int:pk>", v.SeminarDetailView.as_view(), name="oap-seminar-detail"),
    path("seminars/<int:pk>/schedule", v.SeminarScheduleView.as_view(), name="oap-seminar-schedule"),

    # Notifications (CFR-OAP-002, OA-UC-91, 92)
    path("notifications", v.MyNotificationsView.as_view(), name="oap-notifications"),
]
