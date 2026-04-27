# Overstats API 文档

本文档基于当前代码实现整理，面向 `overstats` 服务的调用方。

## 服务地址

- 默认监听地址：`http://127.0.0.1:18080`
- 配置位置：`overstats/config/config.py`
- 健康检查：`GET /healthz`

`/healthz` 返回格式：

```json
{
  "ok": true,
  "service": "overstats-core",
  "default_stream": true,
  "dashen_max_concurrent_requests": 2
}
```

## 通用约定

- 除图片接口外，所有接口返回 `application/json; charset=utf-8`
- 所有 `POST` 接口请求体都应为 JSON 对象
- 服务端会自动兼容部分驼峰字段，例如 `bnetId`、`customerToken`
- 所有路由都会先做一次 `rstrip("/")`，所以带不带末尾 `/` 都可以

通用错误格式：

```json
{
  "ok": false,
  "error": "error_code",
  "message": "错误说明",
  "hint": "可选，调用建议",
  "details": {}
}
```

## 模块总览

| 模块 | 功能 | 是否对外提供 HTTP 端点 |
| --- | --- | --- |
| `dashen_profile` | 查询玩家资料卡、竞技统计、休闲统计 | 是 |
| `dashen_match` | 查询近期战绩列表与单场详情 | 是 |
| `dashen_summary` | 生成今日 / 昨日 / 本周总结 | 是 |
| `dashen_rank_history` | 查询历史竞技 / 战场段位时间线 | 是 |
| `bnet_search` | BattleTag 搜索与 `customer_token` 解析 | 否，内部模块 |
| `query_tool` | 查询工具配置加载、静态资源缓存 | 否，内部模块 |

## 1. `dashen_profile`

功能：查询玩家资料卡，以及当前赛季的竞技和休闲统计。

### 端点

- `POST /api/v2/dashen-profile`
- `POST /api/v2/dashen-profile/image`

### 请求字段

至少提供一项：

- `bnet_id` / `bnetId`
- `customer_token` / `customerToken`

可选字段：

- `season` / `season_c`：指定赛季，整数；不传时按当前赛季
- `include_previous_season`：是否在当前赛季无数据时回退前一赛季，默认 `true`

仅图片接口额外支持：

- `mode` / `render_mode`：`quick` 或 `competitive`
- `competitive`：为 `true` 时等价于 `mode=competitive`

### JSON 返回格式

```json
{
  "ok": true,
  "customer_token": "string",
  "resolved": {
    "query": "原始查询文本",
    "full_id": "完整 BattleTag",
    "bnet_id": "纯数字 bnet id",
    "has_customer_token": true
  },
  "season": {
    "logical": 22,
    "request": null,
    "include_previous_season": true
  },
  "profile_card": {
    "code": 0,
    "success": true,
    "data": {
      "bnetId": 0,
      "name": "string",
      "icon": "url",
      "title": "string",
      "titleIcon": "url",
      "level": 0,
      "gameTime": "string",
      "customerToken": "string"
    }
  },
  "sport": {
    "code": 0,
    "success": true,
    "msg": "ok",
    "data": {}
  },
  "leisure": {
    "code": 0,
    "success": true,
    "msg": "ok",
    "data": {}
  }
}
```

说明：

- `profile_card`、`sport`、`leisure` 基本保持上游返回原样
- `sport.data` 常见字段包括 `guideCountData`、`matchList`、`recentMatchList`、`recentMatchCount`、`presetsSummaryData`
- `leisure.data` 常见字段包括 `v6SummaryData`、`heroUseSummaryList`、`openHeroUseSummaryList`、`gameAction`
- 如果请求时直接传入 `customer_token`，`resolved` 可能为 `null`

### 图片返回格式

- Content-Type：`image/png`
- Body：PNG 二进制图片

## 2. `dashen_match`

功能：查询近期战绩列表，或查询指定一场对局的详情。

### 端点

- `POST /api/v2/dashen-match`
- `POST /api/v2/dashen-match/image`
- `POST /api/v2/dashen-match/detail`
- `POST /api/v2/dashen-match/detail/image`

### 请求字段

战绩列表接口必填其一：

- `bnet_id` / `bnetId`
- `customer_token` / `customerToken`

列表接口可选字段：

