from transformers import TrainerCallback

from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset


class MetricsCallback(TrainerCallback):
    def __init__(self, model_instance, x_train, y_train, x_val, y_val, total_epochs):
        self.model_instance = model_instance
        self.x_train = to_dashai_dataset(x_train)
        self.y_train = to_dashai_dataset(y_train)
        self.x_val = to_dashai_dataset(x_val)
        self.y_val = to_dashai_dataset(y_val)
        self.total_epochs = total_epochs
        self.current_epoch = 0

    def on_epoch_end(self, args, state, control, **kwargs):
        self.current_epoch += 1

        # Calculate training metrics
        self.model_instance.calculate_metrics(
            split=SplitEnum.TRAIN,
            level=LevelEnum.EPOCH,
            x_data=self.x_train,
            y_data=self.y_train,
        )

        # Calculate validation metrics
        self.model_instance.calculate_metrics(
            split=SplitEnum.VALIDATION,
            level=LevelEnum.EPOCH,
            x_data=self.x_val,
            y_data=self.y_val,
        )

    def on_step_end(self, args, state, control, **kwargs):
        pass
