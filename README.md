# 节目载入编排台

剧场值班员将演出工单、工种值班表与固定预约汇到一个载入日。试排给出可下发的执行顺序、延误分钟、待排工序和来源证据。运行快照可复算并下载。

## 启动

```sh
docker compose up --build
```

访问 `http://localhost:18452`。使用 `docker compose exec -T app pytest -q` 运行测试。宿主可安装 `requirements.txt` 后执行 `pytest -q`。数据库存放在 Compose 命名卷 `ledger`，执行 `docker compose down -v` 会清空归档。配置见 `.env.example`。

## 值班演练

1. 打开「转场排程」，选择「冲突场次」。点选 `A01` 查阅跳过预约 `H01`、`H04` 的工序票签，再选 `X05` 查看夜间待排依据。
2. 在「超时勾稽」核对 15 道已落位、3 道待排、6 道工单隔离。`A03` 超时 15 分钟，新排工序资源碰撞为零。
3. 确认归档后打开「执行清单」，可复跑核验或下载包含输入摘要、执行步骤和隔离证据的联单。
4. 自带工单可展开「试排自备工单」，粘贴逐行工单与日历 JSON。样例位于 `sample_data/`，字段见 [数据字典](docs/DATA-DICTIONARY.md)。

## 接口

- `GET /api/health` 检查存储连通性。
- `GET /api/samples/clean` 和 `GET /api/samples/dirty` 返回计算结果。七个子路径分别是 `orders`、`dependencies`、`calendars`、`conflicts`、`schedule`、`reconcile`、`dispatch`。排程支持 `?job=A01`。
- `POST /api/runs` 接收 `{"sample":"dirty"}` 或 `{"orders":"逐行文本","calendar":{...}}`。`GET /api/runs/{id}` 读取归档，`POST /api/runs/{id}/rerun` 复算比对，`GET /api/runs/{id}/export` 下载证据。

## 排程边界

同一批次按依赖、优先级、截止、工单号依次落位，并以最早开始和技师号裁决同分候选。该策略是一轮确定性编排，跨场次全局优化和交互式拖拽排程超出当前范围。见 [规则与测试](docs/DEPTH.md)。
