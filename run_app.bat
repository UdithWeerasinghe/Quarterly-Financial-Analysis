@echo off
echo Running Quarterly Financial Analysis Application...

:: Set PYTHONPATH to include the project root
set PYTHONPATH=%PYTHONPATH%;%CD%

:: Run the Flask application
python -m backend.app

pause 