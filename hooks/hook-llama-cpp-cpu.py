import os

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("llama_cpp")
binaries = []
lib_dir = os.path.join(os.path.dirname(__file__), "..", "llama_cpp", "lib")
lib_dir = os.path.abspath(lib_dir)

if not os.path.exists(lib_dir):
    import llama_cpp

    lib_dir = os.path.join(os.path.dirname(llama_cpp.__file__), "lib")

if os.path.exists(lib_dir):
    for f in os.listdir(lib_dir):
        if f.endswith(".dll"):
            binaries.append((os.path.join(lib_dir, f), "llama_cpp/lib"))
