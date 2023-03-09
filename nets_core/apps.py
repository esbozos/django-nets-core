from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'nets_core'
    
    def ready(self):
        import nets_core.listeners