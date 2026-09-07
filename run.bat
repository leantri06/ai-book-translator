@echo off
chcp 65001 >nul
title AI Book and Research Paper Translator Pro (V3.5)
color 0B
echo =======================================================
echo        AI BOOK AND RESEARCH PAPER TRANSLATOR PRO
echo    Phan mem dich sach va bai bao khoa hoc chuyen nghiep
echo                     Phien ban 3.5
echo =======================================================
echo.

cd /d "%~dp0"

REM 1. Kiem tra Python
set "PY_CMD=python"
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo [LOI] Khong tim thay Python tren he thong!
        echo Vui long cai dat Python 3.10 tro len tu https://www.python.org/
        echo - Luu y: Nho tich chon "Add python.exe to PATH" khi cai dat.
        echo.
        pause
        exit /b 1
    ) else (
        set "PY_CMD=py"
    )
)

REM 2. Kiem tra thu vien phu thuoc can thiet
%PY_CMD% -c "import fastapi, uvicorn, pymupdf, bs4" >nul 2>&1
if errorlevel 1 (
    echo [THONG BAO] Dang kiem tra va cai dat cac thu vien con thieu...
    %PY_CMD% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [LOI] Cai dat thu vien that bai! Vui long kiem tra ket noi Internet.
        echo.
        pause
        exit /b 1
    )
)

REM 3. Khoi chay may chu va trinh duyet
echo Dang khoi dong may chu va mo trinh duyet web...
echo Ung dung se chay tai dia chi: http://localhost:8000
echo.

%PY_CMD% main.py

if errorlevel 1 (
    echo.
    echo [LOI] Ung dung da dung lai hoac gap loi khi khoi chay!
    echo Vui long kiem tra thong bao loi chi tiet o tren.
    echo.
)

echo.
echo =======================================================
echo Ung dung da dung. Nhan phim bat ky de dong cua so...
echo =======================================================
pause >nul
