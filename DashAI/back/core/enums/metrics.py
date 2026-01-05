from enum import Enum


class SplitEnum(Enum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


class LevelEnum(Enum):
    LAST = "last"
    TRIAL = "trial"
    STEP = "step"
    EPOCH = "epoch"
