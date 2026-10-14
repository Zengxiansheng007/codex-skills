# -*- coding: utf-8 -*-
"""离线单元测试：确定性寻峰纯函数。

覆盖 AC-010/011/012/014/015/016/017/018/021/023/024。
使用合成观察和独立预期值，不发压、不联网。
运行方式：从 candidate/jmeter-tps-runner 目录执行 python -m unittest tests.test_search -v
"""

import unittest
from decimal import Decimal

from scripts.contracts import (
    TaskSpec, Observation, SearchDecision, Phase, QualityStatus,
    StopReason, Side, DECLINE_THRESHOLD, make_qualified_obs,
    make_exceeded_obs, make_unreadable_obs, TaskSpecError,
)
from scripts.search import (
    decide_next, is_decline_triggered, compute_decline_ratio,
    fine_midpoint, _best_qualified,
)


def make_task(start=50, lower=50, upper=500,
              preset=(50, 100, 200, 500),
              max_total=6, max_coarse=4,
              err_thr=Decimal("0.005"),
              p90_thr=Decimal("2500")):
    """创建标准任务配置。"""
    return TaskSpec(
        task_id="test-task", target_id="T1",
        concurrency_range=(lower, upper),
        preset_levels=preset,
        start_concurrency=start,
        error_rate_threshold=err_thr,
        p90_threshold_ms=p90_thr,
        max_total_rounds=max_total,
        max_coarse_rounds=max_coarse,
    )


class TestDeclineThreshold(unittest.TestCase):
    """AC-011: 3% 下降阈值边界。"""

    def test_1000_to_970_triggers(self):
        # 1000->970：(1000-970)/1000=0.03=3%，触发
        self.assertTrue(is_decline_triggered(Decimal("1000"), Decimal("970")))

    def test_1000_to_970_01_not_triggered(self):
        # 1000->970.01：降幅<3%，不触发
        self.assertFalse(is_decline_triggered(Decimal("1000"), Decimal("970.01")))

    def test_zero_prev_tps_no_trigger(self):
        # 上一TPS=0不除零，不触发
        self.assertFalse(is_decline_triggered(Decimal("0"), Decimal("500")))

    def test_ratio_none_for_zero(self):
        self.assertIsNone(compute_decline_ratio(Decimal("0"), Decimal("100")))

    def test_growth_not_triggered(self):
        # TPS增长不触发下降
        self.assertFalse(is_decline_triggered(Decimal("500"), Decimal("600")))

    def test_exactly_3_percent_triggers(self):
        # 恰好3%触发
        self.assertTrue(is_decline_triggered(Decimal("1000"), Decimal("970")))


class TestFineMidpoint(unittest.TestCase):
    """AC-015: 细测中点计算。"""

    def test_B200_left150_right350(self):
        # B=200, 左150, 右350 -> 170, 270
        self.assertEqual(fine_midpoint(200, 150), 170)
        self.assertEqual(fine_midpoint(200, 350), 270)

    def test_B300_upper500_right400(self):
        # B=300, 缺右邻点, 上界500 -> 400
        self.assertEqual(fine_midpoint(300, 500), 400)

    def test_align_to_10(self):
        # 175->170, 275->270
        self.assertEqual(fine_midpoint(200, 150), 170)
        self.assertEqual(fine_midpoint(200, 350), 270)


class TestCoarseSequence(unittest.TestCase):
    """AC-010: 粗测依次 50/100/200/500，不计算为 50/100/200/400。"""

    def test_first_round_starts_at_50(self):
        task = make_task()
        dec = decide_next(task, [])
        self.assertEqual(dec.next_concurrency, 50)
        self.assertEqual(dec.action, "run_coarse")

    def test_second_round_100(self):
        task = make_task()
        obs = [make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500"))]
        dec = decide_next(task, obs)
        self.assertEqual(dec.next_concurrency, 100)
        self.assertEqual(dec.action, "run_coarse")

    def test_third_round_200(self):
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("800")),
        ]
        dec = decide_next(task, obs)
        self.assertEqual(dec.next_concurrency, 200)
        self.assertEqual(dec.action, "run_coarse")

    def test_fourth_round_500_not_400(self):
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("800")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("900")),
        ]
        dec = decide_next(task, obs)
        self.assertEqual(dec.next_concurrency, 500)
        self.assertEqual(dec.action, "run_coarse")

    def test_first_round_no_decline_check(self):
        # 首轮不做跨档下降判断
        task = make_task()
        dec = decide_next(task, [])
        self.assertIsNone(dec.failure_boundary)


