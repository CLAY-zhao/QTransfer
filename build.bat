pyinstaller ^
-F ^
--noconsole ^
-i logo.ico ^
--add-data "static/*;static" ^
--add-data "logo.ico;." ^
--hidden-import="pystray.PIL" ^
--additional-hooks-dir=. ^
-n QTransfer ^
main.py
