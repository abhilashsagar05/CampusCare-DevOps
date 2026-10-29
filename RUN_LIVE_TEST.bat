@echo off
title CampusCare - Live Visual E2E Functional Test
cls
echo ========================================================================
echo        CampusCare DevOps Project - Live Automated Visual Test
echo ========================================================================
echo.
echo Select Target Environment:
echo   [1] Local Docker Compose (http://localhost:5000) [Default]
echo   [2] Render Cloud Production (https://campuscare-d52b.onrender.com)
echo.
set /p TARGET="Choose [1 or 2, default 1]: "

if "%TARGET%"=="2" (
    echo.
    echo Running visual E2E test against Render Cloud...
    py -u tests\test_selenium.py https://campuscare-d52b.onrender.com
) else (
    echo.
    echo Running visual E2E test against Local Container...
    py -u tests\test_selenium.py http://localhost:5000
)

echo.
pause
