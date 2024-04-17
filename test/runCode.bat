@echo off

REM Get current date and time
for /f "tokens=1-4 delims=/ " %%a in ('date /t') do (
    set date=%%c-%%a-%%b
    set time=%%d
)

REM Append date and time to log_errors.txt
echo %date% %time% >> log_errors.txt

cd C:\Users\gcanuto\Documents\NominationProject\web
call myenv\Scripts\activate
python manage.py scan >> log_errors.txt 2>&1
