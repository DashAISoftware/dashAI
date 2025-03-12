class BaseTask:
    def __init__(self, id, config):
        self.id = id
        self.config = config

    def execute(self, input_data):
        raise NotImplementedError("Each task must implement its own execute method.")

class ModelTrainingTask:
    def __init__(self, model, data):
        self.model = model
        self.data = data

    def execute(self):
        print(f"Training model {self.model} with data {self.data}")
        # Aquí iría el código para entrenar el modelo

class TaskSelector(BaseTask):
    def execute(self, input_data):
        print(f"[{self.id}] Seleccionando tarea {self.config['task']}")
        return {"task": f"Tarea seleccionada: {self.config['task']}"}