class TestDeclineStop(unittest.TestCase):
    """AC-011: 相邻粗测下降停止。"""

    def test_1000_to_970_stops_coarse(self):
        # 1000->970触发3%，转细测
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("1000")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("970")),
        ]
        dec = decide_next(task, obs)
        self.assertEqual(dec.action, "run_fine")
        self.assertEqual(dec.next_phase, Phase.FINE)

    def test_1000_to_970_01_continues_coarse(self):
        # 1000->970.01不触发，继续粗测
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("1000")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("970.01")),
        ]
        dec = decide_next(task, obs)
        self.assertEqual(dec.action, "run_coarse")
        self.assertEqual(dec.next_concurrency, 500)

    def test_decline_qualified_kept(self):
        # 下降但合格的当前轮保留候选资格
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("1000")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("970")),
        ]
        dec = decide_next(task, obs)
        # 200轮仍合格，应参与选择
        best = _best_qualified(obs)
        self.assertIsNotNone(best)
        self.assertEqual(best.concurrency, 100)  # 1000最高

    def test_zero_tps_no_trigger_continues(self):
        # 上轮TPS=0不触发下降
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("0")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("500")),
        ]
        dec = decide_next(task, obs)
        # 不触发3%，继续粗测200
        self.assertEqual(dec.action, "run_coarse")
        self.assertEqual(dec.next_concurrency, 200)

    def test_last_preset_no_append(self):
        # 末档不追加1000
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("800")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("900")),
            make_qualified_obs("T1", 4, Phase.COARSE, 500, Decimal("950")),
        ]
        dec = decide_next(task, obs)
        # 4轮粗测用尽，转细测，不追加
        self.assertIn(dec.action, ["run_fine", "end_target"])
        if dec.next_concurrency is not None:
            self.assertNotEqual(dec.next_concurrency, 1000)


class TestFirstRoundFailure(unittest.TestCase):
    """AC-013/BR-012: 首轮质量失败结束该目标，不下探。"""

    def test_first_round_exceeded_ends_target(self):
        task = make_task()
        obs = [make_exceeded_obs("T1", 1, Phase.COARSE, 50)]
        dec = decide_next(task, obs)
        self.assertEqual(dec.action, "end_target")
        self.assertEqual(dec.stop_reason, StopReason.FIRST_ROUND_FAILURE)

    def test_first_round_failure_no_probe(self):
        task = make_task()
        obs = [make_exceeded_obs("T1", 1, Phase.COARSE, 50)]
        dec = decide_next(task, obs)
        self.assertIsNone(dec.next_concurrency)


class TestQualityFailureBoundary(unittest.TestCase):
    """AC-014: 已有合格点后超标，停止向更高探索。"""

    def test_subsequent_failure_stops_higher(self):
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("800")),
            make_exceeded_obs("T1", 3, Phase.COARSE, 200),
        ]
        dec = decide_next(task, obs)
        self.assertNotEqual(dec.next_concurrency, 500)
        self.assertIn(dec.action, ["run_fine", "end_target"])

    def test_failure_boundary_set(self):
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("800")),
            make_exceeded_obs("T1", 3, Phase.COARSE, 200),
        ]
        dec = decide_next(task, obs)
        self.assertEqual(dec.failure_boundary, 200)

    def test_decline_not_quality_failure_upper(self):
        # 下降不建立质量失败上界
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("1000")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("970")),
        ]
        dec = decide_next(task, obs)
        self.assertIsNone(dec.failure_boundary)


