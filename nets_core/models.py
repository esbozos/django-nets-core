import json
import shortuuid

from uuid import uuid4


from django.conf import settings
from django.apps import apps
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.cache import cache
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from django.contrib.auth import get_user_model


from nets_core.utils import generate_int_uuid

token_timeout_seconds = 15 * 60  # 15 minutes default
try:
    token_timeout_seconds = settings.NETS_CORE_VERIFICATION_CODE_EXPIRE_SECONDS
except Exception as e:
    # Settings not present use default
    pass


class NetsCoreBaseManager(models.Manager):

    def to_json(self, fields: tuple = None):
        query = self.get_queryset()
        if not query:
            raise ValueError(_("Query must be provided"))

        # get the query instance and check if JSON_DATA_FIELDS is present
        if hasattr(self.model, "JSON_DATA_FIELDS") and not fields:
            if not self.model.JSON_DATA_FIELDS:
                raise ValueError(_("Fields must be provided"))
            if not isinstance(self.model.JSON_DATA_FIELDS, tuple):
                try:
                    fields = tuple(self.model.JSON_DATA_FIELDS)
                except Exception as e:
                    raise ValueError(_("Fields must be a tuple or list"))

        if not fields:
            raise ValueError(_("Fields must be provided"))
        if fields == "__all__":
            # get fiels to tupple but names from columns in db table schema, user should be user_id
            schema = self.model._meta.get_fields()
            fields = tuple(
                [field.column for field in schema if hasattr(field, "column")]
            )

        if not isinstance(fields, tuple):
            raise ValueError(_("Fields must be a tuple"))

        from nets_core.serializers import NetsCoreModelToJson, NetsCoreQuerySetToJson

        if query.count() == 1:
            return NetsCoreModelToJson(query.first(), fields).to_json()

        return NetsCoreQuerySetToJson(query, fields).to_json()


class NetsCoreBaseModel(models.Model):
    created = models.DateTimeField(_("Created"), auto_now_add=True)
    updated = models.DateTimeField(_("updated"), auto_now=True)
    updated_fields = models.JSONField(
        _("Updated fields"), null=True, blank=True, default=dict
    )

    objects = NetsCoreBaseManager()

    class Meta:
        abstract = True

    def validate_fields(self, fields: tuple):
        schema = self._meta.get_fields()
        # add fields that are not in schema and end with _id as user should be user_id and not present in schema
        final_fields = [f for f in fields if f.endswith("_id")]
        for f in schema:
            if f.name in fields and not f.name in final_fields:
                if isinstance(f, models.ForeignKey):
                    related_model = f.related_model

                    if (
                        hasattr(related_model, "JSON_DATA_FIELDS")
                        and related_model.JSON_DATA_FIELDS
                    ):
                        if not isinstance(related_model.JSON_DATA_FIELDS, tuple):
                            try:
                                related_fields = tuple(related_model.JSON_DATA_FIELDS)
                            except Exception as e:
                                raise ValueError(_("Fields must be a tuple or list"))
                        else:
                            related_fields = fields
                        # replace field for related format as field_name:[table_name; ...related_fields]
                        table_name = related_model._meta.db_table
                        related_fields = [table_name] + list(related_fields)
                        final_fields.append(f"{f.name}_id:[{';'.join(related_fields)}]")
                        # final_fields = final_fields + (f"{f.name}:[{';'.join(related_fields)}]",)

                    else:
                        raise ValueError(
                            _(
                                "Field %s is a related model but has no JSON_DATA_FIELDS"
                                % f.name
                            )
                        )
                else:
                    final_fields.append(f.name)

        return tuple(final_fields)

    def to_json(self, fields: tuple = None):
        # check if JSON_DATA_FIELDS is present
        if hasattr(self, "JSON_DATA_FIELDS") and not fields:
            if not self.JSON_DATA_FIELDS:
                raise ValueError(_("Fields must be provided"))
            if not isinstance(self.JSON_DATA_FIELDS, tuple):
                try:
                    fields = tuple(self.JSON_DATA_FIELDS)
                except Exception as e:
                    raise ValueError(_("Fields must be a tuple or list"))

        if not fields:
            raise ValueError(_("Fields must be provided"))
        if fields == "__all__":
            # get fields to tuple but names from columns in db table schema, user should be user_id
            schema = self._meta.get_fields()
            fields = tuple(
                [field.column for field in schema if hasattr(field, "column")]
            )
            related_fields = [
                field.name for field in schema if hasattr(field, "related_model")
            ]
            fields = self.validate_fields(fields + tuple(related_fields))
        else:
            fields = self.validate_fields(fields)
        if not isinstance(fields, tuple):
            raise ValueError(_("Fields must be a tuple"))

        from nets_core.serializers import NetsCoreModelToJson

        return NetsCoreModelToJson(self, fields).to_json()

    def save(self, *args, **kwargs):

        super(NetsCoreBaseModel, self).save(*args, **kwargs)


