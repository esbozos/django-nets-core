from nets_core import firebase_messages
from django.conf import settings
from django.core.management.base import BaseCommand
from django.apps import apps

import logging

logger = logging.getLogger(__name__)

    
class Command(BaseCommand):
    help = 'Send push notification to user_id or firebase_token'
    
    def add_arguments(self, parser):
        parser.add_argument('--user_id', nargs='?', type=int)
        parser.add_argument('--firebase_token', nargs='?', type=str)
        parser.add_argument('--title', nargs='?', type=str)
        parser.add_argument('--message', nargs='?', type=str)

    def handle(self, *args, **options):
        title = options['title'] or 'Planyz'
        message = options['message'] or 'Hello from Planyz (Using command test_push_notification)'
        
        # get user
        if options['user_id']:            
            self.user_notification(options['user_id'], title, message)
            
        elif options['firebase_token']:
            try:
                result = firebase_messages.send_fb_message(
                    title,
                    message,
                    options['firebase_token']
                )
                logger.info(self.style.SUCCESS(f'Message sent: {result}'))
            except Exception as e:
                logger.error(self.style.ERROR(f'Error sending message: {e}'))
        else:
            print('user_id or firebase_token is required')
            exit(1)
            
            
    def user_notification(self, user_id: int, title: str, message: str):
        try:
            User = apps.get_model(settings.AUTH_USER_MODEL)
        except Exception as e:
            logger.error(self.style.ERROR(f'Error getting user model: {e}'))
            exit(1)
        
        user = User.objects.filter(id=user_id).first()
        if not user:
            logger.error(self.style.ERROR(f'User not found'))
            exit(1)
            
        try:
            for device in user.userdevice_set.all():
                
                print(f'Sending message to {device.firebase_token}')
                result = firebase_messages.send_fb_message(
                    title,
                    message,
                    device.firebase_token
                )
                logger.info(self.style.SUCCESS(f'Message sent: {result}'))
        except Exception as e:
            logger.error(self.style.ERROR(f'Error sending message: {e}'))
            exit(1)