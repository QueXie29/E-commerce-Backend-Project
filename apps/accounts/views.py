from django.conf import settings
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.serializers import (
    LoginSerializer,
    RefreshSerializer,
    RegisterSerializer,
    UserSerializer,
)
from apps.common.responses import api_response


def _set_refresh_cookie(response, refresh_token):
    response.set_cookie(
        key=settings.JWT_REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.JWT_REFRESH_COOKIE_MAX_AGE,
        path=settings.JWT_REFRESH_COOKIE_PATH,
        secure=settings.JWT_REFRESH_COOKIE_SECURE,
        httponly=True,
        samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
    )
    return response


def _delete_refresh_cookie(response):
    response.delete_cookie(
        key=settings.JWT_REFRESH_COOKIE_NAME,
        path=settings.JWT_REFRESH_COOKIE_PATH,
        samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
    )
    return response


class RegisterView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return api_response(
            data=UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return api_response(data=serializer.validated_data)


class RefreshView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return api_response(data=serializer.validated_data)


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return api_response(data=UserSerializer(request.user).data)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class BrowserCsrfView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        return api_response(data={"csrfToken": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class BrowserLoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        tokens = serializer.validated_data
        response = api_response(data={"access": tokens["access"]})
        return _set_refresh_cookie(response, tokens["refresh"])


@method_decorator(csrf_protect, name="dispatch")
class BrowserRefreshView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        refresh_token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if not refresh_token:
            raise AuthenticationFailed("缺少刷新令牌")

        serializer = RefreshSerializer(data={"refresh": refresh_token})
        serializer.is_valid(raise_exception=True)
        tokens = serializer.validated_data

        response = api_response(data={"access": tokens["access"]})
        if "refresh" in tokens:
            _set_refresh_cookie(response, tokens["refresh"])
        return response


@method_decorator(csrf_protect, name="dispatch")
class BrowserLogoutView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        refresh_token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except (AttributeError, TokenError):
                # Logout is intentionally idempotent. An invalid, expired, or
                # already blacklisted cookie should still be removed.
                pass

        return _delete_refresh_cookie(api_response())
