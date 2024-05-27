
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.template import TemplateDoesNotExist, TemplateSyntaxError, Template
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

from nets_core.models import EmailNotification

from django.utils.module_loading import import_string
from django.core.mail.backends.smtp import EmailBackend

exclude_domains = []
try:
    exclude_domains = settings.NETS_CORE_EMAIL_EXCLUDE_DOMAINS
except:
    pass

footer_enabled = True
try:
    footer_enabled = settings.NETS_CORE_EMAIL_FOOTER_ENABLED
except:
    pass

footer = "<span><i class=\"small\">{}</i></span>".format(
        _("NETS CORE footer email, you can customize this message in settings.NETS_CORE_EMAIL_FOOTER"))
try:
    footer = f"<span><i class=\"small\">{settings.NETS_CORE_EMAIL_FOOTER}</i></span>"
except:
    pass

footer_template = None
try:
    footer_template = settings.NETS_CORE_EMAIL_FOOTER_TEMPLATE
except:
    pass

try:
    SmsService = import_string(settings.NOTIFY['SMS_SERVICE'])
    sms = SmsService()
except:
    sms = None

mail_debug_enabled = False
try:
    mail_debug_enabled = settings.NETS_CORE_EMAIL_DEBUG_ENABLED
except:
    pass


def send_email(subject: str, email: str|list[str], template: str, context: dict, 
    txt_template: str = None, to_queued: bool = True, force=False, html: str =None):
    """
        Create a email to be sent by command line ./manage.py send_emails
        or dispatch if to_queued is set to False
    """

    if settings.DEBUG and not mail_debug_enabled and not force:
        return (False, _("emails are disabled while debug is true in settings"))

    # Exclude emails from exclude_domain
    if(isinstance(email, str)):
        email_domain = email.split('@')
        email = [email]
        if email_domain in exclude_domains:
            return (False, f'{_("Email domain is in NETS_CORE_EMAIL_EXCLUDE_DOMAINS ")} {email_domain}')

    elif isinstance(email, list):
        for e in email:
            email_domain = e.split('@')
            if email_domain in exclude_domains:
                email.pop(email.index(e))
                print(f"{_('Email domain is in NETS_CORE_EMAIL_EXCLUDE_DOMAINS')} {email_domain}")
    
    if not email:
        return (False, _("email is empty"))
    
    full_context = context
    # full_context.update(context)
    content_txt = None
    if template:
        try:
            content_html = render_to_string(template, context=full_context)
            
            if footer_enabled:
                content_html = brandmark_template(content_html)

        except TemplateDoesNotExist:
            print("Template {} does not exist".format(template))
            return (False, _("Template does not exist"))
        except TemplateSyntaxError as e:
            print(e)
            return (False, _("Template syntax error"))
    elif html:
        # render with html
        template = Template(html)
        content_html = template.render(full_context)
        
    else:
        return (False, _("template or html content for send_email is required"))

    params = {
        'to': email,
        'body': content_html,
        'from_email': settings.DEFAULT_FROM_EMAIL,
        'subject': subject,
    }

    if txt_template:
        content_txt = render_to_string(txt_template)
    
    if to_queued:

        if content_txt:
            params['txt_body'] = content_txt
        email_noti = EmailNotification.objects.create(**params)
        email_noti.save()

        return (True, _("Email in queue."))

    else:
        try:
            msg = EmailMultiAlternatives(**params)
            msg = EmailMultiAlternatives(
                subject, content_html, settings.DEFAULT_FROM_EMAIL, email)
            msg.content_subtype = "html"
            if content_txt:
                msg.attach_alternative(content_txt, "text/plain")
            result = msg.send(fail_silently=False)
            if result:
                return (True, _("Email sent"))
            else:
                return (False, _("Email wasn't sent"))
        except Exception as e:
            print(e)
            return (False, _("Email wasn't sent"))
    # if sms:
    #     sms.send_sms(phone, text)


def brandmark_template(html):
    if footer_template:
        return brandmark_footer_template(html)

    html = html.replace('</body>', '{}</body>'.format(footer))
    return html


def brandmark_footer_template(html):
    brand = render_to_string(
        footer_template)
    html = html.replace('</body>', '{}</body>'.format(brand))
    return html
