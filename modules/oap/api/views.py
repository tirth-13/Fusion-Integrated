"""DRF API views for OAP.

All views use selectors.scoping to enforce data boundaries and ownership.
"""
from __future__ import annotations

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from modules.directory import contracts as directory
from modules.oap.api import serializers as s
from modules.oap.api.permissions import RequirePermissions
from modules.oap.models import (
    AssistantshipClaim,
    BonafideRequest,
    GraduateSeminarRequest,
    LeaveApplication,
    NoDuesAuthorityRecord,
    NoDuesRequest,
    NotificationOutbox,
    SupervisorAssignment,
    TAAssignment,
)
from modules.oap.selectors import scoping
from modules.oap.services import (
    assistantships as assistantship_service,
    bonafide as bonafide_service,
    leaves as leave_service,
    no_dues as nodues_service,
    seminars as seminar_service,
)


def _actor(request):
    return getattr(request, "principal", None)


def _user_profile(user_id: int):
    users = directory.get_users([user_id])
    return users.get(user_id)


# ==============================================================================
# LEAVE VIEWS
# ==============================================================================

class LeaveListView(generics.ListCreateAPIView):
    """List student leaves (scoped) or submit a new leave application."""

    serializer_class = s.LeaveApplicationSerializer

    def get_queryset(self):
        return scoping.scoped_leaves(_actor(self.request)).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        actor = _actor(request)
        if actor is None or not actor.has_permission("oap.leave.apply"):
            raise PermissionDeniedError("Permission oap.leave.apply required.")

        ser = s.LeaveApplicationSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        u = _user_profile(actor.user_id)
        name = u.display_name if u else actor.display_name
        dept = u.department if u else ""
        prog = u.programme if u else ""

        app = leave_service.submit_leave(
            user_id=actor.user_id,
            student_name=name,
            programme=prog,
            department=dept,
            leave_type=data["leave_type"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            reason=data["reason"],
            supporting_document=data.get("supporting_document", ""),
        )
        return Response(s.LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class LeaveDetailView(generics.RetrieveAPIView):
    serializer_class = s.LeaveApplicationSerializer

    def get_queryset(self):
        return scoping.scoped_leaves(_actor(self.request))


class LeaveDecisionView(APIView):
    permission_classes = [RequirePermissions("oap.leave.decide")]

    def post(self, request, pk: int):
        actor = _actor(request)
        ser = s.LeaveDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        app = leave_service.decide_leave(
            leave_id=pk,
            hod_user_id=actor.user_id,
            decision=ser.validated_data["decision"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveApplicationSerializer(app).data, status=status.HTTP_200_OK)


# ==============================================================================
# BONAFIDE VIEWS
# ==============================================================================

class BonafideListView(generics.ListCreateAPIView):
    serializer_class = s.BonafideRequestSerializer

    def get_queryset(self):
        return scoping.scoped_bonafides(_actor(self.request)).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        actor = _actor(request)
        if actor is None or not actor.has_permission("oap.bonafide.request"):
            raise PermissionDeniedError("Permission oap.bonafide.request required.")

        ser = s.BonafideRequestSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        u = _user_profile(actor.user_id)
        name = u.display_name if u else actor.display_name
        dept = u.department if u else ""
        prog = u.programme if u else ""

        req = bonafide_service.request_bonafide(
            user_id=actor.user_id,
            student_name=name,
            programme=prog,
            department=dept,
            purpose=ser.validated_data["purpose"],
        )
        return Response(s.BonafideRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class BonafideDetailView(generics.RetrieveAPIView):
    serializer_class = s.BonafideRequestSerializer

    def get_queryset(self):
        return scoping.scoped_bonafides(_actor(self.request))


class BonafideDecisionView(APIView):
    permission_classes = [RequirePermissions("oap.bonafide.decide")]

    def post(self, request, pk: int):
        actor = _actor(request)
        ser = s.BonafideDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        req = bonafide_service.decide_bonafide(
            request_id=pk,
            admin_user_id=actor.user_id,
            decision=ser.validated_data["decision"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.BonafideRequestSerializer(req).data, status=status.HTTP_200_OK)


class BonafideDownloadView(APIView):
    permission_classes = [RequirePermissions("oap.bonafide.download", "oap.bonafide.view_self")]

    def get(self, request, pk: int):
        actor = _actor(request)
        cert_data = bonafide_service.get_downloadable_certificate_data(
            request_id=pk,
            requesting_user_id=actor.user_id,
        )
        return Response(cert_data, status=status.HTTP_200_OK)


# ==============================================================================
# NO-DUES VIEWS
# ==============================================================================

class NoDuesListView(generics.ListCreateAPIView):
    serializer_class = s.NoDuesRequestSerializer

    def get_queryset(self):
        return scoping.scoped_no_dues(_actor(self.request)).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        actor = _actor(request)
        if actor is None or not actor.has_permission("oap.nodues.request"):
            raise PermissionDeniedError("Permission oap.nodues.request required.")

        u = _user_profile(actor.user_id)
        name = u.display_name if u else actor.display_name
        dept = u.department if u else ""
        prog = u.programme if u else ""

        req = nodues_service.initiate_no_dues(
            user_id=actor.user_id,
            student_name=name,
            programme=prog,
            department=dept,
        )
        return Response(s.NoDuesRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class NoDuesDetailView(generics.RetrieveAPIView):
    serializer_class = s.NoDuesRequestSerializer

    def get_queryset(self):
        return scoping.scoped_no_dues(_actor(self.request))


class NoDuesAuthorityVerifyView(APIView):
    permission_classes = [RequirePermissions("oap.nodues.verify")]

    def post(self, request, pk: int):
        actor = _actor(request)
        ser = s.NoDuesAuthorityVerifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        record = nodues_service.record_authority_clearance(
            request_id=pk,
            domain=data["domain"],
            actor_kind=actor.active_role or getattr(actor, "kind", ""),
            verifier_user_id=actor.user_id,
            status=data["status"],
            dues_amount=data.get("dues_amount", 0.00),
            remarks=data.get("remarks", ""),
        )
        return Response(s.NoDuesAuthorityRecordSerializer(record).data, status=status.HTTP_200_OK)


class NoDuesFinalizeView(APIView):
    permission_classes = [RequirePermissions("oap.nodues.finalize")]

    def post(self, request, pk: int):
        actor = _actor(request)
        ser = s.NoDuesFinalizeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        req = nodues_service.finalize_no_dues(
            request_id=pk,
            admin_user_id=actor.user_id,
            actor_kind="academic_admin",
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.NoDuesRequestSerializer(req).data, status=status.HTTP_200_OK)


class NoDuesDownloadView(APIView):
    permission_classes = [RequirePermissions("oap.nodues.download", "oap.nodues.view_self")]

    def get(self, request, pk: int):
        actor = _actor(request)
        cert_data = nodues_service.get_downloadable_nodues_certificate_data(
            request_id=pk,
            requesting_user_id=actor.user_id,
        )
        return Response(cert_data, status=status.HTTP_200_OK)


# ==============================================================================
# ASSISTANTSHIP VIEWS
# ==============================================================================

class AssistantshipClaimListView(generics.ListCreateAPIView):
    serializer_class = s.AssistantshipClaimSerializer

    def get_queryset(self):
        return scoping.scoped_claims(_actor(self.request)).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        actor = _actor(request)
        if actor is None or not actor.has_permission("oap.assistantship.claim"):
            raise PermissionDeniedError("Permission oap.assistantship.claim required.")

        ser = s.AssistantshipClaimSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        u = _user_profile(actor.user_id)
        dept = u.department if u else ""
        prog = u.programme if u else "PG"

        claim = assistantship_service.submit_assistantship_claim(
            user_id=actor.user_id,
            programme=prog,
            department=dept,
            claim_month=data["claim_month"],
            claim_year=data["claim_year"],
            stipend_amount=data.get("stipend_amount", 0.00),
        )
        return Response(s.AssistantshipClaimSerializer(claim).data, status=status.HTTP_201_CREATED)


class AssistantshipClaimDetailView(generics.RetrieveAPIView):
    serializer_class = s.AssistantshipClaimSerializer

    def get_queryset(self):
        return scoping.scoped_claims(_actor(self.request))


class AssistantshipVerifyView(APIView):
    permission_classes = [RequirePermissions("oap.assistantship.verify")]

    def post(self, request, pk: int):
        actor = _actor(request)
        ser = s.SupervisorVerifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        claim = assistantship_service.verify_supervisor_claim(
            claim_id=pk,
            verifier_user_id=actor.user_id,
            role_type=ser.validated_data["role_type"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.AssistantshipClaimSerializer(claim).data, status=status.HTTP_200_OK)


class AssistantshipForwardView(APIView):
    permission_classes = [RequirePermissions("oap.assistantship.forward")]

    def post(self, request, pk: int):
        actor = _actor(request)
        ser = s.DepartmentForwardSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        claim = assistantship_service.forward_claim_by_department(
            claim_id=pk,
            dept_admin_user_id=actor.user_id,
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.AssistantshipClaimSerializer(claim).data, status=status.HTTP_200_OK)


class AssistantshipHoDDecisionView(APIView):
    permission_classes = [RequirePermissions("oap.assistantship.decide")]

    def post(self, request, pk: int):
        actor = _actor(request)
        ser = s.HoDClaimDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        claim = assistantship_service.decide_claim_by_hod(
            claim_id=pk,
            hod_user_id=actor.user_id,
            decision=ser.validated_data["decision"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.AssistantshipClaimSerializer(claim).data, status=status.HTTP_200_OK)


class AssistantshipDisburseView(APIView):
    permission_classes = [RequirePermissions("oap.stipend.process")]

    def post(self, request, pk: int):
        actor = _actor(request)
        claim = assistantship_service.process_stipend_disbursement(
            claim_id=pk,
            admin_user_id=actor.user_id,
        )
        return Response(s.AssistantshipClaimSerializer(claim).data, status=status.HTTP_200_OK)


# ==============================================================================
# ASSIGNMENT VIEWS
# ==============================================================================

class SupervisorAssignmentListView(generics.ListCreateAPIView):
    serializer_class = s.SupervisorAssignmentSerializer

    def get_queryset(self):
        return scoping.scoped_supervisor_assignments(_actor(self.request)).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        actor = _actor(request)
        if actor is None or not actor.has_permission("oap.assignment.manage"):
            raise PermissionDeniedError("Permission oap.assignment.manage required.")

        ser = s.SupervisorAssignmentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        asgn = assistantship_service.record_thesis_supervisor_assignment(
            student_user_id=data["student_user_id"],
            thesis_supervisor_user_id=data["thesis_supervisor_user_id"],
            department=data["department"],
            assigned_by_user_id=actor.user_id,
        )
        return Response(s.SupervisorAssignmentSerializer(asgn).data, status=status.HTTP_201_CREATED)


class TAAssignmentListView(generics.ListCreateAPIView):
    serializer_class = s.TAAssignmentSerializer

    def get_queryset(self):
        return scoping.scoped_ta_assignments(_actor(self.request)).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        actor = _actor(request)
        if actor is None or not actor.has_permission("oap.assignment.manage"):
            raise PermissionDeniedError("Permission oap.assignment.manage required.")

        ser = s.TAAssignmentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        asgn = assistantship_service.record_ta_assignment(
            student_user_id=data["student_user_id"],
            course_code=data.get("course_code", ""),
            course_name=data.get("course_name", ""),
            ta_supervisor_user_id=data.get("ta_supervisor_user_id"),
            department=data["department"],
            assigned_by_user_id=actor.user_id,
        )
        return Response(s.TAAssignmentSerializer(asgn).data, status=status.HTTP_201_CREATED)


# ==============================================================================
# GRADUATE SEMINAR VIEWS
# ==============================================================================

class SeminarListView(generics.ListCreateAPIView):
    serializer_class = s.GraduateSeminarRequestSerializer

    def get_queryset(self):
        return scoping.scoped_seminars(_actor(self.request)).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        actor = _actor(request)
        if actor is None or not actor.has_permission("oap.seminar.request"):
            raise PermissionDeniedError("Permission oap.seminar.request required.")

        ser = s.GraduateSeminarSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        u = _user_profile(actor.user_id)
        name = u.display_name if u else actor.display_name
        dept = u.department if u else ""
        prog = u.programme if u else "PG"

        req = seminar_service.request_seminar(
            user_id=actor.user_id,
            student_name=name,
            programme=prog,
            department=dept,
            topic=data["topic"],
            proposed_date=data["proposed_date"],
            abstract=data.get("abstract", ""),
        )
        return Response(s.GraduateSeminarRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class SeminarDetailView(generics.RetrieveAPIView):
    serializer_class = s.GraduateSeminarRequestSerializer

    def get_queryset(self):
        return scoping.scoped_seminars(_actor(self.request))


class SeminarScheduleView(APIView):
    permission_classes = [RequirePermissions("oap.seminar.manage")]

    def post(self, request, pk: int):
        actor = _actor(request)
        ser = s.GraduateSeminarScheduleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        req = seminar_service.schedule_seminar(
            seminar_id=pk,
            dept_admin_user_id=actor.user_id,
            scheduled_date=data["scheduled_date"],
            venue=data["venue"],
        )
        return Response(s.GraduateSeminarRequestSerializer(req).data, status=status.HTTP_200_OK)


# ==============================================================================
# NOTIFICATIONS VIEW
# ==============================================================================

class MyNotificationsView(generics.ListAPIView):
    permission_classes = [RequirePermissions("oap.notification.view_self")]
    serializer_class = s.NotificationOutboxSerializer

    def get_queryset(self):
        actor = _actor(self.request)
        if actor is None:
            return NotificationOutbox.objects.none()
        return NotificationOutbox.objects.filter(recipient_user_id=actor.user_id).order_by("-created_at")
