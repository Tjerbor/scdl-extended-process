del /f *.exe
pyinstaller --onefile -y --distpath "./" m4a_fix.py
pyinstaller --onefile -y --distpath "./" -n ###scdl_extended_process scdl_extended_process.py
rmdir /Q /S build
del /f *.spec