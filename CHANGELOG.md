# Changelog

## Unreleased

### Added
- Opt-in `NETS_CORE_UPDATED_FIELDS_MODE`: `full` retains the legacy default,
  `last` keeps one change per field, and `off` avoids automatic tracking and
  its previous-row SELECT. No column is removed and existing history is kept
  unless explicitly pruned.
- `nets_core_prune_updated_fields`: dry-run by default, model/database selection,
  keyset batches, retention by count/age, JSON-size estimates, explicit apply
  and backup acknowledgement. Never creates a backup or runs VACUUM.
- PostgreSQL regression tests for history compatibility/retention and a scoped
  Python/Django CI workflow. These tests do not cover every public API/backend.
- Multi-database backend layer for `to_json` serialization (`nets_core.backends`).
  - `PythonBackend` — universal baseline via Django ORM attribute access, works on every DB engine.
  - `PostgreSQLBackend` — wraps existing stored procedures; auto-falls back to Python if not yet installed.
  - `MySQLBackend` — inline `JSON_OBJECT` expressions; auto-falls back to Python for nested relations or when JSON functions are unavailable.
  - `SQLiteBackend` — inline `json_object` expressions (JSON1); auto-falls back to Python.
  - `get_backend(using)` selector, controlled by `NETS_CORE_TO_JSON_BACKEND` (`"auto"` | `"python"` | `"sql"` | custom dotted path).
- `parse_field_spec()` utility to parse the `nets_core` nested field spec format (`field_id:[table;f1;f2]`) in a single place.
- `request_handler` now supports declarative route metadata: `path` (and alias `url`) plus optional `name`.
- New route builder `nets_core.routing.build_urlpatterns(...)` to auto-generate Django `urlpatterns` from decorated views.
- New docs helper `nets_core.routing.build_route_registry(...)` to expose normalized endpoint metadata.
- New OpenAPI helper `nets_core.routing.build_openapi_paths(...)` to auto-generate OpenAPI `paths` entries.
- Built-in public endpoint `GET /openapi.json` backed by `nets_core.openapi_views`.
- Optional HTTP method guard in `request_handler` via `method` or `methods`.

### Changed
- `nets_core.serializers` refactored: both `NetsCoreModelToJson` and `NetsCoreQuerySetToJson` now delegate to the backend layer instead of calling PostgreSQL procedures directly.
- Fixed bug in `NetsCoreQuerySetToJson` where protected-field filtering was silently discarded and the unfiltered fields were serialized.
- `nets_core.auth_urls` now builds endpoints from decorated view metadata instead of manual `path(...)` declarations.
- Built-in auth and social endpoints now declare allowed HTTP methods explicitly. Unsupported methods return `405` and include the `Allow` header.
- README and usage guide now document declarative routes, method guards, route registry, and OpenAPI generation.
- Added optional OpenAPI settings: `NETS_CORE_OPENAPI_TITLE`, `NETS_CORE_OPENAPI_VERSION`, `NETS_CORE_OPENAPI_DESCRIPTION`, `NETS_CORE_OPENAPI_TAGS`, `NETS_CORE_OPENAPI_MODULES`.
- `NetsCoreBaseModel.to_json()` and `NetsCoreBaseManager.to_json()` now accept an optional `mode` keyword argument (ignored) to avoid `TypeError` when callers pass `mode="json"`/`mode="python"` as with pydantic-style serializers.
