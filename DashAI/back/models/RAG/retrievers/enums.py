from enum import Enum


class RetrievalStrategy(str, Enum):
    ACCUMULATE = "accumulate"
    CASCADE = "cascade"


class MergeStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    INTERLEAVE = "interleave"
