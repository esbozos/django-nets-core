import json
from io import StringIO

from django.core.exceptions import ImproperlyConfigured
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from nets_core.history import prune_history

from .models import HistoryRecord, PlainRecord


class LegacyHistoryTests(TestCase):
    def test_default_appends_and_preserves_public_shape(self):
        record = HistoryRecord.objects.create(name="first")
        self.assertEqual(record.updated_fields, {})
        record.name = "second"
        with self.assertNumQueries(2):
            record.save()
        record.name = "third"
        record.save()
        record.refresh_from_db()
        changes = record.updated_fields["name"]
        self.assertEqual(
            [(item["old"], item["new"]) for item in changes],
            [("first", "second"), ("second", "third")],
        )
        self.assertTrue(all(isinstance(item["time"], str) for item in changes))

    def test_sensitive_fields_are_not_recorded(self):
        record = HistoryRecord.objects.create(name="first")
        record.password = "synthetic-password"
        record.token = "synthetic-token"
        record.save()
        record.refresh_from_db()
        self.assertEqual(record.updated_fields, {})

    def test_plain_models_do_not_query_history(self):
        record = PlainRecord.objects.create(name="first")
        record.name = "second"
        with self.assertNumQueries(1):
            record.save()


class RetentionTests(TestCase):
    def test_nullable_legacy_history_is_initialized(self):
        record = HistoryRecord.objects.create(name="first", updated_fields=None)
        record.name = "second"
        record.save()
        record.refresh_from_db()
        self.assertEqual(record.updated_fields["name"][0]["new"], "second")

    @override_settings(NETS_CORE_UPDATED_FIELDS_MODE="last")
    def test_partial_save_persists_history_when_explicitly_included(self):
        record = HistoryRecord.objects.create(name="first")
        record.name = "second"
        record.save(update_fields=["name", "updated_fields"])
        record.refresh_from_db()
        self.assertEqual(record.updated_fields["name"][0]["new"], "second")

    @override_settings(NETS_CORE_UPDATED_FIELDS_MODE="last")
    def test_raw_fixture_save_does_not_read_or_modify_history(self):
        record = HistoryRecord.objects.create(name="first")
        record.name = "fixture"
        with self.assertNumQueries(1):
            record.save_base(raw=True, force_update=True)
        record.refresh_from_db()
        self.assertEqual(record.updated_fields, {})

    @override_settings(NETS_CORE_UPDATED_FIELDS_MODE="off")
    def test_off_avoids_select_and_preserves_existing_history(self):
        history = {
            "name": [
                {"old": "before", "new": "first", "time": "2026-01-01T00:00:00+00:00"}
            ]
        }
        record = HistoryRecord.objects.create(name="first", updated_fields=history)
        record.name = "second"
        with self.assertNumQueries(1):
            record.save()
        record.refresh_from_db()
        self.assertEqual(record.updated_fields, history)

    @override_settings(NETS_CORE_UPDATED_FIELDS_MODE="last")
    def test_last_bounds_changed_and_unchanged_field_history(self):
        record = HistoryRecord.objects.create(
            name="first",
            updated_fields={
                "other": [{"old": "0", "new": "1"}, {"old": "1", "new": "2"}]
            },
        )
        for name in ("second", "third"):
            record.name = name
            record.save()
        record.refresh_from_db()
        self.assertEqual(
            [(item["old"], item["new"]) for item in record.updated_fields["name"]],
            [("second", "third")],
        )
        self.assertEqual(len(record.updated_fields["other"]), 1)

    @override_settings(NETS_CORE_UPDATED_FIELDS_MODE="invalid")
    def test_invalid_mode_is_rejected(self):
        record = HistoryRecord.objects.create(name="first")
        record.name = "second"
        with self.assertRaises(ImproperlyConfigured), self.assertNumQueries(0):
            record.save()

    def test_prune_defaults_to_dry_run_and_requires_backup_acknowledgement(self):
        history = {
            "name": [
                {"old": "0", "new": "1"},
                {"old": "1", "new": "2"},
                {"old": "2", "new": "3"},
            ]
        }
        record = HistoryRecord.objects.create(name="third", updated_fields=history)
        output = StringIO()
        warning = StringIO()
        call_command(
            "nets_core_prune_updated_fields",
            model=["nets_core_tests.HistoryRecord"],
            stdout=output,
            stderr=warning,
        )
        report = json.loads(output.getvalue())
        self.assertTrue(report["dry_run"])
        self.assertEqual(report["changes_removed"], 2)
        self.assertIn("BACKUP REQUIRED", warning.getvalue())
        record.refresh_from_db()
        self.assertEqual(record.updated_fields, history)
        with self.assertRaises(CommandError):
            call_command(
                "nets_core_prune_updated_fields", apply=True, stderr=StringIO()
            )
        previous_updated = record.updated
        call_command(
            "nets_core_prune_updated_fields",
            model=["nets_core_tests.HistoryRecord"],
            apply=True,
            confirm_backup=True,
            batch_size=1,
            stdout=StringIO(),
            stderr=StringIO(),
        )
        record.refresh_from_db()
        self.assertEqual(len(record.updated_fields["name"]), 1)
        self.assertEqual(record.updated, previous_updated)

    def test_date_retention_preserves_recent_and_unparseable_changes(self):
        from datetime import datetime, timezone

        old = {"time": "2020-01-01T00:00:00+00:00"}
        recent = {"time": "2026-10-01T00:00:00+00:00"}
        unknown = {"time": "unknown"}
        history = {"name": [old, recent, unknown, old]}
        retained, removed = prune_history(
            history, 1, datetime(2026, 1, 1, tzinfo=timezone.utc)
        )
        self.assertEqual(retained["name"], [recent, unknown, old])
        self.assertEqual(removed, 1)
        self.assertEqual(prune_history(history, 0)[0], {})

    def test_command_rejects_invalid_options_and_untracked_models(self):
        for values in (
            {"keep_last": -1},
            {"older_than": -1},
            {"older_than": 1000000000},
            {"batch_size": 0},
            {"model": ["nets_core_tests.PlainRecord"]},
            {"model": ["missing.Model"]},
        ):
            with self.assertRaises(CommandError):
                call_command(
                    "nets_core_prune_updated_fields", stderr=StringIO(), **values
                )
