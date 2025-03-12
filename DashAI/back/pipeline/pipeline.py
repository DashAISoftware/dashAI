from tasks.task_node import ModelTrainingTask, TaskSelector
from exploration.dataexploration_node import DataExploration
from base_job import BaseTask

class Pipeline:
    def __init__(self, name, steps):
        self.name = name
        self.steps = steps
        self.status = "idle"

    def run(self):
        self.status = "running"
        print(f"Ejecutando pipeline: {self.name}")
        
        data = None
        try:
            for step in self.steps:
                data = step.execute(data)
            self.status = "completed"
            print("Pipeline completado.")
            return data
        except Exception as e:
            self.status = "failed"
            print(f"Error en el pipeline: {e}")
            return None
        
class DataLoader(BaseTask):
    def execute(self, input_data=None):
        print(f"[{self.id}] Cargando datos desde {self.config['filePath']}")
        return {"data": f"Datos de {self.config['filePath']}"}

if __name__ == "__main__":
    steps = [
        DataLoader("DataLoader-0", {"filePath": "data.csv"}),
        DataExploration("DataExploration-1", {"options": ["Distribution Plots", "Outlier Detection"]}),
        TaskSelector("TaskSelector-2", {"task": "clustering"})
    ]

    pipeline = Pipeline("My Pipeline", steps)
    resultado = pipeline.run()
    print("Resultado final:", resultado)
