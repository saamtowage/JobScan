from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class User(AbstractUser):
    pass

class Vessel(models.Model):
    name = models.CharField(max_length=120)

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name
        }

    def __str__(self):
        return f"{self.name}"