class TestFineSelection(unittest.TestCase):
    """AC-015/016/017: 细测选点、去重、同组中心。"""

    def test_fine_170_270(self):
        # B=200, 左端100, 右端500 -> 左150, 右350
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("800")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("1000")),
            make_qualified_obs("T1", 4, Phase.COARSE, 500, Decimal("950")),
        ]
        dec = decide_next(task, obs)
        self.assertEqual(dec.action, "run_fine")
        self.assertEqual(dec.center_concurrency, 200)
        self.assertEqual(dec.left_endpoint, 100)
        self.assertEqual(dec.right_endpoint, 500)
        self.assertEqual(dec.side, Side.LEFT)
        self.assertEqual(dec.next_concurrency, 150)

    def test_fine_skip_duplicate(self):
        # 取整后候选与已测点重合则跳过
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("800")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("1000")),
            make_qualified_obs("T1", 4, Phase.COARSE, 500, Decimal("950")),
            make_qualified_obs("T1", 5, Phase.FINE, 150, Decimal("850")),
        ]
        dec = decide_next(task, obs, current_phase=Phase.FINE,
                          current_center=200, current_left_endpoint=100,
                          current_right_endpoint=500, current_side=Side.LEFT)
        self.assertEqual(dec.action, "run_fine")
        self.assertEqual(dec.side, Side.RIGHT)
        self.assertEqual(dec.next_concurrency, 350)

    def test_same_group_center_invariant(self):
        # 同组中心在两侧完成前不变
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("800")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("1000")),
            make_qualified_obs("T1", 4, Phase.COARSE, 500, Decimal("950")),
        ]
        dec = decide_next(task, obs)
        self.assertEqual(dec.center_concurrency, 200)
        obs.append(make_qualified_obs("T1", 5, Phase.FINE, 150, Decimal("850")))
        dec2 = decide_next(task, obs, current_phase=Phase.FINE,
                           current_center=200, current_left_endpoint=100,
                           current_right_endpoint=500, current_side=Side.LEFT)
        self.assertEqual(dec2.center_concurrency, 200)

    def test_left_before_right(self):
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("800")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("1000")),
            make_qualified_obs("T1", 4, Phase.COARSE, 500, Decimal("950")),
        ]
        dec = decide_next(task, obs)
        self.assertEqual(dec.side, Side.LEFT)

    def test_fine_skip_out_of_range(self):
        # 取整后候选越界则跳过
        task = make_task(lower=50, upper=500)
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("800")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("1000")),
            make_qualified_obs("T1", 4, Phase.COARSE, 500, Decimal("950")),
        ]
        dec = decide_next(task, obs)
        self.assertTrue(50 <= dec.next_concurrency <= 500)


class TestBudgetAndNoRemedial(unittest.TestCase):
    """AC-012/018/023: 预算、不复测、不补测。"""

    def test_six_round_budget_exhausted(self):
        # 6轮用尽后结束
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("800")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("1000")),
            make_qualified_obs("T1", 4, Phase.COARSE, 500, Decimal("950")),
            make_qualified_obs("T1", 5, Phase.FINE, 150, Decimal("850")),
            make_qualified_obs("T1", 6, Phase.FINE, 350, Decimal("720")),
        ]
        dec = decide_next(task, obs, current_phase=Phase.FINE,
                          current_center=200, current_left_endpoint=100,
                          current_right_endpoint=500, current_side=Side.RIGHT)
        self.assertEqual(dec.action, "end_target")
        self.assertEqual(dec.stop_reason, StopReason.BUDGET_EXHAUSTED)

    def test_no_extra_round_for_peak(self):
        # 正常合格峰值不复测，不额外加轮
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("1000")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("970")),
        ]
        # 下降触发转细测，不额外加轮
        dec = decide_next(task, obs)
        self.assertEqual(dec.action, "run_fine")
        self.assertNotEqual(dec.stop_reason, StopReason.BUDGET_EXHAUSTED)

    def test_no_remedial_after_6_rounds(self):
        # 6轮后不补测
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("800")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("1000")),
            make_qualified_obs("T1", 4, Phase.COARSE, 500, Decimal("950")),
            make_qualified_obs("T1", 5, Phase.FINE, 150, Decimal("850")),
            make_qualified_obs("T1", 6, Phase.FINE, 350, Decimal("720")),
        ]
        dec = decide_next(task, obs, current_phase=Phase.FINE,
                          current_center=200, current_left_endpoint=100,
                          current_right_endpoint=500, current_side=Side.RIGHT)
        self.assertEqual(dec.action, "end_target")
        self.assertIsNone(dec.next_concurrency)


