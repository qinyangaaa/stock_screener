"""Flask 入口 — 初始化数据库、调度器、注册 API 蓝图"""

import sys
import logging
from pathlib import Path

# 确保 backend 目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flask import Flask
from flask_cors import CORS
from models.database import init_db
from scheduler import start_scheduler, stop_scheduler
from config import app_config, load_config_from_db


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    # 日志配置
    logging.basicConfig(
        level=logging.DEBUG if app_config.debug else logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("APP")
    logger.info("正在初始化数据库...")

    # 初始化数据库
    init_db()
    load_config_from_db()
    logger.info("数据库初始化完成，已加载策略配置")

    # 注册 API 蓝图
    from api.routes import api_bp
    app.register_blueprint(api_bp)
    logger.info("API 蓝图已注册")

    # 启动定时调度器
    start_scheduler()

    # 优雅关闭
    import atexit
    atexit.register(stop_scheduler)

    return app


if __name__ == "__main__":
    application = create_app()
    logging.getLogger("APP").info(f"启动服务 {app_config.host}:{app_config.port}")
    application.run(host=app_config.host, port=app_config.port, debug=app_config.debug)
