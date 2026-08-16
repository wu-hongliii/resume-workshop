const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

let state = null;
let saveTimer = null;
let questionHistory = [];
let currentQuestion = null;
let questionViewIndex = 0;
let draggedSection = null;
let tailoredPreviewTimer = null;
let aiEditTarget = null;
let aiEditUndo = null;
let aiEditRedo = null;
let saveChain = Promise.resolve();
let previewRequestId = 0;
let lastPreviewScale = 1;
let selectedProjectFiles = [];
let currentProjectDraft = null;
let templateSiteOffset = 0;
let onboardingStep = 0;
let currentAiSettings = null;

const onboardingStorageKey = "resume-workshop:onboarding:v2";
const termsStorageKey = "resume-workshop:terms:v1";
const supportPromptStorageKey = "resume-workshop:support-prompt:v1";
const onboardingSteps = [
  {
    label: "准备资料", page: "import", kicker: "STEP 01 · DEMO KIT",
    title: "先下载一套可以放心试错的资料",
    description: "完整资料包提供两条 FDE / AI 工程师演示路线。建议第一次先用演示资料走完流程，再换成自己的简历；下载动作不会改动现有档案。",
    points: ["同行业跳槽：从 AI 应用工程师定制为 FDE", "跨行业转行：从桥涵设计转向初级 FDE", "两条路线都包含旧简历、JD、补充经历和项目证据"],
    sample: "点击左侧“下载完整演示资料包”，解压后先阅读 00-开始前请读.txt。", done: "电脑中出现“简历工坊-完整演示资料包”文件夹。"
  },
  {
    label: "导入旧简历", page: "import", kicker: "STEP 02 · IMPORT",
    title: "像真实用户一样导入旧简历",
    description: "在“导入资料”选择一个案例里的旧简历 DOCX。你也可以多选 PDF、扫描件或照片；系统只提取原文，必须由你点击解析并确认。",
    points: ["先试 01-同行业跳槽-FDE 的旧简历", "体验 OCR 时可改用跨行业案例里的 JD 截图", "没有旧简历也可跳过并手动填写"],
    sample: "01-同行业跳槽-FDE / 01-旧简历-林知远-AI应用工程师-演示专用.docx", done: "导入区显示已提取文字及文件来源，原文件仍留在本机。"
  },
  {
    label: "确认档案", page: "profile", kicker: "STEP 03 · VERIFY",
    title: "逐项确认可长期复用的事实",
    description: "解析后进入“确认档案”，重点核对姓名、联系方式、公司、职位和起止时间。这里是基础人才档案，之后的每份岗位简历都会从这里取基本信息。",
    points: ["优先检查 OCR 最容易出错的日期、数字和专有名词", "岗位 AI 不会回写或覆盖这份基础档案", "演示资料都带“演示专用”标记，避免与真实资料混淆"],
    sample: "核对林知远（演示专用）、两段经历、教育背景和技能。", done: "档案内容准确，并已点击“保存并分析岗位”。"
  },
  {
    label: "识别岗位 JD", page: "match", kicker: "STEP 04 · POSITION",
    title: "粘贴 JD，或用截图体验 OCR 校对",
    description: "JD 是招聘页面里的职位描述。可直接粘贴资料包中的 TXT，也可复制 JD 截图后在输入框按 Ctrl+V；图片会先 OCR，再自动校对明显错字并保留修改记录。",
    points: ["文字版适合快速生成，截图版适合演示 OCR", "校对后仍可查看原始识别和修改明细", "匹配分只用于发现表达与信息缺口，不代表录用概率"],
    sample: "02-跨行业转行-FDE / 03-目标岗位JD截图-OCR演示专用.png", done: "JD 输入框中有完整职位描述，OCR 校对记录可展开查看。"
  },
  {
    label: "选择求职方式", page: "match", kicker: "STEP 05 · GENERATE",
    title: "告诉系统这是跳槽，还是转行",
    description: "同方向跳槽会重组已有相关经历；跨行业转行只保留基础事实，并根据 JD 和能力层级起草个人项目与技能内容，不虚构公司任职、学历或证书。",
    points: ["同行业路线选择“同方向跳槽”", "跨行业路线选择“跨行业转行”，再选当前能力层级", "可粘贴补充经历，或选择项目证据文件夹生成可审查草稿"],
    sample: "使用对应案例的补充经历 TXT 和“项目证据”文件夹。", done: "匹配分析已完成，求职模式、补充信息和项目草稿均符合所选路线。"
  },
  {
    label: "编辑岗位正文", page: "polish", kicker: "STEP 06 · EDIT",
    title: "先生成全文，再按你的判断修改",
    description: "右上角设置里选择 AI 服务并填入自己的 API Key，或连接本机 Ollama / LM Studio 后生成岗位简历。正文与基础档案完全分离，可手动增删，也可选中字段让右侧 AI 定向修改。",
    points: ["未选字段时可让 AI 智能新增项目或其他模块", "选中字段后只修改当前内容，支持撤销和恢复", "动态追问用于补充细节，可上一问、下一问或跳过"],
    sample: "要求 AI 强化客户沟通、原型交付和评测闭环，再人工检查事实边界。", done: "岗位正文已生成，至少人工检查并修改过一处内容。"
  },
  {
    label: "排版并导出", page: "design", kicker: "STEP 07 · EXPORT",
    title: "导入模板，检查成品并导出",
    description: "在“排版导出”导入资料包里的演示模板，选择默认一页或允许多页。实时预览确认无溢出后，可分别导出 Word 和 PDF。",
    points: ["默认一页会自动压缩，内容过多时建议允许多页", "自定义模板只提取视觉规则，不导入模板示例文字", "满意的岗位版本可保存到岗位库，完整数据也可在设置中备份"],
    sample: "03-自定义简历模板 / 编辑部单栏-演示模板.docx", done: "Word 与 PDF 均已下载并打开检查，排版与预览基本一致。"
  }
];

function renderOnboardingNav() {
  const list = $("#onboardingStepList");
  if (list.children.length) return;
  list.innerHTML = onboardingSteps.map((item, index) => `<li><button type="button" data-onboarding-step="${index}"><b>${String(index + 1).padStart(2, "0")}</b><span>${escapeHtml(item.label)}</span></button></li>`).join("");
}

function renderOnboardingStep(index) {
  renderOnboardingNav();
  onboardingStep = Math.max(0, Math.min(index, onboardingSteps.length - 1));
  const item = onboardingSteps[onboardingStep];
  $("#onboardingKicker").textContent = item.kicker;
  $("#onboardingNumber").textContent = String(onboardingStep + 1).padStart(2, "0");
  $("#onboardingTitle").textContent = item.title;
  $("#onboardingDescription").textContent = item.description;
  $("#onboardingPoints").innerHTML = item.points.map(point => `<li>${escapeHtml(point)}</li>`).join("");
  $("#onboardingSample").textContent = item.sample;
  $("#onboardingDone").textContent = item.done;
  $("#onboardingProgressBar").style.width = `${((onboardingStep + 1) / onboardingSteps.length) * 100}%`;
  $$('[data-onboarding-step]').forEach(button => button.classList.toggle("active", Number(button.dataset.onboardingStep) === onboardingStep));
  $("#previousOnboardingBtn").disabled = onboardingStep === 0;
  $("#nextOnboardingBtn").textContent = onboardingStep === onboardingSteps.length - 1 ? "开始制作" : "下一步";
}

function openOnboarding(startAt = 0) {
  renderOnboardingStep(startAt);
  const dialog = $("#onboardingDialog");
  if (!dialog.open) dialog.showModal();
}

function closeOnboarding(markDone = true) {
  if (markDone) localStorage.setItem(onboardingStorageKey, "done");
  const dialog = $("#onboardingDialog");
  if (dialog.open) dialog.close();
}

function openAbout(fromExport = false) {
  $("#supportPromptMessage").classList.toggle("hidden", !fromExport);
  const dialog = $("#aboutDialog");
  if (!dialog.open) dialog.showModal();
}

function showSupportAfterFirstExport() {
  if (localStorage.getItem(supportPromptStorageKey)) return;
  localStorage.setItem(supportPromptStorageKey, "shown");
  openAbout(true);
}

const templateSites = [
  { name: "YY简历网", type: "中文 Word · 免费区", url: "https://www.yyjianli.com/" },
  { name: "简历下载网", type: "中文 Word · 免注册", url: "https://jianlixiazai.cn/" },
  { name: "Career Reload", type: "英文 Word · ATS", url: "https://www.careerreload.com/word-resume-templates/" },
  { name: "QuickCVLab", type: "在线制作 · Word / PDF", url: "https://quickcvlab.com/" },
  { name: "EasyFreeResume", type: "在线制作 · PDF", url: "https://easyfreeresume.com/templates" }
];

const sectionLabels = {
  summary: "个人概述", experience: "工作经历", projects: "项目经历",
  education: "教育背景", skills: "专业技能", certificates: "证书与荣誉", languages: "语言能力"
};
const protectedBasicFields = ["name", "phone", "email", "city", "links", "photo"];

const configs = {
  experience: { title: "工作经历", fields: [["company", "公司"], ["role", "职位"], ["start", "开始时间"], ["end", "结束时间"], ["location", "地点"], ["bullets", "职责与成果（每行一条）", "textarea"]], empty: { company: "", role: "", start: "", end: "", location: "", bullets: [] } },
  projects: { title: "项目经历", fields: [["name", "项目名称"], ["role", "你的角色"], ["start", "开始时间"], ["end", "结束时间"], ["technologies", "技术/工具"], ["bullets", "工作与成果（每行一条）", "textarea"]], empty: { name: "", role: "", start: "", end: "", technologies: "", bullets: [] } },
  education: { title: "教育背景", fields: [["school", "学校"], ["degree", "学历"], ["major", "专业"], ["start", "开始时间"], ["end", "结束时间"]], empty: { school: "", degree: "", major: "", start: "", end: "" } },
  skills: { title: "专业技能", fields: [["category", "技能类别"], ["items", "技能项（每行或顿号分隔）", "textarea"]], empty: { category: "", items: [] } }
};

