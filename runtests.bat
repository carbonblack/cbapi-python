@echo off
setlocal
set PYTHONPATH=src
pytest -v test/
endlocal
