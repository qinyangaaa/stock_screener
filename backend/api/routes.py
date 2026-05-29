"""REST API 路由"""

import threading
import logging
from datetime import date
from flask import Blueprint, jsonify, request

from models import database as db
from strategy.engine import ScreeningEngine
from trading_calendar import is_trading_day

logger = logging.getLogger("API")

api_bp = Blueprint("api", __name__)

_engine = ScreeningEngine()
_task_lock = threading.Lock()
_running = False


def _get_engine():
    return _engine


@api_bp.route("/api/health")
def health():
    return jsonify({"status": "ok", "date": date.today().isoformat()})


@api_bp.route("/api/screen/run", methods=["POST"])
def screen_run():
    global _running
    with _task_lock:
        if _running:
            return jsonify({"error": "已有筛选任务正在运行", "task_id": _engine.task_id}), 409
        _running = True

    trading_day = is_trading_day()

    def _run():
        global _running
        try:
            _engine.run()
        finally:
            _running = False

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    resp = {"task_id": _engine.task_id, "status": "started"}
    if not trading_day:
        resp["warning"] = "今日非交易日，筛选结果可能不完整"
    return jsonify(resp), 202


@api_bp.route("/api/screen/status/<task_id>")
def screen_status(task_id):
    progress = _engine.progress
    run_info = db.get_run_by_task_id(task_id)
    return jsonify({
        "task_id": task_id,
        "progress": progress,
        "run_info": run_info,
    })


@api_bp.route("/api/screen/cancel", methods=["POST"])
def screen_cancel():
    _engine.cancel()
    return jsonify({"status": "cancelled"})


@api_bp.route("/api/recommendations/latest")
def recommendations_latest():
    results = db.get_latest_recommendations()
    run = db.get_latest_run_status()
    return jsonify({
        "date": results[0]["screening_date"] if results else None,
        "total": len(results),
        "recommendations": results,
        "last_run": run,
        "is_trading_day": is_trading_day(),
    })


@api_bp.route("/api/recommendations/history")
def recommendations_history():
    d = request.args.get("date", date.today().isoformat())
    results = db.get_recommendations_by_date(d)
    return jsonify({
        "date": d,
        "total": len(results),
        "recommendations": results,
    })


@api_bp.route("/api/recommendations/history/dates")
def recommendations_dates():
    return jsonify({"dates": db.get_recommendation_dates()})


@api_bp.route("/api/screen/details/<task_id>")
def screen_details(task_id):
    """返回某次筛选的明细，包括各阶段各规则通过/失败详情"""
    details = db.get_screening_details(task_id=task_id)
    return jsonify({"task_id": task_id, "details": details})


@api_bp.route("/api/screen/details")
def screen_details_latest():
    """返回最近一次筛选的明细"""
    details = db.get_screening_details()
    return jsonify({"details": details})


@api_bp.route("/api/config")
def get_config():
    """获取所有策略配置项（含元数据和当前值）"""
    from config import get_config_full
    cfg_list = get_config_full()
    # 按 group 分组
    groups: dict[str, list] = {}
    for item in cfg_list:
        g = item.pop("group")
        groups.setdefault(g, []).append(item)
    return jsonify({"config": cfg_list, "groups": groups})


@api_bp.route("/api/config", methods=["PUT"])
def update_config():
    """更新配置项，支持单个或批量"""
    from config import save_config_to_db, save_config_batch_to_db, reset_config_to_defaults
    body = request.get_json(silent=True) or {}
    action = body.get("action", "update")

    if action == "reset":
        reset_config_to_defaults()
        return jsonify({"status": "ok", "message": "已重置为默认值"})

    if action == "batch":
        items = body.get("items", {})
        if items:
            save_config_batch_to_db(items)
        return jsonify({"status": "ok", "updated": len(items)})

    # 单个更新
    key = body.get("key")
    value = body.get("value")
    if not key or value is None:
        return jsonify({"error": "缺少 key 或 value"}), 400
    save_config_to_db(key, value)
    return jsonify({"status": "ok", "key": key, "value": value})


@api_bp.route("/api/screen/runs")
def screen_runs():
    """获取最近的筛选运行记录"""
    runs = db.get_screening_runs()
    # 去掉较大的 details_json 字段
    for r in runs:
        r.pop("details_json", None)
    return jsonify({"runs": runs})


@api_bp.route("/api/stock/<code>/detail")
def stock_detail(code):
    results = db.get_stock_detail(code)
    run = db.get_latest_run_status()
    # 尝试从最近一次运行的明细中补充该股票的详细数据
    extra = {}
    details = db.get_screening_details()
    s2_all = (details.get("stage2", {}).get("candidates", []) +
              details.get("stage2", {}).get("failed", []))
    for s in s2_all:
        if s.get("code") == code:
            extra = s
            break
    return jsonify({
        "code": code,
        "history": results,
        "last_run": run,
        "analysis": extra,
    })
