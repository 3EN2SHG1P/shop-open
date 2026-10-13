import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "app"))

# 导入 core.config 会先加载 backend/.env，保证 PORT / RELOAD 在 uvicorn 启动前生效。
# PORT / RELOAD 统一由 core.config 解析：写错时会给出可读报错而不是裸 ValueError
import uvicorn

from core.config import config

if __name__ == "__main__":
    # 后端接口服务 + 后台管理系统(manager)统一监听 8001 端口；商城前台(front)独立静态托管于 8000
    # host 固定 127.0.0.1（仅本机可访问），需对外监听请直接改这里的 host
    uvicorn.run("main:app", host="127.0.0.1", port=config.port, reload=config.reload)
