BTC/USDT 跟单交易系统 · 需求文档（SRS）
0. 概述

目标：实时监听“主账户（Binance）”的市价单，并将其“使用可用余额的百分比 X%”复制到多个跟单账户（Binance 主网/测试网，Bitget 主网/模拟盘）。

资产对：固定 BTC/USDT（Spot）。

复制规则（核心）：

主账户买入：主账户市价买入花费了其当前可用 USDT的 X% → 每个跟单账户用其可用 USDT 的 X% 发起市价买入（以 USDT 金额为单位下单）。

主账户卖出：主账户市价卖出了其当前可用 BTC的 Y% → 每个跟单账户用其可用 BTC 的 Y% 发起市价卖出（以 BTC 数量为单位下单）。

部署形态：后端云服务器；Windows 本地 UI 客户端。

MVP 简化：忽略最小交易额检查、滑点保护、手续费缓冲、深度检查等；确保流程跑通与可视化。

1. 术语与约束

主账户（Leader）：仅在 Binance（主网或测试网）上；只产生市价单。

跟单账户（Follower）：在 Binance（主网或测试网）或 Bitget（主网或模拟盘）上；复制主账户的百分比行为。

百分比 X%/Y% 的计算（由系统自动计算）：

买入事件：X% = 主账户当次买单实际 quote 成交金额 / 触发瞬间主账户可用 USDT

卖出事件：Y% = 主账户当次卖单实际 base 成交数量 / 触发瞬间主账户可用 BTC

仅现货，不含杠杆/合约；仅 BTCUSDT。

2. 功能需求（FR）
FR-1 主账户连接与环境切换

支持主账户在 Binance 主网 / 测试网间切换；

系统持久保存主账户 API Key（加密存储），建立 userDataStream 监听其订单/成交事件；

仅处理主账户市价订单事件（BUY/SELL）。

FR-2 跟单账户管理

支持添加多个跟单账户；每个账户录入：

交易所：binance | bitget

  环境：prod | test | demo

API Key/Secret（Bitget 需 passphrase，如有）；

全部 Key 加密存储；

逐账户有效性检测（登录/权限可用）。

FR-3 余额看板

实时显示每个账户的可用 USDT 与可用 BTC。

刷新：事件驱动 + 定时轮询兜底（建议 2s–5s）。

FR-4 跟单启停（全局/单账户）

全局：开始/停止跟单（不影响连接，只控制是否派发复制）。

账户级：暂停/恢复该账户的跟单（暂停期间不下新单；已成交资产与状态保持）。

FR-5 复制执行（核心逻辑）

当检测到主账户市价买单：

读取主账户可用 USDT与本单实际 quote 成交金额，计算 X%；

对每个处于 ACTIVE 的跟单账户：

读取该账户可用 USDT = freeUSDT_i；

计算：quote_to_spend_i = freeUSDT_i * X%；

发起 市价买入：

Binance：type=MARKET, quoteOrderQty=quote_to_spend_i；

Bitget：市价买入的 amount = quote_to_spend_i（按其接口定义为 USDT 金额）。

当检测到主账户市价卖单：

读取主账户可用 BTC与本单实际 base 成交数量，计算 Y%；

对每个 ACTIVE 跟单账户：

读取该账户可用 BTC = freeBTC_i；

计算：qty_to_sell_i = freeBTC_i * Y%；

发起 市价卖出（以数量下单）。

幂等：对同一主单事件，确保每个跟单账户最多复制一次（见 6.6）。

备注：MVP 不做 minNotional、精度、滑点、深度等保护；以交易所实际成交为准。

FR-6 Windows 客户端 UI（必需项）

账户页：新增/编辑/删除账户（选择交易所+环境、填 Key），一键验证；

看板页：列表展示

每账户：交易所/环境、状态（Active/Paused/Disabled）、可用 USDT/BTC、最近复制动作与结果；

全局控制：开始/停止；

单账户控制：暂停/恢复；

错误与告警：在 UI 弹出最近一次失败原因（简要字符串）。

FR-7 访问控制（后端）

模式 A：Open（默认，仅凭后端 API Key 或 Token 访问）。

模式 B：设备白名单（作为“MAC 白名单”的工程替代）：

