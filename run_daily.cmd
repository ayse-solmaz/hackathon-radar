@echo off
rem Hackathon Radar - gunluk calisma (Gorev Zamanlayici bunu cagirir)
cd /d "%~dp0"
if not exist logs mkdir logs
if not exist .venv\Scripts\python.exe (
  py -m venv .venv
  .venv\Scripts\python -m pip install -q -r requirements.txt
)
set PYTHONIOENCODING=utf-8
for /f %%d in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set TODAY=%%d
.venv\Scripts\python -m scraper.daily >> "logs\%TODAY%.log" 2>&1
