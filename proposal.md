# Overstats 云端网页控制面板需求文档 (proposal.md)

本项目旨在基于现有的 Overstats 本地数据服务，延展为一个适合在云端部署、可供你和朋友们共同使用的网页控制面板。无需用户登录验证，直接通过浏览器进行 API 调试与数据预览。

---

## 1. 核心需求与场景定位

### 1.1 普通用户极简战绩查询面板
- **定位**：完全面向普通玩家，隐去全部 API 接口参数、原始 JSON 数据编辑和 JSON 文本预览等开发级杂糅模块。
- **核心功能流与设计**：
  - **今日总结**：一键生成玩家今日 summaries，无需额外参数。
  - **快速强度**：一键生成玩家近期快速模式强度，无需额外参数。
  - **对局详情（图片选择导航流）**：
    - 输入玩家 ID 选中“对局详情”后，点击“生成战绩卡片”会在右侧直接渲染并展现该玩家 20 场的对局列表概览图（调用 `/api/v2/dashen-match/image` 接口）。
    - 同时，左侧控制面板会动态展现“查询单场详情”板块，包含一个 1 - 20 局的下拉选择框与“查询该局详情”按钮。
    - 玩家看图选择对应的场次，点击查询，右侧平铺展出详情图，且左侧提供“返回对局列表图”快捷返回入口。
- **多图渲染预览区**：
  - **对局详情输出 3 张图**：查询对局详情时，系统将调用 `/api/v2/dashen-match/detail/replies` 接口，在右侧以卡片垂直滚动流的形式平铺展出三张高清图片：
    1. **对局主画幅**（单局战绩面板）
    2. **数据详情**（包含英雄详细时长与对局详细曲线）
    3. **AI 总结**（AI 对当局对局的犀利点评报告）
  - **灯箱弹窗大图放大 (Lightbox)**：点击图片时自动唤起全屏大图灯箱覆盖层，支持鼠标滚轮或双指缩放、拖拽平移和一键下载保存。

### 1.2 快捷玩家绑定与本地缓存 (LocalStorage)
- **免登设计**：无需配置后端数据库和用户登录。
- **浏览器缓存**：在前端使用 LocalStorage 缓存用户自己和朋友们常用的 BattleTag / 大神 ID。
- **快速下拉/列表**：在目标值输入框下提供“常用玩家快捷徽章气泡”，一键点击填入，免去重复输入的繁琐。

---

