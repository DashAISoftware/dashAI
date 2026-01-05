from transformers import TrainerCallback

from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset


class MetricsCallback(TrainerCallback):
    def __init__(
        self,
        model_instance,
        x_train,
        y_train,
        x_val,
        y_val,
        total_epochs,
        log_training_every_n_epochs=1,
        log_training_every_n_steps=50,
        log_val_every_n_epochs=1,
        log_val_every_n_steps=50,
    ):
        self.model_instance = model_instance
        self.x_train = to_dashai_dataset(x_train)
        self.y_train = to_dashai_dataset(y_train)
        self.x_val = to_dashai_dataset(x_val)
        self.y_val = to_dashai_dataset(y_val)
        self.log_training_every_n_epochs = log_training_every_n_epochs
        self.log_training_every_n_steps = log_training_every_n_steps
        self.log_val_every_n_epochs = log_val_every_n_epochs
        self.log_val_every_n_steps = log_val_every_n_steps
        self.total_epochs = total_epochs
        self.current_step = 0
        self.last_logged_epoch = 0  # Track last logged epoch to prevent duplicates

    def on_epoch_end(self, args, state, control, **kwargs):
        current_epoch = int(state.epoch)  # Use state.epoch from Trainer

        # Only log if we haven't already logged this epoch
        if current_epoch > self.last_logged_epoch:
            self.last_logged_epoch = current_epoch

            if (
                self.log_training_every_n_epochs
                and current_epoch % self.log_training_every_n_epochs == 0
            ):
                self.model_instance.calculate_metrics(
                    split=SplitEnum.TRAIN,
                    level=LevelEnum.EPOCH,
                    x_data=self.x_train,
                    y_data=self.y_train,
                    log_index=current_epoch,
                )

            if (
                self.log_val_every_n_epochs
                and current_epoch % self.log_val_every_n_epochs == 0
            ):
                self.model_instance.calculate_metrics(
                    split=SplitEnum.VALIDATION,
                    level=LevelEnum.EPOCH,
                    x_data=self.x_val,
                    y_data=self.y_val,
                    log_index=current_epoch,
                )

    def on_step_end(self, args, state, control, **kwargs):
        self.current_step += 1

        if (
            self.log_training_every_n_steps
            and self.current_step % self.log_training_every_n_steps == 0
        ):
            self.model_instance.calculate_metrics(
                split=SplitEnum.TRAIN,
                level=LevelEnum.STEP,
                x_data=self.x_train,
                y_data=self.y_train,
                log_index=self.current_step,
            )

        if (
            self.log_val_every_n_steps
            and self.current_step % self.log_val_every_n_steps == 0
        ):
            self.model_instance.calculate_metrics(
                split=SplitEnum.VALIDATION,
                level=LevelEnum.STEP,
                x_data=self.x_val,
                y_data=self.y_val,
                log_index=self.current_step,
            )
