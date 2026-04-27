from __future__ import annotations

#=======================主要配置===================================#
# 仅在需要修改本地默认配置时编辑此文件。

# API 服务监听地址与端口。
API_HOST = "127.0.0.1"
API_PORT = 18080

# 当请求体中未显式传入 `stream` 时的默认行为。
USE_STREAM_RESPONSE = True

# 大神 / 外部 API 请求配置。***必填***
DASHEN_ACCOUNTS = [
    {
        "name": "account-1",        #账号名任意
        "role_id": 123456789,       #role_id获取方式查看Faststart.md
        "token": "replace-with-your-token", #token获取方式查看Faststart.md
    },
    # {
    #     "name": "account-2",
    #     "role_id": 987654321,
    #     "token": "replace-with-your-token",
    # }
]






#=======================其他配置===================================#
DASHEN_DTS = 2026
DASHEN_SERVER = 1
DASHEN_ACCOUNT_MAX_REQUESTS_PER_SECOND = 5
DASHEN_ACCOUNT_RATE_LIMIT_WINDOW_SECONDS = 1.0
DASHEN_CLIENT_TYPE = "60"
DASHEN_ORIGIN = "https://act.ds.163.com"
DASHEN_REFERER = "https://act.ds.163.com/"
DASHEN_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 "
    "app/df_client dfVersion/100111"
)
DASHEN_ACCOUNT_FAILURE_COOLDOWN_SECONDS = 60
DASHEN_MAX_CONCURRENT_REQUESTS = 2

# 可选：国际接口代理，例如 Overfast。
DASHEN_INTERNATIONAL_PROXY = ""

# 可选：网易接口代理池。使用 `None` 表示直连。
DASHEN_NETEASE_PROXIES = [
    None,
    # "http://your-netease-proxy:port",
]

# 可选：已签名的 OW 电竞接口配置。
OW_ESPORTS_URL = ""
OW_ESPORTS_PAYLOAD = {
    "ids": [],
}

# 其他敏感配置。
GOOGLE_AI_STUDIO_API_KEYS = [
    "replace-with-your-google-ai-studio-api-key",
]
ANALYSIS_FALLBACK_API_KEY = "replace-with-your-fallback-api-key"
ANALYSIS_DEEPSEEK_API_KEY = "replace-with-your-deepseek-api-key"
ANALYSIS_LOCAL_CHAT_API_KEY = "replace-with-your-local-chat-api-key"