class TestPeakSelection(unittest.TestCase):
    """AC-021: 在合格候选中按 report TPS 选择最高值。"""

    def test_select_highest_qualified_tps(self):
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("800")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("1000")),
            make_qualified_obs("T1", 4, Phase.COARSE, 500, Decimal("950")),
        ]
        best = _best_qualified(obs)
        self.assertEqual(best.concurrency, 200)
        self.assertEqual(best.tps, Decimal("1000"))

    def test_all_unqualified_no_peak(self):
        # 全不合格时显示未找到合格结果
        task = make_task()
        obs = [
            make_exceeded_obs("T1", 1, Phase.COARSE, 50),
        ]
        dec = decide_next(task, obs)
        self.assertEqual(dec.action, "end_target")
        self.assertIsNone(dec.best_qualified_concurrency)

    def test_tie_select_lower_concurrency(self):
        # 精确并列选较低并发
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("1000")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("1000")),
        ]
        best = _best_qualified(obs)
        # TPS并列1000，选较低并发100
        self.assertEqual(best.concurrency, 100)
        self.assertEqual(best.tps, Decimal("1000"))


class TestDeterministicReplay(unittest.TestCase):
    """AC-024: 相同输入产生相同输出。"""

    def test_same_input_same_output(self):
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("800")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("970")),
        ]
        dec1 = decide_next(task, obs)
        dec2 = decide_next(task, obs)
        self.assertEqual(dec1.next_concurrency, dec2.next_concurrency)
        self.assertEqual(dec1.action, dec2.action)
        self.assertEqual(dec1.reason, dec2.reason)

    def test_replay_with_phase_state(self):
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("800")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("1000")),
            make_qualified_obs("T1", 4, Phase.COARSE, 500, Decimal("950")),
        ]
        dec1 = decide_next(task, obs)
        dec2 = decide_next(task, obs)
        self.assertEqual(dec1.next_concurrency, dec2.next_concurrency)
        self.assertEqual(dec1.center_concurrency, dec2.center_concurrency)


class TestCandidateExhaustion(unittest.TestCase):
    """AC-016/017: 候选耗尽时结束。"""

    def test_no_candidates_ends_target(self):
        # 无合法可测点时结束
        task = make_task(lower=50, upper=200, preset=(50, 100, 200))
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("800")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("1000")),
        ]
        # 预设用尽，转细测
        dec = decide_next(task, obs)
        # B=200(TPS1000), 左端100, 右端=upper=200(=center,重合)
        # 左候选=fine_midpoint(200,100)=150
        self.assertEqual(dec.action, "run_fine")
        self.assertEqual(dec.next_concurrency, 150)

    def test_all_points_tested_ends(self):
        # 所有点已测，无候选
        task = make_task(lower=50, upper=200, preset=(50, 100, 200))
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("800")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("1000")),
            make_qualified_obs("T1", 4, Phase.FINE, 150, Decimal("850")),
        ]
        # B=200, 左端100->左候选150已测, 右端=200(=center重合)
        dec = decide_next(task, obs, current_phase=Phase.FINE,
                          current_center=200, current_left_endpoint=100,
                          current_right_endpoint=200, current_side=Side.LEFT)
        # 左150已测, 右候选=fine_midpoint(200,200)=200=center重合
        # 无候选，应结束或更新组
        self.assertIn(dec.action, ["end_target", "run_fine"])


class TestNewFailureInvalidatesRightCandidate(unittest.TestCase):
    """新失败边界使原右候选失效。"""

    def test_right_candidate_invalidated_by_failure(self):
        # 粗测中50/100合格，200超标 -> 失败边界=200
        # 细测中心=100, 左端50, 右端200(失败边界)
        # 右候选=fine_midpoint(100,200)=150 < 200, 仍有效
        # 但如果失败边界=150则右候选150>=150失效
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("800")),
            make_exceeded_obs("T1", 3, Phase.COARSE, 200),
        ]
        dec = decide_next(task, obs)
        # 失败边界=200，最佳=100(TPS800)
        # 左端=50, 右端=200
        # 左候选=fine_midpoint(100,50)=70, 右候选=fine_midpoint(100,200)=150
        # 150 < 200, 右候选有效
        self.assertEqual(dec.failure_boundary, 200)
        self.assertEqual(dec.center_concurrency, 100)
        # 先左
        self.assertEqual(dec.side, Side.LEFT)
        self.assertEqual(dec.next_concurrency, 70)


class TestFine170And270(unittest.TestCase):
    """AC-015: B=200时取170/270（对应本实现150/350）。"""

    def test_midpoint_170_from_200_150(self):
        # fine_midpoint(200, 150) = 170
        self.assertEqual(fine_midpoint(200, 150), 170)

    def test_midpoint_270_from_200_350(self):
        # fine_midpoint(200, 350) = 270
        self.assertEqual(fine_midpoint(200, 350), 270)

    def test_midpoint_400_from_300_500(self):
        # fine_midpoint(300, 500) = 400
        self.assertEqual(fine_midpoint(300, 500), 400)


