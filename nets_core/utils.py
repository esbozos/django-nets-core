import calendar
import time
import uuid
from datetime import date, datetime
from django.utils import timezone
import pytz
from django.conf import settings
from django.utils.dateparse import parse_datetime


def local_datetime(s: str, tz: str = settings.TIME_ZONE)-> datetime:
    naive = parse_datetime(s)
    if not naive:
        raise ValueError("local_datetime: Not a valid datetime")

    return pytz.timezone(tz).localize(naive, is_dst=None)

def get_client_ip(request):
    META_PRECEDENCE_ORDER = (
        'HTTP_X_FORWARDED_FOR', 'X_FORWARDED_FOR',  # <client>, <proxy1>, <proxy2>
        'HTTP_CLIENT_IP',
        'HTTP_X_REAL_IP',
        'HTTP_X_FORWARDED',
        'HTTP_X_CLUSTER_CLIENT_IP',
        'HTTP_FORWARDED_FOR',
        'HTTP_FORWARDED',
        'HTTP_VIA',
        'REMOTE_ADDR',
    )

    for h in META_PRECEDENCE_ORDER:
        ip = request.META.get(h, None)
        if ip:
            if ',' in ip:
                ip = ip.split(',')[0]
            return ip
    return None

def generate_int_uuid(size=None):
    u = uuid.uuid1()
    n_random = '{}'.format(u.time_low)

    time_epoch = str(calendar.timegm(time.gmtime()))

    u_id = '{}{}'.format(n_random, time_epoch)

    if size:
        u_id = u_id[:size]
    return int(u_id)

def get_upload_path(instance, filename):
    folder = instance._meta.model_name
    if instance and hasattr(instance, 'customer'):
        path = '{}/'.format(instance.customer.shortname)
    
    path += '{}'.format(folder) if folder.endswith('/') else '{}/'.format(folder)

    today = timezone.now()
    date_path = today.strftime('%Y/%m/%d/')
    path = '{}{}'.format(path, date_path)
    path = '{}{}'.format(path, filename)
    return path