- `target_count` / `limit`：返回目标条数，默认 `20`
- `include_fight`：是否包含战场对局，默认 `true`
- `include_previous_season`：是否在当前赛季基础上补前一赛季，默认 `true`

详情接口额外字段：

- `index` / `idx`：按近期列表索引取某场详情
- `match_id` / `matchId`：直接按对局 ID 查询

注意：

- 若使用 `match_id` 直接查询详情，必须同时提供 `customer_token`
- 若使用 `index` 查询详情，则仍需提供 `bnet_id` 或 `customer_token`

### 战绩列表 JSON 返回格式

```json
{
  "ok": true,
  "customer_token": "string",
  "resolved": {
    "query": "原始查询文本",
    "full_id": "完整 BattleTag",
    "bnet_id": "纯数字 bnet id",
    "has_customer_token": true
  },
  "count": 20,
  "matches": [
    {
      "matchId": "string",
      "beginTs": 0,
      "gameMode": "SportPreset",
      "mapGuid": "string",
      "matchRet": 1,
      "heroGuid": "string",
      "roleType": "tank",
      "teamScore": 2,
      "opponentScore": 1,
      "kill": 10,
      "assist": 5,
      "death": 3,
      "heroDamage": 5000,
      "cure": 2000,
      "resistDamage": 1000,
      "rankInfo": {},
      "_dashenSeason": 22
    }
  ]
}
```

说明：

- `matches` 中的对象大多是上游接口原始对局摘要
- 服务端会额外补一个 `_dashenSeason` 字段，表示该条记录归属的逻辑赛季
- 如果请求时直接传入 `customer_token`，`resolved` 可能为 `null`

### 战绩详情 JSON 返回格式

```json
{
  "ok": true,
  "customer_token": "string",
  "resolved": {
    "query": "原始查询文本",
    "full_id": "完整 BattleTag",
    "bnet_id": "纯数字 bnet id",
    "has_customer_token": true
  },
  "match_id": "string",
  "match_kind": "normal",
  "source_match": {},
  "detail": {}
}
```

说明：

- `match_kind` 取值为 `normal` 或 `fight`
- `source_match` 是用于定位这场比赛的摘要对象；如果直接用 `match_id` 查询，通常为空对象
- `detail` 为上游单场详情原始载荷，字段会因模式不同而变化
- 如果请求时直接传入 `customer_token` 且未经过 BattleTag 解析，`resolved` 可能为 `null`

### 图片返回格式

- `POST /api/v2/dashen-match/image`：`image/png`
- `POST /api/v2/dashen-match/detail/image`：`image/png`

## 3. `dashen_summary`

功能：生成图片化的战绩总结，并返回总结元信息。

### 端点

- `POST /api/v2/dashen-summary/today`
- `POST /api/v2/dashen-summary/today/image`
- `POST /api/v2/dashen-summary/yesterday`
- `POST /api/v2/dashen-summary/yesterday/image`
- `POST /api/v2/dashen-summary/week`
- `POST /api/v2/dashen-summary/week/image`

### 请求字段

至少提供一项：

- `bnet_id` / `bnetId`
- `full_id` / `fullId`
- `customer_token` / `customerToken`

### JSON 返回格式

```json
{
  "ok": true,
  "scope": "today",
  "title": "今日总结",
  "customer_token": "string",
  "resolved": {
    "query": "原始查询文本",
    "full_id": "完整 BattleTag",
    "bnet_id": "纯数字 bnet id",
    "has_customer_token": true
  },
  "summary": {
    "worker_url": "local-module",
    "match_count": 8,
    "all_match_count": 36,
    "payload_kb": 512,
    "timings": [
      {
        "stage": "REQUEST_READY",
        "delta_ms": 12,
        "total_ms": 12,
        "extra": "title=今日总结; match_count=8; all_match_count=36"
      }
    ]
  }
}
```

说明：

- `scope` 仅支持 `today`、`yesterday`、`week`
- `title` 对应为 `今日总结`、`昨日总结`、`本周总结`
- JSON 接口只返回总结元信息，不直接返回 `image_base64`

### 图片返回格式

- Content-Type：`image/jpeg` 或 `image/png`
- Body：总结图片二进制内容

## 4. `dashen_rank_history`

功能：查询指定赛季区间内的历史竞技和战场段位，并可生成时间线图片。

