class BaseTask:
    def __init__(self, id, config):
        self.id = id
        self.config = config

    def execute(self, input_data):
        raise NotImplementedError("Each task must implement its own execute method.")
    
class DataExploration(BaseTask):
    def execute(self, input_data):
        print(f"[{self.id}] Explorando datos con opciones {self.config['options']}")

        print("holaaa", input_data)
        if "Distribution Plots" in self.config["options"]:
            self.plot_distribution(input_data)

        return {"exploration": f"Exploración basada en {input_data['data']}"}
    
    def plot_distribution(self, input_data):
        print(f"[{self.id}] Generando gráficos de distribución")
        pass