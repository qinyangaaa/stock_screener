"""策略参数配置和全局设置 — 支持从 DB 动态加载"""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class StrategyConfig:
    """选股策略参数，集中管理所有可调阈值（以下为默认值，可被 DB 覆盖）"""

    # 涨幅区间 (常规行情)
    change_pct_min: float = 3.0
    change_pct_max: float = 5.0
    # 极端行情放宽区间（全市场涨跌家数比 > 阈值时启用）
    extreme_market_ratio: float = 0.7
    extreme_change_pct_min: float = 2.0
    extreme_change_pct_max: float = 7.0

    # 量比
    volume_ratio_min: float = 1.0

    # 换手率
    turnover_min: float = 5.0
    turnover_max: float = 20.0

    # 流通市值（亿）
    market_cap_min: float = 100
    market_cap_max: float = 500

    # 成交量台阶式上升
    step_volume_window: int = 6
    step_volume_recent: int = 3
    step_volume_min_recent_pass: int = 2

    # K线多头排列
    ma_periods: Tuple[int, int, int, int] = (5, 10, 20, 60)
    ma_conditions_min: int = 3

    # 套牢盘
    trapped_chip_ratio: float = 0.6
    trapped_chip_max: float = 0.6

    # 分时强度
    intraday_above_avg_ratio: float = 0.7
    index_outperform: bool = True

    # 尾盘信号 (14:30后)
    late_session_start: str = "14:30"
    pullback_to_avg_threshold: float = 0.005
    new_high_lookback: str = "14:30"

    # 评分权重
    score_volume_ratio_weight: float = 0.25
    score_change_pct_weight: float = 0.20
    score_turnover_weight: float = 0.15
    score_ma_strength_weight: float = 0.15
    score_intraday_weight: float = 0.15
    score_late_signal_weight: float = 0.10

    # 推荐
    top_n_strong: int = 5

    # 板块过滤
    exclude_boards: str = "300,688"  # 排除的板块代码前缀，逗号分隔（300=创业板, 688=科创板）


@dataclass
class AppConfig:
    """应用全局配置"""
    port: int = 8038
    host: str = "0.0.0.0"
    database_path: str = "stock_screener.db"
    data_source: str = "sina"  # "sina" | "akshare" | "dfcf"
    debug: bool = True


# 模块级单例 — 默认值
strategy_config = StrategyConfig()
app_config = AppConfig()

# ── 配置项元数据（供前端配置面板使用） ──────────────────────

# type: "float" | "int" | "bool" | "text"
CONFIG_META = {
    # 涨幅
    "change_pct_min":         {"group": "规则1: 涨幅",    "type": "float", "min": -10, "max": 10, "step": 0.1, "desc": "涨幅下限(%)"},
    "change_pct_max":         {"group": "规则1: 涨幅",    "type": "float", "min": 0,  "max": 20, "step": 0.1, "desc": "涨幅上限(%)"},
    "extreme_market_ratio":   {"group": "规则1: 涨幅",    "type": "float", "min": 0.5,"max": 0.95,"step": 0.05,"desc": "极端行情触发阈值(涨跌比)"},
    "extreme_change_pct_min": {"group": "规则1: 涨幅",    "type": "float", "min": -10, "max": 10, "step": 0.1, "desc": "极端行情涨幅下限(%)"},
    "extreme_change_pct_max": {"group": "规则1: 涨幅",    "type": "float", "min": 0,  "max": 20, "step": 0.1, "desc": "极端行情涨幅上限(%)"},
    # 量比
    "volume_ratio_min":       {"group": "规则2: 量比",    "type": "float", "min": 0,  "max": 10, "step": 0.1, "desc": "量比下限"},
    # 换手率
    "turnover_min":           {"group": "规则3: 换手率",  "type": "float", "min": 0,  "max": 50, "step": 0.5, "desc": "换手率下限(%)"},
    "turnover_max":           {"group": "规则3: 换手率",  "type": "float", "min": 0,  "max": 100,"step": 0.5, "desc": "换手率上限(%)"},
    # 流通市值
    "market_cap_min":         {"group": "规则4: 流通市值", "type": "float", "min": 0,  "max": 10000,"step": 10, "desc": "流通市值下限(亿)"},
    "market_cap_max":         {"group": "规则4: 流通市值", "type": "float", "min": 0,  "max": 10000,"step": 10, "desc": "流通市值上限(亿)"},
    # 台阶式放量
    "step_volume_window":          {"group": "规则5: 台阶放量","type": "int", "min": 3, "max": 20, "step": 1, "desc": "考察最后N根K线"},
    "step_volume_recent":          {"group": "规则5: 台阶放量","type": "int", "min": 1, "max": 10, "step": 1, "desc": "最近N根需高于前一半均值"},
    "step_volume_min_recent_pass": {"group": "规则5: 台阶放量","type": "int", "min": 1, "max": 10, "step": 1, "desc": "最近N根中至少M根达标"},
    # 均线 + 套牢盘
    "ma_conditions_min":   {"group": "规则6: 多头+套牢","type": "int",   "min": 2, "max": 4,  "step": 1,   "desc": "MA多头至少满足几组"},
    "trapped_chip_max":    {"group": "规则6: 多头+套牢","type": "float", "min": 0, "max": 1,  "step": 0.05,"desc": "上方套牢盘比例上限(超过剔除)"},
    # 分时强度
    "intraday_above_avg_ratio": {"group": "规则7: 分时强度","type": "float", "min": 0.3,"max": 1,  "step": 0.05,"desc": "站上黄线的K线占比下限"},
    "index_outperform":         {"group": "规则7: 分时强度","type": "bool",  "desc": "必须强于大盘"},
    # 尾盘信号
    "late_session_start":        {"group": "规则8: 尾盘信号","type": "text",  "desc": "尾盘起点(HH:MM)"},
    "pullback_to_avg_threshold": {"group": "规则8: 尾盘信号","type": "float", "min": 0, "max": 0.05,"step": 0.001,"desc": "回踩距黄线阈值"},
    "new_high_lookback":         {"group": "规则8: 尾盘信号","type": "text",  "desc": "创新高回溯起点(HH:MM)"},
    # 评分权重
    "score_volume_ratio_weight": {"group": "评分权重", "type": "float", "min": 0, "max": 1, "step": 0.05, "desc": "量比权重"},
    "score_change_pct_weight":   {"group": "评分权重", "type": "float", "min": 0, "max": 1, "step": 0.05, "desc": "涨幅权重"},
    "score_turnover_weight":     {"group": "评分权重", "type": "float", "min": 0, "max": 1, "step": 0.05, "desc": "换手率权重"},
    "score_ma_strength_weight":  {"group": "评分权重", "type": "float", "min": 0, "max": 1, "step": 0.05, "desc": "均线强度权重"},
    "score_intraday_weight":     {"group": "评分权重", "type": "float", "min": 0, "max": 1, "step": 0.05, "desc": "分时强度权重"},
    "score_late_signal_weight":  {"group": "评分权重", "type": "float", "min": 0, "max": 1, "step": 0.05, "desc": "尾盘信号权重"},
    # 推荐
    "top_n_strong": {"group": "推荐", "type": "int", "min": 1, "max": 20, "step": 1, "desc": "强烈推荐前N只"},
    # 板块过滤
    "exclude_boards": {"group": "数据源", "type": "text", "desc": "排除板块代码前缀（逗号分隔，如 300,688）"},
}


