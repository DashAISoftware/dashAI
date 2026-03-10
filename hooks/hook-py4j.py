from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules("py4j")
datas = collect_data_files("py4j")
