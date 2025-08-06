from typing import Dict

from datasets import Features

# encode_nested_example debe ser revisado pero en otro codigo


class DashAIFeatures(Features):
    """Wrapper for Hugging Face for representing features."""

    def __init__(self, *args, **kwargs):
        if not args:
            raise TypeError("At least one feature is required")
        self, *args = args
        super(DashAIFeatures, self).__init__(*args, **kwargs)
        self._column_requires_decoding: Dict[str, bool] = {
            col: self._requires_decoding(feature) for col, feature in self.items()
        }
