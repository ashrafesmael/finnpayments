#!/bin/bash
echo "========================================"
echo "InstaScreen-AML - Starting Backend and Frontend"
echo "========================================"

echo "Starting Backend (FastAPI)..."
python3 run.py &
BACKEND_PID=$!

sleep 5

echo "Starting Frontend (React + Vite)..."
cd frontend
npm install
npm run dev &
FRONTEND_PID=$!
cd ..

echo "========================================"
echo "InstaScreen-AML is running..."
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "API Docs: http://localhost:8000/docs"
echo "========================================"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait and cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
