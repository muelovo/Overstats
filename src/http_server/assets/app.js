(function () {
  "use strict";

  const bootstrap = window.__OVERSTATS_UI_BOOTSTRAP__ || {};
  const modules = Array.isArray(bootstrap.modules) ? bootstrap.modules : [];
  const moduleMap = new Map(modules.map((item) => [item.id, item]));

  const MODULE_TODAY = "dashen-summary-today";
  const MODULE_QUICK = "dashen-quick-strength";
  const MODULE_MATCH = "dashen-match-detail";

  const state = {
    activeModuleId: MODULE_TODAY,
    imageObjectUrls: [], // Supports multiple image previews
    savedPlayers: [],
    overviewImageUrl: "", // Caches the overview image object URL
    overviewImageBlob: null, // Caches the overview image blob
    // Lightbox state
    lightbox: {
      activeUrl: "",
      scale: 1.0,
      translateX: 0,
      translateY: 0,
      isDragging: false,
      startX: 0,
      startY: 0
    }
  };

  const elements = {
    requestForm: document.getElementById("requestForm"),
    targetValueInput: document.getElementById("targetValueInput"),
    savePlayerButton: document.getElementById("savePlayerButton"),
    quickPlayersList: document.getElementById("quickPlayersList"),
    
    // Main tiles
    tileToday: document.getElementById("tileToday"),
    tileQuick: document.getElementById("tileQuick"),
    tileMatch: document.getElementById("tileMatch"),
    
    // Config panel
    simpleParamsPanel: document.getElementById("simpleParamsPanel"),
    singleMatchDetailPanel: document.getElementById("singleMatchDetailPanel"),
    singleMatchIndexSelect: document.getElementById("singleMatchIndexSelect"),
    queryDetailButton: document.getElementById("queryDetailButton"),
    backToOverviewButton: document.getElementById("backToOverviewButton"),
    dynamicFields: document.getElementById("dynamicFields"),
    moduleNav: document.getElementById("moduleNav"),
    
    // Action block
    submitButton: document.getElementById("submitButton"),
    requestStatus: document.getElementById("requestStatus"),
    
    // Headers
    moduleTitle: document.getElementById("moduleTitle"),
    moduleDescription: document.getElementById("moduleDescription"),
    activeEndpoint: document.getElementById("activeEndpoint"),
    
    // Preview panel
    imagePlaceholder: document.getElementById("imagePlaceholder"),
    imagePreviewStack: document.getElementById("imagePreviewStack"),
    
    // Lightbox
    lightbox: document.getElementById("lightbox"),
    lightboxClose: document.getElementById("lightboxClose"),
    lightboxImage: document.getElementById("lightboxImage"),
    lightboxDownload: document.getElementById("lightboxDownload"),

    // Theme & Background Controls
    themeSelect: document.getElementById("themeSelect"),
    bgUploadInput: document.getElementById("bgUploadInput"),
    clearBgButton: document.getElementById("clearBgButton"),
    customBgOverlay: document.getElementById("customBgOverlay"),

    // Mobile Switcher Tabs
    tabConfigBtn: document.getElementById("tabConfigBtn"),
    tabPreviewBtn: document.getElementById("tabPreviewBtn"),

    // Mobile Single Match Selection Panel
    mobileSingleMatchPanel: document.getElementById("mobileSingleMatchPanel"),
    mobileMatchIndexSelect: document.getElementById("mobileMatchIndexSelect"),
    mobileQueryDetailButton: document.getElementById("mobileQueryDetailButton"),
    mobileBackToOverviewButton: document.getElementById("mobileBackToOverviewButton")
  };

  function getActiveModule() {
    return moduleMap.get(state.activeModuleId) || modules[0] || null;
  }

  function getEffectiveEndpoint(module) {
    if (!module) return "";
    return module.image_endpoint || module.json_endpoint;
  }

  function setStatus(message, isError = false) {
    elements.requestStatus.textContent = message;
    elements.requestStatus.style.color = isError ? "var(--accent)" : "var(--secondary)";
  }

  function escapeHtml(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function revokeUrls() {
    state.imageObjectUrls.forEach((url) => {
      try {
        URL.revokeObjectURL(url);
      } catch (_e) {}
    });
    state.imageObjectUrls = [];
  }

  function clearImagePreview() {
    revokeUrls();
    elements.imagePreviewStack.innerHTML = "";
    elements.imagePreviewStack.classList.add("hidden");
    elements.imagePlaceholder.classList.remove("hidden");
  }

  // Helper to append a single image to the stack
  function appendImageToPreview(blob, titleLabel) {
    const objectUrl = URL.createObjectURL(blob);
    state.imageObjectUrls.push(objectUrl);

    const section = document.createElement("div");
    section.className = "preview-card-section";

    const title = document.createElement("div");
    title.className = "preview-card-title";
    title.textContent = titleLabel;

    const img = document.createElement("img");
    img.className = "preview-image";
    img.src = objectUrl;
    img.alt = titleLabel;
    
    // Lightbox binding
    img.addEventListener("click", () => openLightbox(objectUrl));

    section.appendChild(title);
    section.appendChild(img);
    elements.imagePreviewStack.appendChild(section);

    elements.imagePlaceholder.classList.add("hidden");
    elements.imagePreviewStack.classList.remove("hidden");
  }

  // Helper to append text messages
  function appendTextToPreview(textData, titleLabel) {
    const section = document.createElement("div");
    section.className = "preview-card-section";

    const title = document.createElement("div");
    title.className = "preview-card-title";
    title.textContent = titleLabel;

    const p = document.createElement("p");
    p.style.margin = "10px 0 0";
    p.style.lineHeight = "1.6";
    p.style.color = "var(--text)";
    p.style.fontSize = "0.95rem";
    p.style.whiteSpace = "pre-wrap";
    p.textContent = textData;

    section.appendChild(title);
    section.appendChild(p);
    elements.imagePreviewStack.appendChild(section);

    elements.imagePlaceholder.classList.add("hidden");
    elements.imagePreviewStack.classList.remove("hidden");
  }

  function showTextError(errorTitle, errorMessage) {
    clearImagePreview();
    elements.imagePlaceholder.innerHTML = `
      <span class="placeholder-icon">❌</span>
      <p style="color: var(--accent); font-weight: bold;">${escapeHtml(errorTitle)}</p>
      <p class="sub-placeholder" style="max-width: 400px; line-height: 1.5;">${escapeHtml(errorMessage)}</p>
    `;
  }

  function restoreDefaultPlaceholder() {
    if (state.activeModuleId === MODULE_MATCH) {
      elements.imagePlaceholder.innerHTML = `
        <span class="placeholder-icon">⚔️</span>
        <p>输入 ID 并点击生成按钮，20 场对局概览列表图将在这里展示。</p>
        <p class="sub-placeholder">概览图生成后，可利用左侧下拉框选择第几局，并查询该单场的 3 张高清卡片详情与 AI 总结。</p>
      `;
    } else {
      elements.imagePlaceholder.innerHTML = `
        <span class="placeholder-icon">🌌</span>
        <p>输入 ID 并点击生成按钮，高清战绩图片将在这里展示。</p>
        <p class="sub-placeholder">生成后可点击图片进行全屏缩放与下载。</p>
      `;
    }
  }

  // --- Theme Switching ---
  const STORAGE_THEME_KEY = "overstats_theme";
  function initTheme() {
    const savedTheme = localStorage.getItem(STORAGE_THEME_KEY) || "rabbit";
    setTheme(savedTheme);
    if (elements.themeSelect) {
      elements.themeSelect.value = savedTheme;
      elements.themeSelect.addEventListener("change", (e) => {
        setTheme(e.target.value);
      });
    }
  }

  function setTheme(themeName) {
    document.body.classList.remove("theme-neon", "theme-rabbit", "theme-hope");
    document.body.classList.add(`theme-${themeName}`);
    localStorage.setItem(STORAGE_THEME_KEY, themeName);
    // Dynamic theme-specific background check
    checkAndApplyBackground();
  }

  // --- Custom Background Image ---
  const STORAGE_BG_KEY = "overstats_bg_enabled";
  function initCustomBackground() {
    checkAndApplyBackground();

    if (elements.clearBgButton) {
      elements.clearBgButton.addEventListener("click", () => {
        const currentlyEnabled = localStorage.getItem(STORAGE_BG_KEY) !== "false";
        const newStatus = !currentlyEnabled;
        localStorage.setItem(STORAGE_BG_KEY, newStatus ? "true" : "false");

        if (newStatus) {
          elements.clearBgButton.textContent = "🌌 关闭背景";
          elements.clearBgButton.classList.add("is-active");
          checkAndApplyBackground();
        } else {
          elements.clearBgButton.textContent = "🌌 开启背景";
          elements.clearBgButton.classList.remove("is-active");
          document.body.classList.remove("has-custom-bg");
        }
      });
    }
  }

  function checkAndApplyBackground() {
    const activeTheme = elements.themeSelect ? elements.themeSelect.value : "neon";
    const bgEnabled = localStorage.getItem(STORAGE_BG_KEY) !== "false";

    const allThemes = ["neon", "rabbit", "hope"];
    const otherThemes = allThemes.filter(t => t !== activeTheme);
    const exts = [".jpg", ".png", ".webp"];

    const urls = [
      // Current theme first
      ...exts.map(ext => `/ui/bg_${activeTheme}${ext}`),
      // Generic bg
      ...exts.map(ext => `/ui/bg${ext}`),
      // Other themes as fallback
      ...otherThemes.flatMap(t => exts.map(ext => `/ui/bg_${t}${ext}`))
    ];

    let index = 0;
    function tryNext() {
      if (index >= urls.length) {
        // No custom background found at all
        document.body.classList.remove("has-custom-bg");
        if (elements.customBgOverlay) {
          elements.customBgOverlay.style.backgroundImage = "none";
        }
        if (elements.clearBgButton) {
          elements.clearBgButton.classList.add("hidden");
        }
        return;
      }

      const url = urls[index];
      const img = new Image();
      img.onload = () => {
        // Successfully verified background existence — set it directly
        if (elements.customBgOverlay) {
          elements.customBgOverlay.style.backgroundImage = `url(${url})`;
        }

        if (bgEnabled) {
          document.body.classList.add("has-custom-bg");
          if (elements.clearBgButton) {
            elements.clearBgButton.textContent = "🌌 关闭背景";
            elements.clearBgButton.classList.add("is-active");
          }
        } else {
          document.body.classList.remove("has-custom-bg");
          if (elements.clearBgButton) {
            elements.clearBgButton.textContent = "🌌 开启背景";
            elements.clearBgButton.classList.remove("is-active");
          }
        }

        if (elements.clearBgButton) {
          elements.clearBgButton.classList.remove("hidden");
        }
      };
      img.onerror = () => {
        index++;
        tryNext();
      };
      img.src = url;
    }

    tryNext();
  }

  // --- Mobile Tab Switching ---
  function initMobileTabs() {
    if (elements.tabConfigBtn && elements.tabPreviewBtn) {
      elements.tabConfigBtn.addEventListener("click", () => switchMobileTab("config"));
      elements.tabPreviewBtn.addEventListener("click", () => switchMobileTab("preview"));
    }
  }

  // Exposed so other handlers can trigger tab switching automatically
  function switchMobileTab(tabName) {
    if (tabName === "preview") {
      if (elements.tabConfigBtn && elements.tabPreviewBtn) {
        elements.tabConfigBtn.classList.remove("is-active");
        elements.tabPreviewBtn.classList.add("is-active");
      }
      document.body.classList.add("show-preview");
    } else {
      if (elements.tabConfigBtn && elements.tabPreviewBtn) {
        elements.tabPreviewBtn.classList.remove("is-active");
        elements.tabConfigBtn.classList.add("is-active");
      }
      document.body.classList.remove("show-preview");
    }
  }

  // --- LocalStorage Saved Players ---
  const STORAGE_KEY = "overstats_saved_players";

  function loadSavedPlayers() {
    try {
      const data = localStorage.getItem(STORAGE_KEY);
      state.savedPlayers = data ? JSON.parse(data) : [];
    } catch (_e) {
      state.savedPlayers = [];
    }
  }

  function saveSavedPlayers() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state.savedPlayers));
    } catch (_e) {}
  }

  function renderQuickPlayers() {
    elements.quickPlayersList.innerHTML = "";
    state.savedPlayers.forEach((player) => {
      const tag = document.createElement("div");
      tag.className = "quick-player-tag";
      tag.textContent = player;
      
      tag.addEventListener("click", function (event) {
        if (event.target.classList.contains("remove-btn")) return;
        elements.targetValueInput.value = player;
        syncFormToPayload();
      });

      const removeBtn = document.createElement("span");
      removeBtn.className = "remove-btn";
      removeBtn.innerHTML = " &times;";
      removeBtn.title = "删除";
      removeBtn.addEventListener("click", function (event) {
        event.stopPropagation();
        state.savedPlayers = state.savedPlayers.filter((p) => p !== player);
        saveSavedPlayers();
        renderQuickPlayers();
      });

      tag.appendChild(removeBtn);
      elements.quickPlayersList.appendChild(tag);
    });
  }

  function handleSavePlayer() {
    const value = String(elements.targetValueInput.value || "").replace(/＃/g, "#").trim();
    if (!value) {
      setStatus("请输入有效的值再进行收藏", true);
      return;
    }
    if (state.savedPlayers.includes(value)) {
      setStatus("该值已在收藏列表中");
      return;
    }
    state.savedPlayers.push(value);
    saveSavedPlayers();
    renderQuickPlayers();
    setStatus("已添加到常用玩家");
  }

  // --- Active Module toggling ---
  function setActiveFeature(moduleId) {
    state.activeModuleId = moduleId;
    
    // Update active UI classes
    elements.tileToday.classList.toggle("is-active", moduleId === MODULE_TODAY);
    elements.tileQuick.classList.toggle("is-active", moduleId === MODULE_QUICK);
    elements.tileMatch.classList.toggle("is-active", moduleId === MODULE_MATCH);

    const activeNavButton = elements.moduleNav.querySelector(`.module-button.is-active`);
    if (activeNavButton) {
      activeNavButton.classList.remove("is-active");
    }
    const targetNavButton = elements.moduleNav.querySelector(`.module-button[data-module-id="${moduleId}"]`);
    if (targetNavButton) {
      targetNavButton.classList.add("is-active");
    }

    renderDynamicParams();
    updateModuleHeader();
    clearImagePreview();
    restoreDefaultPlaceholder();

    // Reset and hide the single match details panel
    elements.singleMatchDetailPanel.classList.add("hidden");
    elements.mobileSingleMatchPanel.classList.add("hidden");
    elements.backToOverviewButton.classList.add("hidden");
    elements.mobileBackToOverviewButton.classList.add("hidden");
    if (state.overviewImageUrl) {
      URL.revokeObjectURL(state.overviewImageUrl);
      state.overviewImageUrl = "";
      state.overviewImageBlob = null;
    }
  }

  function updateModuleHeader() {
    const activeModule = getActiveModule();
    if (!activeModule) return;

    elements.moduleTitle.textContent = activeModule.title;
    elements.moduleDescription.textContent = activeModule.description;
    
    if (activeModule.id === MODULE_MATCH) {
      elements.activeEndpoint.textContent = "/api/v2/dashen-match/image";
    } else {
      elements.activeEndpoint.textContent = getEffectiveEndpoint(activeModule);
    }
  }

  function renderDynamicParams() {
    const activeModule = getActiveModule();
    elements.dynamicFields.innerHTML = "";
    
    if (!activeModule) return;

    // Advanced fields
    activeModule.fields.forEach((field) => {
      // Don't render index parameter in advanced settings for match module, since we query it visually
      if (activeModule.id === MODULE_MATCH && field.payload_key === "index") {
        return;
      }

      const label = document.createElement("label");
      label.className = "field";

      const title = document.createElement("span");
      title.textContent = field.label;
      label.appendChild(title);

      let control;
      if (field.control_type === "checkbox") {
        control = document.createElement("input");
        control.type = "checkbox";
        control.checked = Boolean(field.default);
      } else if (field.control_type === "select") {
        control = document.createElement("select");
        field.options.forEach((option) => {
          const optionNode = document.createElement("option");
          optionNode.value = option.value;
          optionNode.textContent = option.label;
          if (option.value === field.default) {
            optionNode.selected = true;
          }
          control.appendChild(optionNode);
        });
      } else {
        control = document.createElement("input");
        control.type = field.control_type === "number" ? "number" : "text";
        control.placeholder = field.placeholder || "";
        control.value = field.default === null || field.default === undefined ? "" : String(field.default);
      }

      control.dataset.payloadKey = field.payload_key;
      control.addEventListener("change", syncFormToPayload);
      control.addEventListener("input", syncFormToPayload);
      label.appendChild(control);

      if (field.help_text) {
        const hint = document.createElement("small");
        hint.textContent = field.help_text;
        label.appendChild(hint);
      }

      elements.dynamicFields.appendChild(label);
    });
  }

  function buildPayload() {
    const activeModule = getActiveModule();
    const payload = {};

    if (!activeModule) return payload;

    if (activeModule.requires_target) {
      const targetVal = String(elements.targetValueInput.value || "").replace(/＃/g, "#").trim();
      if (targetVal) {
        payload[activeModule.default_target_key || "bnet_id"] = targetVal;
      }
    }

    // Advanced fields
    const advancedControls = elements.dynamicFields.querySelectorAll("[data-payload-key]");
    advancedControls.forEach((control) => {
      const key = control.dataset.payloadKey;
      if (!key) return;
      if (control.type === "checkbox") {
        payload[key] = Boolean(control.checked);
      } else {
        const raw = String(control.value || "").trim();
        if (raw) {
          payload[key] = control.type === "number" ? parseInt(raw, 10) : raw;
        }
      }
    });

    return payload;
  }

  function syncFormToPayload() {
    updateModuleHeader();
  }

  // --- Fetch Match Details (3 images) ---
  async function handleQueryDetailClick() {
    const playerVal = String(elements.targetValueInput.value || "").replace(/＃/g, "#").trim();
    if (!playerVal) {
      setStatus("请输入玩家 ID (如 BattleTag)", true);
      return;
    }

    const selectVal = parseInt(elements.singleMatchIndexSelect.value, 10) || 1;
    const matchIndex = selectVal - 1; // 1-based to 0-based

    setStatus(`正在生成第 ${selectVal} 场对局的详细报告，请稍候...`);
    elements.queryDetailButton.disabled = true;
    elements.submitButton.disabled = true;
    clearImagePreview();
    switchMobileTab("preview");

    try {
      const payload = buildPayload();
      payload.bnet_id = playerVal;
      payload.index = matchIndex;
      payload.show_all_heroes = true;
      payload.analyze = true;

      const response = await fetch("/api/v2/dashen-match/detail/replies", {
        method: "POST",
        headers: {
          "Content-Type": "application/json; charset=utf-8",
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`服务器返回状态码: ${response.status}`);
      }

      const parsed = await response.json();
      if (!parsed.ok) {
        throw new Error(parsed.message || "后端接口返回失败");
      }

      const imageReplies = (parsed.replies || []).filter(r => r.type === "image" && r.base64);
      const textReplies = (parsed.replies || []).filter(r => r.type === "text" && r.data);

      if (imageReplies.length === 0 && textReplies.length === 0) {
        showTextError("无详情数据", "接口未返回任何图片或文本总结内容。");
        setStatus("无详情数据", true);
        return;
      }

      // Add image elements
      const labels = ["对局主画幅 (单局对局战绩)", "数据详情 (全员详细数据)", "AI 总结 (AI 犀利点评)"];
      imageReplies.forEach((reply, idx) => {
        const binary = window.atob(reply.base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
          bytes[i] = binary.charCodeAt(i);
        }
        const blob = new Blob([bytes], { type: reply.media_type || "image/png" });
        const titleLabel = labels[idx] || `详情图片 ${idx + 1}`;
        appendImageToPreview(blob, titleLabel);
      });

      // Add text elements
      textReplies.forEach((reply, idx) => {
        const titleLabel = `对局分析/提示 ${idx + 1}`;
        appendTextToPreview(reply.data, titleLabel);
      });

      setStatus(`成功加载第 ${selectVal} 场对局详情！`);
      elements.backToOverviewButton.classList.remove("hidden");
      elements.mobileBackToOverviewButton.classList.remove("hidden");

    } catch (err) {
      showTextError("加载详情失败", err.message || "请求失败，请确保本地服务正在运行。");
      setStatus("加载详情失败", true);
      if (state.overviewImageBlob) {
        elements.backToOverviewButton.classList.remove("hidden");
        elements.mobileBackToOverviewButton.classList.remove("hidden");
      }
    } finally {
      elements.queryDetailButton.disabled = false;
      elements.submitButton.disabled = false;
    }
  }

  // --- Return back to list overview ---
  function handleBackToOverviewClick() {
    if (!state.overviewImageBlob) return;
    clearImagePreview();
    appendImageToPreview(state.overviewImageBlob, "近期对局列表概览");
    state.overviewImageUrl = state.imageObjectUrls[state.imageObjectUrls.length - 1];
    elements.backToOverviewButton.classList.add("hidden");
    elements.mobileBackToOverviewButton.classList.add("hidden");
    setStatus("返回到近期对局列表概览图。");
  }

  // --- Submit handler for loading overview / standard images ---
  async function handleFormSubmit(event) {
    event.preventDefault();
    const activeModule = getActiveModule();
    if (!activeModule) {
      setStatus("未选择模块", true);
      return;
    }

    const payload = buildPayload();
    const targetVal = payload[activeModule.default_target_key || "bnet_id"];
    
    if (activeModule.requires_target && !targetVal) {
      setStatus("请输入玩家 ID (如 BattleTag)", true);
      return;
    }

    let endpoint = getEffectiveEndpoint(activeModule);
    let titleLabel = activeModule.title;

    if (activeModule.id === MODULE_MATCH) {
      endpoint = "/api/v2/dashen-match/image";
      titleLabel = "近期对局列表概览";
      
      if (state.overviewImageUrl) {
        URL.revokeObjectURL(state.overviewImageUrl);
        state.overviewImageUrl = "";
        state.overviewImageBlob = null;
      }
      elements.singleMatchDetailPanel.classList.add("hidden");
      elements.backToOverviewButton.classList.add("hidden");
    }

    setStatus("战绩卡片生成中，请稍候...");
    elements.submitButton.disabled = true;
    clearImagePreview();
    switchMobileTab("preview");

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json; charset=utf-8",
        },
        body: JSON.stringify(payload),
      });

      const contentType = String(response.headers.get("Content-Type") || "").toLowerCase();

      // Binary image response
      if (contentType.startsWith("image/")) {
        const blob = await response.blob();
        if (response.ok) {
          appendImageToPreview(blob, titleLabel);
          setStatus("生成成功！点击右侧预览可查看高清大图。");

          if (activeModule.id === MODULE_MATCH) {
            state.overviewImageUrl = state.imageObjectUrls[state.imageObjectUrls.length - 1];
            state.overviewImageBlob = blob;
            elements.singleMatchDetailPanel.classList.remove("hidden");
            elements.mobileSingleMatchPanel.classList.remove("hidden");
            elements.backToOverviewButton.classList.add("hidden");
            elements.mobileBackToOverviewButton.classList.add("hidden");
          }
        } else {
          showTextError("图像响应生成失败", `服务器返回了错误状态码: ${response.status}`);
          setStatus("生成失败", true);
        }
        return;
      }

      // JSON text response
      const text = await response.text();
      let parsed = null;
      try {
        parsed = JSON.parse(text);
      } catch (_e) {}

      if (!response.ok) {
        const errMsg = parsed && parsed.message ? parsed.message : text;
        showTextError("接口调用错误", errMsg || "未知后端错误");
        setStatus("请求失败", true);
        return;
      }

      // Replies JSON
      if (parsed && Array.isArray(parsed.replies)) {
        const imageReplies = parsed.replies.filter((r) => r && r.type === "image" && r.base64);
        const textReplies = parsed.replies.filter((r) => r && r.type === "text" && r.data);

        imageReplies.forEach((reply, idx) => {
          const binary = window.atob(reply.base64);
          const bytes = new Uint8Array(binary.length);
          for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
          }
          const blob = new Blob([bytes], { type: reply.media_type || "image/png" });
          appendImageToPreview(blob, activeModule.title + ` (部分 ${idx + 1})`);
        });

        textReplies.forEach((reply, idx) => {
          appendTextToPreview(reply.data, `文本数据 ${idx + 1}`);
        });

        if (imageReplies.length > 0 || textReplies.length > 0) {
          setStatus("生成成功！");
          return;
        }
      }

      // Fallback
      showTextError("成功返回数据", text.substring(0, 500) + (text.length > 500 ? "..." : ""));
      setStatus("生成完成 (非图片)");

    } catch (error) {
      showTextError("网络连接错误", error.message || "请求发送失败，请确认本地服务正常运行。");
      setStatus("网络请求失败", true);
    } finally {
      elements.submitButton.disabled = false;
    }
  }

  // --- Collapsible More features list rendering ---
  function renderModuleNav() {
    elements.moduleNav.innerHTML = "";
    modules.forEach((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "module-button" + (item.id === state.activeModuleId ? " is-active" : "");
      button.dataset.moduleId = item.id;
      button.innerHTML = "<strong>" + escapeHtml(item.title) + "</strong><span>" + escapeHtml(item.description) + "</span>";
      
      button.addEventListener("click", function () {
        setActiveFeature(item.id);
      });
      elements.moduleNav.appendChild(button);
    });
  }

  // --- Lightbox handlers ---
  function openLightbox(url) {
    if (!url) return;
    state.lightbox.activeUrl = url;
    state.lightbox.scale = 1.0;
    state.lightbox.translateX = 0;
    state.lightbox.translateY = 0;
    updateLightboxTransform();

    elements.lightboxImage.src = url;
    elements.lightboxDownload.href = url;
    elements.lightbox.classList.remove("hidden");
    document.body.style.overflow = "hidden";
  }

  function closeLightbox() {
    elements.lightbox.classList.add("hidden");
    document.body.style.overflow = "";
    state.lightbox.activeUrl = "";
  }

  function updateLightboxTransform() {
    elements.lightboxImage.style.transform = `translate(${state.lightbox.translateX}px, ${state.lightbox.translateY}px) scale(${state.lightbox.scale})`;
  }

  function handleLightboxWheel(event) {
    event.preventDefault();
    const zoomFactor = 0.15;
    if (event.deltaY < 0) {
      state.lightbox.scale = Math.min(6.0, state.lightbox.scale + zoomFactor);
    } else {
      state.lightbox.scale = Math.max(0.3, state.lightbox.scale - zoomFactor);
    }
    updateLightboxTransform();
  }

  function handleLightboxMouseDown(event) {
    event.preventDefault();
    state.lightbox.isDragging = true;
    state.lightbox.startX = event.clientX - state.lightbox.translateX;
    state.lightbox.startY = event.clientY - state.lightbox.translateY;
  }

  // Mouse move event
  function handleLightboxMouseMove(event) {
    if (!state.lightbox.isDragging) return;
    event.preventDefault();
    state.lightbox.translateX = event.clientX - state.lightbox.startX;
    state.lightbox.translateY = event.clientY - state.lightbox.startY;
    updateLightboxTransform();
  }

  function handleLightboxMouseUp() {
    state.lightbox.isDragging = false;
  }

  // --- Touch event handlers for mobile lightbox ---
  function handleLightboxTouchStart(event) {
    if (event.touches.length === 1) {
      event.preventDefault();
      const touch = event.touches[0];
      state.lightbox.isDragging = true;
      state.lightbox.startX = touch.clientX - state.lightbox.translateX;
      state.lightbox.startY = touch.clientY - state.lightbox.translateY;
    } else if (event.touches.length === 2) {
      // Pinch-to-zoom start
      state.lightbox.isDragging = false;
      const dx = event.touches[0].clientX - event.touches[1].clientX;
      const dy = event.touches[0].clientY - event.touches[1].clientY;
      state.lightbox.pinchStartDist = Math.hypot(dx, dy);
      state.lightbox.pinchStartScale = state.lightbox.scale;
    }
  }

  function handleLightboxTouchMove(event) {
    if (event.touches.length === 1 && state.lightbox.isDragging) {
      event.preventDefault();
      const touch = event.touches[0];
      state.lightbox.translateX = touch.clientX - state.lightbox.startX;
      state.lightbox.translateY = touch.clientY - state.lightbox.startY;
      updateLightboxTransform();
    } else if (event.touches.length === 2 && state.lightbox.pinchStartDist) {
      event.preventDefault();
      const dx = event.touches[0].clientX - event.touches[1].clientX;
      const dy = event.touches[0].clientY - event.touches[1].clientY;
      const dist = Math.hypot(dx, dy);
      const ratio = dist / state.lightbox.pinchStartDist;
      state.lightbox.scale = Math.min(6.0, Math.max(0.3, state.lightbox.pinchStartScale * ratio));
      updateLightboxTransform();
    }
  }

  function handleLightboxTouchEnd(event) {
    if (event.touches.length < 2) {
      state.lightbox.pinchStartDist = null;
    }
    if (event.touches.length === 0) {
      state.lightbox.isDragging = false;
    }
  }

  // --- Initializer ---
  function init() {
    initTheme();
    initCustomBackground();
    initMobileTabs();

    loadSavedPlayers();
    renderQuickPlayers();
    elements.savePlayerButton.addEventListener("click", handleSavePlayer);

    elements.tileToday.addEventListener("click", () => setActiveFeature(MODULE_TODAY));
    elements.tileQuick.addEventListener("click", () => setActiveFeature(MODULE_QUICK));
    elements.tileMatch.addEventListener("click", () => setActiveFeature(MODULE_MATCH));

    elements.targetValueInput.addEventListener("change", syncFormToPayload);
    elements.requestForm.addEventListener("submit", handleFormSubmit);

    // Bind sub-query controls for match detail (desktop & mobile)
    elements.queryDetailButton.addEventListener("click", handleQueryDetailClick);
    elements.backToOverviewButton.addEventListener("click", handleBackToOverviewClick);
    elements.mobileQueryDetailButton.addEventListener("click", handleQueryDetailClick);
    elements.mobileBackToOverviewButton.addEventListener("click", handleBackToOverviewClick);

    // Sync select value bi-directionally between desktop and mobile dropdowns
    if (elements.singleMatchIndexSelect && elements.mobileMatchIndexSelect) {
      elements.singleMatchIndexSelect.addEventListener("change", (e) => {
        elements.mobileMatchIndexSelect.value = e.target.value;
      });
      elements.mobileMatchIndexSelect.addEventListener("change", (e) => {
        elements.singleMatchIndexSelect.value = e.target.value;
      });
    }

    // Lightbox events
    elements.lightboxClose.addEventListener("click", closeLightbox);
    elements.lightbox.addEventListener("click", (event) => {
      if (event.target === elements.lightbox || event.target.classList.contains("lightbox-container")) {
        closeLightbox();
      }
    });

    elements.lightboxImage.addEventListener("wheel", handleLightboxWheel);
    elements.lightboxImage.addEventListener("mousedown", handleLightboxMouseDown);
    window.addEventListener("mousemove", handleLightboxMouseMove);
    window.addEventListener("mouseup", handleLightboxMouseUp);

    // Touch events for mobile lightbox drag & pinch-zoom
    elements.lightboxImage.addEventListener("touchstart", handleLightboxTouchStart, { passive: false });
    elements.lightboxImage.addEventListener("touchmove", handleLightboxTouchMove, { passive: false });
    elements.lightboxImage.addEventListener("touchend", handleLightboxTouchEnd);

    renderModuleNav();
    setActiveFeature(MODULE_TODAY);
  }

  init();
})();