## 2. AI 总结 (AI 锐评) API 配置指南
为了让“对局详情”中的 AI 总结功能能够正常生成并渲染，你需要在本地的 [config.py](file:///c:/Users/muelmuel/Desktop/tools/OverstatsWeb/Overstats/config/config.py) 中正确配置大模型 API。

### 2.1 基础参数配置
在 [config.py](file:///c:/Users/muelmuel/Desktop/tools/OverstatsWeb/Overstats/config/config.py) 的 `# ======================= Match Analysis ====================== #` 区域，修改以下变量：
1. **`ANALYSIS_BASE_URL`**：填写你的大模型 API 接口地址（支持任何兼容 OpenAI 格式的端点）。例如：
   - 官方 OpenAI: `https://api.openai.com/v1`
   - DeepSeek: `https://api.deepseek.com/v1`
   - 硅基流动等中转: `https://api.siliconflow.cn/v1`
2. **`ANALYSIS_API_KEY`**：填写你对应 API 的密钥 Key。
3. **`ANALYSIS_OPENAI_MODEL`**：填写所调用的模型名称（例如 `deepseek-chat` 或 `gpt-4o-mini`）。
4. **`ANALYSIS_PROXY`**（可选）：如果你在本地运行需要走代理服务器才能访问 API，请填写你的代理地址（如 `http://127.0.0.1:7890`）。

### 2.2 设定 AI 分析风格与人设
你可以通过修改 `ANALYSIS_PERSONA_PROMPT` 变量来自定义 AI 的语气和分析风格。默认设置了搞笑犀利的“科比”人设，包含 "what can i say", "mamba out" 等特色元素，你可以根据需要直接改写这段 Prompt 提示词。

---

## 2. 视觉设计：朱诺《霓虹脉冲》主题

为了展现极致的视觉效果与可爱的氛围，UI 界面将深度融合《守望先锋 2》英雄**朱诺 (Juno) 的 Epic 皮肤《霓虹脉冲》(Neon Pulse)** 的配色与设计元素：

### 2.1 霓虹脉冲色彩系统 (HSL Palette)
- **背景基底**：深邃的太空港湾与暗夜舞池背景
  - `background-dark`: `#0d0822` (极深紫黑)
  - `background-panel`: `#160e36` (深紫罗兰，带微透明毛玻璃效果)
- **主霓虹色（Juno 粉）**：代表活力与发光的猫耳耳机
  - `color-primary`: `#ff2e93` (高饱和霓虹粉)
  - `color-primary-glow`: `rgba(255, 46, 147, 0.4)`
- **辅助强调色（Juno 青）**：代表全息投影与防护服线条
  - `color-secondary`: `#00f5ff` (高饱和全息青蓝)
  - `color-secondary-glow`: `rgba(0, 245, 255, 0.3)`
- **渐变过渡色（薰衣草紫）**：
  - `color-accent`: `#b88eff` (柔和薰衣草紫)
- **文字与状态**：
  - `text-main`: `#ffffff`
  - `text-muted`: `#a59ebc` (柔和灰紫)

### 2.2 视觉特效与微交互
- **毛玻璃面板 (Glassmorphism)**：卡片使用 `backdrop-filter: blur(12px)` 结合细微的青粉渐变边框。
- **脉冲呼吸灯效果 (Pulsing Glow)**：对按钮、活动导航项以及输入框焦点态，添加柔和的 `box-shadow` 霓虹呼吸动效。
- **朱诺可爱元素挂饰**：
  - 侧边栏及按钮使用猫耳造型微边框（如 `:before` 伪类装饰）。
  - 使用星空、心形、以及数字均衡器（Equalizer）等微动效图标。
  - 界面字体推荐使用带有科技与可爱感的 Google Fonts (如 `Outfit` + `Inter`)。

---

## 3. 技术栈选型

遵循轻量化、易部署、易扩展的原则：
- **后端**：继续采用当前项目基于 Python 标准库 `BaseHTTPRequestHandler` 编写的单体 HTTP 服务，不引入繁重的 FastAPI/Django 等框架。静态资源通过内置路由直接读取并返回。
- **前端**：采用纯原生 **Vanilla HTML5 + Vanilla CSS (CSS 变量/动画) + Vanilla JavaScript (ES6)**。
  - 无需打包工具 (Webpack/Vite) 与运行时框架 (React/Vue)，确保源码结构清晰，代码即改即生效。
  - 遵循 Prettier 规范进行格式化。

---

## 4. 云端容器化部署方案

为了让你和朋友能轻松部署在任何云主机（VPS）上，我们将提供容器化配置支持：

### 4.1 Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装必要的系统依赖（如果渲染组件需要库支持，如 pyppeteer/playwright/Pillow 依赖的动态库）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 暴露服务端口
EXPOSE 18080

CMD ["python", "-m", "overstats.run"]
```

### 4.2 docker-compose.yml
```yaml
version: '3.8'

services:
  overstats-web:
    build: .
    image: overstats-web:latest
    container_name: overstats-web
    ports:
      - "18080:18080"
    volumes:
      - ./config:/app/overstats/config
      - ./cache:/app/overstats/cache
      - ./src/db:/app/overstats/src/db
    restart: always
    environment:
      - PYTHONUNBUFFERED=1
```

---

## 5. 实施路线图

1. **第 1 步：霓虹脉冲 UI 视觉与交互重构**
   - 升级 `app.css`，实现基于 HSL 变量的朱诺“霓虹脉冲”色系，添加猫耳边框、渐变线条与呼吸脉冲动效。
   - 重构 `index.html` 的版面布局，优化请求面板与响应预览区域的比例，使其支持响应式（自适应移动端）。
2. **第 2 步：LocalStorage 缓存机制与快捷绑定**
   - 在 `app.js` 中增加玩家缓存模块。用户点击保存后，将输入的 BattleTag 存入浏览器 LocalStorage，并在输入框下方渲染出一个极具科技感的“快捷常用玩家”卡片列表。
3. **第 3 步：编写 Dockerfile 与 Docker Compose**
   - 在项目根目录添加 `Dockerfile`、`.dockerignore` 与 `docker-compose.yml`，并优化 `config/config.py` 中的敏感信息（如 `DASHEN_ACCOUNTS` 配置）的加载方式，支持通过环境变量或外置卷映射，避免泄露私密 Token。
4. **第 4 步：联调与云端部署验证**
   - 本地构建 Docker 镜像，验证 API 调用和页面渲染完整性，并生成 Walkthrough 交付文档。
