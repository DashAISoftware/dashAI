from enum import Enum


class PluginSource(str, Enum):
    LOCAL = "local"
    GIT = "git"
