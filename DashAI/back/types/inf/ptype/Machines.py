# flake8: noqa

import DashAI.back.types.inf.ptype.Machine as Machine

MACHINES = {
    "integer": Machine.Integers(),
    "string": Machine.Strings(),
    "float": Machine.Floats(),
    "boolean": Machine.Booleans(),
    "gender": Machine.Genders(),
    "date-iso-8601": Machine.DateISO_8601(),
    "date-eu": Machine.Date_EU(),
    "date-non-std-subtype": Machine.SubTypeNonstdDate(),
    "date-non-std": Machine.Nonstd_Date(),
    "IPAddress": Machine.IPAddress(),
    "EmailAddress": Machine.EmailAddress(),
}


class Machines:
    def __init__(self, types, all_machines=None):
        self.types = types
        if all_machines is None:
            all_machines = MACHINES
        self.forType = {t: all_machines[t] for t in types}
        self.anomalous = Machine.Anomaly()
        self.missing = Machine.Missing()
        self.normalize_params()

    @property
    def machines(self):
        return [self.missing, self.anomalous] + [self.forType[t] for t in self.forType]

    def machine_probabilities(self, col):
        return {v: [m.probability(str(v)) for m in self.machines] for v in col}

    def set_unique_values(self, unique_values):
        for machine in self.machines:
            machine.set_unique_values(unique_values)

    def remove_unique_values(
        self,
    ):
        for machine in self.machines:
            machine.supported_words = {}

    def update_values(self, unique_values):
        self.remove_unique_values()
        self.set_unique_values(unique_values)

    def normalize_params(self):
        for machine in self.forType.values():
            machine.normalize_params()

    def initialize_uniformly(self):
        for machine in self.forType.values():
            machine.initialize_uniformly()

    def set_all_probabilities_z(self, w_j_z):
        counter = 0
        for machine in self.forType.values():
            counter = machine.set_probabilities_z(counter, w_j_z)

    def get_all_parameters_z(self):
        return [
            p for machine in self.forType.values() for p in machine.get_parameters_z()
        ]