function escapeHtml(value = "") {
  return String(value).replace(/[&<>'"]/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[ch]));
}

function renderTemplateSites() {
  const visibleSites = Array.from({ length: 3 }, (_, index) => templateSites[(templateSiteOffset + index) % templateSites.length]);
  $("#templateSites").innerHTML = visibleSites.map(site => `<a href="${site.url}" target="_blank" rel="noopener"><strong>${site.name}</strong><small>${site.type}</small></a>`).join("");
}

async function api(path, options = {}) {
  if (path.startsWith("/api/ai/") && !path.includes("test-ai")) ensureAiConsent();
  const headers = { ...(options.headers || {}) };
  const binaryBody = options.body instanceof Blob || options.body instanceof ArrayBuffer || ArrayBuffer.isView(options.body) || options.body instanceof FormData;
  if (options.body && !binaryBody && typeof options.body !== "string") {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }
  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    let message = `请求失败（${response.status}）`;
    try { message = (await response.json()).detail || message; } catch (_) {}
    throw new Error(message);
  }
  const type = response.headers.get("content-type") || "";
  return type.includes("json") ? response.json() : response.text();
}

function ensureAiConsent() {
  const provider = currentAiSettings?.ai_provider || "deepseek";
  if (["ollama", "lmstudio"].includes(provider)) return;
  const endpoint = currentAiSettings?.ai_base_url || "";
  const key = `resume-workshop:ai-consent:${provider}:${endpoint}:v1`;
  if (localStorage.getItem(key)) return;
  const name = currentAiSettings?.ai_provider_name || provider;
  const accepted = confirm(`本次操作会把完成任务所需的简历正文、JD 或选中内容发送给 ${name}（${endpoint}）。API Key、照片和本地历史记录不会作为简历内容发送。是否继续？`);
  if (!accepted) throw new Error("已取消云端 AI 调用");
  localStorage.setItem(key, "accepted");
}

function providerOption(providerId) {
  return currentAiSettings?.ai_providers?.find(item => item.id === providerId) || null;
}

function renderAiSettings(settings, resetFields = true) {
  currentAiSettings = settings;
  const select = $("#aiProvider");
  if (!select.options.length) {
    select.innerHTML = settings.ai_providers.map(item => `<option value="${item.id}">${escapeHtml(item.name)}${item.live_tested ? " · 已实测" : ""}</option>`).join("");
  }
  select.value = settings.ai_provider;
  if (resetFields) {
    $("#aiBaseUrl").value = settings.ai_base_url || "";
    $("#aiModel").value = settings.ai_model || "";
    $("#apiKey").value = "";
  }
  const option = providerOption(select.value);
  $("#aiBaseUrl").readOnly = !["custom", "ollama", "lmstudio"].includes(select.value);
  const readiness = settings.ai_ready ? "可使用" : "尚未完成配置";
  const keyText = settings.configured ? `密钥 ${settings.masked}` : (option?.key_required ? "未保存密钥" : "无需密钥");
  $("#keyStatus").textContent = `${settings.ai_provider_name} · ${settings.ai_model || "未填写模型"} · ${keyText} · ${readiness}`;
}

function aiSettingsPayload(includeKey = true) {
  const payload = {
    ai_provider: $("#aiProvider").value,
    ai_base_url: $("#aiBaseUrl").value.trim(),
    ai_model: $("#aiModel").value.trim(),
  };
  const key = $("#apiKey").value.trim();
  if (includeKey && key) payload.api_key = key;
  return payload;
}

function toast(message, error = false) {
  const node = $("#toast");
  node.textContent = message;
  node.className = error ? "show error" : "show";
  clearTimeout(node._timer);
  node._timer = setTimeout(() => node.className = "", 3200);
}

function busy(button, on, text = "处理中…") {
  if (!button) return;
  if (on) { button.dataset.original = button.innerHTML; button.innerHTML = text; button.disabled = true; }
  else { button.innerHTML = button.dataset.original || button.innerHTML; button.disabled = false; }
}

function showStep(name) {
  $$(".panel").forEach(panel => panel.classList.toggle("active", panel.id === `panel-${name}`));
  $$(".step").forEach(step => step.classList.toggle("active", step.dataset.step === name));
  if (name === "profile") renderProfileEditor();
  if (name === "polish") renderTailoredContent();
  if (name === "design") { renderSectionOrder(); updatePreview(); }
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function setByPath(object, path, value) {
  const parts = path.split(".");
  let cursor = object;
  parts.slice(0, -1).forEach(part => { cursor = cursor[Number.isInteger(+part) ? +part : part]; });
  cursor[parts.at(-1)] = value;
}

function editorFieldValue(path, text) {
  if (/\.items$/.test(path)) return text.split(/\n|、/).map(item => item.trim()).filter(Boolean);
  if (/\.bullets$/.test(path) || ["certificates", "languages"].includes(path)) {
    return text.split(/\n/).map(item => item.trim()).filter(Boolean);
  }
  return text;
}

function queueSave(label = null) {
  $("#saveStatus").textContent = "保存中…";
  clearTimeout(saveTimer);
  saveTimer = setTimeout(async () => {
    try {
      await persistState(label);
      $("#saveStatus").textContent = "已保存";
    } catch (error) {
      $("#saveStatus").textContent = "保存失败";
      toast(error.message, true);
    }
  }, label ? 0 : 450);
}

function persistState(label = null) {
  const payload = cloneData(state);
  saveChain = saveChain.catch(() => {}).then(() => api("/api/state", { method: "PUT", body: { payload, version_label: label } }));
  return saveChain;
}

function ensureSameResume(resumeReference) {
  if (state.resume === resumeReference) return true;
  toast("任务完成时你已切换岗位，本次旧结果未应用", true);
  return false;
}

function fieldHtml(path, label, value, type = "text", full = false) {
  const display = Array.isArray(value) ? value.join("\n") : (value || "");
  const id = `profile-${path.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
  const control = type === "textarea"
    ? `<textarea id="${id}" data-profile-path="${path}">${escapeHtml(display)}</textarea>`
    : `<input id="${id}" type="text" data-profile-path="${path}" value="${escapeHtml(display)}">`;
  return `<div class="field ${full || type === "textarea" ? "full" : ""}"><label for="${id}">${label}</label>${control}</div>`;
}

function renderProfileEditor() {
  const profile = state.profile;
  const basics = profile.basics;
  let html = `<section class="editor-section"><header><h2>基本信息</h2><span class="hint">必填项优先</span></header><div class="field-grid">
    ${fieldHtml("basics.name", "姓名", basics.name)}${fieldHtml("basics.target_role", "目标职位", basics.target_role)}
    ${fieldHtml("basics.phone", "手机", basics.phone)}${fieldHtml("basics.email", "邮箱", basics.email)}
    ${fieldHtml("basics.city", "所在城市", basics.city)}${fieldHtml("basics.links", "个人主页 / GitHub", basics.links)}
    ${fieldHtml("basics.summary", "个人概述", basics.summary, "textarea", true)}</div></section>`;

  Object.entries(configs).forEach(([key, config]) => {
    const items = profile[key] || [];
    html += `<section class="editor-section"><header><h2>${config.title}</h2><button class="text-button" data-add-item="${key}">＋ 添加一项</button></header>`;
    if (!items.length) html += `<p class="hint">暂无内容。可以添加，或返回导入后使用 AI 解析。</p>`;
    items.forEach((item, index) => {
      html += `<div class="item-card"><button class="remove-item" data-remove-item="${key}.${index}" title="删除">×</button><div class="field-grid">`;
      config.fields.forEach(([field, label, type]) => {
        html += fieldHtml(`${key}.${index}.${field}`, label, item[field], type, type === "textarea");
      });
      html += `</div></div>`;
    });
    html += `</section>`;
  });

  [["certificates", "证书与荣誉"], ["languages", "语言能力"]].forEach(([key, title]) => {
    html += `<section class="editor-section"><header><h2>${title}</h2></header>${fieldHtml(key, "每行一项", profile[key] || [], "textarea", true)}</section>`;
  });
  $("#profileEditor").innerHTML = html;
  bindProfileInputs();
  updateCompleteness();
  updatePhoto();
}

function bindProfileInputs() {
  $$('[data-profile-path]', $("#profileEditor")).forEach(input => {
    input.addEventListener("input", () => {
      const path = input.dataset.profilePath;
      setByPath(state.profile, path, editorFieldValue(path, input.value));
      updateCompleteness(); queueSave();
    });
  });
  $$('[data-add-item]', $("#profileEditor")).forEach(button => button.addEventListener("click", () => {
    const key = button.dataset.addItem;
    state.profile[key].push(structuredClone(configs[key].empty)); renderProfileEditor(); queueSave();
  }));
  $$('[data-remove-item]', $("#profileEditor")).forEach(button => button.addEventListener("click", () => {
    const [key, index] = button.dataset.removeItem.split(".");
    state.profile[key].splice(+index, 1); renderProfileEditor(); queueSave("删除档案条目前");
  }));
}

function updateCompleteness() {
  const basics = state.profile.basics;
  const checks = [basics.name, basics.target_role, basics.phone, basics.email, basics.summary, state.profile.experience?.length, state.profile.education?.length, state.profile.skills?.length];
  $("#completeness").textContent = `${Math.round(checks.filter(Boolean).length / checks.length * 100)}%`;
}

function activeProfile() {
  if (!state.resume.tailored_profile) return state.profile;
  const profile = structuredClone(state.resume.tailored_profile);
  profile.basics = profile.basics || {};
  protectedBasicFields.forEach(field => profile.basics[field] = state.profile.basics[field] || "");
  return profile;
}

function ensureTailoredProfile() {
  if (!state.resume.tailored_profile) state.resume.tailored_profile = structuredClone(state.profile);
  state.resume.tailored_profile.basics = state.resume.tailored_profile.basics || {};
  protectedBasicFields.forEach(field => state.resume.tailored_profile.basics[field] = state.profile.basics[field] || "");
  return state.resume.tailored_profile;
}

function tailoredFieldHtml(path, label, value, type = "text") {
  const display = Array.isArray(value) ? value.join("\n") : (value || "");
  const id = `tailored-${path.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
  const control = type === "textarea"
    ? `<textarea id="${id}" data-tailored-path="${path}">${escapeHtml(display)}</textarea>`
    : `<input id="${id}" type="text" data-tailored-path="${path}" value="${escapeHtml(display)}">`;
  return `<div class="field ${type === "textarea" ? "full" : ""}"><label for="${id}">${label}</label>${control}</div>`;
}

function tailoredControlValue(input) {
  return editorFieldValue(input.dataset.tailoredPath, input.value);
}

function commitTailoredControl(input) {
  setByPath(state.resume.tailored_profile, input.dataset.tailoredPath, tailoredControlValue(input));
  clearTimeout(tailoredPreviewTimer);
  tailoredPreviewTimer = setTimeout(updatePreview, 300);
}

function recordEditUndo(entry) {
  aiEditUndo = entry;
  aiEditRedo = null;
  updateEditHistoryControls();
}

function updateEditHistoryControls() {
  $("#undoAiEditBtn").disabled = !aiEditUndo;
  $("#redoAiEditBtn").disabled = !aiEditRedo;
  const hint = $("#editHistoryHint");
  if (!hint) return;
  if (aiEditUndo) hint.textContent = `可撤销：${aiEditUndo.label || "上次操作"}`;
  else if (aiEditRedo) hint.textContent = `可恢复：${aiEditRedo.label || "上次操作"}`;
  else hint.textContent = "暂无可撤销或恢复的操作";
}

async function loadPersistentEditHistory() {
  try {
    const history = await api("/api/edit-history");
    aiEditUndo = history.undo || null;
    aiEditRedo = history.redo || null;
  } catch (_) {
    aiEditUndo = null;
    aiEditRedo = null;
  }
  updateEditHistoryControls();
}

function updateAiEditTarget(input = null) {
  const card = $("#aiEditTarget");
  const applyButton = $("#applyAiEditBtn");
  const addButton = $("#applyAiAddBtn");
  if (!card || !applyButton || !addButton) return;
  if (!input) {
    aiEditTarget = null;
    card.classList.add("empty");
    card.innerHTML = "<strong>整份简历调整模式</strong><span>没有选中字段，可以让 AI 新增、删除或重新生成项目与其他模块。</span>";
    $("#clearAiTargetBtn")?.classList.add("hidden");
    applyButton.disabled = !state?.resume?.tailored_profile;
    addButton.disabled = !state?.resume?.tailored_profile;
    addButton.classList.remove("hidden");
    applyButton.className = "secondary wide";
    applyButton.textContent = "让 AI 调整整份简历";
    return;
  }
  const start = typeof input.selectionStart === "number" ? input.selectionStart : 0;
  const end = typeof input.selectionEnd === "number" ? input.selectionEnd : start;
  const selectedText = end > start ? input.value.slice(start, end) : "";
  const label = input.closest(".field")?.querySelector("label")?.textContent?.trim() || input.dataset.tailoredPath;
  aiEditTarget = { path: input.dataset.tailoredPath, label, fullText: input.value, start, end, selectedText };
  card.classList.remove("empty");
  $("#clearAiTargetBtn")?.classList.remove("hidden");
  addButton.classList.add("hidden");
  applyButton.className = "primary wide";
  card.innerHTML = `<strong>${escapeHtml(selectedText ? `已选中：${label}` : `当前字段：${label}`)}</strong><span>${escapeHtml(selectedText ? `“${selectedText.slice(0, 120)}${selectedText.length > 120 ? "…" : "”"}` : "未选中文字，AI 将修改整个字段。")}</span>`;
  applyButton.disabled = false;
  applyButton.textContent = selectedText ? "让 AI 修改选中片段" : "让 AI 修改当前字段";
}

function renderTailoredContent() {
  const container = $("#tailoredContentEditor");
  if (!container) return;
  if (!state.resume.tailored_profile) {
    container.innerHTML = '<div class="empty-state compact-empty">生成岗位定制简历后，正文会完整显示在这里。</div>';
    updateAiEditTarget();
    return;
  }
  const profile = activeProfile();
  const basics = profile.basics || {};
  const baseBasics = state.profile.basics || {};
  let html = `<div class="tailored-source"><strong>当前岗位版本</strong><span>基本信息沿用：${escapeHtml(baseBasics.name || "未填写")} · ${escapeHtml(baseBasics.phone || "未填写手机号")}</span></div>`;
  html += `<section class="tailored-section" data-tailored-section="basics"><header><h3>求职方向与个人概述</h3><span>AI 已按 JD 定制</span></header><div class="field-grid">${tailoredFieldHtml("basics.target_role", "目标职位", basics.target_role)}${tailoredFieldHtml("basics.summary", "个人概述", basics.summary, "textarea")}</div></section>`;

  Object.entries(configs).forEach(([key, config]) => {
    const items = profile[key] || [];
    html += `<details class="tailored-section" data-tailored-section="${key}" open><summary><strong>${config.title}</strong><div class="tailored-section-actions"><span>${items.length} 项</span><button type="button" data-tailored-add="${key}">＋ 新增一项</button></div></summary>`;
    if (!items.length) html += '<p class="hint">当前岗位版本没有此部分内容。</p>';
    items.forEach((item, index) => {
      html += `<div class="tailored-item" data-tailored-item="${key}.${index}"><div class="tailored-item-toolbar"><span>第 ${index + 1} 项</span><button type="button" data-tailored-remove="${key}.${index}">删除此项</button></div><div class="field-grid">`;
      config.fields.forEach(([field, label, type]) => {
        html += tailoredFieldHtml(`${key}.${index}.${field}`, label, item[field], type);
      });
      html += '</div></div>';
    });
    html += '</details>';
  });

  [["certificates", "证书与荣誉"], ["languages", "语言能力"]].forEach(([key, title]) => {
    html += `<details class="tailored-section"><summary><strong>${title}</strong><span>${(profile[key] || []).length} 项</span></summary>${tailoredFieldHtml(key, "每行一项", profile[key] || [], "textarea")}</details>`;
  });
  container.innerHTML = html;
  updateAiEditTarget();
  $$('[data-tailored-path]', container).forEach(input => {
    input.addEventListener("focus", () => {
      input._editStartValue = input.value;
      input._manualUndoCaptured = false;
      updateAiEditTarget(input);
    });
    ["select", "keyup", "mouseup"].forEach(name => input.addEventListener(name, () => updateAiEditTarget(input)));
    input.addEventListener("input", () => {
      const label = input.closest(".field")?.querySelector("label")?.textContent?.trim() || input.dataset.tailoredPath;
      if (!input._manualUndoCaptured) {
        recordEditUndo({ kind: "field", path: input.dataset.tailoredPath, value: input._editStartValue ?? "", label: `手动编辑${label}` });
        input._manualUndoCaptured = true;
      }
      commitTailoredControl(input);
      updateAiEditTarget(input);
      queueSave(`手动编辑岗位字段：${label}`);
    });
  });
  $$('[data-tailored-add]', container).forEach(button => button.addEventListener("click", event => {
    event.preventDefault(); event.stopPropagation();
    manualTailoredItemChange("add", button.dataset.tailoredAdd).catch(error => toast(error.message, true));
  }));
  $$('[data-tailored-remove]', container).forEach(button => button.addEventListener("click", event => {
    event.preventDefault(); event.stopPropagation();
    const [section, index] = button.dataset.tailoredRemove.split(".");
    manualTailoredItemChange("remove", section, +index).catch(error => toast(error.message, true));
  }));
}

async function manualTailoredItemChange(action, section, index = -1) {
  const config = configs[section];
  if (!config || !state.resume.tailored_profile) return;
  const before = structuredClone(state.resume.tailored_profile);
  const items = state.resume.tailored_profile[section] || (state.resume.tailored_profile[section] = []);
  if (action === "add") items.push(structuredClone(config.empty));
  else if (index >= 0 && index < items.length) items.splice(index, 1);
  else return;
  recordEditUndo({ kind: "profile", profile: before, label: `${action === "add" ? "新增" : "删除"}${config.title}` });
  await persistState(`手动${action === "add" ? "新增" : "删除"}${config.title}`);
  renderTailoredContent();
  updatePreview();
  if (action === "add") {
    const added = $(`[data-tailored-item="${section}.${items.length - 1}"] [data-tailored-path]`);
    added?.focus();
  }
  toast(`已${action === "add" ? "新增" : "删除"}${config.title}${action === "remove" ? "，可立即撤销" : ""}`);
}

async function applyAiSelectionEdit() {
  const instruction = $("#aiEditInstruction").value.trim();
  if (!instruction) { toast("请告诉 AI 你希望怎么修改", true); return; }
  if (!aiEditTarget) { await applyAiSmartAdd(instruction, "adjust", $("#applyAiEditBtn")); return; }
  const target = $$('[data-tailored-path]').find(input => input.dataset.tailoredPath === aiEditTarget.path);
  if (!target || target.value !== aiEditTarget.fullText) { toast("正文已发生变化，请重新选择后再修改", true); return; }
  const button = $("#applyAiEditBtn");
  const resumeReference = state.resume;
  busy(button, true, "AI 正在修改…");
  try {
    const selection = { ...aiEditTarget };
    const result = await api("/api/ai/edit-selection", { method: "POST", body: {
      profile: activeProfile(), jd: state.resume.jd, path: selection.path, field_label: selection.label,
      full_text: selection.fullText, selected_text: selection.selectedText,
      selection_start: selection.start, selection_end: selection.end, instruction,
    } });
    if (!ensureSameResume(resumeReference)) return;
    const replacement = result.replacement_text ?? "";
    const nextValue = selection.selectedText
      ? selection.fullText.slice(0, selection.start) + replacement + selection.fullText.slice(selection.end)
      : replacement;
    recordEditUndo({ kind: "field", path: selection.path, value: selection.fullText, label: selection.label });
    target.value = nextValue;
    commitTailoredControl(target);
    await persistState(`AI 局部修改：${selection.label}`);
    $("#aiEditInstruction").value = "";
    target.focus();
    target.setSelectionRange?.(selection.start, selection.start + replacement.length);
    updateAiEditTarget(target);
    showRefineChanges([{ path: selection.path, label: selection.label }]);
    updatePreview();
    toast(`AI 已修改“${selection.label}”，可立即撤销`);
  } catch (error) { toast(error.message, true); }
  finally { busy(button, false); }
}

async function applyAiSmartAdd(instruction, mode, button) {
  if (!state.resume.tailored_profile) { toast("请先生成岗位定制简历", true); return; }
  busy(button, true, mode === "add" ? "AI 正在新增…" : "AI 正在调整结构…");
  const resumeReference = state.resume;
  try {
    const before = structuredClone(state.resume.tailored_profile);
    const result = await api("/api/ai/add-content", { method: "POST", body: {
      profile: activeProfile(), jd: state.resume.jd, instruction, mode,
    } });
    if (!ensureSameResume(resumeReference)) return;
    const refined = result.profile;
    refined.basics = refined.basics || {};
    protectedBasicFields.forEach(field => refined.basics[field] = state.profile.basics[field] || "");
    recordEditUndo({ kind: "profile", profile: before, label: mode === "add" ? "智能新增" : "整份简历调整" });
    state.resume.tailored_profile = refined;
    await persistState(mode === "add" ? "AI 智能新增简历内容" : "AI 调整岗位简历结构");
    $("#aiEditInstruction").value = "";
    renderTailoredContent();
    showRefineChanges(result.changes || []);
    updatePreview();
    toast(`AI 已${mode === "add" ? "新增内容" : "调整简历"}，实际修改 ${(result.changes || []).length} 处，可立即撤销`);
  } catch (error) { toast(error.message, true); }
  finally { busy(button, false); }
}

async function undoAiSelectionEdit() {
  if (!aiEditUndo) return;
  const undo = aiEditUndo;
  if (undo.kind === "profile") {
    aiEditRedo = { kind: "profile", profile: structuredClone(state.resume.tailored_profile), label: undo.label };
    state.resume.tailored_profile = structuredClone(undo.profile);
    await persistState(`撤销操作：${undo.label}`);
    aiEditUndo = null;
    updateEditHistoryControls();
    renderTailoredContent();
    updatePreview();
    toast("已撤销上次操作");
    return;
  }
  const target = $$('[data-tailored-path]').find(input => input.dataset.tailoredPath === undo.path);
  if (!target) { toast("当前字段已不存在，无法撤销", true); return; }
  aiEditRedo = { kind: "field", path: undo.path, value: target.value, label: undo.label };
  target.value = undo.value;
  commitTailoredControl(target);
  await persistState(`撤销 AI 局部修改：${undo.label}`);
  aiEditUndo = null;
  updateEditHistoryControls();
  target.focus();
  updateAiEditTarget(target);
  updatePreview();
  toast("已撤销本次 AI 修改");
}

async function redoAiSelectionEdit() {
  if (!aiEditRedo) return;
  const redo = aiEditRedo;
  if (redo.kind === "profile") {
    aiEditUndo = { kind: "profile", profile: structuredClone(state.resume.tailored_profile), label: redo.label };
    state.resume.tailored_profile = structuredClone(redo.profile);
    await persistState(`恢复操作：${redo.label}`);
    aiEditRedo = null;
    updateEditHistoryControls();
    renderTailoredContent();
    updatePreview();
    toast("已恢复上次操作");
    return;
  }
  const target = $$('[data-tailored-path]').find(input => input.dataset.tailoredPath === redo.path);
  if (!target) { toast("当前字段已不存在，无法恢复", true); return; }
  aiEditUndo = { kind: "field", path: redo.path, value: target.value, label: redo.label };
  target.value = redo.value;
  commitTailoredControl(target);
  await persistState(`恢复操作：${redo.label}`);
  aiEditRedo = null;
  updateEditHistoryControls();
  target.focus();
  updateAiEditTarget(target);
  updatePreview();
  toast("已恢复上次操作");
}

function updateTailoredStatus() {
  const tailored = !!state.resume.tailored_profile;
  const stale = tailored && state.resume.tailored_jd !== state.resume.jd;
  const banner = $("#tailoredBanner");
  banner.classList.toggle("active", tailored && !stale);
  banner.querySelector("span").textContent = tailored ? (stale ? "定制内容待更新" : "岗位定制模式") : "基础档案模式";
  banner.querySelector("p").textContent = tailored
    ? (stale ? "JD 已发生变化，请重新生成后再继续优化或导出。" : "当前改写、翻译、预览和导出均作用于独立的岗位定制简历，基础档案不会被覆盖。")
    : "尚未生成岗位定制内容，当前操作将以基础档案为准。";
  const badge = $("#contentSourceBadge");
  badge.classList.toggle("active", tailored && !stale);
  badge.textContent = tailored ? (stale ? "岗位内容待重新生成" : "岗位定制内容") : "基础档案";
}

function updatePhoto() {
  const photo = state.profile.basics.photo;
  const preview = $("#photoPreview");
  preview.textContent = photo ? "" : "＋";
  preview.style.backgroundImage = photo ? `url(${photo})` : "";
}

async function handleFiles(fileList) {
  const files = [...(fileList || [])];
  if (!files.length) return;
  const meta = $("#parseMeta");
  const results = [];
  const errors = [];
  for (let index = 0; index < files.length; index += 1) {
    const file = files[index];
    meta.textContent = `正在解析 ${index + 1}/${files.length}：${file.name}…`;
    try {
      const result = await extractLocalText(file);
      results.push(result);
    } catch (error) {
      errors.push(`${file.name}：${error.message}`);
    }
  }
  if (results.length) {
    const extracted = results.map(result => `===== ${result.filename} =====\n${result.text}`).join("\n\n");
    const existing = $("#rawText").value.trim();
    $("#rawText").value = [existing, extracted].filter(Boolean).join("\n\n");
    const ocrCount = results.filter(result => result.used_ocr).length;
    const lowConfidence = results.filter(result => result.used_ocr && typeof result.ocr_confidence === "number" && result.ocr_confidence < 0.82).length;
    meta.textContent = `已提取 ${results.length}/${files.length} 个文件 · ${results.reduce((sum, item) => sum + item.text.length, 0)} 字${ocrCount ? ` · ${ocrCount} 个使用本地 OCR` : ""}${lowConfidence ? ` · ${lowConfidence} 个识别可信度偏低，请重点校对` : ""}`;
  } else {
    meta.textContent = `解析失败 · 0/${files.length} 个文件`;
  }
  if (errors.length) toast(`部分文件未能解析：${errors.join("；")}`, true);
  else toast(`已合并提取 ${results.length} 个文件，请检查原文后继续`);
  $("#resumeFile").value = "";
}

async function extractLocalText(file, filename = file.name) {
  return api(`/api/import?filename=${encodeURIComponent(filename)}`, { method: "POST", headers: { "Content-Type": "application/octet-stream" }, body: await file.arrayBuffer() });
}

async function handleJdPaste(event) {
  const imageItems = [...(event.clipboardData?.items || [])].filter(item => item.type.startsWith("image/"));
  if (!imageItems.length) return;
  event.preventDefault();
  const status = $("#jdPasteStatus");
  status.className = "paste-hint processing";
  status.textContent = `正在用本地 OCR 识别 ${imageItems.length} 张岗位截图…`;
  const pages = [];
  const screenshots = [];
  const errors = [];
  for (let index = 0; index < imageItems.length; index += 1) {
    const file = imageItems[index].getAsFile();
    if (!file) continue;
    const extension = file.type.split("/")[1]?.replace("jpeg", "jpg") || "png";
    try {
      const result = await extractLocalText(file, `clipboard-jd-${Date.now()}-${index + 1}.${extension}`);
      pages.push({ index: pages.length + 1, filename: result.filename, text: result.text, confidence: result.ocr_confidence });
      screenshots.push(await fileToDataUrl(file));
    } catch (error) {
      errors.push(error.message);
    }
  }
  if (pages.length) {
    const textarea = $("#jdText");
    const inserted = pages.map(page => `【截图 ${page.index}】\n${page.text}`).join("\n\n");
    const start = textarea.selectionStart ?? textarea.value.length;
    const end = textarea.selectionEnd ?? start;
    textarea.value = textarea.value.slice(0, start) + inserted + textarea.value.slice(end);
    textarea.setSelectionRange(start + inserted.length, start + inserted.length);
    state.resume.jd_ocr_original = textarea.value;
    state.resume.jd_ocr_images = screenshots;
    state.resume.jd = textarea.value;
    queueSave();
    status.textContent = "本地 OCR 已完成，正在让 AI 校对明显错字…";
    try {
      const correction = await api("/api/ai/correct-ocr", { method: "POST", body: { pages } });
      const prefix = textarea.value.slice(0, start);
      const suffix = textarea.value.slice(start + inserted.length);
      textarea.value = prefix + correction.corrected_text + suffix;
      state.resume.jd = textarea.value;
      state.resume.jd_ocr_corrected = textarea.value;
      state.resume.jd_ocr_corrections = correction.corrections || [];
      status.className = "paste-hint success";
      status.textContent = `已逐张识别并自动校对 ${pages.length} 张截图；原文和修改记录均已保留。`;
      renderJdOcrAudit(); queueSave("自动校对岗位 OCR"); toast("岗位截图识别与校对完成");
    } catch (error) {
      status.className = "paste-hint";
      status.textContent = `OCR 原文已保留；AI 校对未完成：${error.message}`;
      renderJdOcrAudit(); toast("OCR 已完成，可先手动校对", true);
    }
  } else {
    status.className = "paste-hint";
    status.textContent = "未能从截图提取文字，请换一张更清晰的图片。";
  }
  if (errors.length) toast(`部分截图识别失败：${errors.join("；")}`, true);
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(file);
  });
}

function renderJdOcrAudit() {
  const box = $("#jdOcrAudit");
  const hasOriginal = Boolean(state?.resume?.jd_ocr_original);
  box.classList.toggle("hidden", !hasOriginal);
  if (!hasOriginal) return;
  const showingOriginal = $("#jdText").value === state.resume.jd_ocr_original;
  $("#toggleJdOcrBtn").textContent = showingOriginal && state.resume.jd_ocr_corrected ? "查看校对结果" : "查看原始识别";
  $("#undoJdCorrectionBtn").disabled = showingOriginal;
  $("#jdCorrectionList").innerHTML = (state.resume.jd_ocr_corrections || []).map(item => `<li><del>${escapeHtml(item.original || "")}</del> → <ins>${escapeHtml(item.corrected || "")}</ins><small>${escapeHtml(item.reason || "")}</small></li>`).join("") || "<li>模型未返回逐项修改说明，可对照原文查看。</li>";
}

async function importCustomTemplate(file) {
  if (!file) return;
  const status = $("#customTemplateStatus"); status.textContent = `正在解析 ${file.name}…`;
  try {
    const result = await api(`/api/template/analyze?filename=${encodeURIComponent(file.name)}`, { method: "POST", headers: { "Content-Type": "application/octet-stream" }, body: await file.arrayBuffer() });
    state.resume.custom_template = result.template_spec;
    state.resume.template = "custom";
    status.textContent = `已应用“${result.template_spec.name}”：${result.template_spec.layout === "sidebar" ? "侧栏" : "单栏"}布局，主色 ${result.template_spec.accent}`;
    renderDesignSelections(); updatePreview(); queueSave("导入自定义简历模板"); toast("模板已重建并应用");
  } catch (error) { status.textContent = `解析失败：${error.message}`; toast(error.message, true); }
}

const projectIgnoredParts = new Set([".git", ".dart_tool", ".agents", ".codex", ".gradle", "node_modules", ".venv", "venv", "dist", "build", "archive", "third_party", "__pycache__", ".idea", ".vscode", "coverage", "target"]);
const projectAllowedExtensions = new Set(["docx", "pdf", "png", "jpg", "jpeg", "webp", "bmp", "xlsx", "csv", "txt", "md", "json", "py", "dart", "kt", "java", "js", "ts", "tsx", "jsx", "html", "css", "sql", "yaml", "yml", "toml", "sh", "ps1"]);

function projectFilePath(file) {
  return file.projectRelativePath || file.webkitRelativePath || file.name;
}

function isProjectFileAllowed(file, path = projectFilePath(file)) {
  const parts = path.split("/");
  const extension = file.name.split(".").pop().toLowerCase();
  return file.size <= 5 * 1024 * 1024 && projectAllowedExtensions.has(extension)
    && !/app_database\.g\.dart$|generated_plugin|windows\/flutter\//i.test(path)
    && !parts.some(part => projectIgnoredParts.has(part) || /^\.env/i.test(part) || /secret|credential|token|\.key$/i.test(part));
}

function projectFilePriority(file) {
  const path = projectFilePath(file).toLowerCase();
  const name = file.name.toLowerCase();
  if (/^(readme|handoff|changelog)(\.|$)/.test(name) || /pubspec\.yaml$|package\.json$|pyproject\.toml$/.test(path)) return 0;
  if (path.includes("/docs/") || /architecture|design|requirement|schema/.test(name)) return 1;
  if (path.includes("/lib/core/") || path.includes("/src/core/") || path.includes("/app/")) return 2;
  if (path.includes("/lib/features/") || path.includes("/src/features/") || path.includes("/features/")) return 3;
  if (path.includes("/test/") || path.includes("/tests/")) return 4;
  return 5;
}

async function collectDirectoryFiles(handle, rootName, prefix = "", files = []) {
  for await (const [name, entry] of handle.entries()) {
    if (files.length >= 300) break;
    const relative = prefix ? `${prefix}/${name}` : name;
    if (entry.kind === "directory") {
      if (projectIgnoredParts.has(name) || /^\.env/i.test(name) || /secret|credential|token/i.test(name)) continue;
      await collectDirectoryFiles(entry, rootName, relative, files);
    } else {
      const file = await entry.getFile();
      file.projectRelativePath = `${rootName}/${relative}`;
      if (isProjectFileAllowed(file, file.projectRelativePath)) files.push(file);
    }
  }
  return files;
}

async function chooseProjectFolder() {
  if (!("showDirectoryPicker" in window)) {
    $("#projectFolderInput").click();
    return;
  }
  try {
    const handle = await window.showDirectoryPicker({ mode: "read" });
    $("#projectFolderSummary").textContent = `正在读取 ${handle.name} 的文件清单…`;
    const files = await collectDirectoryFiles(handle, handle.name);
    selectProjectFolder(files, handle.name);
  } catch (error) {
    if (error.name !== "AbortError") toast(`读取文件夹失败：${error.message}`, true);
  }
}

function selectProjectFolder(files, selectedFolderName = "") {
  const all = [...files];
  selectedProjectFiles = all.filter(file => isProjectFileAllowed(file)).sort((left, right) => projectFilePriority(left) - projectFilePriority(right)).slice(0, 40);
  const folder = selectedFolderName || projectFilePath(all[0] || {}).split("/")[0] || "项目文件夹";
  $("#projectFolderSummary").textContent = all.length
      ? `${folder} · 已从 ${all.length} 个有效文件中优先选择 ${selectedProjectFiles.length} 个分析（最多 40 个）`
    : `${folder} · 没有找到支持的文件`;
  $("#analyzeProjectFolderBtn").disabled = !selectedProjectFiles.length;
}

function confidencePercent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "";
  return `${Math.round(number <= 1 ? number * 100 : number)}%`;
}

