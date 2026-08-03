#!/bin/bash
# A1proj 一键启动脚本 — 自动处理前后端启动、重试、健康检查
set -e

PROJECT_DIR="/home/lj/A1proj_real_api 2/A1proj_real_api 2"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo "===== A1proj 系统启动 ====="

# 1. 清理旧进程
echo "[1/5] 清理旧进程..."
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 5173/tcp 2>/dev/null || true
sleep 1

# 2. 确保 vite symlink
echo "[2/5] 检查前端依赖..."
mkdir -p "$FRONTEND_DIR/node_modules/@vitejs"
for pkg in vite @vitejs/plugin-vue; do
    target="$FRONTEND_DIR/node_modules/$pkg"
    if [ -d "$target" ] && [ ! -L "$target" ]; then
        rm -rf "$target"
    fi
    if [ ! -e "$target" ]; then
        ln -sf "/home/lj/.local/lib/node_modules/$pkg" "$target"
    fi
done

# 3. 启动后端
echo "[3/5] 启动后端..."
cd "$PROJECT_DIR"
PYTHONPATH="./backend:$PYTHONPATH" uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
echo "  后端 PID: $BACKEND_PID"

# 等待后端就绪
echo "  等待后端启动..."
for i in $(seq 1 30); do
    if curl -s http://127.0.0.1:8000/user/login -X POST -H "Content-Type: application/json" -d '{"username":"admin","password":"admin"}' > /dev/null 2>&1; then
        echo "  ✅ 后端已就绪"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "  ❌ 后端启动超时，请检查日志"
        exit 1
    fi
    sleep 2
done

# 4. 启动前端
echo "[4/5] 启动前端..."
cd "$FRONTEND_DIR"
npx vite --host 127.0.0.1 --port 5173 &
FRONTEND_PID=$!
echo "  前端 PID: $FRONTEND_PID"

# 等待前端就绪
echo "  等待前端启动..."
for i in $(seq 1 15); do
    if curl -s http://127.0.0.1:5173/ > /dev/null 2>&1; then
        echo "  ✅ 前端已就绪"
        break
    fi
    sleep 1
done

# 5. 验证
echo "[5/5] 验证系统..."
if curl -s http://127.0.0.1:5173/user/login -X POST -H "Content-Type: application/json" -d '{"username":"admin","password":"admin"}' | grep -q '"success":true'; then
    echo "✅ 登录验证通过"
else
    echo "⚠️  登录验证失败，但服务可能仍在启动中"
fi

echo ""
echo "===== 启动完成 ====="
echo "前端: http://localhost:5173/"
echo "后端: http://localhost:8000/"
echo "账号: admin / admin"
echo ""
echo "后端 PID: $BACKEND_PID"
echo "前端 PID: $FRONTEND_PID"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo "===================="

# 等待任意子进程退出
wait
