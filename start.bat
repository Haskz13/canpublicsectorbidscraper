@echo off
echo ========================================
echo Starting Canadian Procurement Scanner...
echo ========================================
echo.
echo Rebuilding images to include recent code changes...
docker-compose up --build -d
echo.
echo Waiting for services to start...
timeout /t 15 /nobreak > nul
echo.
echo Service Status:
docker-compose ps
echo.
echo ========================================
echo Access Points:
echo - Frontend: http://localhost:3000
echo - API: http://localhost:8000
echo - API Docs: http://localhost:8000/docs
echo ========================================
pause