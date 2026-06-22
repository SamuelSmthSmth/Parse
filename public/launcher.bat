@echo off
title LaTeX Calc - Desktop Engine
echo LaTeX Calc - Desktop Engine Launcher (Windows)
echo ==============================================
echo.

:: 1. Find Julia Executable
set "JULIA_CMD="
where julia >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "JULIA_CMD=julia"
    goto :CHECK_PKG
)

:: Check common installation directory
if exist "%LOCALAPPDATA%\Programs\Julia\bin\julia.exe" (
    set "JULIA_CMD=%LOCALAPPDATA%\Programs\Julia\bin\julia.exe"
    goto :CHECK_PKG
)

:: Not found
echo ERROR: Could not find 'julia' in PATH or default install locations.
echo Please install Julia from https://julialang.org/downloads/
echo.
pause
exit /b 1

:CHECK_PKG
echo Verifying Julia packages...
%JULIA_CMD% -e "using Pkg; installed=[p.name for p in values(Pkg.dependencies())]; for p in [\"HTTP\", \"JSON3\", \"SymPy\", \"Roots\"]; p in installed || Pkg.add(p); end"

echo.
echo Starting Desktop Engine...
%JULIA_CMD% server.jl

echo.
echo Desktop Engine has crashed or terminated.
pause
