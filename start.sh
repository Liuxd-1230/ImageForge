#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "   ImageForge — Anima 提示词工作台启动中   "
echo "=========================================="

# Start backend
echo "[1/2] 启动后端服务 (FastAPI + Uvicorn)..."
PYTHONPATH="$SCRIPT_DIR/backend" "$SCRIPT_DIR/backend/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

# Start frontend
echo "[2/2] 启动前端服务 (Vite + Vue 3)..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

trap 'echo "正在关闭 ImageForge 服务..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true' EXIT INT TERM

echo ""
echo "=========================================="
echo "   ImageForge 服务已全部就绪！"
echo "   前端地址: http://localhost:5173"
echo "   后端 API: http://localhost:8000"
echo "   API 文档: http://localhost:8000/docs"
echo "=========================================="
echo "按 Ctrl+C 即可一键安全停止所有服务。"
echo ""

wait