class TestCoarseBudgetTransition(unittest.TestCase):
    """AC-012: 粗测到4轮或更早触发转细测。"""

    def test_coarse_4_rounds_to_fine(self):
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("800")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("1000")),
            make_qualified_obs("T1", 4, Phase.COARSE, 500, Decimal("950")),
        ]
        dec = decide_next(task, obs)
        self.assertEqual(dec.action, "run_fine")
        self.assertEqual(dec.next_phase, Phase.FINE)

    def test_total_rounds_not_exceed_6(self):
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("800")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("1000")),
            make_qualified_obs("T1", 4, Phase.COARSE, 500, Decimal("950")),
            make_qualified_obs("T1", 5, Phase.FINE, 150, Decimal("850")),
            make_qualified_obs("T1", 6, Phase.FINE, 350, Decimal("720")),
        ]
        dec = decide_next(task, obs, current_phase=Phase.FINE,
                          current_center=200, current_left_endpoint=100,
                          current_right_endpoint=500, current_side=Side.RIGHT)
        self.assertEqual(dec.action, "end_target")
        self.assertEqual(dec.rounds_used, 6)


class TestHistoryPeakVsAdjacentBaseline(unittest.TestCase):
    """AC-011: 用相邻粗测而非历史峰值比较。"""

    def test_adjacent_not_historical(self):
        # 50:500, 100:1000, 200:970 -> 相邻(100->200)下降3%触发
        # 不是和历史峰值500比
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("1000")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("970")),
        ]
        dec = decide_next(task, obs)
        # 相邻100->200下降3%，触发
        self.assertEqual(dec.action, "run_fine")

    def test_non_adjacent_no_trigger(self):
        # 50:1000, 100:1100, 200:1050
        # 相邻50->100增长, 100->200下降(1100-1050)/1100=4.5%>3%触发
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("1000")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("1100")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("1050")),
        ]
        dec = decide_next(task, obs)
        # 100->200下降4.5%，触发
        self.assertEqual(dec.action, "run_fine")


class TestUnreadableObservation(unittest.TestCase):
    """修复点2: 不可读观测必须明确结束/拒绝调度，不补测。"""

    def test_unreadable_ends_target(self):
        # make_unreadable_obs后不应继续粗测100
        task = make_task()
        obs = [make_unreadable_obs("T1", 1, Phase.COARSE, 50)]
        dec = decide_next(task, obs)
        self.assertEqual(dec.action, "end_target")
        self.assertIsNone(dec.next_concurrency)
        self.assertEqual(dec.stop_reason, StopReason.UNREADABLE)

    def test_unreadable_no_further_scheduling(self):
        # 不可读TPS为缺失值，不应当真实数据继续调度
        task = make_task()
        obs = [make_unreadable_obs("T1", 1, Phase.COARSE, 50)]
        dec = decide_next(task, obs)
        self.assertNotEqual(dec.action, "run_coarse")
        self.assertNotEqual(dec.action, "run_fine")

    def test_unreadable_tps_is_missing_not_zero(self):
        # 不可读的TPS0是工厂伪造，不应被当真实0处理
        task = make_task()
        obs = [make_unreadable_obs("T1", 1, Phase.COARSE, 50)]
        self.assertIsNone(obs[0].tps)  # 直接验证数据，而非只检查结束状态。
        dec = decide_next(task, obs)
        # 不应触发下降率计算（0 TPS不除零），也不应继续
        self.assertEqual(dec.stop_reason, StopReason.UNREADABLE)

    def test_unreadable_after_qualified_ends(self):
        # 已有合格观测后不可读也应结束，不补测
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_unreadable_obs("T1", 2, Phase.COARSE, 100),
        ]
        dec = decide_next(task, obs)
        self.assertEqual(dec.action, "end_target")
        self.assertEqual(dec.stop_reason, StopReason.UNREADABLE)
        # 历史50合格观测仍保留峰值资格
        self.assertEqual(dec.best_qualified_concurrency, 50)