function renderProjectCaseDraft(draft, folderName) {
  currentProjectDraft = draft;
  const labels = draft.labels || {};
  const highlights = Array.isArray(draft.highlights) ? draft.highlights : [];
  const bullets = Array.isArray(draft.bullets) ? draft.bullets : [];
  const lines = [
    `案例：${draft.name || folderName}`,
    `类型：${draft.material_type_label || "通用工作案例"}`,
    `角色：${draft.role || "待确认"}`,
    draft.summary ? `案例概述：${draft.summary}` : "",
    draft.methods ? `${labels.methods || "方法与工具"}：${draft.methods}` : "",
    draft.structure ? `${labels.structure || "工作框架"}：${draft.structure}` : "",
    ...(highlights.length ? [`${labels.highlights || "关键要点"}：`, ...highlights.map(item => `- ${item}`)] : []),
    ...(bullets.length ? ["工作与成果：", ...bullets.map(item => `- ${item}`)] : []),
  ].filter(Boolean);
  $("#projectCaseText").value = lines.join("\n");
  const confidence = confidencePercent(draft.classification_confidence);
  $("#projectMaterialTypeStatus").textContent = `识别为：${draft.material_type_label || "通用工作案例"}${confidence ? ` · 置信度 ${confidence}` : ""}`;
  $("#projectMaterialType").value = draft.material_type || "general";
  const evidenceItems = Array.isArray(draft.evidence_items) ? draft.evidence_items : [];
  $("#projectCaseEvidence").textContent = `查看 ${evidenceItems.length} 条材料依据${(draft.uncertainties || []).length ? ` · ${draft.uncertainties.length} 项待确认` : ""}`;
  $("#projectCaseEvidenceList").innerHTML = evidenceItems.length ? evidenceItems.map(item => `<article><b>${escapeHtml(item.statement || "材料事实")}</b><span>${escapeHtml(item.filename || "未知文件")}${confidencePercent(item.confidence) ? ` · 可信度 ${confidencePercent(item.confidence)}` : ""}</span><span>原文：${escapeHtml(item.quote || "未提供摘录")}</span></article>`).join("") : '<span class="hint">模型没有返回逐条原文依据，请谨慎审核草稿。</span>';
  if ((draft.uncertainties || []).length) $("#projectCaseEvidenceList").insertAdjacentHTML("beforeend", `<article><b>需要你确认</b><span>${draft.uncertainties.map(escapeHtml).join("；")}</span></article>`);
  $("#projectCaseDraft").classList.remove("hidden");
}

