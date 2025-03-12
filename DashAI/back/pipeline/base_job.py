class BaseTask:
    def __init__(self, id, config):
        self.id = id
        self.config = config

    def execute(self, input_data):
        raise NotImplementedError("Each task must implement its own execute method.")