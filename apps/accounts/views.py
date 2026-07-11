from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.serializers import (
    LoginSerializer,
    RefreshSerializer,
    RegisterSerializer,
    UserSerializer,
)
from apps.common.responses import api_response


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
