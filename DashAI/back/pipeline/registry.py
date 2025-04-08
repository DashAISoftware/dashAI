from typing import Any, Dict

class ComponentRegistry:
    def __init__(self) -> None:
        self.registry: Dict[str, Dict[str, Any]] = {}

    def register(self, component_type: str, component_class: Any) -> None:
        self.registry[component_type] = {
            "class": component_class,
        }

    def __getitem__(self, component_type: str) -> Dict[str, Any]:
        return self.registry[component_type]

component_registry = ComponentRegistry()
