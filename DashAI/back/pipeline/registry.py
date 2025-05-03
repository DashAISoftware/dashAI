from typing import Any, Dict, List, Union
from DashAI.back.dependencies.registry.relationship_manager import RelationshipManager

class ComponentRegistry:
    def __init__(self) -> None:
        # _registry maps component_key -> component_dict
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._relationship_manager = RelationshipManager()

    def register(self, component_key: str, component_class: Any) -> None:
        component = {
            "name": component_key,
            "class": component_class,
        }
        if component_key not in self._registry:
            self._registry[component_key] = []
        self._registry[component_key].append(component)

    def __contains__(self, component_key: str) -> bool:
        return component_key in self._registry

    def __getitem__(self, component_key: str) -> Dict[str, Any]:
        try:
            return self._registry[component_key]
        except KeyError:
            raise KeyError(f"Component '{component_key}' not found in registry.")

    def get_components_by_types(
        self,
        select: Union[str, List[str], None] = None,
        ignore: Union[str, List[str], None] = None,
    ) -> List[Dict[str, Any]]:
        if select is not None and ignore is not None:
            raise ValueError("Only select or ignore can be provided, not both at the same time.")

        all_components = list(self._registry.values())
        if select is None and ignore is None:
            return all_components

        if select is not None:
            keys = [select] if isinstance(select, str) else select
            result: List[Dict[str, Any]] = []
            for key in keys:
                if key not in self._registry:
                    raise ValueError(f"Component type '{key}' does not exist in registry.")
                result.append(self._registry[key])
            return result

        ignore_keys = [ignore] if isinstance(ignore, str) else ignore
        return [comp for k, comp in self._registry.items() if k not in ignore_keys]

    def get_related_components(self, component_id: str) -> List[Dict[str, Any]]:
        if component_id not in self:
            raise KeyError(f"Component '{component_id}' does not exist in registry.")

        related = self._relationship_manager[component_id]
        return [self._registry[rel_id] for rel_id in related]

component_registry = ComponentRegistry()
