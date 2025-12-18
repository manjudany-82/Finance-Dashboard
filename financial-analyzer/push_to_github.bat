@echo off
echo ==========================================
echo   Financial Dashboard - GitHub Pusher
echo ==========================================
echo.
echo Please create a new repository at: https://github.com/new
echo Name it: financial-dashboard
echo.
set /p REPO_URL="Enter the GitHub Repository URL (e.g., https://github.com/User/repo.git): "

"C:\Program Files\Git\cmd\git.exe" remote remove origin 2>nul
"C:\Program Files\Git\cmd\git.exe" remote add origin %REPO_URL%
"C:\Program Files\Git\cmd\git.exe" branch -M main
"C:\Program Files\Git\cmd\git.exe" push -u origin main

echo.
echo ==========================================
echo   Done! Your code is on GitHub.
echo ==========================================
pause