### 端点

- `POST /api/v2/dashen-rank-history`
- `POST /api/v2/dashen-rank-history/image`

### 请求字段

至少提供一项：

- `bnet_id` / `bnetId`
- `customer_token` / `customerToken`

可选字段：

- `start_season` / `startSeason`：起始赛季，默认 `15`
- `end_season` / `endSeason`：结束赛季，默认当前赛季

### JSON 返回格式

```json
{
  "ok": true,
  "customer_token": "string",
  "resolved": {
    "query": "原始查询文本",
    "full_id": "完整 BattleTag",
    "bnet_id": "纯数字 bnet id",
    "has_customer_token": true
  },
  "season_range": {
    "start_season": 15,
    "end_season": 22
  },
  "seasons": [
    {
      "season": 22,
      "has_competitive": true,
      "has_stadium": true,
      "competitive": {
        "frequent_hero_ids": [
          "207165582859043131"
        ],
        "roles": [
          {
            "role_type": "tank",
            "match_sum": 10,
            "win_rate": 60.0,
            "win_sum": 6,
            "current": {
              "rank_score": 398,
              "rank_sub_tier": 2,
              "rank_level": 4
            },
            "peak": {
              "rank_score": 498,
              "rank_sub_tier": 2,
              "rank_level": 5
            }
          }
        ]
      },
      "stadium": {
        "hero_use_summary_ids": [
          "207165582859043626"
        ],
        "roles": [
          {
            "role_type": "dps",
            "match_sum": 6,
            "win_rate": 50.0,
            "win_sum": 3,
            "current": {
              "rank_score": 197,
              "rank_sub_tier": 3,
              "rank_level": 2
            },
            "peak": {
              "rank_score": 197,
              "rank_sub_tier": 3,
              "rank_level": 2
            }
          }
        ]
      }
    }
  ],
  "missing_assets": [
    "overstats/res/season_logo/s21.png"
  ]
}
```

说明：

- `competitive` 对应传统竞技数据
- `stadium` 对应战场模式数据
- 某赛季某模式无数据时，对应字段为 `null`
- `missing_assets` 表示生成时间线图片时缺失的本地素材

### 图片返回格式

- Content-Type：`image/png`
- Body：段位历史时间线图片

## 5. `bnet_search`（内部模块）

功能：根据 BattleTag 查询上游搜索接口，并提取：

- `customer_token`
- `bnet_id`
- `full_id`
- `icon_url`

当前没有独立 HTTP 端点，主要被以下模块内部依赖：

- `dashen_profile`
- `dashen_match`
- `dashen_summary`
- `dashen_rank_history`

内部返回核心结构可理解为：

```json
{
  "query": "Player#12345",
  "payload": {},
  "derived": {
    "customer_token": "string",
    "bnet_id": "string",
    "full_id": "string",
    "icon_url": "string"
  }
}
```

## 6. `query_tool`（内部模块）

功能：

- 拉取并合并网易远端 `query_tool` 配置
- 保留本地手工维护字段
- 下载并缓存配置中引用的静态资源

当前没有独立 HTTP 端点。

内部常用返回：

`load_query_tool()` 返回合并后的查询工具配置字典。

`ensure_query_tool_assets()` 返回：

```json
{
  "checked": 0,
  "cached": 0,
  "downloaded": 0,
  "failed": 0,
  "asset_dir": "path"
}
```

## 7. 额外公共接口

这两个不是 `src/modules` 目录下的业务模块，但当前服务对外也开放了，方便调用方排查和联调。

### `POST /api/v2/query`

功能：通用占位查询接口，当前实现是一个回显型接口。

请求格式：

```json
{
  "route": "default",
  "text": "hello",
  "stream": false,
  "extra": {}
}
```

非流式返回：

```json
{
  "ok": true,
  "route": "default",
  "text": "hello",
  "stream": false,
  "extra": {},
  "replies": [
    {
      "type": "meta",
      "data": {
        "route": "default",
        "stream": false
      }
    },
    {
      "type": "text",
      "data": "overstats core received: hello"
    }
  ]
}
```

若 `stream=true`，则返回 `application/x-ndjson`，每行一个 JSON 事件，事件类型依次通常为：

- `meta`
- `text`
- `done`

### `GET /healthz`

见文档开头“服务地址”部分。
