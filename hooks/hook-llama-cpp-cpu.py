import os

from PyInstaller.utils.hooks import collect_data_files

# Incluye los datos del paquete llama_cpp (archivos __init__, etc.)
datas = collect_data_files("llama_cpp")

# Incluye explícitamente las DLL del subdirectorio "lib"
binaries = []
lib_dir = os.path.join(os.path.dirname(__file__), "..", "llama_cpp", "lib")
lib_dir = os.path.abspath(lib_dir)

# Fallback: busca en site-packages si no está en __file__
if not os.path.exists(lib_dir):
    import llama_cpp

    lib_dir = os.path.join(os.path.dirname(llama_cpp.__file__), "lib")

if os.path.exists(lib_dir):
    for f in os.listdir(lib_dir):
        if f.endswith(".dll"):
            binaries.append((os.path.join(lib_dir, f), "llama_cpp/lib"))
