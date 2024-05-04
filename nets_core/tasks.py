from celery import shared_task
# get_user_model() returns the User model that is active in this project
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


@shared_task
def send_user_devices_notifications(user_id:  int, title: str, message: str, data: dict, channel: str=None):
    from nets_core.firebase_messages import send_user_device_notification
    user = User.objects.get(id=user_id)    
    # ensure data is a dict of strings
    data = {k: str(v) for k, v in data.items()}
    send_user_device_notification(user, title, message, data, channel)