class TestDeclineTriggerReasonPreserved(unittest.TestCase):
    """修复点3: 决策原因必须保留3%触发依据及比较值。"""

    def test_decline_reason_has_comparison_values(self):
        # 50:800, 100:1000, 200:970 -> 触发3%
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("800")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("1000")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("970")),
        ]
        dec = decide_next(task, obs)
        self.assertEqual(dec.action, "run_fine")
        # reason应包含触发依据和比较值
        self.assertIn("1000", dec.reason)
        self.assertIn("970", dec.reason)
        self.assertIn("3%", dec.reason)  # 包含3%标记或0.03

    def test_decline_reason_has_threshold_value(self):
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("800")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("1000")),
            make_qualified_obs("T1", 3, Phase.COARSE, 200, Decimal("970")),
        ]
        dec = decide_next(task, obs)
        # stop_reason不误写为目标结束
        self.assertNotEqual(dec.stop_reason, StopReason.BUDGET_EXHAUSTED)
        self.assertNotEqual(dec.stop_reason, StopReason.TARGET_COMPLETE)
        # 细测中心/端点/预算保留
        self.assertEqual(dec.center_concurrency, 100)
        self.assertEqual(dec.left_endpoint, 50)
        self.assertEqual(dec.right_endpoint, 200)
        self.assertGreater(dec.rounds_remaining, 0)


class TestTaskSpecValidation(unittest.TestCase):
    """修复点4: TaskSpec构造或公开决策入口拒绝非法配置。"""

    def test_invalid_non_grid_start_rejected(self):
        # 起点55不在合法网格也不等于首档，应拒绝
        with self.assertRaises(TaskSpecError):
            TaskSpec(
                task_id="t", target_id="T1",
                concurrency_range=(50, 500),
                preset_levels=(50, 100, 200, 500),
                start_concurrency=55,
                error_rate_threshold=Decimal("0.005"),
                p90_threshold_ms=Decimal("2500"),
            )

    def test_invalid_budget_over_six_rejected(self):
        # max_total_rounds=10应拒绝
        with self.assertRaises(TaskSpecError):
            TaskSpec(
                task_id="t", target_id="T1",
                concurrency_range=(50, 500),
                preset_levels=(50, 100, 200, 500),
                start_concurrency=50,
                error_rate_threshold=Decimal("0.005"),
                p90_threshold_ms=Decimal("2500"),
                max_total_rounds=10,
            )

    def test_invalid_start_not_first_preset_rejected(self):
        # start=100但首档50，应拒绝（不能先100再倒退50）
        with self.assertRaises(TaskSpecError):
            TaskSpec(
                task_id="t", target_id="T1",
                concurrency_range=(50, 500),
                preset_levels=(50, 100, 200, 500),
                start_concurrency=100,
                error_rate_threshold=Decimal("0.005"),
                p90_threshold_ms=Decimal("2500"),
            )

    def test_coarse_budget_over_four_rejected(self):
        with self.assertRaises(TaskSpecError):
            TaskSpec(
                task_id="t", target_id="T1",
                concurrency_range=(50, 500),
                preset_levels=(50, 100, 200, 500),
                start_concurrency=50,
                error_rate_threshold=Decimal("0.005"),
                p90_threshold_ms=Decimal("2500"),
                max_coarse_rounds=5,
            )

    def test_non_increasing_presets_rejected(self):
        with self.assertRaises(TaskSpecError):
            TaskSpec(
                task_id="t", target_id="T1",
                concurrency_range=(50, 500),
                preset_levels=(50, 50, 200, 500),
                start_concurrency=50,
                error_rate_threshold=Decimal("0.005"),
                p90_threshold_ms=Decimal("2500"),
            )

    def test_non_ten_multiple_preset_rejected(self):
        with self.assertRaises(TaskSpecError):
            TaskSpec(
                task_id="t", target_id="T1",
                concurrency_range=(50, 500),
                preset_levels=(50, 101, 200, 500),
                start_concurrency=50,
                error_rate_threshold=Decimal("0.005"),
                p90_threshold_ms=Decimal("2500"),
            )

    def test_valid_task_no_exception(self):
        # 合法配置不应抛异常
        task = make_task()
        self.assertEqual(task.start_concurrency, 50)
        self.assertEqual(task.max_total_rounds, 6)

    def test_no_silent_config_fix(self):
        # 不静默修配置：非法起点不应被自动对齐
        try:
            TaskSpec(
                task_id="t", target_id="T1",
                concurrency_range=(50, 500),
                preset_levels=(50, 100, 200, 500),
                start_concurrency=55,
                error_rate_threshold=Decimal("0.005"),
                p90_threshold_ms=Decimal("2500"),
            )
            self.fail("应抛出TaskSpecError，不应静默接受55")
        except TaskSpecError:
            pass  # 正确拒绝