async function analyzeProjectFolder(materialType = "", triggerButton = null) {
  const button = triggerButton || $("#analyzeProjectFolderBtn"); busy(button, true, "正在提取事实并整理…");
  try {
    const excerpts = [];
    for (const file of selectedProjectFiles) {
      try {
        const result = await extractLocalText(file, projectFilePath(file));
        excerpts.push({ filename: projectFilePath(file), text: result.text.slice(0, 20000) });
      } catch (_) {}
      if (excerpts.reduce((sum, item) => sum + item.text.length, 0) >= 120000) break;
    }
    if (!excerpts.length) throw new Error("没有文件成功提取出文字");
    const folderName = projectFilePath(selectedProjectFiles[0]).split("/")[0] || "项目文件夹";
    const draft = await api("/api/ai/project-case", { method: "POST", body: { profile: state.profile, jd: state.resume.jd || "", folder_name: folderName, files: excerpts, material_type: materialType || null } });
    renderProjectCaseDraft(draft, folderName); toast("案例草稿已生成，请结合原文依据审核");
  } catch (error) { toast(error.message, true); } finally { busy(button, false); }
}

async function generateLearningPath(triggerButton = null) {
  if (!state.resume.analysis) { toast("请先完成岗位匹配分析", true); return; }
  const button = triggerButton || $("#generateLearningPathBtn"); busy(button, true, "正在检索课程…");
  try {
    const result = await api("/api/ai/learning-path", { method: "POST", body: { profile: state.profile, jd: state.resume.jd, analysis: state.resume.analysis } });
    state.resume.learning_path = result; renderLearningPath(); queueSave("生成转行学习路径");
  } catch (error) { toast(error.message, true); } finally { busy(button, false); }
}

