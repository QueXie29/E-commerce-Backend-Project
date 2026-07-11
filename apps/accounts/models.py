from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        USER = "user", "普通用户"
        ADMIN = "admin", "业务管理员"

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
        db_index=True,
    )

    @property
    def is_business_admin(self) -> bool:
        return self.is_superuser or self.role == self.Role.ADMIN

    def __str__(self) -> str:
        return self.username
