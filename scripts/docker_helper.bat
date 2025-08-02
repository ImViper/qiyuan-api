@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM Docker Compose 渠道管理助手脚本 (Windows)

cd /d "%~dp0"

set MYSQL_DSN=root:123456@tcp(localhost:3306)/new-api
set MYSQL_CONTAINER=mysql
set COMPOSE_FILE=..\docker-compose.yml

if "%~1"=="" (
    echo Please specify a command. Use "%~nx0 help" for help.
    exit /b 1
)

if "%~1"=="help" goto help
if "%~1"=="--help" goto help
if "%~1"=="-h" goto help
if "%~1"=="check" goto check
if "%~1"=="export" goto export
if "%~1"=="backup" goto backup
if "%~1"=="import" goto import
if "%~1"=="restore" goto restore

echo [ERROR] Unknown command: %~1
echo Use "%~nx0 help" to see available commands.
exit /b 1

:help
echo.
echo Docker Compose 渠道管理助手
echo.
echo 用法: %~nx0 [命令] [选项]
echo.
echo 命令:
echo   check       检查 Docker 服务状态和连接
echo   export      导出渠道数据
echo   backup      备份渠道数据（完整备份）
echo   import      导入渠道数据
echo   restore     恢复渠道数据（删除现有数据）
echo   help        显示此帮助信息
echo.
echo 导出选项:
echo   export [格式] [输出文件]
echo   格式: json, csv, txt (默认: json)
echo.
echo   示例:
echo     %~nx0 export json
echo     %~nx0 export csv channels.csv
echo     %~nx0 export txt report.txt
echo.
echo 备份选项:
echo   backup [输出文件]
echo.
echo   示例:
echo     %~nx0 backup
echo     %~nx0 backup my_backup.json
echo.
echo 导入选项:
echo   import ^<文件^> [模式]
echo   模式: skip (跳过重复), update (更新重复) (默认: skip)
echo.
echo   示例:
echo     %~nx0 import channels.json
echo     %~nx0 import channels.json update
echo.
echo 恢复选项:
echo   restore ^<备份文件^>
echo.
echo   示例:
echo     %~nx0 restore backup.json
echo.
exit /b 0

:check
echo [INFO] Checking Docker Compose service status...

docker-compose -f "%COMPOSE_FILE%" ps | findstr "mysql.*Up" >nul
if !errorlevel! neq 0 (
    echo [ERROR] MySQL service is not running
    echo Please start Docker Compose service first:
    echo   cd .. ^&^& docker-compose up -d
    exit /b 1
)

echo [SUCCESS] MySQL service is running

echo [INFO] Testing database connection...
go run channel_manager.go -action=export -dry-run -verbose -output=nul 2>nul | findstr "找到.*个渠道" >nul

if !errorlevel! equ 0 (
    echo [SUCCESS] Database connection successful
) else (
    echo [ERROR] Database connection failed
    echo Please check:
    echo   1. MySQL service is running
    echo   2. Port mapping is correct
    echo   3. Database connection string is correct
    exit /b 1
)
exit /b 0

:export
set FORMAT=%~2
set OUTPUT=%~3

if "%FORMAT%"=="" set FORMAT=json

if "%OUTPUT%"=="" (
    for /f "tokens=2 delims==" %%i in ('wmic OS Get localdatetime /value') do set datetime=%%i
    set timestamp=!datetime:~0,8!_!datetime:~8,6!
    set OUTPUT=channels_export_!timestamp!.!FORMAT!
)

echo [INFO] Exporting channel data in %FORMAT% format...

go run channel_manager.go -action=export -format="%FORMAT%" -output="%OUTPUT%" -dsn="%MYSQL_DSN%" -verbose

if !errorlevel! equ 0 (
    echo [SUCCESS] Channel data exported to: %OUTPUT%
) else (
    echo [ERROR] Export failed
    exit /b 1
)
exit /b 0

:backup
set OUTPUT=%~2

if "%OUTPUT%"=="" (
    for /f "tokens=2 delims==" %%i in ('wmic OS Get localdatetime /value') do set datetime=%%i
    set timestamp=!datetime:~0,8!_!datetime:~8,6!
    set OUTPUT=channels_backup_!timestamp!.json
)

echo [INFO] Backing up channel data...

go run channel_manager.go -action=backup -output="%OUTPUT%" -dsn="%MYSQL_DSN%" -verbose

if !errorlevel! equ 0 (
    echo [SUCCESS] Channel data backed up to: %OUTPUT%
) else (
    echo [ERROR] Backup failed
    exit /b 1
)
exit /b 0

:import
set INPUT=%~2
set MODE=%~3

if "%INPUT%"=="" (
    echo [ERROR] Please specify the file to import
    exit /b 1
)

if not exist "%INPUT%" (
    echo [ERROR] File not found: %INPUT%
    exit /b 1
)

if "%MODE%"=="" set MODE=skip

echo [INFO] Importing channel data from: %INPUT%

set IMPORT_FLAGS=-skip-existing
if "%MODE%"=="update" (
    set IMPORT_FLAGS=-update-existing
    echo [WARNING] Will update existing channels
) else (
    echo [INFO] Will skip existing channels
)

echo [INFO] Running simulation import...
go run channel_manager.go -action=import -input="%INPUT%" %IMPORT_FLAGS% -dsn="%MYSQL_DSN%" -dry-run

if !errorlevel! equ 0 (
    echo.
    set /p "confirm=Confirm actual import? (y/n): "
    if /i "!confirm!"=="y" (
        echo [INFO] Running actual import...
        go run channel_manager.go -action=import -input="%INPUT%" %IMPORT_FLAGS% -dsn="%MYSQL_DSN%" -verbose
        if !errorlevel! equ 0 (
            echo [SUCCESS] Import completed
        ) else (
            echo [ERROR] Import failed
            exit /b 1
        )
    ) else (
        echo [INFO] Import cancelled
    )
) else (
    echo [ERROR] Simulation import failed
    exit /b 1
)
exit /b 0

:restore
set INPUT=%~2

if "%INPUT%"=="" (
    echo [ERROR] Please specify backup file to restore
    exit /b 1
)

if not exist "%INPUT%" (
    echo [ERROR] Backup file not found: %INPUT%
    exit /b 1
)

echo [WARNING] Restore operation will delete all existing channel data!
echo Backup file: %INPUT%
echo.
set /p "confirm=Confirm restore operation? (y/n): "

if /i "!confirm!"=="y" (
    echo [INFO] Running restore operation...
    go run channel_manager.go -action=restore -input="%INPUT%" -dsn="%MYSQL_DSN%" -verbose
    if !errorlevel! equ 0 (
        echo [SUCCESS] Restore completed
    ) else (
        echo [ERROR] Restore failed
        exit /b 1
    )
) else (
    echo [INFO] Restore cancelled
)
exit /b 0