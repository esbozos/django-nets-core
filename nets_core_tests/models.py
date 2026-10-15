from django.db import models
from nets_core.models import NetsCoreBaseModel


class HistoryRecord(NetsCoreBaseModel):
    name = models.CharField(max_length=100)
    token = models.CharField(max_length=100, default="")
    password = models.CharField(max_length=100, default="")


class PlainRecord(models.Model):
    name = models.CharField(max_length=100)
