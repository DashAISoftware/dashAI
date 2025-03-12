from pipeline import Pipeline

class PipelineJob:
    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline
        self.status = 'queued'

    def start(self):
        self.status = 'in_progress'
        try:
            self.pipeline.run()
            self.status = 'completed'
        except Exception as e:
            self.status = 'failed'
            print(f"Error during pipeline execution: {e}")