function renderLearningPath() {
  const box = $("#learningPathCard");
  box.classList.toggle("hidden", state.resume.generation_mode !== "career_switch");
  const button = $("#generateLearningPathBtn");
  button.disabled = !state.resume.analysis;
  button.title = state.resume.analysis ? "" : "请先完成岗位匹配分析";
  const result = state.resume.learning_path;
  if (!result) {
    $("#learningPathResult").innerHTML = '<p class="hint">当前岗位尚未生成学习路径。</p>';
    return;
  }
  state.resume.learning_resource_notes ||= {};
  const stagesHtml = (result.stages || []).map((stage, index) => {
    const pool = Array.isArray(stage.resource_pool) && stage.resource_pool.length ? stage.resource_pool : (stage.resources || []);
    const offset = Number.isInteger(stage.resource_offset) && stage.resource_offset < pool.length ? stage.resource_offset : 0;
    const visibleResources = pool.slice(offset, offset + 3);
    const resources = visibleResources.map(resource => {
      const details = [resource.platform, resource.kind, resource.source, resource.verified_at ? `校验于 ${resource.verified_at}` : ""].filter(Boolean).join(" · ");
      const review = [resource.reason, resource.coverage ? `覆盖：${resource.coverage}` : "", resource.level_match ? `难度：${resource.level_match}` : ""].filter(Boolean).join("；");
      const note = state.resume.learning_resource_notes[resource.url] || "";
      const feedbackButton = (verdict, label) => `<button type="button" class="${resource.feedback === verdict ? "active" : ""}" data-learning-feedback="${verdict}" data-resource-url="${escapeHtml(resource.url)}">${label}</button>`;
      return `<div class="learning-resource ${["irrelevant", "broken"].includes(resource.feedback) ? "rejected" : ""}"><a href="${escapeHtml(resource.url)}" target="_blank" rel="noopener"><b>${escapeHtml(resource.title || resource.platform)}</b><small>${escapeHtml(details)}</small>${review ? `<em>${escapeHtml(review)}</em>` : ""}</a><div class="learning-feedback"><span>这个推荐：</span>${feedbackButton("useful", "有用")}${feedbackButton("irrelevant", "不相关")}${feedbackButton("too_hard", "太难")}${feedbackButton("too_easy", "太简单")}${feedbackButton("broken", "链接失效")}</div><div class="learning-custom-feedback"><input type="text" maxlength="300" value="${escapeHtml(note)}" placeholder="写下你的评价或希望改进的地方"><button type="button" data-save-learning-note data-resource-url="${escapeHtml(resource.url)}">保存评价</button></div></div>`;
    }).join("");
    const meta = [stage.prerequisite ? `前置：${stage.prerequisite}` : "", stage.resource_type ? `资源类型：${stage.resource_type}` : ""].filter(Boolean).join(" · ");
    const refreshMeta = pool.length > 3 ? `${offset + 1}–${Math.min(offset + 3, pool.length)} / ${pool.length}` : "重新检索";
    const refreshButton = `<button type="button" class="learning-refresh" data-refresh-learning-stage="${index}">↻ 换一批课程 <small>${refreshMeta}</small></button>`;
    return `<article><header class="learning-stage-head"><strong>${index + 1}. ${escapeHtml(stage.title || "学习阶段")}</strong><span>${escapeHtml(stage.duration || "")}</span>${refreshButton}</header><p>${escapeHtml(stage.goal || "")}</p>${meta ? `<small>${escapeHtml(meta)}</small>` : ""}<small>交付物：${escapeHtml(stage.deliverable || "")}</small>${stage.acceptance_criteria ? `<small>完成标准：${escapeHtml(stage.acceptance_criteria)}</small>` : ""}<div class="learning-links">${resources || '<span class="resource-missing">暂未找到通过审核的具体课程。可以调整关键词或配置实时搜索服务后重试。</span>'}</div></article>`;
  }).join("");
  $("#learningPathResult").innerHTML = `<p>${escapeHtml(result.summary || "")}</p><p class="resource-note">${escapeHtml(result.resource_note || "")}</p>${stagesHtml}`;
}

async function submitLearningFeedback(button) {
  const verdict = button.dataset.learningFeedback;
  const url = button.dataset.resourceUrl;
  if (!verdict || !url) return;
  try {
    await api("/api/learning-feedback", { method: "POST", body: { url, verdict } });
    $$('[data-learning-feedback]', button.parentElement).forEach(item => item.classList.toggle("active", item === button));
    for (const stage of state.resume.learning_path?.stages || []) {
      for (const resource of [...(stage.resource_pool || []), ...(stage.resources || [])]) {
        if (resource.url === url) resource.feedback = verdict;
      }
    }
    queueSave("记录课程推荐反馈");
    if (["irrelevant", "broken"].includes(verdict)) button.closest(".learning-resource")?.classList.add("rejected");
    toast("课程反馈已保存在本机，后续推荐会参考它");
  } catch (error) { toast(error.message, true); }
}

async function refreshLearningStage(button) {
  const stage = state.resume.learning_path?.stages?.[Number(button.dataset.refreshLearningStage)];
  const pool = stage?.resource_pool || [];
  if (pool.length <= 3) {
    await generateLearningPath(button);
    return;
  }
  const nextOffset = (Number(stage.resource_offset || 0) + 3 >= pool.length) ? 0 : Number(stage.resource_offset || 0) + 3;
  stage.resource_offset = nextOffset;
  stage.resources = pool.slice(nextOffset, nextOffset + 3);
  renderLearningPath();
  queueSave("切换学习课程推荐");
}

function saveLearningNote(button) {
  const url = button.dataset.resourceUrl;
  const input = button.closest(".learning-custom-feedback")?.querySelector("input");
  if (!url || !input) return;
  state.resume.learning_resource_notes ||= {};
  const note = input.value.trim();
  if (note) state.resume.learning_resource_notes[url] = note;
  else delete state.resume.learning_resource_notes[url];
  queueSave("记录课程自由评价");
  toast(note ? "评价已保存在当前岗位简历中" : "已清空这条评价");
}

async function structureResume() {
  const button = $("#structureBtn");
  const raw = $("#rawText").value.trim();
  if (!raw) { showStep("profile"); toast("请手动填写人才档案"); return; }
  busy(button, true, "AI 正在提取事实…");
  try {
    const profile = await api("/api/ai/structure", { method: "POST", body: { raw_text: raw } });
    profile.basics = { ...state.profile.basics, ...(profile.basics || {}), photo: state.profile.basics.photo || "" };
    state.profile = { ...state.profile, ...profile };
    queueSave("AI 解析旧简历"); showStep("profile"); toast("解析完成，请逐项确认");
  } catch (error) { toast(error.message, true); }
  finally { busy(button, false); }
}

async function analyzeJD() {
  const button = $("#analyzeBtn");
  const jd = $("#jdText").value.trim();
  if (!jd) { toast("请先粘贴岗位 JD", true); return; }
  state.resume.jd = jd; busy(button, true, "正在分析岗位…");
  const resumeReference = state.resume;
  try {
    const result = await api("/api/ai/analyze", { method: "POST", body: { profile: state.profile, jd } });
    if (!ensureSameResume(resumeReference)) return;
    state.resume.analysis = result; renderAnalysis(result); renderLearningPath(); queueSave("完成岗位匹配分析"); toast("岗位分析完成");
  } catch (error) { toast(error.message, true); }
  finally { busy(button, false); }
}

async function generateTailoredResume() {
  const jd = $("#jdText").value.trim();
  const relatedExperience = $("#relatedExperience").value.trim();
  if (!jd) { toast("请先粘贴或识别岗位 JD", true); return; }
  const button = $("#generateTailoredBtn");
  busy(button, true, "正在生成岗位定制内容…");
  const resumeReference = state.resume;
  try {
    state.resume.jd = jd;
    state.resume.related_experience = relatedExperience;
    await persistState("生成岗位定制简历前");
    const response = await api("/api/ai/generate", { method: "POST", body: {
      profile: state.profile, jd, related_experience: relatedExperience,
      generation_mode: state.resume.generation_mode || "same_direction",
      proficiency_level: state.resume.proficiency_level || "beginner"
    } });
    if (!ensureSameResume(resumeReference)) return;
    const generated = response.profile || response;
    generated.basics = generated.basics || {};
    protectedBasicFields.forEach(field => generated.basics[field] = state.profile.basics[field] || "");
    state.resume.tailored_profile = generated;
    state.resume.tailored_jd = jd;
    state.resume.candidate_drafts = [];
    state.resume.suggestions = [];
    await persistState("生成岗位定制简历");
    updateTailoredStatus(); renderTailoredContent(); showStep("polish");
    toast("岗位定制简历已生成，基础人才档案保持不变");
  } catch (error) { toast(error.message, true); }
  finally { busy(button, false); }
}

