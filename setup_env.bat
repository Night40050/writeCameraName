@echo off
REM ──────────────────────────────────────────────────────────────────────────
REM  AirSign – Phase 1: Virtual environment setup (Windows)
REM  Run once from the airsign/ directory:  setup_env.bat
REM ──────────────────────────────────────────────────────────────────────────

echo [1/4] Creating virtual environment ...
python -m venv .venv

echo [2/4] Activating ...
call .venv\Scripts\activate.bat

echo [3/4] Upgrading pip ...
python -m pip install --upgrade pip

echo [4/4] Installing dependencies ...
pip install -r requirements.txt

echo.
echo =========================================================
echo  Virtual environment ready!
echo  Activate with:  .venv\Scripts\activate
echo  Run camera scan: python utils/obs_helper.py
echo  Launch app:      python main.py
echo =========================================================
pause
