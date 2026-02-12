@echo off
REM 快速部署脚本：上传到 GitHub（Windows 版本）

echo.
echo 📚 阅读计划 - GitHub 部署脚本 (Windows)
echo ======================================
echo.
echo 此脚本将帮你上传代码到 GitHub
echo.

REM 检查是否已初始化 git
if not exist ".git" (
    echo 1️⃣ 初始化 Git
    call git init
    echo ✅ Git 已初始化
    echo.
)

REM 获取 GitHub 仓库地址
set /p REPO_URL=请输入你的 GitHub 仓库地址 (如 https://github.com/你的用户名/reading-club.git): 

if "%REPO_URL%"=="" (
    echo ❌ 仓库地址为空
    pause
    exit /b 1
)

REM 检查是否已连接远程
git remote | findstr /i "origin" >nul
if errorlevel 1 (
    echo 2️⃣ 添加远程仓库
    call git remote add origin "%REPO_URL%"
    echo ✅ 远程仓库已添加
    echo.
)

echo 3️⃣ 添加所有文件
call git add .
echo ✅ 文件已添加
echo.

echo 4️⃣ 提交更改
call git commit -m "Initial commit - 阅读计划应用"
echo ✅ 更改已提交
echo.

echo 5️⃣ 推送到 GitHub
call git push -u origin main
if %errorlevel% equ 0 (
    echo ✅ 推送成功！
    echo.
    echo 📌 下一步：
    echo    1. 访问 https://render.com
    echo    2. 用 GitHub 登录
    echo    3. 创建新的 Web Service
    echo    4. 选择你提交的仓库
    echo    5. 点击 Deploy
    echo.
    echo 🎉 部署完毕后，所有朋友都能通过公网链接访问了！
) else (
    echo ❌ 推送失败，请检查：
    echo    1. 仓库地址是否正确
    echo    2. GitHub 权限是否正确
)

pause
