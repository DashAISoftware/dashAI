from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Incluir todos los submódulos de py4j (como java_collections, protocol, etc.)
hiddenimports = collect_submodules("py4j")

# Incluir posibles archivos de datos internos
datas = collect_data_files("py4j")
