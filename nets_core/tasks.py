from celery import shared_task
# get_user_model() returns the User model that is active in this project
from django.contrib.auth import get_user_model
from django.conf import settings

import requests
import os
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


@shared_task
def send_user_devices_notifications(user_id:  int, title: str, message: str, data: dict, channel: str=None):
    from nets_core.firebase_messages import send_user_device_notification
    user = User.objects.get(id=user_id)    
    # ensure data is a dict of strings
    data = {k: str(v) for k, v in data.items()}
    send_user_device_notification(user, title, message, data, channel)

@shared_task
def check_permissions(user_id: int, permission: str):
    user = User.objects.get(id=user_id)
    return user.has_perm(permission)


@shared_task
def get_google_avatar(user_id, avatar, field="avatar"):
    user = User.objects.get(id=user_id)
    if not hasattr(user, field):
        return
    if not avatar:
        return
    # download avatar to temp folder in media ROOT
    res = requests.get(avatar)
    if res.status_code == 200:
        temp_path = os.path.join(settings.MEDIA_ROOT, "tmp")
        if not os.path.exists(temp_path):
            os.makedirs(temp_path)

        with open(os.path.join(temp_path, f"{user_id}.jpg"), "wb") as f:
            f.write(res.content)

        with open(os.path.join(temp_path, f"{user_id}.jpg"), "rb") as f:
            field_instance = getattr(user, field)
            field_instance.save(f"{user_id}.jpg", f, save=True)
            # user.avatar.save(f"{user_id}.jpg", f, save=True)  # type: ignore
    else:
        logger.error(f"Error downloading avatar for user {user_id} from {avatar}")