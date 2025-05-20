pyinstaller ^
-F ^
--noconsole ^
-i logo.ico ^
--add-data "static/*;static" ^
--add-data "logo.ico;." ^
--hidden-import="pystray.PIL" ^
--additional-hooks-dir=. ^
--target-architecture=win32 ^
-n QTransfer ^
main.py