class OwnedModel(NetsCoreBaseModel):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)

    objects = NetsCoreBaseManager()

    class Meta:
        abstract = True


class Permission(NetsCoreBaseModel):
    name = models.CharField(_("Name"), max_length=150)
    codename = models.CharField(_("Codename"), max_length=150, unique=True)
    description = models.CharField(
        _("Description"), max_length=250, null=True, blank=True
    )
    # project_content_type = models.ForeignKey(
    #     ContentType,
    #     on_delete=models.CASCADE,
    #     null=True,
    #     blank=True,
    #     related_name="nets_core_permissions",
    # )
    # project_id = models.PositiveIntegerField(null=True, blank=True)
    # project = GenericForeignKey("project_content_type", "project_id")

    JSON_DATA_FIELDS = ["name", "codename", "description"]
    objects = NetsCoreBaseManager()

    class Meta:
        verbose_name = _("Permission")
        verbose_name_plural = _("Permissions")
        db_table = "nets_core_permission"

    def __str__(self):
        return f"{self.name} - {self.codename}"

    def save(self, *args, **kwargs):
        self.codename = self.codename.lower()
        if not self.name:
            self.name = self.codename

        super(Permission, self).save(*args, **kwargs)


class Role(NetsCoreBaseModel):
    name = models.CharField(_("Name"), max_length=150)
    codename = models.CharField(_("Codename"), max_length=150)
    description = models.CharField(_("Description"), max_length=250)
    permissions = models.ManyToManyField(
        Permission, related_name="roles", through="RolePermission"
    )
    project_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    project_id = models.PositiveIntegerField(null=True, blank=True)
    project = GenericForeignKey("project_content_type", "project_id")
    enabled = models.BooleanField(_("Enabled?"), default=True)

    JSON_DATA_FIELDS = [
        "name",
        "codename",
        "description",
        "project_id",
        "enabled",
    ]

    objects = NetsCoreBaseManager()

    class Meta:
        verbose_name = _("Role")
        verbose_name_plural = _("Roles")
        db_table = "nets_core_role"
        indexes = [
            models.Index(
                fields=["project_content_type", "project_id"], name="role_index"
            )
        ]

    def __str__(self):
        if self.project:
            return f"{self.name} - {self.project}"
        return self.name

    def save(self, *args, **kwargs):
        self.codename = self.codename.lower()
        super(Role, self).save(*args, **kwargs)


class RolePermission(NetsCoreBaseModel):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    custom_name = models.CharField(
        _("Custom name"), max_length=150, null=True, blank=True
    )

    JSON_DATA_FIELDS = ["role_id", "permission_id", "custom_name"]
    objects = NetsCoreBaseManager()

    class Meta:
        verbose_name = _("Role Permission")
        verbose_name_plural = _("Role Permissions")
        db_table = "nets_core_role_permission"

    def __str__(self):
        if self.project:
            return f"{self.role} - {self.permission} - {self.project}"
        return f"{self.role} - {self.permission}"

    def save(self, *args, **kwargs):
        if hasattr(self, "project") and self.project:
            self.project_content_type = ContentType.objects.get_for_model(self.project)
            self.project_id = self.project.id

        super(RolePermission, self).save(*args, **kwargs)