function list(items = []) { return `<ul>${items.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`; }
function renderAnalysis(result) {
  const box = $("#analysisResult");
  if (!result) return;
  box.className = "analysis-card";
  const requirements = (result.requirements || []).map(item => `<li><strong>${escapeHtml({ met: "已满足", partial: "部分满足", missing: "缺失" }[item.status] || "待判断")}：</strong>${escapeHtml(item.requirement)}<small>${escapeHtml(item.evidence || "")}</small></li>`).join("");
  box.innerHTML = `<div class="score-row"><span class="score">${escapeHtml(result.score ?? "—")}</span><span>/ 100 证据匹配度</span></div><p class="hint">${escapeHtml(result.score_basis || "仅作岗位要求覆盖参考")}</p>
    <h3>${escapeHtml(result.summary || "分析完成")}</h3><div class="analysis-columns">
    <div class="analysis-block"><h4>已有优势</h4>${list(result.strengths)}</div><div class="analysis-block"><h4>关键缺口</h4>${list(result.gaps)}</div>
    <div class="analysis-block"><h4>已覆盖关键词</h4>${list(result.keywords_present)}</div><div class="analysis-block"><h4>建议补充</h4>${list(result.recommendations)}</div></div>
    ${requirements ? `<div class="requirement-evidence"><h4>岗位要求与档案证据</h4><ul>${requirements}</ul></div>` : ""}`;
  renderDeliveryChecklist();
}

async function fetchQuestion(skip = false) {
  if (!state.resume.jd) { toast("请先粘贴岗位 JD", true); return; }
  if (skip && currentQuestion) {
    questionHistory.push({ question: currentQuestion.question, answer: "用户跳过", why: currentQuestion.why || "" });
    state.resume.questions = questionHistory;
  }
  const button = $("#questionBtn"); busy(button, true, "正在思考下一问…");
  const resumeReference = state.resume;
  try {
    const result = await api("/api/ai/question", { method: "POST", body: { profile: activeProfile(), jd: state.resume.jd, history: questionHistory } });
    if (!ensureSameResume(resumeReference)) return;
    if (result.done) {
      currentQuestion = null;
      if (questionHistory.length) { showQuestionView(questionHistory.length - 1); toast("没有更多高价值问题了，可以返回修改之前的回答"); }
      else { $("#questionCard").classList.add("hidden"); toast("没有更多高价值问题了"); }
      return;
    }
    currentQuestion = result;
    showQuestionView(questionHistory.length);
  } catch (error) { toast(error.message, true); }
  finally { busy(button, false); }
}

function showQuestionView(index) {
  const total = questionHistory.length + (currentQuestion ? 1 : 0);
  if (!total) { $("#questionCard").classList.add("hidden"); return; }
  questionViewIndex = Math.max(0, Math.min(index, total - 1));
  const historical = questionViewIndex < questionHistory.length;
  const entry = historical ? questionHistory[questionViewIndex] : currentQuestion;
  $("#questionText").textContent = entry.question;
  $("#questionWhy").textContent = entry.why || (historical ? "这是之前保存的回答，可以修改后重新融入简历。" : "这个答案将帮助简历更具体。");
  $("#answerText").value = historical ? entry.answer : "";
  $("#questionPosition").textContent = `第 ${questionViewIndex + 1} 问 / 共 ${total} 问`;
  $("#previousQuestionBtn").disabled = questionViewIndex === 0;
  $("#nextQuestionBtn").disabled = questionViewIndex >= total - 1;
  $("#skipQuestionBtn").disabled = historical;
  $("#answerBtn").textContent = historical ? "更新答案并应用" : "提交并继续";
  $("#questionCard").classList.remove("hidden");
}

async function submitAnswer() {
  const answer = $("#answerText").value.trim();
  if (!answer) { toast("请输入回答，或选择跳过", true); return; }
  const historical = questionViewIndex < questionHistory.length;
  const entry = historical ? questionHistory[questionViewIndex] : currentQuestion;
  if (!entry) { toast("请先开始动态追问", true); return; }
  const previousAnswer = historical ? entry.answer : "";
  const button = $("#answerBtn");
  busy(button, true, "正在融入简历…");
  const resumeReference = state.resume;
  try {
    const response = await api("/api/ai/refine", { method: "POST", body: {
      profile: activeProfile(), jd: state.resume.jd, question: entry.question,
      answer, previous_answer: previousAnswer, history: questionHistory
    } });
    if (!ensureSameResume(resumeReference)) return;
    const refined = response.profile || response;
    const changes = response.changes || [];
    refined.basics = refined.basics || {};
    protectedBasicFields.forEach(field => refined.basics[field] = state.profile.basics[field] || "");
    state.resume.tailored_profile = refined;
    if (historical) questionHistory[questionViewIndex] = { ...entry, answer };
    else questionHistory.push({ question: entry.question, answer, why: entry.why || "" });
    state.resume.questions = questionHistory;
    await persistState(changes.length ? "动态追问精修简历" : "记录追问回答（正文未修改）");
    renderTailoredContent(); showRefineChanges(changes); updatePreview();
    if (historical) {
      showQuestionView(questionViewIndex);
      toast(changes.length ? `历史答案已更新，实际修改 ${changes.length} 处` : "答案已更新，但简历正文没有发生变化", !changes.length);
    } else {
      currentQuestion = null;
      toast(changes.length ? `回答已融入简历，实际修改 ${changes.length} 处` : "回答已保存，但模型没有修改简历正文", !changes.length);
      await fetchQuestion();
    }
  } catch (error) { toast(error.message, true); }
  finally { busy(button, false); }
}

function showRefineChanges(changes = []) {
  const notice = $("#refineChangeNotice");
  if (!changes.length) {
    notice.className = "refine-change-notice no-change";
    notice.innerHTML = "<strong>本轮未修改正文</strong><span>回答已经保存，但没有产生可应用的内容变化。</span>";
    return;
  }
  notice.className = "refine-change-notice";
  notice.innerHTML = `<strong>本轮实际修改 ${changes.length} 处</strong><span>${changes.map(change => escapeHtml(change.label)).join("、")}</span>`;
  const firstPath = changes[0].path || "";
  setTimeout(() => {
    let target = $(`[data-tailored-path="${firstPath}"]`);
    if (!target) target = $(`[data-tailored-section="${firstPath.split(".")[0]}"]`);
    if (!target) return;
    target.classList.add("refine-highlight");
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => target.classList.remove("refine-highlight"), 2600);
  }, 80);
}

function renderGenerationOptions() {
  const mode = state.resume.generation_mode || "same_direction";
  const level = state.resume.proficiency_level || "beginner";
  $$('[data-generation-mode]').forEach(button => button.classList.toggle("active", button.dataset.generationMode === mode));
  $$('[data-proficiency-level]').forEach(button => button.classList.toggle("active", button.dataset.proficiencyLevel === level));
  renderLearningPath();
}

function renderSectionOrder() {
  const container = $("#sectionOrder");
  container.innerHTML = state.resume.section_order.map(key => `<div class="order-item" draggable="true" data-section="${key}">${sectionLabels[key] || key}</div>`).join("");
  $$(".order-item", container).forEach(item => {
    item.addEventListener("dragstart", () => draggedSection = item.dataset.section);
    item.addEventListener("dragover", event => event.preventDefault());
    item.addEventListener("drop", () => {
      const target = item.dataset.section;
      if (!draggedSection || draggedSection === target) return;
      const order = state.resume.section_order;
      order.splice(order.indexOf(target), 0, order.splice(order.indexOf(draggedSection), 1)[0]);
      renderSectionOrder(); updatePreview(); queueSave();
    });
  });
}

async function updatePreview() {
  const requestId = ++previewRequestId;
  try {
    const markup = await api("/api/preview", { method: "POST", body: state });
    if (requestId !== previewRequestId) return;
    const frame = $("#resumePreview");
    frame.onload = () => {
      setTimeout(() => {
        if (state.resume.page_mode === "one") {
          frame.contentWindow?.fitResumeToOnePage?.();
          const scale = Number(frame.contentDocument?.querySelector(".resume-page")?.dataset.fitScale || 1);
          lastPreviewScale = scale;
          const hint = $("#overflowHint");
          hint.className = scale < 0.75 ? "readability-warning" : "";
          hint.textContent = scale < 0.75 ? `仅 ${Math.round(scale * 100)}% · 字号过小，请精简或改为多页` : `自动缩放至一页 · ${Math.round(scale * 100)}%`;
          renderDeliveryChecklist();
        } else { lastPreviewScale = 1; $("#overflowHint").className = ""; $("#overflowHint").textContent = "正常字号 · 自动多页"; renderDeliveryChecklist(); }
      }, 180);
    };
    frame.srcdoc = markup;
    $("#overflowHint").textContent = state.resume.page_mode === "one" ? "正在计算一页缩放…" : "正常字号 · 自动多页";
  } catch (error) { toast(error.message, true); }
}

async function translateResume(target, button) {
  if (state.resume.language === target) return;
  if (!confirm("翻译会创建历史快照并更新当前岗位定制简历，基础人才档案不会改变。是否继续？")) { renderDesignSelections(); return; }
  busy(button, true, "翻译中…");
  const resumeReference = state.resume;
  try {
    await persistState("切换简历语言前");
    const translated = await api("/api/ai/translate", { method: "POST", body: { profile: activeProfile(), target } });
    if (!ensureSameResume(resumeReference)) return;
    translated.basics = translated.basics || {};
    protectedBasicFields.forEach(field => translated.basics[field] = state.profile.basics[field] || "");
    state.resume.tailored_profile = translated;
    state.resume.language = target; renderDesignSelections(); updatePreview(); queueSave("生成语言版本"); toast("语言版本生成完成");
  } catch (error) { renderDesignSelections(); toast(error.message, true); }
  finally { busy(button, false); }
}

function renderDesignSelections() {
  $$('[data-template]').forEach(btn => btn.classList.toggle("active", btn.dataset.template === state.resume.template));
  $$('[data-language]').forEach(btn => btn.classList.toggle("active", btn.dataset.language === state.resume.language));
  $$('[data-pages]').forEach(btn => btn.classList.toggle("active", btn.dataset.pages === state.resume.page_mode));
  if (state.resume.template === "custom" && state.resume.custom_template) {
    $("#customTemplateStatus").textContent = `已应用“${state.resume.custom_template.name}”：${state.resume.custom_template.layout === "sidebar" ? "侧栏" : "单栏"}布局，主色 ${state.resume.custom_template.accent}`;
  } else {
    $("#customTemplateStatus").textContent = "解析后会重建为可编辑模板，不导入示例人物内容。";
  }
  renderDeliveryChecklist();
}

function renderDeliveryChecklist() {
  const list = $("#deliveryChecklist");
  if (!list || !state) return;
  const profile = activeProfile();
  const basics = profile.basics || {};
  const warnings = [];
  if (!state.resume.tailored_profile) warnings.push("尚未生成岗位定制正文");
  if (state.resume.tailored_profile && state.resume.tailored_jd !== state.resume.jd) warnings.push("JD 已变化，需要重新生成岗位正文");
  if (!basics.name || (!basics.phone && !basics.email)) warnings.push("姓名或联系方式不完整");
  const missing = (state.resume.analysis?.requirements || []).filter(item => item.status === "missing").length;
  if (missing) warnings.push(`岗位分析中仍有 ${missing} 项要求缺少档案证据`);
  const draftProjects = (profile.projects || []).filter(item => /个人项目|模拟项目|案例研究/.test(item.role || "")).length;
  if (draftProjects) warnings.push(`${draftProjects} 个个人/模拟项目需要确认自己能够解释`);
  if (state.resume.page_mode === "one" && lastPreviewScale < 0.75) warnings.push(`一页缩放仅 ${Math.round(lastPreviewScale * 100)}%，低于可读下限`);
  $("#deliveryCheckCount").textContent = warnings.length ? `${warnings.length} 项待确认` : "可以导出";
  list.innerHTML = warnings.length
    ? warnings.map(item => `<li class="warning">● ${escapeHtml(item)}</li>`).join("")
    : '<li class="ok">● 未发现明显的投递阻塞项</li>';
}

