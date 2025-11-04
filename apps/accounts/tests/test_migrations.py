from django.apps import apps
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.questioner import NonInteractiveMigrationQuestioner
from django.db.migrations.state import ProjectState
from django.test import override_settings
from django.test import TestCase


class MigrationsTestCase(TestCase):
    @override_settings(MIGRATION_MODULES={})
    def test_no_migration_conflicts(self):
        loader = MigrationLoader(None, ignore_no_migrations=True)
        self.assertEqual({}, loader.detect_conflicts())

    @override_settings(MIGRATION_MODULES={})
    def test_no_missing_migrations(self):
        loader = MigrationLoader(None, ignore_no_migrations=True)
        autodetector = MigrationAutodetector(
            loader.project_state(),
            ProjectState.from_apps(apps),
            NonInteractiveMigrationQuestioner(),
        )
        self.assertEqual({}, autodetector.changes(graph=loader.graph))
