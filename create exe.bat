del /f *.exe
pyinstaller --onefile -y --distpath "./" m4a_fix.py
pyinstaller --onefile -y --distpath "./" -n #cli_dl_extended_process.exe cli_dl_extended_process.py
rmdir /Q /S build
del /f *.spec