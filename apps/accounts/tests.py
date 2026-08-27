from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt import serializers as simplejwt_serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


class AuthApiTests(APITestCase):
    def test_login_with_invalid_credentials_returns_401(self):
        User.objects.create_user(username="testuser", password="Test123456")

        response = self.client.post(
            reverse("auth-login"),
            {
                "username": "testuser",
                "password": "WrongPassword",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], 40100)
        self.assertEqual(response.data["message"], "用户名或密码错误")

    def test_register_login_and_me(self):
        register_response = self.client.post(
            reverse("auth-register"),
            {
                "username": "testuser",
                "password": "Test123456",
                "password_confirm": "Test123456",
                "email": "test@example.com",
                "phone": "13800000000",
            },
            format="json",
        )

        self.assertEqual(register_response.status_code, 201)
        self.assertEqual(register_response.data["code"], 0)
        self.assertEqual(register_response.data["data"]["username"], "testuser")

        login_response = self.client.post(
            reverse("auth-login"),
            {
                "username": "testuser",
                "password": "Test123456",
            },
            format="json",
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertIn("access", login_response.data["data"])
        self.assertIn("refresh", login_response.data["data"])

        refresh_response = self.client.post(
            reverse("auth-refresh"),
            {"refresh": login_response.data["data"]["refresh"]},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, 200)
        self.assertIn("access", refresh_response.data["data"])

        access = login_response.data["data"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        me_response = self.client.get(reverse("auth-me"))

        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.data["data"]["username"], "testuser")

    def test_me_reports_superuser_as_admin_for_frontend_routing(self):
        admin = User.objects.create_superuser(
            username="super-admin",
            password="Test123456",
            email="admin@example.com",
        )
        self.client.force_authenticate(admin)

        response = self.client.get(reverse("auth-me"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["role"], "admin")


class BrowserAuthApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="browser-user",
            password="Test123456",
        )
        self.browser_client = APIClient(enforce_csrf_checks=True)

    def bootstrap_csrf(self):
        response = self.browser_client.get(reverse("browser-auth-csrf"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)
        self.assertIn("csrfToken", response.data["data"])
        return response.cookies["csrftoken"].value

    def browser_login(self):
        csrf_token = self.bootstrap_csrf()
        response = self.browser_client.post(
            reverse("browser-auth-login"),
            {
                "username": self.user.username,
                "password": "Test123456",
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, 200)
        return csrf_token, response

    def test_browser_writes_require_csrf_token(self):
        self.bootstrap_csrf()

        protected_requests = (
            (
                "browser-auth-login",
                {"username": self.user.username, "password": "Test123456"},
            ),
            ("browser-auth-refresh", {}),
            ("browser-auth-logout", {}),
        )
        for url_name, data in protected_requests:
            with self.subTest(url_name=url_name):
                response = self.browser_client.post(
                    reverse(url_name),
                    data,
                    format="json",
                )
                self.assertEqual(response.status_code, 403)

    def test_browser_login_sets_httponly_refresh_cookie(self):
        _, response = self.browser_login()

        self.assertEqual(set(response.data["data"]), {"access"})
        cookie = response.cookies[settings.JWT_REFRESH_COOKIE_NAME]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(bool(cookie["secure"]), settings.JWT_REFRESH_COOKIE_SECURE)
        self.assertEqual(cookie["samesite"], settings.JWT_REFRESH_COOKIE_SAMESITE)
        self.assertEqual(cookie["path"], settings.JWT_REFRESH_COOKIE_PATH)
        self.assertEqual(
            int(cookie["max-age"]),
            settings.JWT_REFRESH_COOKIE_MAX_AGE,
        )

    def test_browser_refresh_reads_refresh_token_from_cookie(self):
        csrf_token, login_response = self.browser_login()
        original_refresh = login_response.cookies[
            settings.JWT_REFRESH_COOKIE_NAME
        ].value

        response = self.browser_client.post(
            reverse("browser-auth-refresh"),
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data["data"]), {"access"})
        self.assertNotIn(settings.JWT_REFRESH_COOKIE_NAME, response.cookies)
        self.assertEqual(
            self.browser_client.cookies[settings.JWT_REFRESH_COOKIE_NAME].value,
            original_refresh,
        )

    @patch.object(simplejwt_serializers.api_settings, "ROTATE_REFRESH_TOKENS", True)
    @patch.object(simplejwt_serializers.api_settings, "BLACKLIST_AFTER_ROTATION", True)
    def test_browser_refresh_updates_cookie_when_rotation_is_enabled(self):
        csrf_token, login_response = self.browser_login()
        original_refresh = login_response.cookies[
            settings.JWT_REFRESH_COOKIE_NAME
        ].value

        response = self.browser_client.post(
            reverse("browser-auth-refresh"),
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        rotated_refresh = response.cookies[settings.JWT_REFRESH_COOKIE_NAME].value
        self.assertNotEqual(rotated_refresh, original_refresh)
        with self.assertRaises(TokenError):
            RefreshToken(original_refresh)

    def test_browser_logout_blacklists_and_deletes_refresh_cookie(self):
        csrf_token, login_response = self.browser_login()
        refresh_token = login_response.cookies[settings.JWT_REFRESH_COOKIE_NAME].value

        response = self.browser_client.post(
            reverse("browser-auth-logout"),
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        deleted_cookie = response.cookies[settings.JWT_REFRESH_COOKIE_NAME]
        self.assertEqual(deleted_cookie.value, "")
        self.assertEqual(deleted_cookie["max-age"], 0)
        self.assertEqual(deleted_cookie["path"], settings.JWT_REFRESH_COOKIE_PATH)
        with self.assertRaises(TokenError):
            RefreshToken(refresh_token)

        refresh_response = self.browser_client.post(
            reverse("browser-auth-refresh"),
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(refresh_response.status_code, 401)
