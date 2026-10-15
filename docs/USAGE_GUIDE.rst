Usage Guide
===========

This guide complements README.rst with implementation details and architecture-level guidance.

Architecture Overview
---------------------

NETS CORE is composed of six major layers:

- HTTP layer: views, auth_urls, request parsing.
- Validation layer: RequestParam and request_handler.
- Security layer: OTP verification + OAuth2 token minting.
- Data layer: base models and authorization entities.
- Messaging layer: email and push notifications.
- Operational layer: settings bootstrap and signal listeners.

Auth Flow Patterns
------------------

OTP Flow
^^^^^^^^

1. Client calls /login/ with identity and device payload.
2. VerificationCode is created and hashed token is stored.
3. Token is delivered by listener-triggered email template.
4. Client calls /authenticate/ with code + OAuth client credentials.
5. NETS CORE validates code/device/client and returns OAuth2 tokens.

Social Flow
^^^^^^^^^^^

1. Client obtains provider token externally (Google/Apple/Facebook/Microsoft/GitHub).
2. Client calls social endpoint with provider token + OAuth client credentials.
3. NETS CORE validates provider token/profile and upserts local user.
4. NETS CORE mints internal OAuth2 access/refresh token pair.

Design Principles
-----------------

- Validation at boundary: reject malformed payloads early.
- Explicit auth context: all issued app tokens map to oauth2_provider Application.
- Least surprise responses: standardized success/error envelope.
- Safe defaults for development: debug verification code behavior is configurable.
- Optional model-change history: updated_fields is not an immutable audit log.

Updated Fields Retention (Unreleased)
------------------------------------

The source tree supports ``NETS_CORE_UPDATED_FIELDS_MODE`` with these values:

- ``"full"`` (default): preserve the existing per-field lists of changes.
- ``"last"``: keep only the last change per field when saving an existing row.
- ``"off"``: skip automatic history tracking and the previous-row SELECT.
	Existing history is not erased. Use a separate protected audit trail when
	accountability is required.

The JSON column remains on the abstract model. These options are not available
in releases preceding this change. No release, change of default, automatic
data migration or column removal is performed by enabling the source option.
The existing ``save(update_fields=...)`` persistence semantics are unchanged;
include ``updated_fields`` explicitly when persisting history in a partial save.

Preview historical retention before writing:

.. code-block:: sh

		python manage.py nets_core_prune_updated_fields --model myapp.MyModel --keep-last 1 --dry-run

After taking and testing a database backup, explicitly acknowledge it:

.. code-block:: sh

		python manage.py nets_core_prune_updated_fields --model myapp.MyModel --keep-last 1 --apply --confirm-backup

``--model`` may be repeated; without it all managed concrete subclasses are
considered. ``--database`` selects a Django alias and ``--batch-size`` bounds
each transaction (1..10000). ``--keep-last 0`` can remove all eligible history.
``--older-than DAYS`` only removes entries older than the cutoff, preserving
the newest N entries per field and recent/unparseable/ambiguous timestamps.

Reports contain counts and an estimated JSON byte reduction, not recovered
physical database space or original field values. Invalid structures stop the
command; earlier applied batches may already be committed. Row locks protect
each applied batch, not a global snapshot. Review a fresh dry-run first.

The command neither creates backups nor runs VACUUM. A Git checkpoint protects
code, not deleted history. Rollback of pruned data requires restoring a backup;
changing the mode back to ``"full"`` does not reconstruct removed entries.
Schedule PostgreSQL maintenance separately: ordinary VACUUM can reuse space,
while VACUUM FULL rewrites/locks tables and requires explicit operational planning.
Other database engines need their own maintenance procedure. Do not use this
history field as evidence of tamper-resistant auditing or regulatory compliance.

request_handler Best Practices
------------------------------

- Keep endpoint-level params explicit with RequestParam.
- Use can_do for intent-level permissions (for example myapp.can_delete_order).
- Use perm_required=True on sensitive operations that should never fallback to owner-only rules.
- Use project_required=True in multi-tenant/project-scoped endpoints.

Auto Documentation and OpenAPI
------------------------------

You can declare endpoint route metadata directly in request_handler and reuse it
for URL wiring, docs pages, and OpenAPI generation.

Example:

.. code-block:: python

	from django.http import JsonResponse
	from django.urls import path
	from nets_core.decorators import request_handler
	from nets_core.routing import build_openapi_paths, build_route_registry, build_urlpatterns

	@request_handler(path="health/", name="health", methods=["GET"], public=True)
	def health(request):
		return JsonResponse({"res": 1, "data": "ok"})

	urlpatterns = [
		*build_urlpatterns("myapp.views"),
	]

	route_registry = build_route_registry("myapp.views")
	openapi_paths = build_openapi_paths("myapp.views", tags=["infra"])

Recommended approach:

- Keep methods explicit on every endpoint.
- Use build_route_registry to generate internal docs pages/tables.
- Use build_openapi_paths to populate the paths section in your OpenAPI schema pipeline.

Built-in schema endpoint:

- If you include nets_core.auth_urls, NETS CORE now exposes GET /openapi.json.
- The response is generated from request_handler route metadata.
- You can customize title/version/tags/modules with NETS_CORE_OPENAPI_* settings.

Model Serialization Notes
-------------------------

NetsCoreBaseModel and its manager expose to_json methods. For predictable output:

- Define JSON_DATA_FIELDS in your models.
- Keep PROTECTED_FIELDS updated to avoid accidental leakage.
- Prefer explicit field tuples over __all__ in public APIs.

Role and Permission Strategy
----------------------------

Recommended production strategy:

- Keep global permissions for cross-project capabilities.
- Use UserRole with project-scoped Role entries for tenant isolation.
- Gate write operations with can_do checks.
- Keep role names stable and lowercase for consistency.

Email Delivery Strategy
-----------------------

- Use queued mode for high-volume/non-urgent emails.
- Use immediate mode for auth/security-critical messages.
- Configure exclusion domains in staging/test environments.
- Define NETS_CORE_EMAIL_FOOTER or NETS_CORE_EMAIL_FOOTER_TEMPLATE for brand control.

Push Notification Strategy
--------------------------

- Store firebase token per UserDevice.
- Filter inactive devices from fan-out logic.
- Remove unregistered tokens when Firebase reports invalid registration.

Security and Compliance Checklist
---------------------------------

- Use HTTPS everywhere.
- Rotate OAuth client secrets periodically.
- Restrict CORS origins in production.
- Protect service credentials (Firebase, SMTP, OAuth secrets) with secret management.
- Set secure session and CSRF settings according to deployment architecture.

Production Readiness Checklist
------------------------------

- Configure cache backend (Redis/Memcached) for verification code performance.
- Configure Celery broker and worker autoscaling.
- Verify email backend deliverability and SPF/DKIM/DMARC.
- Enable structured logging and monitoring.
- Run migration checks and backup strategy validation.

Extending NETS CORE
-------------------

Typical extension points:

- Add provider-specific auth validators in social_auth.
- Add domain-specific permissions using Permission + RolePermission.
- Add custom notification channels via tasks and provider SDKs.
- Wrap request_handler in project-local decorators for common policy defaults.

Migration from Legacy Google Endpoint
-------------------------------------

- Keep existing clients on /loginWithGoogle/ until rollout is complete.
- Migrate new clients to /loginWithGoogleSocial/.
- Once all clients are migrated, deprecate legacy endpoint with API versioning policy.
