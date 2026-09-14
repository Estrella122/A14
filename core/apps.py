from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        import logging
        from .skills.registry import get_registry
        registry = get_registry()
        logging.getLogger(__name__).info("Skill manifests: loaded=%s legacy_documents=%s registered=%s invalid=%s duplicate=%s dependency_errors=%s",
            registry.stats.get("loaded_skills", 0), len(registry.stats.get("legacy_documents", [])),
            len(registry.list()), registry.stats.get("invalid_skills", []),
            registry.stats.get("duplicate_skills", []), registry.stats.get("dependency_errors", []))
