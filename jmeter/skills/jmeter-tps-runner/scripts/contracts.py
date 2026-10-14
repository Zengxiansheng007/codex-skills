# -*- coding: utf-8 -*-
"""jmeter-tps-runner 纯数据契约。

定义不可变/可验证的数据类型与单位：
- TaskSpec：任务配置（并发范围、档位、阈值、预算）
- Observation：一轮观测（并发、TPS、P90、错误率、质量判定）
- SearchDecision：下一档决策及完整理由
- Quantity / Decimal 精确数值语义

本模块仅定义数据契约，不执行命令、不访问网络/文件/进程/模型。
数值阈值使用 Decimal 以保证 3% 边界精确：1000→970 必须触发。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional


# ── 枚举 ──────────────────────────────────────────────

class Phase(str, Enum):
    """轮次阶段。"""
    COARSE = "coarse"   # 粗测
    FINE = "fine"       # 细测


class QualityStatus(str, Enum):
    """观测质量判定。"""
    QUALIFIED = "qualified"     # 合格（P90≤阈值 且 错误率≤阈值）
    EXCEEDED = "exceeded"       # 质量超标
    UNREADABLE = "unreadable"   # 报告不可读


class StopReason(str, Enum):
    """目标结束原因。"""
    NONE = "none"
    BUDGET_EXHAUSTED = "budget_exhausted"               # 6轮用尽
    COARSE_BUDGET_EXHAUSTED = "coarse_budget_exhausted" # 粗测4轮用尽
    PRESET_EXHAUSTED = "preset_exhausted"               # 预设档位用尽
    DECLINE_TRIGGERED = "decline_triggered"            # 相邻粗测TPS下降≥3%
    FIRST_ROUND_FAILURE = "first_round_failure"         # 首轮质量失败
    UNREADABLE = "unreadable"                        # 报告不可读，结束目标不补测
    NO_CANDIDATES = "no_candidates"                    # 无合法可测点
    TARGET_COMPLETE = "target_complete"


class Side(str, Enum):
    """细测侧。"""
    LEFT = "left"
    RIGHT = "right"


# ── 数值常量 ────────────────────────────────────────────

# 3% 下降阈值：Decimal 精确语义，1000→970 必须触发
DECLINE_THRESHOLD = Decimal("0.03")

# 默认预设绝对并发档位
DEFAULT_PRESET_LEVELS = (50, 100, 200, 500)

# 细测中点向下对齐基数
FINE_ALIGN_BASE = 10

# 预算
MAX_TOTAL_ROUNDS = 6
MAX_COARSE_ROUNDS = 4


def to_decimal(value) -> Decimal:
    """将任意数值安全转为 Decimal，保留原始可读精度。"""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class TaskSpecError(ValueError):
    """TaskSpec 配置校验失败。不静默修正，不自动对齐或减预算。"""


def validate_task_spec(task: "TaskSpec") -> None:
    """在构造或公开决策入口拒绝非法配置。

    上限最多6、粗测最多4；档位合法、递增、起点一致；
    质量阈值和数值单位有效。不静默修配置。
    """
    if task.max_total_rounds > 6:
        raise TaskSpecError(f"max_total_rounds={task.max_total_rounds} 超过上限6")
    if task.max_coarse_rounds > 4:
        raise TaskSpecError(f"max_coarse_rounds={task.max_coarse_rounds} 超过上限4")
    if task.max_coarse_rounds > task.max_total_rounds:
        raise TaskSpecError(
            f"max_coarse_rounds={task.max_coarse_rounds} 超过 max_total_rounds={task.max_total_rounds}"
        )
    if len(task.preset_levels) == 0:
        raise TaskSpecError("preset_levels 不能为空")
    levels = task.preset_levels
    for i in range(len(levels) - 1):
        if levels[i + 1] <= levels[i]:
            raise TaskSpecError(
                f"preset_levels 必须严格递增：{levels[i]} -> {levels[i+1]} 不满足"
            )
    # 档位须为10的正整数倍
    for lv in levels:
        if lv <= 0 or lv % 10 != 0:
            raise TaskSpecError(f"preset_levels 档位 {lv} 必须是10的正整数倍")
    # 起点必须等于首个预设档位
    if task.start_concurrency != levels[0]:
        raise TaskSpecError(
            f"start_concurrency={task.start_concurrency} 必须等于首档 {levels[0]}"
        )
    lower, upper = task.concurrency_range
    if lower > upper:
        raise TaskSpecError(f"concurrency_range 下界{lower}大于上界{upper}")
    if task.start_concurrency < lower or task.start_concurrency > upper:
        raise TaskSpecError(
            f"start_concurrency={task.start_concurrency} 超出范围 [{lower}, {upper}]"
        )
    for lv in levels:
        if lv < lower or lv > upper:
            raise TaskSpecError(f"preset_levels 档位 {lv} 超出范围 [{lower}, {upper}]")
    # 质量阈值有效性
    if task.error_rate_threshold < 0 or task.error_rate_threshold > 1:
        raise TaskSpecError(
            f"error_rate_threshold={task.error_rate_threshold} 无效，须在 [0, 1] 范围"
        )
    if task.p90_threshold_ms <= 0:
        raise TaskSpecError(f"p90_threshold_ms={task.p90_threshold_ms} 必须为正")
    if task.decline_threshold < 0:
        raise TaskSpecError(f"decline_threshold={task.decline_threshold} 不能为负")


# ── 数据类 ─────────────────────────────────────────────

@dataclass(frozen=True)
class TaskSpec:
    """任务配置，启动前确认并冻结。"""
    task_id: str
    target_id: str
    concurrency_range: tuple  # (lower, upper) 确认范围
    preset_levels: tuple      # 确认的预设绝对并发档位，如 (50,100,200,500)
    start_concurrency: int    # 起始并发
    error_rate_threshold: Decimal   # 错误率比例，0.5% = 0.005
    p90_threshold_ms: Decimal       # P90 毫秒阈值
    decline_threshold: Decimal = DECLINE_THRESHOLD
    max_total_rounds: int = MAX_TOTAL_ROUNDS
    max_coarse_rounds: int = MAX_COARSE_ROUNDS

    def __post_init__(self):
        # 构造时即拒绝非法配置，不静默修正
        if not isinstance(self.concurrency_range, tuple) or len(self.concurrency_range) != 2:
            raise TaskSpecError(f"concurrency_range 必须为二元组，得到 {self.concurrency_range}")
        if not isinstance(self.preset_levels, tuple) or len(self.preset_levels) == 0:
            raise TaskSpecError(f"preset_levels 必须为非空元组，得到 {self.preset_levels}")
        # 将数值字段归一为 Decimal
        object.__setattr__(self, "error_rate_threshold", to_decimal(self.error_rate_threshold))
        object.__setattr__(self, "p90_threshold_ms", to_decimal(self.p90_threshold_ms))
        object.__setattr__(self, "decline_threshold", to_decimal(self.decline_threshold))
        validate_task_spec(self)


@dataclass(frozen=True)
class Observation:
    """一轮观测结果，来自官方 report。

    所有数值使用 Decimal 保留原始可读精度。
    """
    target_id: str
    round_number: int
    phase: Phase
    concurrency: int
    tps: Optional[Decimal]          # 官方次/秒；不可读时保留缺失值。
    p90_ms: Optional[Decimal]        # P90 毫秒，None 表示不可读
    error_rate: Optional[Decimal]    # 错误率比例，None 表示不可读
    quality: QualityStatus
    is_qualified: bool = False      # 便捷标记
    is_started: bool = True         # 是否实际已启动发压

    def __post_init__(self):
        if self.tps is not None:
            object.__setattr__(self, "tps", to_decimal(self.tps))
        elif self.quality != QualityStatus.UNREADABLE:
            raise ValueError("可读观测必须提供官方TPS")  # 缺失值不能伪装成有效观测。
        if self.p90_ms is not None:
            object.__setattr__(self, "p90_ms", to_decimal(self.p90_ms))
        if self.error_rate is not None:
            object.__setattr__(self, "error_rate", to_decimal(self.error_rate))
        object.__setattr__(self, "is_qualified", self.quality == QualityStatus.QUALIFIED)


@dataclass(frozen=True)
class SearchDecision:
    """寻峰器输出的决策及完整理由。"""
    action: str  # "run_coarse" | "run_fine" | "end_target"
    next_concurrency: Optional[int]
    next_phase: Phase
    stop_reason: StopReason
    reason: str
    center_concurrency: Optional[int] = None    # 细测当前中心
    left_endpoint: Optional[int] = None         # 细测左端点
    right_endpoint: Optional[int] = None        # 细测右端点
    side: Optional[Side] = None                 # 当前细测侧
    rounds_used: int = 0                        # 已用预算
    rounds_remaining: int = 0                   # 剩余预算
    failure_boundary: Optional[int] = None      # 质量失败上界（不可向上跨越）
    best_qualified_concurrency: Optional[int] = None  # 当前最佳合格并发
    best_qualified_tps: Optional[Decimal] = None      # 当前最佳合格 TPS


# ── 辅助工厂 ────────────────────────────────────────────

def make_qualified_obs(
    target_id: str,
    round_number: int,
    phase: Phase,
    concurrency: int,
    tps,
    p90_ms=Decimal("500"),
    error_rate=Decimal("0.001"),
) -> Observation:
    """创建合格观测的便捷工厂。"""
    return Observation(
        target_id=target_id,
        round_number=round_number,
        phase=phase,
        concurrency=concurrency,
        tps=to_decimal(tps),
        p90_ms=to_decimal(p90_ms),
        error_rate=to_decimal(error_rate),
        quality=QualityStatus.QUALIFIED,
    )


def make_exceeded_obs(
    target_id: str,
    round_number: int,
    phase: Phase,
    concurrency: int,
    tps=Decimal("0"),
    p90_ms=Decimal("3000"),
    error_rate=Decimal("0.01"),
) -> Observation:
    """创建质量超标观测的便捷工厂。"""
    return Observation(
        target_id=target_id,
        round_number=round_number,
        phase=phase,
        concurrency=concurrency,
        tps=to_decimal(tps),
        p90_ms=to_decimal(p90_ms),
        error_rate=to_decimal(error_rate),
        quality=QualityStatus.EXCEEDED,
    )


def make_unreadable_obs(
    target_id: str,
    round_number: int,
    phase: Phase,
    concurrency: int,
) -> Observation:
    """创建不可读观测的便捷工厂。"""
    return Observation(
        target_id=target_id,
        round_number=round_number,
        phase=phase,
        concurrency=concurrency,
        tps=None,  # 不可读不填造0。
        p90_ms=None,
        error_rate=None,
        quality=QualityStatus.UNREADABLE,
    )
