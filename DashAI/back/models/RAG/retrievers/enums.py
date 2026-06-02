from enum import Enum

class MergeStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    INTERLEAVE = "interleave"
