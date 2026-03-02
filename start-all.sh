#!/bin/bash
echo "========================================"
echo "FinnPayments - Starting Backend and Frontend"
echo "========================================"

# Load environment
# Load from .env
if [ -f .env ]; then export $(grep -v "^#" .env | xargs); fi
# export GROQ_API_KEY="${GROQ_API_KEY}"
# export FINNPAYMENTS_PORT=8001

echo "Starting Backend (FastAPI on port $FINNPAYMENTS_PORT)..."
python3 run.py &
BACKEND_PID=$!
sleep 5
echo "Starting Frontend (React + Vite on port 3001)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..
echo "========================================"
echo "FinnPayments is running..."
echo "Backend:  http://localhost:$FINNPAYMENTS_PORT"
echo "Frontend: http://localhost:3001"
echo "API Docs: http://localhost:$FINNPAYMENTS_PORT/docs"
echo "GROQ AI:  ✅ Enabled"
echo "========================================"
echo ""
echo "Press Ctrl+C to stop all services"
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
