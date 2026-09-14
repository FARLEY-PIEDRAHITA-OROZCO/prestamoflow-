@echo off
start "PrestamoFlow API" cmd /k "cd backend && if not exist .venv python -m venv .venv && call .venv\Scripts\activate && pip install -r requirements.txt && uvicorn main:app --reload --port 8001"
timeout /t 4 >nul
start "PrestamoFlow Frontend" cmd /k "cd frontend && npm install && npm run dev"