def _str_to_val(val_type: str, val: str):
    if val_type == "float":
        return float(val)
    elif val_type == "int":
        return int(float(val))
    elif val_type == "bool":
        return val.lower() in ("true", "1", "yes")
    return str(val)


def load_config_from_db():
    """从 DB 读取覆盖值，更新模块级 strategy_config 和 app_config"""
    try:
        from models.database import get_all_config
        db_config = get_all_config()
    except Exception:
        db_config = {}

    _apply_overrides(strategy_config, db_config)
    _apply_overrides(app_config, db_config)


def _apply_overrides(target, db_config: dict):
    for field_name in target.__dataclass_fields__:
        if field_name in db_config:
            field_type = type(getattr(target, field_name))
            try:
                if field_type == tuple:
                    # 特殊处理 tuple 字段如 ma_periods
                    val = tuple(int(x.strip()) for x in db_config[field_name].split(","))
                else:
                    val = field_type(db_config[field_name])
                setattr(target, field_name, val)
            except (ValueError, TypeError):
                pass


def save_config_to_db(key: str, value):
    """保存单个配置到 DB 并立即生效"""
    from models.database import save_config
    meta = CONFIG_META.get(key, {})
    save_config(key, value, description=meta.get("desc"))
    # 立即应用到内存
    _apply_overrides(strategy_config, {key: str(value)})
    _apply_overrides(app_config, {key: str(value)})


def save_config_batch_to_db(items: dict):
    """批量保存并生效"""
    from models.database import save_config_batch
    save_config_batch(items)
    load_config_from_db()


def get_config_full() -> list[dict]:
    """返回完整配置列表（含元数据 + 当前值），供前端配置面板使用"""
    result = []
    for key, meta in CONFIG_META.items():
        # 获取当前值
        current_val = getattr(strategy_config, key, None)
        if current_val is None:
            current_val = getattr(app_config, key, None)
        if isinstance(current_val, tuple):
            current_val = ", ".join(str(x) for x in current_val)

        item = dict(meta)
        item["key"] = key
        item["value"] = current_val
        result.append(item)
    # 按 group 排序
    result.sort(key=lambda x: (list(CONFIG_META.keys()).index(x["key"])))
    return result


def reset_config_to_defaults():
    """重置所有配置为默认值"""
    from models.database import get_connection
    conn = get_connection()
    conn.execute("DELETE FROM strategy_config")
    conn.commit()
    conn.close()
    # 重置内存中的值
    global strategy_config, app_config
    defaults_s = StrategyConfig()
    defaults_a = AppConfig()
    for field_name in strategy_config.__dataclass_fields__:
        setattr(strategy_config, field_name, getattr(defaults_s, field_name))
    for field_name in app_config.__dataclass_fields__:
        setattr(app_config, field_name, getattr(defaults_a, field_name))