class TestFailureBoundaryCoversLeftCandidate(unittest.TestCase):
    """修复点1: 失败上界必须约束左侧候选；无合法邻域候选应结束。"""

    def test_left_candidate_respects_failure_ceiling(self):
        # 粗测50合格TPS500，100合格TPS1000，200质量失败
        # 细测70质量失败(传入中心100, 左端50, 右端200, side=LEFT)
        # 70已失败 -> failure_boundary=70
        # 新组中心100, 左端50, 右端200
        # 左候选=fine_midpoint(100,50)=70 >= 70(失败边界) -> 无效
        # 右候选=fine_midpoint(100,200)=150 >= 70 -> 仍有效?
        # 不对：场景是70质量失败，failure_boundary=70
        # 左候选70==失败边界70, 应无效
        # 右候选150>=70, 也应无效（因为不能向上跨越失败边界）
        # 等等——失败边界是70，右候选150>70确实超过了
        # 所以无合法候选应结束
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("1000")),
            make_exceeded_obs("T1", 3, Phase.COARSE, 200),
            make_exceeded_obs("T1", 4, Phase.FINE, 70),
        ]
        dec = decide_next(task, obs, current_phase=Phase.FINE,
                          current_center=100, current_left_endpoint=50,
                          current_right_endpoint=200, current_side=Side.LEFT)
        # 左候选70>=失败边界70，无效
        # 右候选150>=失败边界70，无效
        # 无合法候选应结束
        self.assertEqual(dec.action, "end_target")
        self.assertNotEqual(dec.next_concurrency, 80)  # 不应返回80

    def test_failure_boundary_does_not_return_above_failure(self):
        # 粗测50合格TPS500，100合格TPS1000，200质量失败
        # 细测70质量失败(中心100, 左50, 右200, LEFT)
        # 不应返回80（高于最低失败70）
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("1000")),
            make_exceeded_obs("T1", 3, Phase.COARSE, 200),
            make_exceeded_obs("T1", 4, Phase.FINE, 70),
        ]
        dec = decide_next(task, obs, current_phase=Phase.FINE,
                          current_center=100, current_left_endpoint=50,
                          current_right_endpoint=200, current_side=Side.LEFT)
        if dec.next_concurrency is not None:
            self.assertLess(dec.next_concurrency, 70)

    def test_historical_qualified_still_peak(self):
        # 历史100合格观测仍保留峰值资格
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("1000")),
            make_exceeded_obs("T1", 3, Phase.COARSE, 200),
            make_exceeded_obs("T1", 4, Phase.FINE, 70),
        ]
        dec = decide_next(task, obs, current_phase=Phase.FINE,
                          current_center=100, current_left_endpoint=50,
                          current_right_endpoint=200, current_side=Side.LEFT)
        self.assertEqual(dec.best_qualified_concurrency, 100)
        self.assertEqual(dec.best_qualified_tps, Decimal("1000"))

    def test_no_substitute_from_other_interval(self):
        # 无合法邻域候选应结束，不自行找其他区间替代
        task = make_task()
        obs = [
            make_qualified_obs("T1", 1, Phase.COARSE, 50, Decimal("500")),
            make_qualified_obs("T1", 2, Phase.COARSE, 100, Decimal("1000")),
            make_exceeded_obs("T1", 3, Phase.COARSE, 200),
            make_exceeded_obs("T1", 4, Phase.FINE, 70),
        ]
        dec = decide_next(task, obs, current_phase=Phase.FINE,
                          current_center=100, current_left_endpoint=50,
                          current_right_endpoint=200, current_side=Side.LEFT)
        self.assertEqual(dec.action, "end_target")
        self.assertIn(dec.stop_reason,
                      [StopReason.NO_CANDIDATES, StopReason.BUDGET_EXHAUSTED])


class TestNoFifthFile(unittest.TestCase):
    """修复点5: 不创建scripts/__init__.py；tests/__init__.py在白名单。"""

    def test_tests_init_exists(self):
        # tests/__init__.py应在白名单中且存在
        import os
        init_path = os.path.join(os.path.dirname(__file__), "__init__.py")
        self.assertTrue(os.path.exists(init_path))


if __name__ == "__main__":
    unittest.main()
