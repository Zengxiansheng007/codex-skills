# -*- coding: utf-8 -*-
"""jmeter-tps-runner 确定性寻峰纯函数。

输入：TaskSpec（配置）、已测 Observation 列表、显式阶段/同组状态。
输出：SearchDecision（下一档及完整原因）。
不访问网络、文件、进程或模型。

核心规则（PRD BR-006~BR-016, 架构 8.2/8.3）：
1. 粗测按确认的绝对档位顺序 50->100->200->500 执行。
2. 相邻粗测官方 TPS 下降率=(上一TPS-本轮TPS)/上一TPS >= 3% 转细测。
   上一TPS=0 不计算比例、不触发。1000->970 触发；1000->970.01 不触发。
3. 首轮质量失败结束该目标，不下探。
4. 后续质量失败：当前轮保留，停止向高于失败点探索，转细测。
   新失败边界使原右候选失效（若右候选 > 失败边界则跳过）。
5. 细测中点 C = 10 * floor((B + E) / 20)，向下对齐 10 倍数。
6. 同组中心在两侧完成前不变；先左后右。
7. 精确 TPS 并列选较低并发为中心及推荐并发。
8. 预算：每目标最多 6 轮，粗测最多 4 轮。
9. 正常合格峰值不复测。
10. 下降不建立质量失败上界。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, List, Tuple

from .contracts import (
    TaskSpec, Observation, SearchDecision, Phase, QualityStatus,
    StopReason, Side, DECLINE_THRESHOLD, FINE_ALIGN_BASE,
)


def compute_decline_ratio(prev_tps: Decimal, curr_tps: Decimal) -> Optional[Decimal]:
    """计算相邻粗测 TPS 下降率。返回 None 表示不可计算（上一TPS=0）。"""
    if prev_tps == 0:
        return None  # 零TPS不除零，不触发
    return (prev_tps - curr_tps) / prev_tps


def is_decline_triggered(prev_tps: Decimal, curr_tps: Decimal,
                         threshold: Decimal = DECLINE_THRESHOLD) -> bool:
    """判断相邻粗测是否触发 3% 下降停止。

    1000->970：(1000-970)/1000 = 0.03 = 3%，触发。
    1000->970.01：(1000-970.01)/1000 < 3%，不触发。
    上一TPS=0：不触发。
    """
    ratio = compute_decline_ratio(prev_tps, curr_tps)
    if ratio is None:
        return False
    return ratio >= threshold


def fine_midpoint(center: int, endpoint: int) -> int:
    """细测中点：10 * floor((B + E) / 20)，向下对齐 10 倍数。

    B=200,E=150 -> 170；B=200,E=350 -> 270；B=300,E=500 -> 400。
    """
    return FINE_ALIGN_BASE * ((center + endpoint) // 20)


def _qualified_observations(obs_list: List[Observation]) -> List[Observation]:
    """返回合格观测列表。"""
    return [o for o in obs_list if o.is_qualified]


def _best_qualified(obs_list: List[Observation]) -> Optional[Observation]:
    """在合格候选中按 report TPS 选择最高值。精确并列选较低并发。"""
    qualified = _qualified_observations(obs_list)
    if not qualified:
        return None
    sorted_q = sorted(qualified, key=lambda o: (-o.tps, o.concurrency))
    return sorted_q[0]


def _tested_concurrencies(obs_list: List[Observation]) -> set:
    """已测并发集合。"""
    return {o.concurrency for o in obs_list}


def _lowest_failure_concurrency(obs_list: List[Observation]) -> Optional[int]:
    """已测质量失败点中的最低并发，作为后续不可向上跨越的边界。"""
    failures = [o.concurrency for o in obs_list if o.quality == QualityStatus.EXCEEDED]
    return min(failures) if failures else None


def _in_range(concurrency: int, lower: int, upper: int) -> bool:
    """判断并发是否在确认范围内。"""
    return lower <= concurrency <= upper


def _find_endpoints(center: int, all_obs: List[Observation],
                    lower: int, upper: int) -> Tuple[Optional[int], Optional[int]]:
    """找中心左右最近的已测档位作为端点。缺失侧用确认边界。"""
    tested = sorted(_tested_concurrencies(all_obs))
    left_endpoint = None
    for c in reversed(tested):
        if c < center:
            left_endpoint = c
            break
    if left_endpoint is None:
        left_endpoint = lower
    right_endpoint = None
    for c in tested:
        if c > center:
            right_endpoint = c
            break
    if right_endpoint is None:
        right_endpoint = upper
    return left_endpoint, right_endpoint


def _start_fine(task, observations, rounds_used, best, failure_boundary,
                current_center, current_left_endpoint, current_right_endpoint,
                current_side, decline_triggered=False, decline_reason=None):
    """从粗测转入细测，确定初始中心和端点。"""
    lower, upper = task.concurrency_range
    rounds_remaining = task.max_total_rounds - rounds_used

    if rounds_remaining <= 0:
        return SearchDecision(
            action="end_target", next_concurrency=None, next_phase=Phase.FINE,
            stop_reason=StopReason.BUDGET_EXHAUSTED,
            reason="预算用尽，无法进入细测",
            rounds_used=rounds_used, rounds_remaining=0,
            best_qualified_concurrency=best.concurrency,
            best_qualified_tps=best.tps,
            failure_boundary=failure_boundary)

    # 如果已有同组中心，继续该组
    if current_center is not None:
        return _continue_fine(task, observations, rounds_used, best,
                               failure_boundary, current_center,
                               current_left_endpoint, current_right_endpoint,
                               current_side)

    center = best.concurrency
    left_ep, right_ep = _find_endpoints(center, observations, lower, upper)
    left_cand = fine_midpoint(center, left_ep)
    right_cand = fine_midpoint(center, right_ep)
    tested = _tested_concurrencies(observations)

    left_valid = (left_cand != center and left_cand not in tested
                  and _in_range(left_cand, lower, upper))
    right_valid = (right_cand != center and right_cand not in tested
                   and _in_range(right_cand, lower, upper))
    # 质量失败边界：所有候选（含左侧）都受同一失败上界约束
    if failure_boundary is not None:
        if left_cand >= failure_boundary:
            left_valid = False
        if right_cand >= failure_boundary:
            right_valid = False

    # 无合法邻域候选时应结束，不自行找其他区间替代
    if not left_valid and not right_valid:
        return SearchDecision(
            action="end_target", next_concurrency=None, next_phase=Phase.FINE,
            stop_reason=StopReason.NO_CANDIDATES,
            reason=(
                f"细测中心{center}邻域无合法候选"
                f"（左{left_cand}右{right_cand}均被失败边界{failure_boundary}"
                "或范围/去重排除），不替代其他区间"
            ),
            center_concurrency=center, left_endpoint=left_ep,
            right_endpoint=right_ep,
            rounds_used=rounds_used, rounds_remaining=rounds_remaining,
            failure_boundary=failure_boundary,
            best_qualified_concurrency=best.concurrency,
            best_qualified_tps=best.tps)

    return _pick_side(task, rounds_used, rounds_remaining, best, failure_boundary,
                      center, left_ep, right_ep, left_cand, right_cand,
                      left_valid, right_valid, is_new_group=True,
                      decline_reason=decline_reason)


def _pick_side(task, rounds_used, rounds_remaining, best, failure_boundary,
               center, left_ep, right_ep, left_cand, right_cand,
               left_valid, right_valid, is_new_group=True, current_side=None,
               decline_reason=None):
    """先左后右选择细测候选；剩1轮优先合法左点。"""
    group_label = "新组" if is_new_group else "同组"
    # 保留转阶段原因作为前置依据
    prefix = ""
    if decline_reason and is_new_group:
        prefix = decline_reason + "；"
    if rounds_remaining == 1:
        if left_valid:
            return SearchDecision(
                action="run_fine", next_concurrency=left_cand,
                next_phase=Phase.FINE, stop_reason=StopReason.NONE,
                reason=f"{prefix}细测：{group_label}剩余1轮，优先合法左点 {left_cand}",
                center_concurrency=center, left_endpoint=left_ep,
                right_endpoint=right_ep, side=Side.LEFT,
                rounds_used=rounds_used, rounds_remaining=rounds_remaining,
                failure_boundary=failure_boundary,
                best_qualified_concurrency=best.concurrency,
                best_qualified_tps=best.tps)
        elif right_valid:
            return SearchDecision(
                action="run_fine", next_concurrency=right_cand,
                next_phase=Phase.FINE, stop_reason=StopReason.NONE,
                reason=f"{prefix}细测：{group_label}剩余1轮，左无效取右 {right_cand}",
                center_concurrency=center, left_endpoint=left_ep,
                right_endpoint=right_ep, side=Side.RIGHT,
                rounds_used=rounds_used, rounds_remaining=rounds_remaining,
                failure_boundary=failure_boundary,
                best_qualified_concurrency=best.concurrency,
                best_qualified_tps=best.tps)
        else:
            return SearchDecision(
                action="end_target", next_concurrency=None, next_phase=Phase.FINE,
                stop_reason=StopReason.NO_CANDIDATES,
                reason=f"细测：{group_label}无合法可测点",
                center_concurrency=center, left_endpoint=left_ep,
                right_endpoint=right_ep,
                rounds_used=rounds_used, rounds_remaining=rounds_remaining,
                failure_boundary=failure_boundary,
                best_qualified_concurrency=best.concurrency,
                best_qualified_tps=best.tps)

    # 正常先左
    if left_valid:
        return SearchDecision(
            action="run_fine", next_concurrency=left_cand,
            next_phase=Phase.FINE, stop_reason=StopReason.NONE,
            reason=f"{prefix}细测：{group_label}先左 {left_cand}（中心{center}）",
            center_concurrency=center, left_endpoint=left_ep,
            right_endpoint=right_ep, side=Side.LEFT,
            rounds_used=rounds_used, rounds_remaining=rounds_remaining,
            failure_boundary=failure_boundary,
            best_qualified_concurrency=best.concurrency,
            best_qualified_tps=best.tps)
    elif right_valid:
        return SearchDecision(
            action="run_fine", next_concurrency=right_cand,
            next_phase=Phase.FINE, stop_reason=StopReason.NONE,
            reason=f"{prefix}细测：{group_label}左无效先右 {right_cand}（中心{center}）",
            center_concurrency=center, left_endpoint=left_ep,
            right_endpoint=right_ep, side=Side.RIGHT,
            rounds_used=rounds_used, rounds_remaining=rounds_remaining,
            failure_boundary=failure_boundary,
            best_qualified_concurrency=best.concurrency,
            best_qualified_tps=best.tps)
    else:
        return SearchDecision(
            action="end_target", next_concurrency=None, next_phase=Phase.FINE,
            stop_reason=StopReason.NO_CANDIDATES,
            reason=f"细测：{group_label}左右候选均无效",
            center_concurrency=center, left_endpoint=left_ep,
            right_endpoint=right_ep,
            rounds_used=rounds_used, rounds_remaining=rounds_remaining,
            failure_boundary=failure_boundary,
            best_qualified_concurrency=best.concurrency,
            best_qualified_tps=best.tps)


def _continue_fine(task, observations, rounds_used, best, failure_boundary,
                    center, left_ep, right_ep, current_side):
    """继续当前细测组（中心不变）。"""
    lower, upper = task.concurrency_range
    rounds_remaining = task.max_total_rounds - rounds_used
    tested = _tested_concurrencies(observations)

    if rounds_remaining <= 0:
        return SearchDecision(
            action="end_target", next_concurrency=None, next_phase=Phase.FINE,
            stop_reason=StopReason.BUDGET_EXHAUSTED,
            reason="细测：6轮预算用尽",
            center_concurrency=center, left_endpoint=left_ep,
            right_endpoint=right_ep,
            rounds_used=rounds_used, rounds_remaining=0,
            failure_boundary=failure_boundary,
            best_qualified_concurrency=best.concurrency,
            best_qualified_tps=best.tps)

    left_cand = fine_midpoint(center, left_ep)
    right_cand = fine_midpoint(center, right_ep)
    left_valid = (left_cand != center and left_cand not in tested
                  and _in_range(left_cand, lower, upper))
    right_valid = (right_cand != center and right_cand not in tested
                   and _in_range(right_cand, lower, upper))
    # 新失败边界使原候选失效：左侧也受同一失败上界约束
    if failure_boundary is not None:
        if left_cand >= failure_boundary:
            left_valid = False
        if right_cand >= failure_boundary:
            right_valid = False

    # 同组中心在两侧完成前不变，先左后右
    if current_side == Side.LEFT or current_side is None:
        if left_valid:
            return SearchDecision(
                action="run_fine", next_concurrency=left_cand,
                next_phase=Phase.FINE, stop_reason=StopReason.NONE,
                reason=f"细测：同组左 {left_cand}（中心{center}）",
                center_concurrency=center, left_endpoint=left_ep,
                right_endpoint=right_ep, side=Side.LEFT,
                rounds_used=rounds_used, rounds_remaining=rounds_remaining,
                failure_boundary=failure_boundary,
                best_qualified_concurrency=best.concurrency,
                best_qualified_tps=best.tps)
        if right_valid:
            return SearchDecision(
                action="run_fine", next_concurrency=right_cand,
                next_phase=Phase.FINE, stop_reason=StopReason.NONE,
                reason=f"细测：同组右 {right_cand}（中心{center}）",
                center_concurrency=center, left_endpoint=left_ep,
                right_endpoint=right_ep, side=Side.RIGHT,
                rounds_used=rounds_used, rounds_remaining=rounds_remaining,
                failure_boundary=failure_boundary,
                best_qualified_concurrency=best.concurrency,
                best_qualified_tps=best.tps)
    elif current_side == Side.RIGHT:
        if right_valid:
            return SearchDecision(
                action="run_fine", next_concurrency=right_cand,
                next_phase=Phase.FINE, stop_reason=StopReason.NONE,
                reason=f"细测：同组右 {right_cand}（中心{center}）",
                center_concurrency=center, left_endpoint=left_ep,
                right_endpoint=right_ep, side=Side.RIGHT,
                rounds_used=rounds_used, rounds_remaining=rounds_remaining,
                failure_boundary=failure_boundary,
                best_qualified_concurrency=best.concurrency,
                best_qualified_tps=best.tps)
        if left_valid:
            return SearchDecision(
                action="run_fine", next_concurrency=left_cand,
                next_phase=Phase.FINE, stop_reason=StopReason.NONE,
                reason=f"细测：同组左 {left_cand}（中心{center}）",
                center_concurrency=center, left_endpoint=left_ep,
                right_endpoint=right_ep, side=Side.LEFT,
                rounds_used=rounds_used, rounds_remaining=rounds_remaining,
                failure_boundary=failure_boundary,
                best_qualified_concurrency=best.concurrency,
                best_qualified_tps=best.tps)

    # 同组两侧均完成，更新中心进入下一组 (BR-015)
    return _next_fine_group(task, observations, rounds_used, failure_boundary)


def _next_fine_group(task, observations, rounds_used, failure_boundary):
    """同组完成后更新最佳中心和邻点，进入下一组。"""
    lower, upper = task.concurrency_range
    rounds_remaining = task.max_total_rounds - rounds_used

    if rounds_remaining <= 0:
        best = _best_qualified(observations)
        b_conc = best.concurrency if best else None
        b_tps = best.tps if best else None
        return SearchDecision(
            action="end_target", next_concurrency=None, next_phase=Phase.FINE,
            stop_reason=StopReason.BUDGET_EXHAUSTED,
            reason="细测：6轮预算用尽，无更多组",
            rounds_used=rounds_used, rounds_remaining=0,
            failure_boundary=failure_boundary,
            best_qualified_concurrency=b_conc,
            best_qualified_tps=b_tps)

    best = _best_qualified(observations)
    if best is None:
        return SearchDecision(
            action="end_target", next_concurrency=None, next_phase=Phase.FINE,
            stop_reason=StopReason.NO_CANDIDATES,
            reason="细测：无合格候选",
            rounds_used=rounds_used, rounds_remaining=rounds_remaining,
            failure_boundary=failure_boundary)

    # 以新最佳合格并发为中心
    center = best.concurrency
    left_ep, right_ep = _find_endpoints(center, observations, lower, upper)
    left_cand = fine_midpoint(center, left_ep)
    right_cand = fine_midpoint(center, right_ep)
    tested = _tested_concurrencies(observations)

    left_valid = (left_cand != center and left_cand not in tested
                  and _in_range(left_cand, lower, upper))
    right_valid = (right_cand != center and right_cand not in tested
                   and _in_range(right_cand, lower, upper))
    # 失败边界约束所有候选，含左侧
    if failure_boundary is not None:
        if left_cand >= failure_boundary:
            left_valid = False
        if right_cand >= failure_boundary:
            right_valid = False

    # 无合法候选则结束，不自行找其他区间替代
    if not left_valid and not right_valid:
        return SearchDecision(
            action="end_target", next_concurrency=None, next_phase=Phase.FINE,
            stop_reason=StopReason.NO_CANDIDATES,
            reason=(
                f"细测中心{center}邻域无合法候选"
                f"（左{left_cand}右{right_cand}均被失败边界{failure_boundary}"
                "或范围/去重排除），不替代其他区间"
            ),
            center_concurrency=center, left_endpoint=left_ep,
            right_endpoint=right_ep,
            rounds_used=rounds_used, rounds_remaining=rounds_remaining,
            failure_boundary=failure_boundary,
            best_qualified_concurrency=best.concurrency,
            best_qualified_tps=best.tps)

    return _pick_side(task, rounds_used, rounds_remaining, best,
                      failure_boundary, center, left_ep, right_ep,
                      left_cand, right_cand, left_valid, right_valid,
                      is_new_group=True)


def _coarse_decision(task, observations, rounds_used, coarse_rounds_used,
                     current_phase, current_center, current_left_endpoint,
                     current_right_endpoint, current_side):
    """粗测阶段决策逻辑。"""
    lower, upper = task.concurrency_range
    preset = task.preset_levels
    rounds_remaining = task.max_total_rounds - rounds_used
    coarse_remaining = task.max_coarse_rounds - coarse_rounds_used
    coarse_obs = [o for o in observations if o.phase == Phase.COARSE]
    failure_boundary = _lowest_failure_concurrency(observations)

    # 首轮质量失败：结束该目标，不下探 (BR-012)
    if len(coarse_obs) == 1 and coarse_obs[0].quality == QualityStatus.EXCEEDED:
        return SearchDecision(
            action="end_target", next_concurrency=None, next_phase=Phase.COARSE,
            stop_reason=StopReason.FIRST_ROUND_FAILURE,
            reason="首轮质量超标且无合格候选，结束该目标，不下探",
            rounds_used=rounds_used, rounds_remaining=rounds_remaining,
            failure_boundary=failure_boundary)

    # 粗测预算用尽 (BR-006)
    if coarse_rounds_used >= task.max_coarse_rounds:
        best = _best_qualified(observations)
        if best is None:
            return SearchDecision(
                action="end_target", next_concurrency=None, next_phase=Phase.COARSE,
                stop_reason=StopReason.COARSE_BUDGET_EXHAUSTED,
                reason="粗测4轮用尽，无合格候选",
                rounds_used=rounds_used, rounds_remaining=rounds_remaining,
                failure_boundary=failure_boundary)
        return _start_fine(task, observations, rounds_used, best,
                           failure_boundary, current_center,
                           current_left_endpoint, current_right_endpoint,
                           current_side)

    # 确定下一预设档位
    tested_coarse_levels = [o.concurrency for o in coarse_obs]
    next_preset = None
    for level in preset:
        if level not in tested_coarse_levels:
            next_preset = level
            break

    # 预设档位用尽
    if next_preset is None:
        best = _best_qualified(observations)
        if best is None:
            return SearchDecision(
                action="end_target", next_concurrency=None, next_phase=Phase.COARSE,
                stop_reason=StopReason.PRESET_EXHAUSTED,
                reason="预设档位用尽，无合格候选",
                rounds_used=rounds_used, rounds_remaining=rounds_remaining,
                failure_boundary=failure_boundary)
        return _start_fine(task, observations, rounds_used, best,
                           failure_boundary, current_center,
                           current_left_endpoint, current_right_endpoint,
                           current_side)

    # 相邻粗测 3% 下降检查 (BR-008)
    if len(coarse_obs) >= 2:
        prev_coarse = coarse_obs[-2]
        curr_coarse = coarse_obs[-1]
        ratio = compute_decline_ratio(prev_coarse.tps, curr_coarse.tps)
        if ratio is not None and ratio >= task.decline_threshold:
            best = _best_qualified(observations)
            # 保留3%触发依据：记录比较值和降幅
            decline_reason = (
                f"相邻粗测TPS下降≥3%：上一{prev_coarse.concurrency}并发"
                f"TPS={prev_coarse.tps}，本轮{curr_coarse.concurrency}并发"
                f"TPS={curr_coarse.tps}，降幅={ratio}≥{task.decline_threshold}，"
                f"转细测中心{best.concurrency if best else '无'}"
            )
            if best is not None:
                return _start_fine(task, observations, rounds_used, best,
                                  failure_boundary, current_center,
                                  current_left_endpoint, current_right_endpoint,
                                  current_side, decline_triggered=True,
                                  decline_reason=decline_reason)
            return SearchDecision(
                action="end_target", next_concurrency=None, next_phase=Phase.COARSE,
                stop_reason=StopReason.DECLINE_TRIGGERED,
                reason=decline_reason + "，无合格候选",
                rounds_used=rounds_used, rounds_remaining=rounds_remaining,
                failure_boundary=failure_boundary)

    # 质量失败后停止向更高并发探索 (BR-011)
    if failure_boundary is not None and next_preset > failure_boundary:
        best = _best_qualified(observations)
        if best is not None:
            return _start_fine(task, observations, rounds_used, best,
                               failure_boundary, current_center,
                               current_left_endpoint, current_right_endpoint,
                               current_side)
        return SearchDecision(
            action="end_target", next_concurrency=None, next_phase=Phase.COARSE,
            stop_reason=StopReason.NO_CANDIDATES,
            reason="质量失败边界阻止更高档位，无合格候选",
            rounds_used=rounds_used, rounds_remaining=rounds_remaining,
            failure_boundary=failure_boundary)

    # 预算检查
    if rounds_remaining <= 0:
        best = _best_qualified(observations)
        if best is not None:
            return _start_fine(task, observations, rounds_used, best,
                               failure_boundary, current_center,
                               current_left_endpoint, current_right_endpoint,
                               current_side)
        return SearchDecision(
            action="end_target", next_concurrency=None, next_phase=Phase.COARSE,
            stop_reason=StopReason.BUDGET_EXHAUSTED,
            reason="6轮预算用尽",
            rounds_used=rounds_used, rounds_remaining=0,
            failure_boundary=failure_boundary)

    # 档位越界检查
    if not _in_range(next_preset, lower, upper):
        best = _best_qualified(observations)
        if best is not None:
            return _start_fine(task, observations, rounds_used, best,
                               failure_boundary, current_center,
                               current_left_endpoint, current_right_endpoint,
                               current_side)
        return SearchDecision(
            action="end_target", next_concurrency=None, next_phase=Phase.COARSE,
            stop_reason=StopReason.PRESET_EXHAUSTED,
            reason="下一预设档位超出范围",
            rounds_used=rounds_used, rounds_remaining=rounds_remaining,
            failure_boundary=failure_boundary)

    # 正常下一档粗测
    return SearchDecision(
        action="run_coarse", next_concurrency=next_preset,
        next_phase=Phase.COARSE, stop_reason=StopReason.NONE,
        reason=f"粗测下一预设档位 {next_preset}",
        rounds_used=rounds_used, rounds_remaining=rounds_remaining,
        failure_boundary=failure_boundary)


def decide_next(task, observations, current_phase=Phase.COARSE,
                current_center=None, current_left_endpoint=None,
                current_right_endpoint=None, current_side=None):
    """确定性寻峰主函数。

    纯函数：相同输入产生相同输出。不访问网络、文件、进程或模型。

    参数:
        task: TaskSpec 任务配置
        observations: 已测 Observation 列表（按轮号顺序）
        current_phase: 当前阶段 (coarse/fine)
        current_center: 细测当前中心（同组完成前不变）
        current_left_endpoint: 细测当前左端点
        current_right_endpoint: 细测当前右端点
        current_side: 当前细测侧 (left/right)

    返回:
        SearchDecision: 下一档决策及完整原因
    """
    rounds_used = len(observations)
    coarse_rounds_used = len([o for o in observations if o.phase == Phase.COARSE])
    lower, upper = task.concurrency_range

    # 无观测时：从首档开始
    if not observations:
        start = task.start_concurrency
        if not _in_range(start, lower, upper):
            return SearchDecision(
                action="end_target", next_concurrency=None,
                next_phase=Phase.COARSE,
                stop_reason=StopReason.NO_CANDIDATES,
                reason="起始并发超出确认范围",
                rounds_used=0,
                rounds_remaining=task.max_total_rounds)
        return SearchDecision(
            action="run_coarse", next_concurrency=start,
            next_phase=Phase.COARSE, stop_reason=StopReason.NONE,
            reason=f"粗测起始档位 {start}",
            rounds_used=0,
            rounds_remaining=task.max_total_rounds)

    # 6轮预算用尽
    if rounds_used >= task.max_total_rounds:
        best = _best_qualified(observations)
        b_conc = best.concurrency if best else None
        b_tps = best.tps if best else None
        failure_boundary = _lowest_failure_concurrency(observations)
        return SearchDecision(
            action="end_target", next_concurrency=None,
            next_phase=current_phase,
            stop_reason=StopReason.BUDGET_EXHAUSTED,
            reason="6轮预算用尽，正常结束",
            rounds_used=rounds_used, rounds_remaining=0,
            failure_boundary=failure_boundary,
            best_qualified_concurrency=b_conc,
            best_qualified_tps=b_tps)

    # 不可读观测：明确结束/拒绝调度，不把工厂伪造的TPS0当真实数据 (AC-026)
    last_obs = observations[-1]
    if last_obs.quality == QualityStatus.UNREADABLE:
        # 报告不可读应为缺失值，不补测、不继续调度
        best = _best_qualified(observations)
        b_conc = best.concurrency if best else None
        b_tps = best.tps if best else None
        return SearchDecision(
            action="end_target", next_concurrency=None,
            next_phase=current_phase,
            stop_reason=StopReason.UNREADABLE,
            reason=(
                f"目标 {last_obs.target_id} 第{last_obs.round_number}轮"
                f"并发{last_obs.concurrency}报告不可读，"
                "不可读TPS为缺失值，不补测，结束该目标"
            ),
            rounds_used=rounds_used,
            rounds_remaining=task.max_total_rounds - rounds_used,
            best_qualified_concurrency=b_conc,
            best_qualified_tps=b_tps)

    # 按阶段分发
    if current_phase == Phase.COARSE:
        return _coarse_decision(
            task, observations, rounds_used, coarse_rounds_used,
            current_phase, current_center, current_left_endpoint,
            current_right_endpoint, current_side)
    else:
        best = _best_qualified(observations)
        failure_boundary = _lowest_failure_concurrency(observations)
        if best is None:
            return SearchDecision(
                action="end_target", next_concurrency=None,
                next_phase=Phase.FINE,
                stop_reason=StopReason.NO_CANDIDATES,
                reason="细测阶段无合格候选",
                rounds_used=rounds_used,
                rounds_remaining=task.max_total_rounds - rounds_used,
                failure_boundary=failure_boundary)
        if current_center is not None:
            return _continue_fine(task, observations, rounds_used, best,
                                  failure_boundary, current_center,
                                  current_left_endpoint, current_right_endpoint,
                                  current_side)
        else:
            return _start_fine(task, observations, rounds_used, best,
                                failure_boundary, current_center,
                                current_left_endpoint, current_right_endpoint,
                                current_side)
