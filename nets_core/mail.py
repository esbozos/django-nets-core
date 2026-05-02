
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.template import TemplateDoesNotExist, TemplateSyntaxError, Template
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

from nets_core.models import EmailNotification

from django.utils.module_loading import import_string
from django.core.mail.backends.smtp import EmailBackend
import logging
import mimetypes

logger = logging.getLogger(__name__)

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

EMAIL_REASONS = {
    'invalid_email': _('Invalid email address'),
    'email_domain_excluded': _('Email domain is in NETS_CORE_EMAIL_EXCLUDE_DOMAINS'),
    'empty_email': _('Email is empty'),
    'template_not_found': _('Template does not exist'),
    'template_syntax_error': _('Template syntax error'),
    'template_or_html_required': _('template or html content for send_email is required'),
    'email_not_sent': _('Email wasn\'t sent'),
    'email_sent': _('Email sent'),
    'email_in_queue': _('Email in queue.'),
    'email_disabled': _('emails are disabled while debug is true in settings'),
    'invalid_attachment': _('Invalid attachment format')
}


def _normalize_attachments(attachments):
    """
    Normalize accepted attachment formats to Django's attach signature:
    (filename, content, mimetype)
    """
    if not attachments:
        return []

    normalized = []
    for item in attachments:
        # tuple/list: (filename, content) or (filename, content, mimetype)
        if isinstance(item, (tuple, list)):
            if len(item) == 2:
                filename, content = item
                mimetype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                normalized.append((filename, content, mimetype))
                continue
            if len(item) == 3:
                filename, content, mimetype = item
                normalized.append((filename, content, mimetype))
                continue
            raise ValueError(EMAIL_REASONS['invalid_attachment'])

        # UploadedFile / File-like objects
        if hasattr(item, 'read') and hasattr(item, 'name'):
            filename = item.name
            content = item.read()
            mimetype = getattr(item, 'content_type', None) or mimetypes.guess_type(filename)[0] or "application/octet-stream"
            normalized.append((filename, content, mimetype))
            continue

        raise ValueError(EMAIL_REASONS['invalid_attachment'])

    return normalized

def valid_email_domain(email):
    if not email:
        return False, EMAIL_REASONS['invalid_email']
    if not isinstance(email, str):
        return False, EMAIL_REASONS['invalid_email']
    if not '@' in email:
        return False, EMAIL_REASONS['invalid_email']
    email_domain = email.split('@')
    for domain in exclude_domains:
        if domain in email_domain:
            return False, domain
    return True, None
    

def send_email(subject: str, email: str|list[str], template: str, context: dict,
    txt_template: str = None, to_queued: bool = True, force=False, html: str =None,
    attachments: list|tuple|None = None, **kwargs):
    """
        Create a email to be sent by command line ./manage.py send_emails
        or dispatch if to_queued is set to False
    """

    if settings.DEBUG and not mail_debug_enabled and not force:
        return (False, 'email_disabled', EMAIL_REASONS['email_disabled'])

    # Backward compatibility for callers using "files" keyword.
    if attachments is None:
        attachments = kwargs.get('files')

    try:
        normalized_attachments = _normalize_attachments(attachments)
    except ValueError as e:
        return (False, 'invalid_attachment', str(e))

    reason = ''
    # Exclude emails from exclude_domain
    if(isinstance(email, str)):
        email = [email]
    
    invalid_emails = []
    for e in email:
        valid_email, email_domain = valid_email_domain(e)
        if not valid_email:
            reason += ' ' + email_domain
            invalid_emails.append(e)
            email.pop(email.index(e))           
        
    if reason:
        logger.error(f'Email(s) domain(s) excluded: {reason}')
        reason = f'{EMAIL_REASONS["email_domain_excluded"]}, the following email(s) were excluded: {invalid_emails} for domain(s): {reason}'
    
    if not email:        
        return (False, 'empty_email', EMAIL_REASONS['empty_email'] + ' ' + reason)
    
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
            return (False, 'template_not_found', EMAIL_REASONS['template_not_found'] + ' ' + template + ' ' + reason)
        except TemplateSyntaxError as e:
            print(e)
            return (False, 'template_syntax_error', EMAIL_REASONS['template_syntax_error'] + ' ' + template + ' ' + reason)
        
    elif html:
        # render with html
        template = Template(html)
        content_html = template.render(full_context)
        
    else:
        return (False, 'template_or_html_required', EMAIL_REASONS['template_or_html_required'] + ' ' + reason)

    params = {
        'to': email,
        'body': content_html,
        'from_email': settings.DEFAULT_FROM_EMAIL,
        'subject': subject,
    }

    if txt_template:
        content_txt = render_to_string(txt_template)
    
    # EmailNotification does not persist attachments; send immediately when present.
    if normalized_attachments and to_queued:
        logger.warning('Attachments are not supported in queued emails; sending immediately.')
        to_queued = False

    if to_queued:

        if content_txt:
            params['txt_body'] = content_txt
        email_noti = EmailNotification.objects.create(**params)
        email_noti.save()

        return (True, 'email_in_queue', EMAIL_REASONS['email_in_queue'])

    else:
        try:
            msg = EmailMultiAlternatives(
                subject, content_html, settings.DEFAULT_FROM_EMAIL, email)
            msg.content_subtype = "html"
            if content_txt:
                msg.attach_alternative(content_txt, "text/plain")
            for filename, content, mimetype in normalized_attachments:
                msg.attach(filename, content, mimetype)
            result = msg.send(fail_silently=False)
            if result:
                return (True, 'email_sent', EMAIL_REASONS['email_sent'] + ' ' + str(result) + ' ' + reason)
            else:
                return (False, 'email_not_sent', EMAIL_REASONS['email_not_sent'] + ' ' + reason)
        except Exception as e:
            print(e)
            return (False, 'email_not_sent', EMAIL_REASONS['email_not_sent'] + ' ' + reason)


def send_mail(subject: str, email: str|list[str], template: str, context: dict,
    txt_template: str = None, to_queued: bool = True, force=False, html: str =None,
    files: list|tuple|None = None, **kwargs):
    """Compatibility wrapper for callers expecting send_mail and files kwargs."""
    return send_email(
        subject=subject,
        email=email,
        template=template,
        context=context,
        txt_template=txt_template,
        to_queued=to_queued,
        force=force,
        html=html,
        attachments=files,
        **kwargs,
    )


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
