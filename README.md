terminal:
pyinstaller   --onefile   --noconsole   --name MTDataOnemine   --collect-all customtkinter   --collect-submodules tkcalendar   --hidden-import pyodbc   src/mtdataonemine/app/main.py