class UserRole(NetsCoreBaseModel):
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="roles"
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    project_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    project_id = models.PositiveIntegerField(null=True, blank=True)
    project = GenericForeignKey("project_content_type", "project_id")

    objects = NetsCoreBaseManager()

    JSON_DATA_FIELDS = ["user_id", "role_id", "project_content_type", "project_id"]

    class Meta:
        verbose_name = _("User Role")
        verbose_name_plural = _("User Roles")
        db_table = "nets_core_user_role"

    def __str__(self):
        if self.project:
            return f"{self.user} - {self.role} - {self.project}"
        return f"{self.user} - {self.role}"

    def save(self, *args, **kwargs):
        if hasattr(self, "project") and self.project:
            self.project_content_type = ContentType.objects.get_for_model(self.project)
            self.project_id = self.project.id

        super(UserRole, self).save(*args, **kwargs)


class VerificationCode(OwnedModel):
    token = models.CharField(_("Verification token"), max_length=150)
    device = models.ForeignKey(
        "nets_core.UserDevice",
        max_length=150,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    verified = models.BooleanField(_("Verified?"), default=False)
    ip = models.CharField(_("IP"), max_length=150, null=True, blank=True)

    class Meta:
        db_table = "nets_core_verification_code"

    def get_token_cache_key(self):
        token_key_prefix = "NC_T"
        try:
            token_key_prefix = settings.NETS_CORE_VERIFICATION_CODE_CACHE_KEY
        except:
            pass

        return f"{token_key_prefix}{self.user.pk}"

    def save(self, *args, **kwargs):
        token = 123456
        cache_token_key = self.get_token_cache_key()
        tester_emails = ["google_tester*"]
        # check if settings has testers emails
        if (
            hasattr(settings, "NETS_CORE_TESTERS_EMAILS")
            and type(settings.TESTERS_EMAILS) == list
        ):
            tester_emails += settings.NETS_CORE_TESTERS_EMAILS

        is_tester = False
        for tester_email in tester_emails:
            # emails can be like google_tester* or google_tester1@gmail.com
            if tester_email.endswith("*"):
                if self.user.email.startswith(tester_email.replace("*", "")):
                    is_tester = True
                    break
            else:
                if self.user.email == tester_email:
                    is_tester = True
                    break

        if is_tester:
            token = 789654
            if hasattr(settings, "NETS_CORE_TESTERS_VERIFICATION_CODE"):
                token = settings.NETS_CORE_TESTERS_VERIFICATION_CODE

        if not settings.DEBUG and not is_tester:
            # Check cache if token is present and return the same token
            token = cache.get(cache_token_key)
            if not token:
                # Generate a new numeric token six digits
                token = generate_int_uuid(6)

        # Set token in cache system
        cache.set(cache_token_key, "{}".format(token), token_timeout_seconds)

        # Encrypt the token and send email
        self.token = make_password(str(token))
        super(VerificationCode, self).save(*args, **kwargs)

    def validate(self, token: str = None, device_uuid: str = None):
        if not token or not self.token:
            return False

        if self.device:
            if not device_uuid or self.device.uuid != device_uuid:
                return False

        if (timezone.now() - self.created).total_seconds() > token_timeout_seconds:
            # code expired delete it.
            self.delete()
            return False

        return check_password(token, self.token)


TEMPLATES_USES = (
    ("verification_code", _("Verification code: send each time a code is generated")),
    (
        "other",
        _(
            "Other: Nets core not implemented use. You can use this from any view quering from nets_core.models.EmailTemplate"
        ),
    ),
)


class EmailTemplate(OwnedModel):
    name = models.CharField(_("Name"), max_length=150, unique=True)
    html_body = models.TextField(
        _("HTML BODY"),
        help_text=_(
            "You can use Django template language see: https://docs.djangoproject.com/en/4.1/ref/templates/language/ "
        ),
    )
    text_body = models.TextField(
        _("TXT BODY"),
        help_text=_(
            "You can use Django template language see: https://docs.djangoproject.com/en/4.1/ref/templates/language/ "
        ),
    )
    enabled = models.BooleanField(_("Enabled?"), default=True)
    use_for = models.CharField(
        _("Use template for"), default="other", choices=TEMPLATES_USES, max_length=50
    )
    project_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    project_id = models.PositiveIntegerField(null=True, blank=True)
    project = GenericForeignKey("project_content_type", "project_id")
    JSON_DATA_FIELDS = [
        "name",
        "html_body",
        "text_body",
        "enabled",
        "use_for",
        "project_content_type",
        "project_id",
    ]

    class Meta:
        verbose_name = _("Email Template")
        verbose_name_plural = _("Email Templates")
        db_table = "nets_core_email_template"
        indexes = [
            models.Index(
                fields=["project_content_type", "project_id"],
                name="email_template_index",
            )
        ]

    def __str__(self) -> str:
        if self.project:
            return f"{self.name} - {self.project}"
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
    project_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    project_id = models.PositiveIntegerField(null=True, blank=True)
    project = GenericForeignKey("project_content_type", "project_id")
    JSON_DATA_FIELDS = [
        "subject",
        "to_email",
        "from_email",
        "html_body",
        "txt_body",
        "completed",
        "sent_count",
        "failed_count",
    ]

    class Meta:
        verbose_name = _("Email")
        verbose_name_plural = _("Emails")
        db_table = "nets_core_custom_email"
        indexes = [
            models.Index(
                fields=["project_content_type", "project_id"], name="custom_email_index"
            )
        ]

    def __str__(self):
        return self.subject


class EmailNotification(NetsCoreBaseModel):
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
    custom_email = models.ForeignKey(CustomEmail, null=True, on_delete=models.CASCADE)
    project_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    project_id = models.PositiveIntegerField(null=True, blank=True)
    project = GenericForeignKey("project_content_type", "project_id")
    JSON_DATA_FIELDS = [
        "subject",
        "to",
        "from_email",
        "body",
        "txt_body",
        "sent",
        "tries",
        "sent_at",
        "created",
        "updated",
        "custom_email_id",
    ]

    def __str__(self):
        if self.project:
            return "%s %s %s" % (self.to, self.subject, self.project)

        return "%s %s" % (self.to, self.subject)

    class Meta:
        verbose_name = _("Email Notification")
        verbose_name_plural = _("Email Notifications")
        db_table = "nets_core_email_notification"
        indexes = [
            models.Index(
                fields=["project_content_type", "project_id"],
                name="email_notification_index",
            )
        ]


class UserDevice(OwnedModel):
    uuid = models.UUIDField(_("UUID"), default=uuid4, editable=False, unique=True)
    name = models.CharField(_("Name"), max_length=250)
    os = models.CharField(_("OS"), max_length=250, null=True, blank=True)
    os_version = models.CharField(
        _("OS Version"), max_length=250, null=True, blank=True
    )
    app_version = models.CharField(
        _("App Version"), max_length=250, null=True, blank=True
    )
    device_type = models.CharField(
        _("Device Type"), max_length=250, null=True, blank=True
    )
    device_token = models.CharField(
        _("Device Token"), max_length=250, null=True, blank=True
    )
    firebase_token = models.CharField(
        _("Firebase Token"), max_length=250, null=True, blank=True
    )
    active = models.BooleanField(_("Active"), default=True)
    last_login = models.DateTimeField(_("Last login"), null=True)
    ip = models.CharField(_("IP"), max_length=250, null=True, blank=True)
    JSON_DATA_FIELDS = [
        "uuid",
        "user_id",
        "name",
        "os",
        "os_version",
        "app_version",
        "device_type",
        "active",
        "last_login",
        "ip",
    ]
    PROTECTED_FIELDS = ["device_token", "firebase_token"]

    class Meta:
        verbose_name = _("User Device")
        verbose_name_plural = _("User Devices")
        db_table = "nets_core_user_device"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):

        super(UserDevice, self).save(*args, **kwargs)


class UserFirebaseNotification(OwnedModel):
    message = models.TextField(_("Message"), null=True, blank=True)
    devices = models.ManyToManyField(UserDevice, related_name="notifications")
    data = models.JSONField(_("Data"), null=True, blank=True)
    sent = models.BooleanField(_("Sent"), default=False)
    message_id = models.CharField(
        _("Message ID"), max_length=250, null=True, blank=True
    )
    error = models.TextField(_("Error"), null=True, blank=True)
    device = models.ForeignKey(UserDevice, on_delete=models.CASCADE)

    JSON_DATA_FIELDS = [
        "message",
        "data",
        "sent",
        "message_id",
        "error",
        "device_id",
        "user_id",
    ]
    
    class Meta:
        verbose_name = _("User Firebase Notification")
        verbose_name_plural = _("User Firebase Notifications")
        db_table = "nets_core_firebase_notification"

    def __str__(self):
        return self.message_id
