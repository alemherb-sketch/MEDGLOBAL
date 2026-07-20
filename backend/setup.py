import sys
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {
    "packages": ["uvicorn", "fastapi", "sqlalchemy", "pydantic", "starlette", "webbrowser", "threading", "sqlite3"],
    "include_files": ["static/", "medglobal.db", ".env"],
    "excludes": ["tkinter", "test", "unittest"]
}

base = None
# if sys.platform == "win32":
#    base = "Win32GUI" # Use this if you don't want a console window. For a web server we want it visible to close it or hidden. Let's make it console for now to debug, or hidden.
# Actually, since it opens a browser, a console is fine, but maybe GUI is better.
# We'll use Win32GUI to hide the console, but the server will run in the background until the PC is shut down, or killed via task manager. 
# It's better to show a console so the user can close the server by closing the terminal window.

setup(
    name="MEDGLOBAL",
    version="1.0",
    description="Sistema Medglobal Local",
    options={"build_exe": build_exe_options},
    executables=[Executable("app_desktop.py", base=base, target_name="MEDGLOBAL.exe", icon=None)]
)
