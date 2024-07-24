import json
from django.db import models, connections
from django.conf import settings
from django.utils.translation import gettext_lazy as _

GLOBAL_PROTECTED_FIELDS = [
    'password',
    'is_active',
    'enabled',
    'staff',
    'superuser',
    'verified',
    'deleted',
    'token',
    'auth',
    'perms',
    'groups',
    'ip'
    'date_joined',
    'last_login',
    
]

if hasattr(settings, "NETS_CORE_GLOBAL_PROTECTED_FIELDS"):
    GLOBAL_PROTECTED_FIELDS = settings.NETS_CORE_GLOBAL_PROTECTED_FIELDS

class NetsCoreQuerySetToJson():
    
    def __init__(self, queryset: models.QuerySet, fields: tuple = None, using: str = "default"):
        if not fields:
            # check if instance has JSON_FIELDS attribute
            if hasattr(queryset.model, "JSON_DATA_FIELDS"):
                if not queryset.model.JSON_DATA_FIELDS:
                    raise ValueError(_("Fields must be provided"))
                if not isinstance(queryset.model.JSON_DATA_FIELDS, tuple):
                    try:
                        fields = tuple(queryset.model.JSON_DATA_FIELDS)
                    except Exception as e:
                        raise ValueError(_("Fields must be a tuple or list"))
            else:
                
                raise ValueError(_("Fields must be provided"))
        
        if not isinstance(fields, tuple):
            raise ValueError(_("Fields must be a tuple"))
        
        if not isinstance(queryset, models.QuerySet):
            raise ValueError(_("Queryset must be a queryset instance or subclass of models.QuerySet"))
        
        if not isinstance(using, str):
            raise ValueError(_("Using must be a string"))
        
        if not using in connections.databases:
            raise ValueError(_("Database alias not found"))
        
        self.queryset = queryset
        if len(queryset) > 1:
            instance = queryset.first()
            # check if instance has protected_fields
            if hasattr(instance, "PROTECTED_FIELDS"):
                # get the protected fields
                protected_fields = [f.lower() for f in instance.PROTECTED_FIELDS]
                # remove the protected fields from the fields
                self.fields = [field for field in fields if field.lower() not in protected_fields]
                
            else:
                # remove the global protected fields from the fields using contains for each GLOBAL_PROTECTED_FIELDS
                for field in GLOBAL_PROTECTED_FIELDS:
                    for i, f in enumerate(fields):
                        if field.lower() in f.lower():
                            fields = fields[:i] + fields[i+1:]
        self.fields = ", ".join(fields)
        self.using = using
        
    def to_json(self):
        
        query_ids = ", ".join([str(obj.pk) for obj in self.queryset])
        with models.connections[self.using].cursor() as cursor:
            cursor.execute(f"SELECT nets_core_postgre_array_model_to_json('{self.queryset.model._meta.db_table}', '{self.fields}', ARRAY[{query_ids}])")
            row = cursor.fetchone()
            return row[0]
    

class NetsCoreModelToJson():

    def __init__(self, instance: models.Model, fields: tuple = None, using: str = "default"):
        if not fields:
            # check if instance has JSON_FIELDS attribute
            if hasattr(instance, "JSON_DATA_FIELDS"):
                if not instance.JSON_DATA_FIELDS:
                    raise ValueError(_("Fields must be provided"))
                if not isinstance(instance.JSON_DATA_FIELDS, tuple):
                    try:
                        fields = tuple(instance.JSON_DATA_FIELDS)
                    except Exception as e:
                        raise ValueError(_("Fields must be a tuple or list"))
            else:
                raise ValueError(_("Fields must be provided"))            
            
        
        if not isinstance(fields, tuple):
            raise ValueError(_("Fields must be a tuple"))
        
        if not isinstance(instance, models.Model):
            raise ValueError(_("Instance must be a model instance or subclass of models.Model"))
        
        if not isinstance(using, str):
            raise ValueError(_("Using must be a string"))
        
        if not using in connections.databases:
            raise ValueError(_("Database alias not found"))
        
        self.instance = instance

        # check if instance has protected_fields
        if hasattr(instance, "PROTECTED_FIELDS"):
            # get the protected fields
            protected_fields = [f.lower() for f in instance.PROTECTED_FIELDS]
            # remove the protected fields from the fields
            self.fields = [field for field in fields if field.lower() not in protected_fields]
            
        else:
            # remove the global protected fields from the fields
            for field in GLOBAL_PROTECTED_FIELDS:
                for i, f in enumerate(fields):
                    if field.lower() in f.lower():
                        fields = fields[:i] + fields[i+1:]

        self.fields = ",".join(fields)
        self.using = using
        
    def to_json(self, returning_query: bool = False):
        with connections[self.using].cursor() as cursor:
            t_query = f"SELECT nets_core_postgre_model_to_json('{self.instance._meta.db_table}', '{self.fields}', {self.instance.pk})"
            if returning_query:
                return t_query
            cursor.execute(t_query)
            row = cursor.fetchone()
            if not row:
                return None
            return row[0]
        
