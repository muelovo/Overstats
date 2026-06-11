# Overstats 普通用户网页面板 UI 设计文档 (proposal_ui.md)

本设计文档旨在为 Overstats 网页面板提供一套专为普通玩家设计的极简、美观、沉浸式的 UI 方案。核心理念是**隐藏开发细节，突出核心战绩图，支持便捷操作与大图保存，并针对移动端适配与主题个性化进行全面升级**。

---

## 1. 页面版面结构 (响应式与多端适配)

整个界面支持 Desktop、Tablet 与 Mobile 端的自适应布局。为了应对微信、QQ 内置浏览器（Webview）高度受限的环境，页面布局如下：

### 1.1 桌面端布局 (Desktop)
- **左右分栏**：左侧 `sidebar`（460px 宽度，固定高度自适应滚动）展示参数控制区，右侧 `workspace` 占满剩余宽度展示大图。

### 1.2 移动端布局 (Mobile - Width <= 1024px)
- **单栏流式布局**：左右分栏自动折叠为单栏。
- **视图切换卡片 (View Switcher Tab)**：
  - 手机端顶部或控制区顶部新增**双标签页切换器**：“📝 配置参数”与“🖼️ 战绩预览”。
  - 默认展示“📝 配置参数”标签页。当玩家点击“生成战绩卡片”时，程序会自动切到“🖼️ 战绩预览”标签页，并伴随流畅的滑入动画，避免手机端用户不知道卡片已生成的痛点。
- **悬浮操作按钮**：生成按钮在配置页中置底展示，在微信/QQ 浏览器中适配安全区域 (`padding-bottom: env(safe-area-inset-bottom)`)。

---

## 2. 主题与配色系统 (Juno 皮肤配色)

系统支持动态主题切换，在 `body` 节点注入对应的 `theme-xxx` 类，利用 CSS 变量控制全局色彩体系。

### 2.1 主题配色定义
1. **霓虹脉冲 (theme-neon - 默认)**
   - 朱诺经典霓虹皮肤配色，未来科技感。
   - 背景色 (`--bg`): `#070415` (极深紫)
   - 主色/文字高亮 (`--accent`): `#ff2e93` (霓虹粉)
   - 辅色/胜利高亮 (`--secondary`): `#00f5ff` (全息青蓝)
   - 面板底色 (`--bg-panel`): `rgba(18, 11, 44, 0.75)`
2. **天外飞兔 (theme-rabbit)**
   - 朱诺“天外飞兔”黑白丝兔女郎与青粉双色发光配色。
   - 背景色 (`--bg`): `#070709` (深炭黑)
   - 主色/文字高亮 (`--accent`): `#ff54b0` (兔耳发光粉)
   - 辅色/胜利高亮 (`--secondary`): `#00f0ff` (发色渐变青)
   - 面板底色 (`--bg-panel`): `rgba(13, 13, 18, 0.75)` (半透深灰)
   - 装饰细节：侧边栏标题上方自动浮现呼吸发光的白色兔耳挂件字符 `ᕱᕱ`。
3. **希望之心 (theme-hope)**
   - 朱诺“希望之心”粉金皮肤配色，柔和治愈感。
   - 背景色 (`--bg`): `#1a0815` (深李子暗红)
   - 主色/文字高亮 (`--accent`): `#ff528c` (爱心粉)
   - 辅色/胜利高亮 (`--secondary`): `#9be5ff` (晴空淡蓝)
   - 面板底色 (`--bg-panel`): `rgba(38, 16, 33, 0.75)`

### 2.2 主题切换机制
- 头部区域提供一个高颜值的主题切换下拉框/图标选择器。
- 用户选择的主题会实时写入 `LocalStorage` 中（键名为 `overstats_theme`），下次访问自动激活。

---

## 3. 自定义网页背景图片 (Custom Background)

