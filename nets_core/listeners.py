from nets_core.firebase_messages import send_user_device_notification
from nets_core.models import VerificationCode
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver
from nets_core.mail import send_email
from nets_core.models import EmailTemplate
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=VerificationCode)
def send_verification_code_email(sender, instance, created, **kwargs):
    if created:
        # send email
        cache_token_key = instance.get_token_cache_key()
        button_link = {"url": "", "label": cache.get(cache_token_key)}
        template = None
        html = None
        email_template = (
            EmailTemplate.objects.filter(use_for="verification_code", enabled=True)
            .order_by("-created")
            .first()
        )

        if email_template:
            html = email_template.html_body
        else:
            template = "nets_core/email/verification_code.html"

        result = send_email(
            _("Verification code"),
            [instance.user.email],
            template,
            {"button_link": button_link, "user": instance.user},
            html=html,
            to_queued=False,
        )
        logger.info(
            f"Verification code email to {instance.user.email} with result {result}"
        )

    else:
        if instance.verified:
            # send notification to user about new login
            template = "nets_core/email/new_login.html"
            send_email(
                _("New login"),
                [instance.user.email],
                template,
                {"user": instance.user, "ip": instance.ip, "device": instance.device},
                to_queued=False,
            )

            message = _("New login to your account from ip address") + " " + instance.ip
            data = {"type": "login", "ip": instance.ip, "device": ""}
            if instance.device:
                message += " " + _("using device") + " " + instance.device.__str__()
                data["device"] = instance.device.name
                data["device_id"] = f"{instance.device_id}"
            title = f"{_('New login')} {instance.user.username}"
            send_user_device_notification(
                instance.user, title=title, message=message, data=data
            )
