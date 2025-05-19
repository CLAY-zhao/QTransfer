.PHONY: install

build:
	pyinstaller \
	-F \
	--noconsole \
	-i logo.ico \
	--add-data "static/*;static" \
	--add-data "logo.ico;." \
	--hidden-import="pystray.PIL" \
	--additional-hooks-dir=. \
	-n QTransfer \
	main.py

install:
	pip install -r requirements.txt

clean:
	rm -rf __pycache__
	rm -rf build
	rm -rf dist
