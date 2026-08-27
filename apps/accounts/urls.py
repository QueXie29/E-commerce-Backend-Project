from django.urls import path

from apps.accounts.views import (
    BrowserCsrfView,
    BrowserLoginView,
    BrowserLogoutView,
    BrowserRefreshView,
    LoginView,
    MeView,
    RefreshView,
    RegisterView,
)


urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("browser/csrf/", BrowserCsrfView.as_view(), name="browser-auth-csrf"),
    path("browser/login/", BrowserLoginView.as_view(), name="browser-auth-login"),
    path(
        "browser/refresh/",
        BrowserRefreshView.as_view(),
        name="browser-auth-refresh",
    ),
    path("browser/logout/", BrowserLogoutView.as_view(), name="browser-auth-logout"),
]
