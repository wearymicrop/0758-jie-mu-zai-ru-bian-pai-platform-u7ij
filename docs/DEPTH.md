# 深度登记 · 节目载入编排台

- 规模：中型
- 使用者：剧场值班员按剧场排期批准载入日执行单。
- 核心规则：依赖图先验，逐工单找舞台、剧场和流动技师的共同空段。

## 功能模块

| 模块 | 使用者动作 | 入口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 演出工单 | 逐行采信与冲突隔离 | `GET /api/samples/{sample}/orders` | `app/modules/orders/intake.py` | `tests/test_orders.py` |
| M2 工序依赖 | 查环并检查缺失前置 | `GET /api/samples/{sample}/dependencies` | `app/modules/dependencies/checks.py` | `tests/test_dependencies.py` |
| M3 工种日历 | 核对有效开工交集 | `GET /api/samples/{sample}/calendars` | `app/modules/calendars/registry.py` | `tests/test_calendars.py` |
| M4 工位冲突 | 定位重叠预约与未知资源 | `GET /api/samples/{sample}/conflicts` | `app/modules/conflicts/occupancy.py` | `tests/test_conflicts.py` |
| M5 转场排程 | 按工种、工位和预约找空段 | `GET /api/samples/{sample}/schedule` | `app/modules/schedule/planner.py` | `tests/test_schedule.py` |
| M6 超时勾稽 | 复核工单覆盖及资源碰撞 | `GET /api/samples/{sample}/reconcile` | `app/modules/reconcile/audit.py` | `tests/test_reconcile.py` |
| M7 执行清单 | 归档各工位执行顺序 | `GET /api/samples/{sample}/dispatch` | `app/modules/dispatch/checklist.py` | `tests/test_dispatch.py` |
| M8 停场恢复 | 封场事件后重排唯一执行单 | `POST /api/recoveries/preview` | `app/modules/recovery/planner.py` | `tests/test_recovery.py` |

## 陷阱登记

| TRAP | 现象 | 朴素实现会怎样 | 本项目处理 | 处理位置 | 测试 |
|---|---|---|---|---|---|
| TRAP-02 | 带 BOM 的工单 | 首行解码失败 | 文件首字符清理后保留行号 | `app/modules/orders/intake.py` | `tests/test_orders.py::test_bom_and_source_line` |
| TRAP-07 | 时长为未知 | 误当零分钟 | 无效行留下源值 | `app/modules/orders/contract.py` | `tests/test_orders.py::test_sentinel_refused` |
| TRAP-14 | 同号时长不同 | 后写覆盖 | 同号两行隔离 | `app/modules/orders/intake.py` | `tests/test_orders.py::test_conflicting_rollback` |
| TRAP-16 | 工单尾行截断 | 整个导入中断 | 保留截断物理行，继续采信 | `app/modules/orders/intake.py` | `tests/test_orders.py::test_truncated_record` |
| TRAP-18 | 空文本或空行 | 误作正常工单 | 按物理行分类 | `app/modules/orders/intake.py` | `tests/test_orders.py::test_blank_distinguished` |
| TRAP-19 | 重叠预约连续阻塞 | 只避第一条预约 | 跳过所有当前阻塞的最大结束点 | `app/modules/schedule/search.py` | `tests/test_schedule.py::test_skips_over_both_holds` |
| TRAP-20 | 双节点环和自环 | 把下游工序也认作成环 | 强连通分量标记环成员 | `app/modules/dependencies/graph.py` | `tests/test_dependencies.py::test_cycle_members` |
| TRAP-23 | 预约与工序端点相邻 | 多占一分钟 | 半开区间统一判断 | `app/modules/calendars/intervals.py` | `tests/test_calendars.py::test_adjacent_endpoints` |
| TRAP-24 | 封场窗内尚未开工的工序与封场端点相接 | 当作不受影响而锁定 | 仅「巡检前完工」或「起点不早于封场结束」才锁定 | `app/modules/recovery/planner.py` | `tests/test_recovery.py::test_locked_work_is_kept_as_fact` |
| TRAP-25 | 备用舞台改场与原工位同分开工 | 无规则摇摆或任意改场 | 按最早开工排序，同分原工位优先 | `app/modules/recovery/planner.py` | `tests/test_recovery.py::test_tie_break_prefers_original_stage` |
| TRAP-26 | 开工中工序被改场后丢失开工事实 | active 计数归零、现场无法交接 | `entry_status` 记开工事实，`recovery_status` 记最终安排，两维正交 | `app/modules/recovery/planner.py` | `tests/test_recovery.py::test_started_work_is_active_and_unstarted_is_waiting` |
| TRAP-27 | 同一停场事件重复下发 | 生成第二份执行单 | 按规则版本+输入摘要+事件摘要取摘要，归档表幂等 upsert | `app/modules/recovery/archive.py` | `tests/test_recovery.py::test_archive_idempotent_same_event_single_record` |

除空输入对照外，陷阱由 `sample_data/dirty/orders.jsonl` 与 `sample_data/dirty/calendar.json` 触发。预约相邻对照由 `sample_data/clean/calendar.json` 提供。

## 对账

- 输入行 = 已落位 + 待排 + 隔离工单 + 源隔离 + 重传 + 空行。
- 复核同工位、同技师、预约、前置顺序及两侧键集合。超时在已落位内单列。
- 技师的选择按最早可用、技师号决定。固定预约交叠与排程碰撞分别计数。

## 停场恢复（M8）

- 输入是停场事件：事件号、封场工位、起止、巡检时刻（缺省取封场开始）、可选备用工位。事件先经字段与营业窗口校验，失败在写库前返回 `BAD_CLOSURE`。
- 已落位工序按巡检时刻与封场窗分三类：`locked`（巡检前完工或整段在封场结束之后）、`active`（巡检时刻已开工）、`waiting`（尚未开工）。未落位与隔离工单保留原证据，不重新采信。
- active 与 waiting 工序在原排程基线上重排，固定预约与封场窗都作为占用；恢复开工不早于巡检时刻。备用舞台仅当给出严格更早的开工位时才改场，同分裁决回到原工位。
- `entry_status` 记开工事实，`recovery_status` 记最终安排（含 `relocated`），两维正交；截止分钟不顺延，恢复后超时按完工减截止重新列报。
- 空档按各工位有效营业窗口减去恢复后占用生成，与封场窗相交的空档归因到事件号，其余记为排程空档。
- 恢复单号 = 摘要（规则版本、工单与日历摘要、事件摘要）。同一事件重复提交、并发提交都收敛到同一行；先算后存，失败不产生任何记录。现场清单与页面预览共用同一份恢复结果。
