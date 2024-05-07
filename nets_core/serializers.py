import json
from django.db import models
from django.utils.translation import gettext_lazy as _

class NetsCoreModelToJson:

    def __init__(self, instance: models.Model, fields: tuple = None, using: str = "default"):
        if not fields:
            raise ValueError(_("Fields must be provided"))
        
        if not isinstance(fields, tuple):
            raise ValueError(_("Fields must be a tuple"))
        
        if not isinstance(instance, models.Model):
            raise ValueError(_("Instance must be a model instance or subclass of models.Model"))
        
        if not isinstance(using, str):
            raise ValueError(_("Using must be a string"))
        
        if not using in models.connections.databases:
            raise ValueError(_("Database alias not found"))
        
        self.instance = instance 
        self.fields = ", ".join(fields)
        self.using = using
        
    def to_json(self):
        with models.connections[self.using].cursor() as cursor:
            cursor.execute(f"SELECT nets_core_model_to_json({self.instance._meta.db_table}, {self.fields}), self.instance.pk")
            row = cursor.fetchone()
            return json.dumps(dict(zip(self.fields, row)))
        
