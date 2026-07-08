"""Events services package.

Import services from their submodules directly (e.g.
``from apps.events.services.event_service import EventService``). This package
deliberately avoids eager re-exports: ``event_service`` imports ``events.tasks``,
so re-exporting it here would make importing any sibling submodule (e.g. the
analytics singleton from a Celery task) pull in a tasks ↔ service import cycle.
"""
