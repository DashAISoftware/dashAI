from typing import List, Dict

NODE_RULES = {
    "DataSelector": {
        "predecessors": set(),
        "successors": {"DataExploration", "Train"},
    },
    "DataExploration": {
        "predecessors": {"DataSelector"},
        "successors": set(),
    },
    "Train": {
        "predecessors": {"DataSelector"},
        "successors": {"Prediction"},
    },
    "Prediction": {
        "predecessors": {"Train"},
        "successors": set(),
    },
}

class PipelineValidator:
    def __init__(self, nodes: List[Dict], edges: List[Dict]):
        self.nodes = nodes
        self.edges = edges
        self.errors: Dict[str, List[str]] = {}
        self.node_map = {n["id"]: n for n in nodes}
        self.duplicated_ids = set()

    def validate(self) -> Dict[str, List[str]]:
        self._validate_duplicates()
        self._validate_structure()
        return self.errors

    def _validate_duplicates(self):
        type_to_ids = {}
        for node in self.nodes:
            node_type = node["type"]
            node_name = node["data"].get("name", node_type)
            type_to_ids.setdefault(node_type, []).append((node["id"], node_name))

        for t, ids in type_to_ids.items():
            sorted_ids = sorted(ids)
            for id, name in sorted_ids[1:]:
                self.duplicated_ids.add(id)
                self.errors.setdefault(id, []).append(f"{name} already exists.")

    def _validate_structure(self):
        for node in self.nodes:
            node_id = node["id"]
            if node_id in self.duplicated_ids:
                continue

            node_type = node["type"]
            node_name = node["data"].get("name", node_type)
            rule = NODE_RULES.get(node_type)
            if not rule:
                continue

            expected_predecessors = rule["predecessors"]

            predecessors = [e for e in self.edges if e["target"] == node_id]
            predecessor_types = [
                self.node_map[e["source"]]["type"]
                for e in predecessors
                if e["source"] in self.node_map
            ]

            if expected_predecessors:
                if not all(req in predecessor_types for req in expected_predecessors):
                    expected_names = []
                    for expected_type in sorted(expected_predecessors):
                        nodes_of_type = [
                            n["data"].get("name", expected_type)
                            for n in self.nodes
                            if n["type"] == expected_type
                        ]
                        if nodes_of_type:
                            expected_names.append("/".join(nodes_of_type))
                        else:
                            expected_names.append(expected_type)

                    expected_str = ", ".join(expected_names)
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
