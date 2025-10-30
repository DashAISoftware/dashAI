import logging

from kink import inject

from DashAI.back.job.base_job import BaseJob
from DashAI.back.plugins.utils import (
    get_available_plugins,
    register_plugin_components,
    unregister_plugin_components,
)

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class SyncComponentsJob(BaseJob):
    DESCRIPTION = "Sync consumer ComponentRegistry with installed DashAI plugins"

    def set_status_as_delivered(self):
        log.debug("Prediction job marked as delivered")

    def set_status_as_error(self):
        log.debug("Sync components job failed")

    @inject
    def get_job_name(self):
        return "Adding/removing plugins"

    @inject
    def run(self):
        from kink import di

        component_registry = di["component_registry"]
        available = set(get_available_plugins())
        registered = set(
            component_registry[comp]["class"]
            for comp in [
                c["name"] for c in component_registry.get_components_by_types()
            ]
        )
        to_add = list(available - registered)
        to_remove = list(registered - available)
        if to_add:
            register_plugin_components(to_add, component_registry)
        if to_remove:
            unregister_plugin_components(to_remove, component_registry)

        return {
            "added": [cls.__name__ for cls in to_add],
            "removed": [cls.__name__ for cls in to_remove],
        }
