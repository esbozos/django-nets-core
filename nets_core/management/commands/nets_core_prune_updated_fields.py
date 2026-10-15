import json
from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from nets_core.history import prune_history
from nets_core.models import NetsCoreBaseModel


class Command(BaseCommand):
    help = "Preview or explicitly apply bounded updated_fields history retention."

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--dry-run", action="store_true")
        mode.add_argument("--apply", action="store_true")
        parser.add_argument("--confirm-backup", action="store_true")
        parser.add_argument("--keep-last", type=int, default=1)
        parser.add_argument("--older-than", type=int)
        parser.add_argument("--model", action="append")
        parser.add_argument("--batch-size", type=int, default=500)
        parser.add_argument(
            "--database", default="default", choices=list(settings.DATABASES)
        )

    def handle(self, *args, **options):
        keep = options["keep_last"]
        days = options["older_than"]
        size = options["batch_size"]
        applying = options["apply"]
        if keep < 0 or (days is not None and days < 0) or not 1 <= size <= 10000:
            raise CommandError("Nonnegative retention and batch size 1..10000 required")
        self.stderr.write(
            "BACKUP REQUIRED before applying. Review dry-run; changes commit per batch. Rollback requires restoring your backup. No backup or VACUUM is performed by this command."
        )
        if applying and not options["confirm_backup"]:
            raise CommandError(
                "--apply requires --confirm-backup after verifying a restorable backup"
            )
        if options["model"]:
            try:
                models = [apps.get_model(label) for label in options["model"]]
            except (LookupError, ValueError) as error:
                raise CommandError("Unknown model label") from error
        else:
            models = list(apps.get_models())
        selected = []
        for model in models:
            valid = (
                issubclass(model, NetsCoreBaseModel)
                and model._meta.managed
                and not model._meta.proxy
            )
            if not valid:
                if options["model"]:
                    raise CommandError("Select a managed concrete NetsCoreBaseModel")
                continue
            if model not in selected:
                selected.append(model)
        try:
            cutoff = timezone.now() - timedelta(days=days) if days is not None else None
        except OverflowError as error:
            raise CommandError(
                "Retention date is outside the supported range"
            ) from error
        summary = {
            "dry_run": not applying,
            "database": options["database"],
            "rows_scanned": 0,
            "rows_changed": 0,
            "changes_removed": 0,
            "estimated_json_bytes_saved": 0,
            "models": [],
        }
        alias = options["database"]
        for model in selected:
            last_pk = None
            summary["models"].append(model._meta.label)
            while True:
                with transaction.atomic(using=alias):
                    query = (
                        model._base_manager.using(alias)
                        .order_by("pk")
                        .only("pk", "updated_fields")
                    )
                    if last_pk is not None:
                        query = query.filter(pk__gt=last_pk)
                    if applying:
                        query = query.select_for_update()
                    rows = list(query[:size])
                    if not rows:
                        break
                    for row in rows:
                        summary["rows_scanned"] += 1
                        try:
                            retained, removed = prune_history(
                                row.updated_fields, keep, cutoff
                            )
                        except ValueError as error:
                            raise CommandError(
                                f"Invalid history in {model._meta.label} pk={row.pk}; earlier batches may already be committed"
                            ) from error
                        if retained != row.updated_fields:
                            summary["rows_changed"] += 1
                            summary["changes_removed"] += removed
                            summary["estimated_json_bytes_saved"] += len(
                                json.dumps(
                                    row.updated_fields, ensure_ascii=False
                                ).encode()
                            ) - len(json.dumps(retained, ensure_ascii=False).encode())
                            if applying:
                                model._base_manager.using(alias).filter(
                                    pk=row.pk
                                ).update(updated_fields=retained)
                    last_pk = rows[-1].pk
        self.stdout.write(json.dumps(summary, sort_keys=True))
