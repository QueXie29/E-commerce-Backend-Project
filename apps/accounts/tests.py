from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase


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

        access = login_response.data["data"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        me_response = self.client.get(reverse("auth-me"))

        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.data["data"]["username"], "testuser")
