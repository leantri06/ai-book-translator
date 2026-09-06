@echo off
title AI Book & Paper Translator Pro
color 0B
chcp 65001 > nul
echo =======================================================
echo          AI BOOK & PAPER TRANSLATOR PRO
echo    Phần mềm dịch sách & bài báo khoa học chuyên nghiệp
echo =======================================================
echo.
echo Đang kiểm tra môi trường và khởi động máy chủ...
echo.

cd /d "%~dp0"
python main.py

if errorlevel 1 (
    echo.
    echo [LỖI] Không thể khởi chạy ứng dụng!
    echo Vui lòng kiểm tra Python và các thư viện cần thiết.
    echo.
)
pause
