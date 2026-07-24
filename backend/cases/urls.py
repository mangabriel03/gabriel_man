from django.urls import path

from .views import (
    AdminCaseDetailView,
    AdminCaseListView,
    AdminNavigationView,
    AdminUserListView,
    CaseCreateView,
    ChangePasswordView,
    CompensationPreviewView,
    LoginView,
    LogoutView,
)

urlpatterns = [
    path("admin/navigation/", AdminNavigationView.as_view(), name="admin-navigation"),
    path("admin/cases/", AdminCaseListView.as_view(), name="admin-case-list"),
    path("admin/cases/<uuid:case_id>/", AdminCaseDetailView.as_view(), name="admin-case-detail"),
    path("admin/users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("cases/", CaseCreateView.as_view(), name="case-create"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    path("compensation/preview/", CompensationPreviewView.as_view(),
         name="compensation-preview"),
]
