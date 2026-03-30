import contextlib

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

deps = [
    "transformers",
    "tokenizers",
    "tqdm",
    "regex",
    "requests",
    "packaging",
    "filelock",
    "safetensors",
    "sentencepiece",
    "huggingface_hub",
    "numpy",
    "torch",
    "tensorflow",
    "jax",
    "optimum",
    "accelerate",
    "pandas",
    "pillow",
    "protobuf",
    "pyyaml",
    "scipy",
    "sacrebleu",
]

datas = []
hiddenimports = ["transformers.models"]

for dep in deps:
    with contextlib.suppress(Exception):
        datas += copy_metadata(dep)
    with contextlib.suppress(Exception):
        hiddenimports += collect_submodules(dep)