async function downloadExport(type, button) {
  if (state.resume.page_mode === "one" && lastPreviewScale < 0.75) {
    toast(`当前内容缩放到 ${Math.round(lastPreviewScale * 100)}%，低于可读下限；请精简内容或选择允许多页`, true);
    return;
  }
  busy(button, true, "正在生成…");
  try {
    const response = await fetch(`/api/export/${type}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(state) });
    if (!response.ok) { const error = await response.json(); throw new Error(error.detail || "导出失败"); }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = `${state.resume.title || "简历"}.${type === "docx" ? "docx" : "pdf"}`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000); toast(`${type.toUpperCase()} 已生成`);
    showSupportAfterFirstExport();
  } catch (error) { toast(error.message, true); }
  finally { busy(button, false); }
}

async function loadVersions() {
  const versions = await api("/api/versions");
  $("#versionList").innerHTML = versions.length ? versions.map(item => `<div class="version-item"><span>${escapeHtml(item.label)}<br><small>${new Date(item.created_at).toLocaleString()}</small></span><button type="button" class="text-button" data-restore-version="${item.id}">恢复</button></div>`).join("") : '<p class="hint">还没有历史版本。</p>';
  $$('[data-restore-version]').forEach(button => button.addEventListener("click", async () => {
    if (!confirm("恢复后，当前状态会先自动保存为快照。继续吗？")) return;
    state = await api(`/api/versions/${button.dataset.restoreVersion}/restore`, { method: "POST" });
    syncUI(); toast("历史版本已恢复");
  }));
}

function cloneData(value) {
  return typeof structuredClone === "function" ? structuredClone(value) : JSON.parse(JSON.stringify(value));
}

function blankResumeFrom(current = {}) {
  return {
    title: "新的岗位简历",
    language: current.language || "zh",
    template: current.template || "ats",
    custom_template: cloneData(current.custom_template || null),
    page_mode: current.page_mode || "one",
    section_order: cloneData(current.section_order || ["summary", "experience", "projects", "education", "skills", "certificates", "languages"]),
    jd: "",
    jd_ocr_original: "",
    jd_ocr_corrected: "",
    jd_ocr_corrections: [],
    jd_ocr_images: [],
    learning_path: null,
    analysis: null,
    tailored_profile: null,
    tailored_jd: "",
    related_experience: "",
    generation_mode: "same_direction",
    proficiency_level: "beginner",
    candidate_drafts: [],
    suggestions: [],
    questions: [],
  };
}

async function saveStateNow(label) {
  clearTimeout(saveTimer);
  $("#saveStatus").textContent = "保存中…";
  await persistState(label);
  $("#saveStatus").textContent = "已保存";
}

function renderResumeLibrary() {
  state.resume_library ||= [];
  $("#resumeLibraryBtn").textContent = `岗位库（${state.resume_library.length}）`;
  const list = $("#resumeLibraryList");
  if (!list) return;
  if (!state.resume_library.length) {
    list.innerHTML = '<p class="hint">还没有保存岗位版本。完成当前简历后，点击顶部“保存当前岗位”。</p>';
    return;
  }
  list.innerHTML = state.resume_library.map((item, index) => {
    const role = item.resume?.tailored_profile?.basics?.target_role || item.resume?.title || "未命名岗位";
    const savedAt = item.saved_at ? new Date(item.saved_at).toLocaleString() : "保存时间未知";
    const active = item.id === state.active_resume_id ? " active" : "";
    return `<article class="resume-library-item${active}"><div><h3>${escapeHtml(item.name || "未命名岗位简历")}</h3><p class="resume-library-meta">目标：${escapeHtml(role)}<br>${escapeHtml(savedAt)}${active ? " · 当前打开" : ""}</p></div><div class="resume-library-actions"><button type="button" class="secondary" data-load-resume-variant="${index}">打开</button><button type="button" class="text-button" data-delete-resume-variant="${index}">删除</button></div></article>`;
  }).join("");
}

function resetTransientToolUI() {
  selectedProjectFiles = [];
  currentProjectDraft = null;
  const folderInput = $("#projectFolderInput");
  if (folderInput) folderInput.value = "";
  $("#projectFolderSummary").textContent = "尚未选择文件夹";
  $("#analyzeProjectFolderBtn").disabled = true;
  $("#projectCaseDraft").classList.add("hidden");
  $("#projectCaseText").value = "";
  $("#projectCaseEvidence").textContent = "查看材料依据";
  $("#projectCaseEvidenceList").innerHTML = "";
  $("#projectMaterialTypeStatus").textContent = "等待识别材料类型";
  $("#projectMaterialType").value = "";
  $(".project-folder-card").open = false;
  $("#learningPathCard").open = false;
}

async function saveCurrentResumeVariant() {
  state.resume_library ||= [];
  const currentIndex = state.resume_library.findIndex(item => item.id === state.active_resume_id);
  const currentName = currentIndex >= 0 ? state.resume_library[currentIndex].name : "";
  const suggestedName = currentName || state.resume.title || state.resume.tailored_profile?.basics?.target_role || state.profile.basics.target_role || "岗位简历";
  const name = prompt("给这个岗位版本起个名字：", suggestedName);
  if (name === null) return;
  if (!name.trim()) { toast("岗位版本名称不能为空", true); return; }
  const item = {
    id: currentIndex >= 0 ? state.resume_library[currentIndex].id : (crypto.randomUUID?.() || `resume-${Date.now()}`),
    name: name.trim(),
    saved_at: new Date().toISOString(),
    resume: cloneData(state.resume),
  };
  if (currentIndex >= 0) state.resume_library[currentIndex] = item;
  else state.resume_library.unshift(item);
  state.active_resume_id = item.id;
  await saveStateNow(`保存岗位简历：${item.name}`);
  renderResumeLibrary();
  toast(`已保存到岗位库：${item.name}`);
}

async function createNewResumeVariant() {
  const message = "将清空当前岗位的 JD、定制正文和问答记录，基础人才档案会保留。请确认当前岗位简历已经保存。继续吗？";
  if (!confirm(message)) return;
  state.resume = blankResumeFrom(state.resume);
  state.active_resume_id = null;
  questionHistory = [];
  currentQuestion = null;
  aiEditTarget = null;
  aiEditUndo = null;
  aiEditRedo = null;
  await saveStateNow("新建岗位简历");
  syncUI();
  showStep("match");
  toast("已开始新的岗位简历，基础人才档案已保留");
}

async function loadResumeVariant(index) {
  const item = state.resume_library?.[index];
  if (!item) return;
  if (!confirm(`打开“${item.name}”将替换当前工作区的岗位内容，基础人才档案不会改变。继续吗？`)) return;
  state.resume = cloneData(item.resume);
  state.active_resume_id = item.id;
  questionHistory = state.resume.questions || [];
  currentQuestion = null;
  aiEditTarget = null;
  aiEditUndo = null;
  aiEditRedo = null;
  await saveStateNow(`打开岗位简历：${item.name}`);
  $("#resumeLibraryDialog").close();
  syncUI();
  showStep(state.resume.tailored_profile ? "polish" : "match");
  toast(`已打开：${item.name}`);
}

async function deleteResumeVariant(index) {
  const item = state.resume_library?.[index];
  if (!item || !confirm(`确定从岗位库删除“${item.name}”吗？当前基础人才档案不会受影响。`)) return;
  state.resume_library.splice(index, 1);
  if (state.active_resume_id === item.id) state.active_resume_id = null;
  await saveStateNow(`删除岗位简历：${item.name}`);
  renderResumeLibrary();
  toast(`已从岗位库删除：${item.name}`);
}

function syncUI() {
  state.resume_library ||= [];
  if (!("active_resume_id" in state)) state.active_resume_id = null;
  $("#resumeTitle").value = state.resume.title || "我的定制简历";
  $("#jdText").value = state.resume.jd || "";
  $("#relatedExperience").value = state.resume.related_experience || "";
  resetTransientToolUI();
  questionHistory = state.resume.questions || [];
  renderProfileEditor(); renderAnalysis(state.resume.analysis); renderGenerationOptions(); renderTailoredContent(); renderDesignSelections(); renderSectionOrder(); updateTailoredStatus(); updatePreview(); renderResumeLibrary(); updateEditHistoryControls(); renderJdOcrAudit(); renderLearningPath();
}

async function initialize() {
  try {
    state = await api("/api/state"); syncUI(); await loadPersistentEditHistory();
    const settings = await api("/api/settings");
    renderAiSettings(settings);
    $("#searchProvider").value = settings.search_provider || "";
    $("#searchKeyStatus").textContent = settings.search_configured ? `已配置 ${settings.search_provider === "brave" ? "Brave Search" : "Tavily"}：${settings.search_masked}` : "未配置时只能推荐内置课程。搜索 Key 同样由系统当前账户安全保存。";
  } catch (error) { toast(`初始化失败：${error.message}`, true); return; }

  $$(".step").forEach(button => button.addEventListener("click", () => showStep(button.dataset.step)));
  $$('[data-goto]').forEach(button => button.addEventListener("click", () => { queueSave(); showStep(button.dataset.goto); }));
  $("#resumeTitle").addEventListener("input", event => { state.resume.title = event.target.value; queueSave(); });
  $("#saveResumeVariantBtn").addEventListener("click", () => saveCurrentResumeVariant().catch(error => toast(error.message, true)));
  $("#newResumeVariantBtn").addEventListener("click", () => createNewResumeVariant().catch(error => toast(error.message, true)));
  $("#resumeLibraryBtn").addEventListener("click", () => { renderResumeLibrary(); $("#resumeLibraryDialog").showModal(); });
  $("#helpBtn").addEventListener("click", () => openOnboarding(0));
  $("#aboutBtn").addEventListener("click", () => openAbout(false));
  $("#closeAboutBtn").addEventListener("click", () => $("#aboutDialog").close());
  $("#aboutDialog").addEventListener("cancel", event => { event.preventDefault(); $("#aboutDialog").close(); });
  $("#acceptTermsBtn").addEventListener("click", () => {
    localStorage.setItem(termsStorageKey, "accepted");
    $("#termsDialog").close();
    if (!localStorage.getItem(onboardingStorageKey)) openOnboarding(0);
  });
  $("#termsDialog").addEventListener("cancel", event => event.preventDefault());
  $("#checkUpdateBtn").addEventListener("click", async event => {
    busy(event.currentTarget, true, "检查中…");
    try {
      const result = await api("/api/update-check");
      const status = $("#updateStatus");
      if (!result.latest) status.textContent = "公开版本尚未发布，请稍后再试";
      else if (result.update_available) status.innerHTML = `发现 v${escapeHtml(result.latest)} · <a href="${escapeHtml(result.release_url)}" target="_blank" rel="noopener">查看下载</a>`;
      else status.textContent = `当前已是最新版本 v${result.current}`;
    } catch (error) { $("#updateStatus").textContent = error.message; }
    finally { busy(event.currentTarget, false); }
  });
  $("#closeOnboardingBtn").addEventListener("click", closeOnboarding);
  $("#skipOnboardingBtn").addEventListener("click", closeOnboarding);
  $("#previousOnboardingBtn").addEventListener("click", () => renderOnboardingStep(onboardingStep - 1));
  $("#nextOnboardingBtn").addEventListener("click", () => {
    if (onboardingStep === onboardingSteps.length - 1) closeOnboarding();
    else renderOnboardingStep(onboardingStep + 1);
  });
  $("#onboardingStepList").addEventListener("click", event => {
    const button = event.target.closest("[data-onboarding-step]");
    if (button) renderOnboardingStep(Number(button.dataset.onboardingStep));
  });
  $("#goOnboardingBtn").addEventListener("click", () => {
    const page = onboardingSteps[onboardingStep].page;
    closeOnboarding(false); showStep(page);
  });
  $("#onboardingDialog").addEventListener("cancel", event => { event.preventDefault(); closeOnboarding(); });
  $("#resumeLibraryList").addEventListener("click", event => {
    const loadButton = event.target.closest("[data-load-resume-variant]");
    const deleteButton = event.target.closest("[data-delete-resume-variant]");
    if (loadButton) loadResumeVariant(Number(loadButton.dataset.loadResumeVariant)).catch(error => toast(error.message, true));
    if (deleteButton) deleteResumeVariant(Number(deleteButton.dataset.deleteResumeVariant)).catch(error => toast(error.message, true));
  });
  $("#chooseFilesBtn").addEventListener("click", event => {
    event.preventDefault(); event.stopPropagation(); $("#resumeFile").click();
  });
  $("#resumeFile").addEventListener("change", event => handleFiles(event.target.files));
  $("#structureBtn").addEventListener("click", structureResume);
  $("#openDemoGuideBtn").addEventListener("click", () => openOnboarding(0));
  $("#jdText").addEventListener("input", event => { state.resume.jd = event.target.value; updateTailoredStatus(); queueSave(); });
  $("#jdText").addEventListener("paste", handleJdPaste);
  $("#toggleJdOcrBtn").addEventListener("click", () => {
    const currentIsOriginal = $("#jdText").value === state.resume.jd_ocr_original;
    const target = currentIsOriginal ? state.resume.jd_ocr_corrected : state.resume.jd_ocr_original;
    if (!target) return;
    $("#jdText").value = target; state.resume.jd = target; renderJdOcrAudit(); queueSave();
  });
  $("#undoJdCorrectionBtn").addEventListener("click", () => {
    if (!state.resume.jd_ocr_original) return;
    $("#jdText").value = state.resume.jd_ocr_original; state.resume.jd = state.resume.jd_ocr_original; renderJdOcrAudit(); queueSave("撤销岗位 OCR 自动校对"); toast("已恢复 OCR 原始文字");
  });
  $("#relatedExperience").addEventListener("input", event => { state.resume.related_experience = event.target.value; queueSave(); });
  $$('[data-generation-mode]').forEach(button => button.addEventListener("click", () => { state.resume.generation_mode = button.dataset.generationMode; renderGenerationOptions(); queueSave(); }));
  $$('[data-proficiency-level]').forEach(button => button.addEventListener("click", () => { state.resume.proficiency_level = button.dataset.proficiencyLevel; renderGenerationOptions(); queueSave(); }));
  $("#analyzeBtn").addEventListener("click", analyzeJD);
  $("#generateTailoredBtn").addEventListener("click", generateTailoredResume);
  $("#chooseProjectFolderBtn").addEventListener("click", chooseProjectFolder);
  $("#projectFolderInput").addEventListener("change", event => selectProjectFolder(event.target.files));
  $("#analyzeProjectFolderBtn").addEventListener("click", event => analyzeProjectFolder("", event.currentTarget));
  $("#reanalyzeProjectCaseBtn").addEventListener("click", event => {
    if (!selectedProjectFiles.length) { toast("请先重新选择材料文件夹", true); return; }
    analyzeProjectFolder($("#projectMaterialType").value, event.currentTarget);
  });
  $("#addProjectCaseBtn").addEventListener("click", () => {
    const value = $("#projectCaseText").value.trim(); if (!value) return;
    const textarea = $("#relatedExperience"); textarea.value = [textarea.value.trim(), value].filter(Boolean).join("\n\n");
    state.resume.related_experience = textarea.value; queueSave("加入项目案例补充信息"); toast("项目案例已加入补充信息");
  });
  $("#generateLearningPathBtn").addEventListener("click", () => generateLearningPath());
  $("#learningPathResult").addEventListener("click", event => {
    const feedbackButton = event.target.closest("[data-learning-feedback]");
    const refreshButton = event.target.closest("[data-refresh-learning-stage]");
    const noteButton = event.target.closest("[data-save-learning-note]");
    if (feedbackButton) submitLearningFeedback(feedbackButton);
    else if (refreshButton) refreshLearningStage(refreshButton);
    else if (noteButton) saveLearningNote(noteButton);
  });
  $("#applyAiAddBtn").addEventListener("click", () => {
    const instruction = $("#aiEditInstruction").value.trim();
    if (!instruction) { toast("请告诉 AI 你希望增加什么", true); return; }
    applyAiSmartAdd(instruction, "add", $("#applyAiAddBtn"));
  });
  $("#applyAiEditBtn").addEventListener("click", applyAiSelectionEdit);
  $("#clearAiTargetBtn").addEventListener("click", () => updateAiEditTarget());
  $("#undoAiEditBtn").addEventListener("click", () => undoAiSelectionEdit().catch(error => toast(error.message, true)));
  $("#redoAiEditBtn").addEventListener("click", () => redoAiSelectionEdit().catch(error => toast(error.message, true)));
  $$("[data-ai-prompt]").forEach(button => button.addEventListener("click", () => {
    $("#aiEditInstruction").value = button.dataset.aiPrompt;
    $("#aiEditInstruction").focus();
  }));
  $("#questionBtn").addEventListener("click", () => fetchQuestion());
  $("#previousQuestionBtn").addEventListener("click", () => showQuestionView(questionViewIndex - 1));
  $("#nextQuestionBtn").addEventListener("click", () => showQuestionView(questionViewIndex + 1));
  $("#skipQuestionBtn").addEventListener("click", () => fetchQuestion(true));
  $("#stopQuestionBtn").addEventListener("click", () => { $("#questionCard").classList.add("hidden"); toast("已结束本轮追问"); });
  $("#answerBtn").addEventListener("click", submitAnswer);
  $("#photoInput").addEventListener("change", event => {
    const file = event.target.files[0]; if (!file) return;
    if (file.size > 4 * 1024 * 1024) { toast("照片不能超过 4 MB", true); return; }
    const reader = new FileReader(); reader.onload = () => { state.profile.basics.photo = reader.result; updatePhoto(); queueSave("更新个人照片"); }; reader.readAsDataURL(file);
  });
  const dropzone = $("#dropzone");
  ["dragenter", "dragover"].forEach(name => dropzone.addEventListener(name, event => { event.preventDefault(); dropzone.classList.add("dragging"); }));
  ["dragleave", "drop"].forEach(name => dropzone.addEventListener(name, event => { event.preventDefault(); dropzone.classList.remove("dragging"); }));
  dropzone.addEventListener("drop", event => handleFiles(event.dataTransfer.files));
  $$('[data-template]').forEach(button => button.addEventListener("click", () => { state.resume.template = button.dataset.template; renderDesignSelections(); updatePreview(); queueSave(); }));
  renderTemplateSites();
  $("#refreshTemplateSitesBtn").addEventListener("click", () => { templateSiteOffset = (templateSiteOffset + 3) % templateSites.length; renderTemplateSites(); });
  $("#templateFileInput").addEventListener("change", event => { importCustomTemplate(event.target.files[0]); event.target.value = ""; });
  $$('[data-pages]').forEach(button => button.addEventListener("click", () => { state.resume.page_mode = button.dataset.pages; renderDesignSelections(); updatePreview(); queueSave(); }));
  $$('[data-language]').forEach(button => button.addEventListener("click", () => translateResume(button.dataset.language, button)));
  $("#pdfBtn").addEventListener("click", event => downloadExport("pdf", event.currentTarget));
  $("#docxBtn").addEventListener("click", event => downloadExport("docx", event.currentTarget));
  $("#printBtn").addEventListener("click", () => $("#resumePreview").contentWindow.print());
  $("#settingsBtn").addEventListener("click", () => { $("#settingsDialog").showModal(); loadVersions(); });
  $("#aiProvider").addEventListener("change", event => {
    const option = providerOption(event.target.value);
    if (!option) return;
    $("#aiBaseUrl").value = option.default_base_url;
    $("#aiModel").value = option.default_model;
    $("#aiBaseUrl").readOnly = !["custom", "ollama", "lmstudio"].includes(option.id);
    $("#apiKey").value = "";
    $("#keyStatus").textContent = `${option.name} · ${option.live_tested ? "项目已完成真实接口验证" : "请使用测试连接确认当前账号和模型"}`;
  });
  $("#testAiBtn").addEventListener("click", async event => {
    busy(event.currentTarget, true, "测试中…");
    try {
      const result = await api("/api/settings/test-ai", { method: "POST", body: aiSettingsPayload() });
      $("#keyStatus").textContent = `${result.name} · ${result.model} · 连接成功`;
      toast("AI 模型连接成功");
    } catch (error) { toast(error.message, true); }
    finally { busy(event.currentTarget, false); }
  });
  $("#saveKeyBtn").addEventListener("click", async event => {
    busy(event.currentTarget, true, "保存中…");
    try { const result = await api("/api/settings", { method: "PUT", body: aiSettingsPayload() }); renderAiSettings(result); toast("AI 设置已保存在本机"); }
    catch (error) { toast(error.message, true); } finally { busy(event.currentTarget, false); }
  });
  $("#clearAiKeyBtn").addEventListener("click", async event => {
    if (!confirm("只清除当前服务商保存在本机的 API Key，其他服务商密钥不会受影响。继续吗？")) return;
    busy(event.currentTarget, true, "清除中…");
    try {
      const result = await api("/api/settings", { method: "PUT", body: { ...aiSettingsPayload(false), clear_ai_key: true } });
      renderAiSettings(result); toast("当前服务商 API Key 已清除");
    } catch (error) { toast(error.message, true); }
    finally { busy(event.currentTarget, false); }
  });
  $("#saveSearchKeyBtn").addEventListener("click", async event => {
    busy(event.currentTarget, true, "保存中…");
    try {
      const result = await api("/api/settings", { method: "PUT", body: { search_provider: $("#searchProvider").value, search_api_key: $("#searchApiKey").value } });
      $("#searchApiKey").value = "";
      $("#searchKeyStatus").textContent = result.search_configured ? `已配置 ${result.search_provider === "brave" ? "Brave Search" : "Tavily"}：${result.search_masked}` : "实时课程搜索已关闭，仅使用本地课程目录。";
      toast(result.search_configured ? "课程实时搜索已启用" : "课程实时搜索已关闭");
    } catch (error) { toast(error.message, true); } finally { busy(event.currentTarget, false); }
  });
  $("#refreshVersionsBtn").addEventListener("click", loadVersions);
  $("#backupBtn").addEventListener("click", () => { const anchor = document.createElement("a"); anchor.href = "/api/backup"; anchor.click(); });
  $("#restoreInput").addEventListener("change", async event => {
    const file = event.target.files[0]; if (!file || !confirm("恢复备份将替换当前档案，系统会先创建快照。继续吗？")) return;
    try { await api("/api/restore", { method: "POST", headers: { "Content-Type": "application/json" }, body: await file.text() }); state = await api("/api/state"); syncUI(); toast("备份恢复完成"); }
    catch (error) { toast(error.message, true); }
  });
  if (!localStorage.getItem(termsStorageKey)) $("#termsDialog").showModal();
  else if (!localStorage.getItem(onboardingStorageKey)) openOnboarding(0);
}

initialize();