采用 mTLS 客户端证书或设备指纹 + 签名 Token 的方式限制可访问的 Windows 客户端；

支持在 UI 中注册/撤销设备。

3. 非功能需求（NFR）

稳定性：在网络短暂抖动下自动重连；

性能：从主单事件到完成所有跟单下单的目标延迟 < 500ms（P95）（与机房距离相关，仅作参考值）；

安全：API 密钥加密存储；后端日志不得打印明文密钥；

可观测性：基础日志（INFO/ERROR）+ 近期事件列表（内存/文件）。

4. 系统架构（建议）
4.1 模块

Exchange Connector（Binance / Bitget，各自支持 prod/test）：

REST 客户端；WebSocket 客户端（主账户需要 userDataStream）。

Leader Watcher：监听主账户订单/成交事件，判断 BUY/SELL，计算 X%/Y%。

Copy Dispatcher：遍历 ACTIVE 跟单账户，按账户可用余额计算目标金额/数量并并发下单。

Account Service：账户增删改查、Key 加密保存、有效性校验、余额拉取。

State & Idempotency：记录“主事件 → 跟单提交结果”的幂等键。

API（FastAPI/Nest/Go 任一）：给 Windows 客户端的管理与看板接口。

4.2 技术选型（可直接用）

后端：Python 3.11 + FastAPI + httpx + websockets（开发效率高）；

存储：MVP 无数据库，用 加密 JSON 文件 存账户与少量状态；后续可换 PostgreSQL；

Windows UI：Electron（JS/TS） 或 .NET WPF 任选其一（MVP 建议 Electron，接 WebSocket 易）。

5. API 规范（后端 → Windows 客户端）

路径前缀 /api/v1

5.1 账户管理

POST /accounts
入参：

{
  "name": "acc-1",
  "exchange": "binance|bitget",
  "env": "prod|test|demo",
  "api_key": "xxx",
  "api_secret": "yyy",
  "passphrase": "zzz-optional"
}


出参：{ "id": "uuid", "status": "CREATED" }

Bitget 模拟盘 API Key 需要先在官网切换到 **Demo Mode**，然后依次点击「个人中心 → API Key 管理 → 创建 Demo API Key」。
在创建跟单账户时将 `env` 设为 `"demo"`，系统会自动在请求头添加 `paptrading: 1`，请求地址仍为 `https://api.bitget.com`。

POST /accounts/{id}/verify → 返回 { "ok": true, "freeUSDT": 50000.0, "freeBTC": 0.123 }

GET /accounts → 列表（含余额、状态）

PATCH /accounts/{id} → 更新 name/env/key 等

POST /accounts/{id}/pause / POST /accounts/{id}/resume

DELETE /accounts/{id}

5.2 主账户设置

PUT /leader

{ "exchange": "binance", "env": "prod|test", "api_key": "xxx", "api_secret": "yyy" }


返回：{ "listening": true }

5.3 全局控制

POST /copy/start → { "running": true }

POST /copy/stop → { "running": false }

GET /status →

{
  "running": true,
  "leader": {"exchange":"binance","env":"prod","connected":true},
  "followers": [
    {"id":"...","exchange":"bitget","env":"prod","state":"ACTIVE","freeUSDT":...,"freeBTC":...}
  ],
  "recent_events":[
    {"t": "...", "type":"BUY", "x_percent":0.12, "fanout": 7, "ok":7, "fail":0}
  ]
}

6. 复制算法（实现要点）
6.1 触发事件

仅响应主账户的 市价单（BUY/SELL）事件；

从事件中读取实际成交金额/数量（若仅有新建事件，也可立刻用“下单名义值”近似，MVP 可接受）。

6.2 百分比计算

买入：
x_percent = (主单实际成交 quote) / (触发时刻主账户可用 USDT)

卖出：
y_percent = (主单实际成交 base) / (触发时刻主账户可用 BTC)

说明：可用余额以事件触发前最新快照为准，MVP 不必强一致。

6.3 扇出复制（并发）

对每个处于 ACTIVE 的跟单账户 i：

BUY：
quote_i = freeUSDT_i * x_percent

Binance：MARKET + quoteOrderQty = quote_i

Bitget：市价买入 amount = quote_i

