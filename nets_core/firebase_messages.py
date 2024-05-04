import os
import firebase_admin
from django.conf import settings
from firebase_admin import messaging
from firebase_admin.exceptions import FirebaseError
from firebase_admin import credentials
from nets_core.models import UserDevice, UserFirebaseNotification
import logging

logger = logging.getLogger(__name__)

firebase_config = os.getenv('FIREBASE_CONFIG')

if hasattr(settings, 'FIREBASE_CONFIG'):
        firebase_config = settings.FIREBASE_CONFIG

if not firebase_config:
    logger.warning('FIREBASE_CONFIG not set')
    # raise ValueError('FIREBASE_CONFIG not set')
else:
    try:
        cred = credentials.Certificate(firebase_config)
        default_app = firebase_admin.initialize_app(cred)
    except Exception as e:
        logger.error('Error initializing firebase', e)
    # raise ValueError('Error initializing firebase', e)


def send_fb_message(title:str, message:str, registration_token:str, data: dict=None, channel: str=None) -> str:

    try:
        android_config = messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                icon='ic_launcher',
                color='#f45342',
                channel_id=channel or 'default'
            ),
        )
        message = messaging.Message(
            data=data,
            token=registration_token,
            notification=messaging.Notification(
                title=title,
                body=message
            ),
            android=android_config,
        )
        response = messaging.send(message)
        return response
    except Exception as e:
        
        raise ValueError('Error sending message', e)

    


def send_user_device_notification(user, title: str, message: str, data: dict=None, channel: str=None) -> dict:
    devices = UserDevice.objects.filter(user=user).exclude(last_login=None).exclude(firebase_token=None)
    devices_results = {}
    if devices:
        for device in devices:
            notification = UserFirebaseNotification.objects.create(
                    user=user, 
                    device=device, 
                    message=message, 
                    data=data, 
                )
            try:
                message_id = send_fb_message(title, message, device.firebase_token, data, channel)
                notification.message_id = message_id
                notification.sent = True
                notification.save()

                devices_results[device.id] = {
                    'success': True,
                    'message_id': message_id
                }
            except messaging.UnregisteredError as e:
                # delete device
                
                device.delete()

            except Exception as e:
                msg_error = str(e)
                if 'UnregisteredError' in msg_error:
                    device.delete()
                    continue
                logger.error(f'Error sending message {e}')
                message_id = None
                notification.error = str(e)
                notification.save()

                devices_results[device.id] = {
                    'success': False,
                    'error': str(e)
                }

    return devices_results
                
                