> [!IMPORTANT]
> ### 🌌 自定义背景图存放与命名规范
> - **文件存放路径**：`src/http_server/assets/` 静态资源目录下。
> - **全局通用背景**：请命名为 `bg.jpg`（或 `.png` / `.webp`）。
> - **主题专属背景**（优先尝试加载，若不存在则退回加载通用背景）：
>   - **霓虹脉冲**：`bg_neon.jpg` / `bg_neon.png` / `bg_neon.webp`
>   - **天外飞兔**：`bg_rabbit.jpg` / `bg_rabbit.png` / `bg_rabbit.webp`
>   - **希望之心**：`bg_hope.jpg` / `bg_hope.png` / `bg_hope.webp`
> - **自动检测启用**：前端自动探测文件存在性，只有检测到有匹配的文件存在时，主控制面板才会展现 **“🌌 开启背景 / 关闭背景”** 的切换键，状态由 LocalStorage 持久化记住。

### 3.2 视觉遮罩与可读性保障
- 自定义背景图片渲染于页面最底层。
- **防花眼设计**：在背景图上方覆盖一层半透明的磨砂玻璃遮罩：
  ```css
  .custom-bg-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background-image: var(--custom-bg-url);
    background-size: cover;
    background-position: center;
    z-index: -2;
  }
  .custom-bg-blur {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    backdrop-filter: blur(8px) brightness(0.35);
    background: rgba(7, 4, 21, 0.4);
    z-index: -1;
  }
  ```
- 这样能保证即使背景图色彩非常斑斓，上层的文字、输入框和按钮依然具有高对比度与极佳的可读性。

---

## 4. 灯箱与手势交互 (Lightbox Gesture)

针对微信和手机浏览器进行优化：
- **双击/捏合缩放**：移动端激活灯箱后，支持双指捏合（Pinch to Zoom）或双击大图放大，支持单指拖拽平移查看卡片细节。
- **微信长按保存**：在微信/QQ 中，由于安全限制，点击“下载图片”可能无法直接唤起文件下载。因此，移动端灯箱的大图会以标准的 `<img>` 标签直接展示，并提示用户“长按图片保存到相册”。
- **关闭手势**：点击大图边缘的任意半透明空白区、或向下滑动（Swipe Down）即可直接关闭灯箱。

- 用户输入 BattleTag 后点击 `♥ 收藏`，输入框下方即时生成一个小气泡标签。
- 点击该标签直接自动填入输入框，并触发对应模块的 Payload 生成，便于朋友间快速切换查询。

### 2.2 灯箱弹窗大图放大 (Lightbox Overlay)
为了解决老版本“图片太小无法看清与保存”的痛点，引入灯箱弹窗机制：
- **触发**：点击渲染出来的战绩大图。
- **展现形式**：弹出一个全屏半透明遮罩层（`backdrop-filter: blur(10px)`），图片以原始分辨率大小居中显示。
- **操作逻辑**：
  - 支持鼠标滚轮或手机双指进行图片缩放（Zoom In/Out）和拖拽平移。
  - 遮罩层右上角提供一个显眼的“📥 保存/下载图片”按钮，以及“×”关闭按钮。
  - 点击遮罩层任意非图片空白区域，即可关闭弹窗。

---

## 3. 前端界面样式配置 (CSS Theme)

```css
/* 灯箱样式 */
.lightbox-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(7, 4, 21, 0.85);
  backdrop-filter: blur(12px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  cursor: zoom-out;
}

.lightbox-content {
  max-width: 90%;
  max-height: 90%;
  object-fit: contain;
  border-radius: 12px;
  box-shadow: 0 0 30px rgba(0, 245, 255, 0.4);
  cursor: grab;
  transition: transform 0.1s ease;
}

/* 核心大瓷砖按钮样式 */
.feature-tile-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin: 16px 0;
}

.feature-tile {
  background: var(--bg-panel-strong);
  border: 1px solid var(--line);
  padding: 16px 12px;
  border-radius: 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.25s ease;
}

.feature-tile:hover {
  border-color: var(--secondary);
  box-shadow: 0 0 12px var(--secondary-soft);
  transform: translateY(-2px);
}

.feature-tile.is-active {
  background: rgba(255, 46, 147, 0.12);
  border-color: var(--accent);
  box-shadow: 0 0 15px rgba(255, 46, 147, 0.3);
}
```
