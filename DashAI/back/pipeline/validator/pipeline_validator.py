from typing import Dict, List

from DashAI.back.pipeline.validator.nodes_definitions import NODE_TYPES


class PipelineValidator:
    def __init__(self, nodes: List[Dict], edges: List[Dict]):
        self.nodes = nodes
        self.edges = edges
        self.errors: Dict[str, List[str]] = {}
        self.node_map = {n["id"]: n for n in nodes}

        self.type_to_rule = {
            nt["type"]: {
                "predecessors": set(nt.get("predecessors", [])),
                "successors": set(nt.get("successors", [])),
                "max_outputs": nt.get("maxOutputs"),
            }
            for nt in NODE_TYPES
        }
        self.type_to_name = {nt["type"]: nt["name"] for nt in NODE_TYPES}

    def validate(self) -> Dict[str, List[str]]:
        self._validate_structure()
        return self.errors

    def _get_node_display_name(self, node: Dict) -> str:
        node_type = node["type"]
        return node["data"].get("name", self.type_to_name.get(node_type, node_type))

    def _get_type_display_name(self, node_type: str) -> str:
        return self.type_to_name.get(node_type, node_type)

    def _validate_structure(self):
        for node in self.nodes:
            node_id = node["id"]
            node_type = node["type"]
            node_name = self._get_node_display_name(node)
            rule = self.type_to_rule.get(node_type)
            if not rule:
                continue

            expected_predecessors = rule["predecessors"]
            predecessors = [e for e in self.edges if e["target"] == node_id]

            if len(predecessors) > 1:
                self.errors.setdefault(node_id, []).append(
                    f"{node_name} cannot have more than one input."
                )

            predecessor_types = [
                self.node_map[e["source"]]["type"]
                for e in predecessors
                if e["source"] in self.node_map
            ]

            if expected_predecessors and not expected_predecessors.intersection(
                predecessor_types
            ):
                expected_names = [
                    self._get_type_display_name(t) for t in expected_predecessors
                ]
                expected_str = " or ".join(expected_names)
                self.errors.setdefault(node_id, []).append(
                    f"{node_name} must be connected to {expected_str} node."
                )

            if not expected_predecessors and predecessors:
                self.errors.setdefault(node_id, []).append(
                    f"{node_name} should not have any inputs."
                )

            if not rule["successors"]:
                successors = [e for e in self.edges if e["source"] == node_id]
                if successors:
                    self.errors.setdefault(node_id, []).append(
                        f"{node_name} should not have any outputs."
                    )

            max_outputs = rule.get("max_outputs")
            if max_outputs is not None:
                outgoing_edges = [e for e in self.edges if e["source"] == node_id]
                if len(outgoing_edges) > max_outputs:
                    self.errors.setdefault(node_id, []).append(
                        f"{node_name} supports up to {max_outputs} outputs."
                    )
