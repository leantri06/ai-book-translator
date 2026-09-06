@echo off
title AI Book and Paper Translator Pro
color 0B
echo =======================================================
echo          AI BOOK AND PAPER TRANSLATOR PRO
echo    Phan mem dich sach va bai bao khoa hoc chuyen nghiep
echo =======================================================
echo.
echo Dang khoi dong may chu va mo trinh duyet...
echo.

cd /d "%~dp0"
python main.py

if errorlevel 1 (
    echo.
    echo [LOI] Khong the khoi chay ung dung!
    echo Vui long kiem tra Python va cac thu vien can thiet.
    echo.
)
pause
