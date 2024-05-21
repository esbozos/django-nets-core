import mimetypes
from datetime import date, datetime
import json
import pytz
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from nets_core.utils import local_datetime
from dateutil.parser import parse
from django.utils.translation import gettext_lazy as _

def is_email(email: str):
    validate_email(email)
    return email.lower()


def is_datetime(s: str, tz: str = settings.TIME_ZONE):
    naive = parse_datetime(s)
    
    if not naive:
        return False, _("Fecha no válida")
    if tz:
        try:
            naive = pytz.timezone(tz).localize(naive, is_dst=None)
        except Exception as e:
            print('timezone error', e)
   
    return timezone.localtime(naive)


def is_date(s: str):

    d = None
    if isinstance(s, str):
        try:
            d = parse_datetime(s)
        except:
            d = parse(s)
        if not d:
            d = parse(s)

        # d = d.date()
    elif isinstance(s, datetime):
        d =  s.date()
    elif isinstance(s, date):
        d = s
    if d:
        
        # localize date
        if not isinstance(d, datetime):
            try:
                d = local_datetime(d)
            except Exception as e:
                print('e', e)
                
            # d = timezone.localtime(d)
        
        if timezone.is_naive(d):
            
            d = timezone.make_aware(d)           

        if isinstance(d, datetime):
            return d.date()
        return d

    raise ValueError(_("Fecha no válida"))

MAP_INSTANCES = {
    "int": int,
    "str": str,
    "bool": bool,
    "float": float,
    "date": is_date,
    "datetime": is_datetime,
    "file": "file",
    "email": is_email
}

class RequestParam():
    errors = {
        'required': 'El parámetro {} es obligatorio',
        'invalid_value': 'El valor del parámetro {} no es válido',
        'invalid_type': 'El tipo del parámetro {} no es válido',
        
    }
    def __init__(self, key, type, optional=False, validate=None, **kwargs) -> None:
        # filetypes = ['image', 'video', 'audio', 'document', 'pdf']

        self.default = kwargs.get('default', None)
        self.value = self.default
        self.filetypes = kwargs.get('filetypes', [])
        self.key = key
        self.type = type
        self.optional = optional
        self.validate = validate
        self.project = None

        pass
    
    def __str__(self) -> str:
        return f'{self.key}, Type: {self.type}, Optional? {self.optional}, default: {self.default}'

    def get_file(self, files):
        try:
            v = files.get(self.key, None)
            if self.filetypes:
                # Check if file is a valid filetype
                mime_type, encoding = mimetypes.guess_type(v.name)
                if mime_type in self.filetypes:
                    return v
                else:
                    raise ValueError(f"RP file02: {self.errors['invalid_type']}: el fichero {mime_type} no es tipo permitido")
            
            return v
                
        except KeyError:
            if self.optional:
                return self.default
            raise ValueError(f"RP file01: {self.errors['required'].format(self.key)} ")
        
        
    def get_value(self, data):
        
        v = data.get(self.key, None)
        # Handle boolean values 
        if self.type in ['bool', bool]:
            if not v:
                return False
            if v in ['true', 'True', '1', 1, True]:
                return True
            return False

        if v in [0, '0']:
            return 0
        
        if not v and not self.optional and not self.type in ['bool', bool]:
            raise ValueError(f"RP value01: {self.errors['required'].format(self.key)} ")
        
        if not v and self.optional:
            print('param is optional, check default', self.default)
            v = self.default if self.default else None
            return v

        if isinstance(v, dict):
            if not self.type == dict:
                # Check if value was post as dict from select {value: str, label: str}
                if 'value' in v:
                    v = v['value']

        if v == None and not self.optional and not self.type in ['bool', bool]:
            raise ValueError(f"RP01: {self.errors['required'].format(self.key)}")

        if v == None and not self.type in [bool, 'bool']:
            return None

        if isinstance(self.type, type) or callable(self.type):

            try:
                if self.type == list and isinstance(v, str):
                    # Check if value is a list of values
                    # then convert to list
                    v = v.replace('[', '').replace(']', '').replace("'", '').replace('"', '')
                    v = v.split(',')
                elif self.type == dict and isinstance(v, str):
                    # Check if value is a dict
                    # then convert to dict
                    v = json.loads(v)
                else:
                    # Check type by type()
                    v = self.type(v)
                
            except Exception as e:

                raise ValueError(
                    f"RP02: {self.errors['invalid_value'].format(self.key)}:  {v} no es {self.type}")

        if isinstance(self.type, str):
            # Check type by MAP_INSTANCES
            if not self.type in MAP_INSTANCES:
                raise KeyError(
                    f"RP03: {self.errors['invalid_type'].format(self.type)}; {MAP_INSTANCES.keys().__str__()}")

            instance_type = MAP_INSTANCES[self.type]
            try:
                
                v = instance_type(v)
            except Exception as e:
                print('call', v, self.type, instance_type)
                raise ValueError(
                    f"RP04: {self.errors['invalid_value'].format(self.key)}: {v} no es {self.type} ")

        if self.validate:
            if self.project:
                valid = self.validate(v, self.project)
            else:
                valid = self.validate(v)
            if not valid:
                raise ValueError(
                    f"RP05: {self.errors['invalid_value'].format(self.key)}: {v} no es {self.type}")
        
        return v