SELL：
qty_i = freeBTC_i * y_percent

两家均以数量卖出市价单。

6.4 返回与记录

记录每笔跟单提交的 exchange_order_id、时间、金额/数量。

UI 上显示成功/失败与错误信息（字符串）。

6.5 错误处理（MVP）

网络/限频 → 重试 1 次；仍失败则标记“失败”，不再追单。

Key 无效 / 权限不足 → 提示并将账户状态标记为 DISABLED。

不做：滑点、深度、最小交易额、精度对齐等校验。

6.6 幂等

幂等键：{leader_event_id} + {follower_account_id}；

若重复收到同一主事件，不再次下单。

7. Windows UI 交互草图（描述）

顶部：全局状态指示（Running/Stopped），按钮：开始 / 停止。

左栏：主账户设置（Binance 主/测 + Key，连接状态）。

右侧主面板（表格）：

列：账户名｜交易所｜环境｜状态｜freeUSDT｜freeBTC｜最近一次复制（方向/占比/金额或数量）｜错误

行操作：暂停/恢复、验证、删除

底部日志：最近 50 条事件（主单 → 扇出结果汇总）。

8. 配置与环境变量（示例）

APP_MODE=open|device_whitelist

JWT_SECRET=...（若用 Token）

TLS_CLIENT_CA=...（若用 mTLS）

DATA_DIR=/var/app/data（加密 JSON 文件目录）

WS_HEARTBEAT_SEC=30

BALANCE_POLL_SEC=2

9. 安全与合规（MVP）

API Key/Secret AES-256-GCM 加密保存（主密钥由环境变量或 KMS 注入）；

日志不打印密钥与完整签名；

若启用设备白名单：mTLS 验证或设备指纹校验。

10. 交付物与目录结构（建议）
/server
  /connectors
    binance.py
    bitget.py
  leader_watcher.py
  copy_dispatcher.py
  accounts.py
  balances.py
  idempotency.py
  api.py            # FastAPI
  models.py         # Pydantic 模型
  storage.py        # 加密JSON 存取
  main.py
/client-win
  /ui               # Electron/Vite 前端
  /ipc              # 与后端通信封装
README.md

11. 验收标准（MVP）

在 Binance 测试网设置主账户、在（Binance 测试网 / Bitget 模拟盘）添加 ≥2 个跟单账户；

主账户手动或策略触发 市价买入，系统能计算 X% 并分别在每个跟单账户用各自 USDT 的 X% 完成市价买入；

主账户触发 市价卖出，系统能计算 Y% 并在每个跟单账户用各自 BTC 的 Y% 完成市价卖出；

Windows UI 能查看余额、查看最近复制记录，支持账户暂停/恢复与全局启停；

任一账户 Key 无效时，验证失败并有明确错误提示。

12. 明确不在本版范围（可后续迭代）

多交易对；

限价单与撤单联动；

滑点/深度/最小额/精度保护；

数据库、HA、完善监控；

手续费优化（平台币抵扣等）。

附：复制核心伪代码（供 Codex 参考）
def on_leader_market_order(event):
    # event: {side: "BUY"|"SELL", quote_filled: float, base_filled: float,
    #         leader_free_usdt: float, leader_free_btc: float, event_id: str}

    if is_duplicate(event.event_id):
        return

    if event.side == "BUY":
        x = event.quote_filled / max(event.leader_free_usdt, 1e-9)  # X%
        for acc in followers.active():
            free_usdt = balances.get_free_usdt(acc)
            quote_i = free_usdt * x
            place_market_buy(acc, quote_amount=quote_i)  # binance: quoteOrderQty; bitget: amount
    else:  # SELL
        y = event.base_filled / max(event.leader_free_btc, 1e-9)   # Y%
        for acc in followers.active():
            free_btc = balances.get_free_btc(acc)
            qty_i = free_btc * y
            place_market_sell(acc, quantity=qty_i)

    mark_done(event.event_id)

## 开发环境

后端基于 Python 3.11+ 与 FastAPI 实现，`server` 目录包含主要模块。可用以下命令启动示例服务：

```bash
uvicorn server.main:app --reload
```

示例接口：访问 `GET /api/status` 可获取服务健康状态。
