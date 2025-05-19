from PyInstaller.utils.hooks import collect_data_files

# 强制包含static目录下所有文件
datas = collect_data_files("static", include_py_files=False)
