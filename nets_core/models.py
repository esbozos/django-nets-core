from uuid import uuid4
from django.db import models
from django.utils.translation import gettext_lazy as _
import json
from django.conf import settings
import shortuuid
from django.core.cache import cache
from nets_core.utils import generate_int_uuid
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

token_timeout_seconds = 15*60 # 15 minutes default
try:
    token_timeout_seconds = settings.NS_VERIFICATION_CODE_EXPIRE_SECONDS
except Exception as e:
    # Settings not present use default
    pass

class OwnedModel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
>>>>>>> 557f77fde5694bd5b79946c60df5b3dc916b8512
    created = models.DateTimeField(_('Created'), auto_now_add=True)
    updated = models.DateTimeField(_('updated'), auto_now=True)

    class Meta:
        abstract = True

class VerificationCode(OwnedModel):
    token = models.CharField(_("Verification token"), max_length=150)
    device = models.ForeignKey("nets_core.UserDevice", max_length=150, null=True, blank=True, on_delete=models.CASCADE)
    verified = models.BooleanField(_("Verified?"), default=False)
    ip = models.CharField(_("IP"), max_length=150, null=True, blank=True)
    verified = models.BooleanField(_("Verified?"), default=False)

    class Meta:
        db_table = 'nets_core_verification_code'
    
    def get_token_cache_key(self):
        token_key_prefix = 'NC_T'
        try:
            token_key_prefix = settings.NS_VERIFICATION_CODE_CACHE_KEY 
        except:
            pass

        return f'{token_key_prefix}{self.user.pk}'

    def save(self, *args, **kwargs):
        token = 123456
        cache_token_key = self.get_token_cache_key()
        tester_emails = ['google_tester*']
        # check if settings has testers emails
        if hasattr(settings, 'TESTERS_EMAILS') and type(settings.TESTERS_EMAILS) == list:
            tester_emails += settings.TESTERS_EMAILS
        
        is_tester = False
        for tester_email in tester_emails:
            # emails can be like google_tester* or google_tester1@gmail.com
            if tester_email.endswith('*'):
                if self.user.email.startswith(tester_email.replace('*', '')):
                    is_tester = True
                    break
            else:
                if self.user.email == tester_email:
                    is_tester = True
                    break

        if is_tester:
            token = 789654
            if hasattr(settings, 'TESTERS_VERIFICATION_CODE'):
                token = settings.TESTERS_VERIFICATION_CODE

        if not settings.DEBUG and not is_tester:

        if not settings.DEBUG:
            # Check cache if token is present and return the same token
            token = cache.get(cache_token_key)
            if not token:
                # Generate a new numeric token six digits
                token = generate_int_uuid(6)
        
        # Set token in cache system 
        cache.set(cache_token_key, '{}'.format(token), token_timeout_seconds)
        
        # Encrypt the token and send email 
        self.token = make_password(str(token))
        super(VerificationCode, self).save(*args, **kwargs)

        

    def validate(self, token: str=None, device_uuid: str=None):
        if not token or not self.token:
            return False
        
        if self.device:
            if not device_uuid or self.device.uuid != device_uuid:
                return False 
    def validate(self, token: str=None):
        if not token or not self.token:
            return False

        if (timezone.now() - self.created).total_seconds() > token_timeout_seconds:
            # code expired delete it.
            self.delete()
            return False
            
        return check_password(token, self.token)

TEMPLATES_USES = (
    ('verification_code', _("Verification code: send each time a code is generated")),
    ('other', _("Other: Nets core not implemented use. You can use this from any view quering from nets_core.models.EmailTemplate"))
)
class EmailTemplate(OwnedModel):
    name = models.CharField(_("Name"), max_length=150, unique=True)
    html_body = models.TextField(_("HTML BODY"), help_text=_("You can use Django template language see: https://docs.djangoproject.com/en/4.1/ref/templates/language/ "))
    text_body = models.TextField(_("TXT BODY"), help_text=_("You can use Django template language see: https://docs.djangoproject.com/en/4.1/ref/templates/language/ "))
    enabled = models.BooleanField(_("Enabled?"), default=True)
    use_for = models.CharField(_("Use template for"), default='other', choices=TEMPLATES_USES, max_length=50)
    def __str__(self) -> str:
        return self.name



class CustomEmail(OwnedModel):
    subject = models.CharField(_("subject"), max_length=250)
    to_email = models.TextField(_("To Email"), max_length=250)
    from_email = models.CharField(_("From Email"), max_length=250)
    html_body = models.TextField(_("HTML Body"))
    txt_body = models.TextField(_("TXT Body"), null=True, blank=True)
    completed = models.BooleanField(_("completed"), default=False)
    sent_count = models.IntegerField(_("Sent count"), default=0)
    failed_count = models.IntegerField(_("Failed count"), default=0)

    class Meta:
        verbose_name = _("Email")
        verbose_name_plural = _("Emails")

    def __str__(self):
        return self.subject

class EmailNotification(models.Model):
    subject = models.CharField(_("subject"), max_length=250)
    to = models.TextField(_("To Email"), max_length=250)
    from_email = models.CharField(_("From Email"), max_length=250)
    body = models.TextField(_("HTML Body"))
    txt_body = models.TextField(_("TXT Body"), null=True, blank=True)
    sent = models.BooleanField(_("sent"), default=False)
    tries = models.IntegerField(_("tries"), default=0)
    sent_at = models.DateTimeField(_("Sent at"), null=True)
    created = models.DateTimeField(_("created"), auto_now_add=True)
    updated = models.DateTimeField(_("created"), auto_now=True)
    custom_email = models.ForeignKey(
        CustomEmail, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return "%s %s" % (self.to, self.subject)


class UserDevice(OwnedModel):
    uuid = models.UUIDField(_("UUID"), default=uuid4, editable=False, unique=True)
    name = models.CharField(_("Name"), max_length=250)
    os = models.CharField(_("OS"), max_length=250, null=True, blank=True)
    os_version = models.CharField(_("OS Version"), max_length=250, null=True, blank=True)
    app_version = models.CharField(_("App Version"), max_length=250, null=True, blank=True)
    device_type = models.CharField(_("Device Type"), max_length=250, null=True, blank=True)
    device_token = models.CharField(_("Device Token"), max_length=250, null=True, blank=True)
    firebase_token = models.CharField(_("Firebase Token"), max_length=250, null=True, blank=True)
    active = models.BooleanField(_("Active"), default=True)
    last_login = models.DateTimeField(_("Last login"), null=True)
    ip = models.CharField(_("IP"), max_length=250, null=True, blank=True)

    class Meta:
        verbose_name = _("User Device")
        verbose_name_plural = _("User Devices")
        db_table = 'nets_core_user_device'


    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
            
        super(UserDevice, self).save(*args, **kwargs)

class UserFirebaseNotification(OwnedModel):
    message = models.TextField(_("Message"), null=True, blank=True)
    devices = models.ManyToManyField(UserDevice, related_name='notifications')
    data = models.JSONField(_("Data"), null=True, blank=True)
    sent = models.BooleanField(_("Sent"), default=False)
    message_id = models.CharField(_("Message ID"), max_length=250, null=True, blank=True)
    error = models.TextField(_("Error"), null=True, blank=True)
    device = models.ForeignKey(UserDevice, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("User Firebase Notification")
        verbose_name_plural = _("User Firebase Notifications")
        db_table = 'nets_core_firebase_notification'

    def __str__(self):
        return self.message_id
