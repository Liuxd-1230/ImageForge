#!/bin/bash

echo "=========================================="
echo "   ImageForge — 正在强制停止所有服务...   "
echo "=========================================="

# 1. Kill by port 8000 (Backend FastAPI/Uvicorn)
echo "[1/4] 清理后端端口 (8000)..."
if lsof -ti:8000 >/dev/null 2>&1; then
    PIDS=$(lsof -ti:8000)
    echo "  发现占用 8000 端口的进程: $PIDS，正在强制终止..."
    kill -9 $PIDS 2>/dev/null || true
fi
fuser -k -9 8000/tcp 2>/dev/null || true

# 2. Kill by port 5173 (Frontend Vite)
echo "[2/4] 清理前端端口 (5173)..."
if lsof -ti:5173 >/dev/null 2>&1; then
    PIDS=$(lsof -ti:5173)
    echo "  发现占用 5173 端口的进程: $PIDS，正在强制终止..."
    kill -9 $PIDS 2>/dev/null || true
fi
fuser -k -9 5173/tcp 2>/dev/null || true

# 3. Kill any lingering processes by name
echo "[3/4] 清理残留的 ImageForge 进程..."
pkill -9 -f "uvicorn.*app\.main:app" 2>/dev/null || true
pkill -9 -f "ImageForge/backend.*uvicorn" 2>/dev/null || true
pkill -9 -f "vite.*ImageForge" 2>/dev/null || true
pkill -9 -f "npm.*run.*dev" 2>/dev/null || true

sleep 0.5

# 4. Check status
echo "[4/4] 验证服务关闭状态..."
PORT_8000_BUSY=0
PORT_5173_BUSY=0

if lsof -ti:8000 >/dev/null 2>&1; then
    PORT_8000_BUSY=1
fi
if lsof -ti:5173 >/dev/null 2>&1; then
    PORT_5173_BUSY=1
fi

echo ""
if [ $PORT_8000_BUSY -eq 0 ] && [ $PORT_5173_BUSY -eq 0 ]; then
    echo "=========================================="
    echo "   ✅ 所有 ImageForge 服务与端口已彻底停止！"
    echo "   - 后端端口 (8000): 已释放"
    echo "   - 前端端口 (5173): 已释放"
    echo "=========================================="
else
    echo "=========================================="
    if [ $PORT_8000_BUSY -eq 1 ]; then
        echo "   ⚠️ 后端端口 (8000) 仍有占用: $(lsof -ti:8000)"
    fi
    if [ $PORT_5173_BUSY -eq 1 ]; then
        echo "   ⚠️ 前端端口 (5173) 仍有占用: $(lsof -ti:5173)"
    fi
    echo "=========================================="
fi
