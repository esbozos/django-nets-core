from django.apps import AppConfig
from django.db.models.signals import post_migrate
import logging
logger = logging.getLogger(__name__)

def post_migrate_handler(sender, **kwargs):
    from nets_core.procedures import nets_core_functions
    using = kwargs.get("using")
    # add style colors to logger    
    logger.warning("Creating nets_core functions")    
    nets_core_functions.create_nets_core_functions(using=using)
    
class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'nets_core'
    
    def ready(self):
        import nets_core.listeners
        post_migrate.connect(post_migrate_handler, sender=self)