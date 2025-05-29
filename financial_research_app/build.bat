@echo off
echo Cleaning up previous builds...
IF EXIST dist rmdir /s /q dist
IF EXIST build rmdir /s /q build
IF EXIST FinancialResearchEmailer.spec del /q FinancialResearchEmailer.spec

echo Activating virtual environment (if venv exists)...
IF EXIST .\venv\Scripts\activate.bat (
    call .\venv\Scripts\activate.bat
) ELSE (
    echo Virtual environment .\venv\Scripts\activate.bat not found. Proceeding without.
)

echo Running PyInstaller...
pyinstaller main.py ^
    --name FinancialResearchEmailer ^
    --onedir ^
    --add-data "config/config.ini.sample:config/" ^
    --noconfirm

echo Build process complete. Find output in the 'dist' directory.
pause
