const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

const state = {
    currentTab: "dashboard",
    logAutoRefresh: true,
    loadingAction: false,
    currentConfig: {},
    configConfirmResolve: null,
    dialogResolve: null,
    lastMetricValues: {},
    tabTransitionTimer: null,
    saveStatus: null,
    saveSlots: [],
    saveLoading: false,
    saveBusy: false,
    systemHistory: [],
    auditRecords: [],
    auditFilter: "all",
    auditLoading: false,
    updateStatus: null,
    updateLoading: false,
    installStatus: null,
    installLoading: false,
};

const particles = {
    canvas: null,
    ctx: null,
    items: [],
    meteors: [],
    raf: null,
    width: 0,
    height: 0,
    dpr: 1,
    visible: true,
    lastMeteorAt: 0,
    pointer: { x: -9999, y: -9999, active: false },
    colors: [
        [47, 111, 237],
        [124, 92, 255],
        [21, 127, 92],
        [83, 143, 255],
        [176, 146, 255],
    ],
};

const glowSelector = [
    ".topbar",
    ".tabs",
    ".panel",
    ".hero-panel",
    ".metric-card",
    ".system-card",
    ".trend-card",
    ".config-group",
    ".save-current-card",
    ".save-slot-card",
    ".audit-item",
    ".update-card",
    ".update-step",
    ".install-card",
    ".install-check",
    ".modal-card",
    ".toast",
    ".log-box",
    ".console-output",
    ".primary",
    ".secondary",
    ".icon-button",
    ".tab-button",
].join(",");

const configGroups = [
    {
        icon: "☰",
        title: "服务器基础",
        fields: [
            ["ServerName", "服务器名称", "text"],
            ["ServerDescription", "服务器描述", "text"],
            ["ServerPassword", "服务器密码", "text"],
            ["AdminPassword", "管理员密码", "text"],
            ["ServerPlayerMaxNum", "最大玩家数", "number"],
            ["GuildPlayerMaxNum", "公会最大人数", "number"],
            ["AutoSaveSpan", "自动存档间隔(秒)", "number", "1"],
            ["ChatPostLimitPerMinute", "聊天限速(条/分钟)", "number"],
        ],
    },
    {
        icon: "↗",
        title: "倍率设置",
        fields: [
            ["ExpRate", "经验倍率", "number", { step: "0.1", min: 0.1, max: 20, hint: "范围：0.1 - 20，默认 1" }],
            ["DayTimeSpeedRate", "白天速度", "number", { step: "0.1", min: 0.1, max: 5, hint: "范围：0.1 - 5，默认 1" }],
            ["NightTimeSpeedRate", "夜晚速度", "number", { step: "0.1", min: 0.1, max: 5, hint: "范围：0.1 - 5，默认 1" }],
            ["WorkSpeedRate", "工作速度", "number", { step: "0.1", min: 0.5, max: 5, hint: "范围：0.5 - 5，默认 1" }],
            ["ItemWeightRate", "物品重量倍率", "number", { step: "0.1", min: 0.1, max: 5, hint: "范围：0.1 - 5，默认 1；越低物品越轻" }],
        ],
    },
    {
        icon: "✦",
        title: "系统概率",
        fields: [
            ["PalCaptureRate", "帕鲁捕获概率", "number", { step: "0.1", min: 0.5, max: 2, hint: "范围：0.5 - 2，默认 1；越高越容易捕获" }],
            ["PalSpawnNumRate", "帕鲁刷新概率", "number", { step: "0.1", min: 0.5, max: 3, hint: "范围：0.5 - 3，默认 1；调高会增加服务器性能压力" }],
            ["CollectionDropRate", "采集掉落概率", "number", { step: "0.1", min: 0.5, max: 3, hint: "范围：0.5 - 3，默认 1；影响采集资源掉落" }],
            ["EnemyDropItemRate", "敌人掉落概率", "number", { step: "0.1", min: 0.5, max: 3, hint: "范围：0.5 - 3，默认 1；影响击败敌人的物品掉落" }],
            ["DropItemMaxNum", "掉落物上限", "number", { step: "100", min: 0, max: 10000, hint: "建议范围：0 - 10000，默认 3000；过高会增加性能压力" }],
            ["DropItemAliveMaxHours", "掉落物保留时间(时)", "number", { step: "0.5", min: 0.5, max: 24, hint: "建议范围：0.5 - 24，默认 1；越高掉落物保留越久" }],
            ["SupplyDropSpan", "空投间隔(分)", "number", { step: "1", min: 1, max: 1440, hint: "建议范围：1 - 1440，默认 180；单位是分钟" }],
        ],
    },
    {
        icon: "⚔",
        title: "战斗设置",
        fields: [
            ["PalDamageRateAttack", "帕鲁攻击力倍率", "number", { step: "0.1", min: 0.1, max: 5, hint: "建议范围：0.1 - 5，默认 1；越高帕鲁造成伤害越高" }],
            ["PalDamageRateDefense", "帕鲁受伤倍率", "number", { step: "0.1", min: 0.1, max: 5, hint: "建议范围：0.1 - 5，默认 1；越低帕鲁越抗打" }],
            ["PlayerDamageRateAttack", "玩家攻击力倍率", "number", { step: "0.1", min: 0.1, max: 5, hint: "建议范围：0.1 - 5，默认 1；越高玩家造成伤害越高" }],
            ["PlayerDamageRateDefense", "玩家受伤倍率", "number", { step: "0.1", min: 0.1, max: 5, hint: "建议范围：0.1 - 5，默认 1；越低玩家越抗打" }],
            ["bEnablePlayerToPlayerDamage", "玩家对战伤害", "bool"],
            ["bEnableFriendlyFire", "友军伤害", "bool"],
            ["bIsPvP", "PvP 模式", "bool"],
            ["bEnableInvaderEnemy", "入侵敌人", "bool"],
        ],
    },
    {
        icon: "⌂",
        title: "生存与建造",
        fields: [
            ["PlayerStomachDecreaceRate", "玩家饥饿速率", "number", { step: "0.1", min: 0.1, max: 5, hint: "建议范围：0.1 - 5，默认 1；越低饥饿越慢" }],
            ["PlayerStaminaDecreaceRate", "玩家体力消耗", "number", { step: "0.1", min: 0.1, max: 5, hint: "建议范围：0.1 - 5，默认 1；越低体力消耗越慢" }],
            ["PlayerAutoHPRegeneRate", "玩家自动回血", "number", { step: "0.1", min: 0.1, max: 5, hint: "建议范围：0.1 - 5，默认 1；越高回血越快" }],
            ["PlayerAutoHpRegeneRateInSleep", "玩家睡觉回血", "number", { step: "0.1", min: 0.1, max: 5, hint: "建议范围：0.1 - 5，默认 1；越高睡觉回血越快" }],
            ["PalStomachDecreaceRate", "帕鲁饥饿速率", "number", { step: "0.1", min: 0.1, max: 5, hint: "建议范围：0.1 - 5，默认 1；越低帕鲁饥饿越慢" }],
            ["PalStaminaDecreaceRate", "帕鲁体力消耗", "number", { step: "0.1", min: 0.1, max: 5, hint: "建议范围：0.1 - 5，默认 1；越低帕鲁体力消耗越慢" }],
            ["PalAutoHPRegeneRate", "帕鲁自动回血", "number", { step: "0.1", min: 0.1, max: 5, hint: "建议范围：0.1 - 5，默认 1；越高回血越快" }],
            ["PalAutoHpRegeneRateInSleep", "帕鲁睡觉回血", "number", { step: "0.1", min: 0.1, max: 5, hint: "建议范围：0.1 - 5，默认 1；越高 Palbox 内回血越快" }],
            ["BuildObjectHpRate", "建筑生命倍率", "number", { step: "0.1", min: 0.1, max: 10, hint: "建议范围：0.1 - 10，默认 1；越高建筑越耐久" }],
            ["BuildObjectDamageRate", "建筑受伤倍率", "number", { step: "0.1", min: 0.1, max: 10, hint: "建议范围：0.1 - 10，默认 1；越低建筑越抗打" }],
            ["BuildObjectDeteriorationDamageRate", "建筑腐蚀速率", "number", { step: "0.1", min: 0, max: 10, hint: "建议范围：0 - 10，默认 1；0 通常表示关闭腐蚀" }],
            ["CollectionObjectHpRate", "采集物生命倍率", "number", { step: "0.1", min: 0.5, max: 3, hint: "建议范围：0.5 - 3，默认 1；越高采集物更耐打" }],
            ["CollectionObjectRespawnSpeedRate", "采集物刷新速度", "number", { step: "0.1", min: 0.5, max: 3, hint: "建议范围：0.5 - 3，默认 1；越高刷新越快" }],
            ["BaseCampMaxNum", "据点最大数量", "number"],
            ["BaseCampWorkerMaxNum", "据点工人数上限", "number"],
            ["BaseCampMaxNumInGuild", "公会据点上限", "number"],
        ],
    },
    {
        icon: "◎",
        title: "玩法与网络",
        fields: [
            ["DeathPenalty", "死亡惩罚", "select", [["None", "无"], ["Item", "仅物品"], ["ItemAndEquipment", "物品+装备"], ["All", "全部"]]],
            ["PalEggDefaultHatchingTime", "帕鲁蛋孵化时间(时)", "number", { step: "0.5", min: 0, max: 240, hint: "建议范围：0 - 240，默认 72；0 通常表示立即孵化" }],
            ["EquipmentDurabilityDamageRate", "装备耐久损耗倍率", "number", { step: "0.1", min: 0, max: 5, hint: "建议范围：0 - 5，默认 1；0 通常表示不损耗耐久" }],
            ["AutoResetGuildTimeNoOnlinePlayers", "无玩家自动解散公会时间(时)", "number", { step: "1", min: 0, max: 720, hint: "建议范围：0 - 720，默认 72；0 通常表示关闭自动解散" }],
            ["bEnableFastTravel", "快速旅行", "bool"],
            ["bEnableFastTravelOnlyBaseCamp", "仅基地快速旅行", "bool"],
            ["bIsStartLocationSelectByMap", "选择出生点", "bool"],
            ["bAllowClientMod", "允许客户端 MOD", "bool"],
            ["bIsShowJoinLeftMessage", "显示加入/离开消息", "bool"],
            ["bShowPlayerList", "显示玩家列表", "bool"],
            ["bIsUseBackupSaveData", "启用备份存档", "bool"],
            ["EnablePredatorBossPal", "捕食者 Boss 帕鲁", "bool"],
            ["bHardcore", "困难模式", "bool"],
            ["bPalLost", "帕鲁丢失", "bool"],
            ["RCONPort", "RCON 端口", "number", { step: "1", min: 1024, max: 65535, hint: "范围：1024 - 65535，默认 25575；修改后面板环境变量也要同步" }],
            ["RESTAPIPort", "REST API 端口", "number", { step: "1", min: 1024, max: 65535, hint: "范围：1024 - 65535，默认 8212" }],
            ["RCONEnabled", "RCON 启用", "bool"],
            ["RESTAPIEnabled", "REST API 启用", "bool"],
        ],
    },
];

const configDefaults = {
    ServerName: "Default Palworld Server",
    ServerDescription: "",
    ServerPassword: "",
    AdminPassword: "",
    ServerPlayerMaxNum: "32",
    GuildPlayerMaxNum: "20",
    AutoSaveSpan: "30.000000",
    ChatPostLimitPerMinute: "30",
    ExpRate: "1.000000",
    PalCaptureRate: "1.000000",
    PalSpawnNumRate: "1.000000",
    DayTimeSpeedRate: "1.000000",
    NightTimeSpeedRate: "1.000000",
    WorkSpeedRate: "1.000000",
    CollectionDropRate: "1.000000",
    EnemyDropItemRate: "1.000000",
    ItemWeightRate: "1.000000",
    PalDamageRateAttack: "1.000000",
    PalDamageRateDefense: "1.000000",
    PlayerDamageRateAttack: "1.000000",
    PlayerDamageRateDefense: "1.000000",
    bEnablePlayerToPlayerDamage: "False",
    bEnableFriendlyFire: "False",
    bIsPvP: "False",
    bEnableInvaderEnemy: "True",
    PlayerStomachDecreaceRate: "1.000000",
    PlayerStaminaDecreaceRate: "1.000000",
    PlayerAutoHPRegeneRate: "1.000000",
    PlayerAutoHpRegeneRateInSleep: "1.000000",
    PalStomachDecreaceRate: "1.000000",
    PalStaminaDecreaceRate: "1.000000",
    PalAutoHPRegeneRate: "1.000000",
    PalAutoHpRegeneRateInSleep: "1.000000",
    DeathPenalty: "All",
    BuildObjectHpRate: "1.000000",
    BuildObjectDamageRate: "1.000000",
    BuildObjectDeteriorationDamageRate: "1.000000",
    BaseCampMaxNum: "128",
    BaseCampWorkerMaxNum: "15",
    BaseCampMaxNumInGuild: "4",
    CollectionObjectHpRate: "1.000000",
    CollectionObjectRespawnSpeedRate: "1.000000",
    DropItemMaxNum: "3000",
    DropItemAliveMaxHours: "1.000000",
    PalEggDefaultHatchingTime: "72.000000",
    EquipmentDurabilityDamageRate: "1.000000",
    SupplyDropSpan: "180",
    AutoResetGuildTimeNoOnlinePlayers: "72.000000",
    bEnableFastTravel: "True",
    bEnableFastTravelOnlyBaseCamp: "False",
    bIsStartLocationSelectByMap: "True",
    bAllowClientMod: "True",
    bIsShowJoinLeftMessage: "True",
    bShowPlayerList: "False",
    bIsUseBackupSaveData: "True",
    EnablePredatorBossPal: "True",
    bHardcore: "False",
    bPalLost: "False",
    RCONPort: "25575",
    RESTAPIPort: "8212",
    RCONEnabled: "True",
    RESTAPIEnabled: "False",
};

const stringFields = new Set(["ServerName", "ServerDescription", "ServerPassword", "AdminPassword"]);

function stripQuotes(value) {
    return String(value ?? "").replace(/^"|"$/g, "");
}

function normalizeSubmitValue(key, value) {
    const text = stripQuotes(value).trim();
    if (stringFields.has(key)) return `"${text.replaceAll('"', '\\"')}"`;
    return String(value ?? "").trim();
}

function setMessage(el, text, type = "") {
    if (!el) return;
    el.textContent = text;
    el.className = `message ${type ? `is-${type}` : ""}`.trim();
    if (el.id === "configMsg" || el.id === "saveMsg") el.classList.add("panel-message");
}

function showToast(message, type = "info") {
    const stack = $("#toastStack");
    if (!stack || !message) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`.trim();
    toast.textContent = message;
    stack.appendChild(toast);

    setTimeout(() => {
        toast.classList.add("is-leaving");
        setTimeout(() => toast.remove(), 180);
    }, 3200);
}

function closeDialog(result = null) {
    const modal = $("#interactionModal");
    if (!modal) return;
    modal.classList.remove("is-open", "is-danger", "is-progress");
    modal.setAttribute("aria-hidden", "true");
    $("#dialogBody").replaceChildren();
    if (state.dialogResolve) {
        state.dialogResolve(result);
        state.dialogResolve = null;
    }
}

function createDialogField(field) {
    const wrapper = document.createElement("label");
    wrapper.className = "dialog-field";
    const label = document.createElement("span");
    label.textContent = field.label;
    const input = document.createElement(field.type === "textarea" ? "textarea" : "input");
    input.name = field.name;
    input.value = field.value || "";
    input.placeholder = field.placeholder || "";
    input.required = Boolean(field.required);
    if (field.type && field.type !== "textarea") input.type = field.type;
    wrapper.append(label, input);
    if (field.hint) {
        const hint = document.createElement("small");
        hint.textContent = field.hint;
        wrapper.appendChild(hint);
    }
    return wrapper;
}

function openDialog(options = {}) {
    const modal = $("#interactionModal");
    const body = $("#dialogBody");
    const submit = $("#dialogSubmit");
    const cancel = $("#dialogCancel");
    if (!modal || !body || !submit || !cancel) return Promise.resolve(null);

    $("#dialogEyebrow").textContent = options.eyebrow || "Action";
    $("#dialogTitle").textContent = options.title || "确认操作";
    $("#dialogText").textContent = options.text || "";
    submit.textContent = options.submitText || "确认";
    cancel.textContent = options.cancelText || "取消";
    submit.className = `primary ${options.danger ? "danger" : ""}`.trim();
    cancel.style.display = options.hideCancel ? "none" : "";
    submit.style.display = options.hideSubmit ? "none" : "";
    body.replaceChildren();
    modal.classList.toggle("is-danger", Boolean(options.danger));
    modal.classList.toggle("is-progress", Boolean(options.progress));

    if (options.progress) {
        const list = document.createElement("div");
        list.className = "progress-steps";
        (options.steps || []).forEach((step, index) => {
            const item = document.createElement("div");
            item.className = `progress-step ${index === 0 ? "is-active" : ""}`;
            item.dataset.stepIndex = String(index);
            const dot = document.createElement("span");
            dot.className = "progress-dot";
            const text = document.createElement("div");
            const title = document.createElement("b");
            title.textContent = step;
            const msg = document.createElement("small");
            msg.textContent = index === 0 ? "准备中..." : "等待中";
            text.append(title, msg);
            item.append(dot, text);
            list.appendChild(item);
        });
        body.appendChild(list);
    } else if (options.fields?.length) {
        const form = document.createElement("form");
        form.className = "dialog-form";
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            submit.click();
        });
        form.append(...options.fields.map(createDialogField));
        body.appendChild(form);
        setTimeout(() => form.querySelector("input, textarea")?.focus(), 50);
    } else if (options.details) {
        const details = document.createElement("div");
        details.className = "dialog-details";
        details.textContent = options.details;
        body.appendChild(details);
    }

    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");

    return new Promise((resolve) => {
        state.dialogResolve = resolve;
        submit.onclick = () => {
            if (options.progress) return;
            if (options.fields?.length) {
                const values = {};
                let valid = true;
                body.querySelectorAll("input, textarea").forEach((input) => {
                    if (input.required && !input.value.trim()) {
                        input.classList.add("is-invalid");
                        valid = false;
                    } else {
                        input.classList.remove("is-invalid");
                    }
                    values[input.name] = input.value;
                });
                if (!valid) {
                    showToast("请补全必填内容", "warn");
                    return;
                }
                closeDialog(values);
                return;
            }
            closeDialog(true);
        };
        cancel.onclick = () => closeDialog(null);
        $("#dialogClose").onclick = () => closeDialog(null);
    });
}

function setProgressStep(index, status = "active", message = "") {
    const item = $(`#interactionModal [data-step-index="${index}"]`);
    if (!item) return;
    item.classList.remove("is-active", "is-done", "is-error");
    item.classList.add(status === "done" ? "is-done" : status === "error" ? "is-error" : "is-active");
    const small = item.querySelector("small");
    if (small) small.textContent = message || (status === "done" ? "完成" : status === "error" ? "失败" : "进行中...");
}

function openProgressDialog(title, steps, text = "") {
    return openDialog({
        eyebrow: "Progress",
        title,
        text,
        steps,
        progress: true,
        hideCancel: true,
        hideSubmit: true,
    });
}

function finishProgressDialog(message, type = "success") {
    $("#dialogText").textContent = message;
    const submit = $("#dialogSubmit");
    submit.textContent = "完成";
    submit.style.display = "";
    submit.className = `primary ${type === "error" ? "danger" : ""}`.trim();
    submit.onclick = () => closeDialog(true);
}

function formatBytes(bytes) {
    const value = Number(bytes || 0);
    if (!value) return "0 B";
    const units = ["B", "KB", "MB", "GB", "TB"];
    const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
    return `${(value / (1024 ** index)).toFixed(index ? 1 : 0)} ${units[index]}`;
}

function formatOptional(value, fallback = "-") {
    return value === undefined || value === null || value === "" ? fallback : String(value);
}

function flashMetric(id, nextValue) {
    const element = $(`#${id}`);
    if (!element) return;
    const previous = state.lastMetricValues[id];
    state.lastMetricValues[id] = nextValue;
    if (previous === undefined || previous === nextValue) return;
    const card = element.closest(".metric-card");
    if (!card) return;
    card.classList.remove("is-flashing");
    void card.offsetWidth;
    card.classList.add("is-flashing");
}

function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function particleCountForViewport(width, height) {
    const area = width * height;
    const isSmall = width < 720;
    const base = Math.round(area / (isSmall ? 17000 : 9200));
    return Math.max(isSmall ? 38 : 92, Math.min(isSmall ? 88 : 230, base));
}

function createParticle(width, height, initial = false) {
    const color = particles.colors[Math.floor(Math.random() * particles.colors.length)];
    const speed = 0.16 + Math.random() * 0.36;
    const angle = Math.random() * Math.PI * 2;
    return {
        x: Math.random() * width,
        y: initial ? Math.random() * height : height + Math.random() * 80,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 0.08,
        radius: 1.2 + Math.random() * 3.6,
        alpha: 0.42 + Math.random() * 0.64,
        color,
        phase: Math.random() * Math.PI * 2,
    };
}

function createMeteor(width, height) {
    const color = particles.colors[Math.floor(Math.random() * particles.colors.length)];
    const fromLeft = Math.random() > 0.4;
    return {
        x: fromLeft ? -80 : Math.random() * width * 0.55,
        y: Math.random() * height * 0.38,
        vx: 2.6 + Math.random() * 2.4,
        vy: 1.0 + Math.random() * 1.6,
        life: 0,
        maxLife: 70 + Math.random() * 55,
        length: 72 + Math.random() * 110,
        alpha: 0.32 + Math.random() * 0.24,
        color,
    };
}

function resizeParticles() {
    const canvas = particles.canvas;
    if (!canvas) return;
    particles.dpr = Math.min(window.devicePixelRatio || 1, 2);
    particles.width = window.innerWidth;
    particles.height = window.innerHeight;
    canvas.width = Math.round(particles.width * particles.dpr);
    canvas.height = Math.round(particles.height * particles.dpr);
    canvas.style.width = `${particles.width}px`;
    canvas.style.height = `${particles.height}px`;
    particles.ctx.setTransform(particles.dpr, 0, 0, particles.dpr, 0, 0);
    particles.items = Array.from(
        { length: particleCountForViewport(particles.width, particles.height) },
        () => createParticle(particles.width, particles.height, true)
    );
    particles.meteors = [];
}

function drawParticles(time) {
    if (!particles.ctx || !particles.visible) return;
    const { ctx, width, height, pointer } = particles;
    ctx.clearRect(0, 0, width, height);
    ctx.lineWidth = 1;

    for (const particle of particles.items) {
        const pulse = 0.72 + Math.sin(time * 0.0012 + particle.phase) * 0.28;
        if (pointer.active) {
            const dx = particle.x - pointer.x;
            const dy = particle.y - pointer.y;
            const distance = Math.hypot(dx, dy);
            if (distance < 190 && distance > 0.1) {
                const force = (190 - distance) / 190;
                particle.vx += (dx / distance) * force * 0.014;
                particle.vy += (dy / distance) * force * 0.014;
                particle.vx += (pointer.x - particle.x) * force * 0.0007;
                particle.vy += (pointer.y - particle.y) * force * 0.0007;
            }
        }

        particle.x += particle.vx;
        particle.y += particle.vy;
        particle.vx *= 0.995;
        particle.vy *= 0.995;

        if (particle.x < -30) particle.x = width + 30;
        if (particle.x > width + 30) particle.x = -30;
        if (particle.y < -40) {
            particle.x = Math.random() * width;
            particle.y = height + 30;
        }
        if (particle.y > height + 60) particle.y = -20;

        const [r, g, b] = particle.color;
        const glow = particle.radius * 8.4;
        const gradient = ctx.createRadialGradient(particle.x, particle.y, 0, particle.x, particle.y, glow);
        gradient.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${particle.alpha * pulse})`);
        gradient.addColorStop(0.34, `rgba(${r}, ${g}, ${b}, ${particle.alpha * 0.34 * pulse})`);
        gradient.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, glow, 0, Math.PI * 2);
        ctx.fill();
    }

    const linkDistance = width < 720 ? 104 : 154;
    for (let i = 0; i < particles.items.length; i += 1) {
        for (let j = i + 1; j < particles.items.length; j += 1) {
            const a = particles.items[i];
            const b = particles.items[j];
            const dx = a.x - b.x;
            const dy = a.y - b.y;
            const distance = Math.hypot(dx, dy);
            if (distance > linkDistance) continue;
            const opacity = (1 - distance / linkDistance) * 0.32;
            ctx.strokeStyle = `rgba(47, 111, 237, ${opacity})`;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
        }
    }

    if (time - particles.lastMeteorAt > (width < 720 ? 4200 : 2600) && particles.meteors.length < (width < 720 ? 1 : 3)) {
        particles.meteors.push(createMeteor(width, height));
        particles.lastMeteorAt = time + Math.random() * 1200;
    }

    particles.meteors = particles.meteors.filter((meteor) => {
        meteor.life += 1;
        meteor.x += meteor.vx;
        meteor.y += meteor.vy;
        const progress = meteor.life / meteor.maxLife;
        const fade = Math.sin(Math.min(1, progress) * Math.PI);
        const [r, g, b] = meteor.color;
        const tailX = meteor.x - meteor.length;
        const tailY = meteor.y - meteor.length * 0.38;
        const line = ctx.createLinearGradient(tailX, tailY, meteor.x, meteor.y);
        line.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0)`);
        line.addColorStop(0.62, `rgba(${r}, ${g}, ${b}, ${meteor.alpha * 0.34 * fade})`);
        line.addColorStop(1, `rgba(255, 255, 255, ${meteor.alpha * fade})`);
        ctx.strokeStyle = line;
        ctx.lineWidth = 1.4;
        ctx.beginPath();
        ctx.moveTo(tailX, tailY);
        ctx.lineTo(meteor.x, meteor.y);
        ctx.stroke();

        const head = ctx.createRadialGradient(meteor.x, meteor.y, 0, meteor.x, meteor.y, 18);
        head.addColorStop(0, `rgba(255, 255, 255, ${0.58 * fade})`);
        head.addColorStop(0.4, `rgba(${r}, ${g}, ${b}, ${meteor.alpha * fade})`);
        head.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);
        ctx.fillStyle = head;
        ctx.beginPath();
        ctx.arc(meteor.x, meteor.y, 18, 0, Math.PI * 2);
        ctx.fill();
        return meteor.life < meteor.maxLife && meteor.x < width + meteor.length && meteor.y < height + 120;
    });
}

function animateParticles(time = 0) {
    drawParticles(time);
    particles.raf = requestAnimationFrame(animateParticles);
}

function initParticles() {
    if (prefersReducedMotion()) return;
    const canvas = $("#ambientParticles");
    if (!canvas || !canvas.getContext) return;
    particles.canvas = canvas;
    particles.ctx = canvas.getContext("2d", { alpha: true });
    resizeParticles();
    window.addEventListener("resize", resizeParticles);
    window.addEventListener("mousemove", (event) => {
        particles.pointer = { x: event.clientX, y: event.clientY, active: true };
    });
    window.addEventListener("mouseleave", () => {
        particles.pointer.active = false;
    });
    document.addEventListener("visibilitychange", () => {
        particles.visible = !document.hidden;
        if (!particles.visible && particles.ctx) {
            particles.ctx.clearRect(0, 0, particles.width, particles.height);
        }
    });
    animateParticles();
}

function initCursorGlow() {
    if (prefersReducedMotion()) return;
    const root = document.documentElement;
    const glow = $("#cursorGlow");
    let activeElement = null;

    window.addEventListener("pointermove", (event) => {
        root.style.setProperty("--cursor-x", `${event.clientX}px`);
        root.style.setProperty("--cursor-y", `${event.clientY}px`);
        document.body.classList.add("has-cursor");

        const target = event.target.closest?.(glowSelector);
        if (activeElement && activeElement !== target) {
            activeElement.classList.remove("is-pointer-hot");
        }
        activeElement = target;
        if (!target) return;

        const rect = target.getBoundingClientRect();
        target.style.setProperty("--mx", `${event.clientX - rect.left}px`);
        target.style.setProperty("--my", `${event.clientY - rect.top}px`);
        target.classList.add("is-pointer-hot");
    }, { passive: true });

    window.addEventListener("pointerleave", () => {
        document.body.classList.remove("has-cursor");
        if (activeElement) activeElement.classList.remove("is-pointer-hot");
        activeElement = null;
    });

    if (glow) {
        glow.addEventListener("transitionend", () => {
            if (!document.body.classList.contains("has-cursor")) {
                glow.style.opacity = "";
            }
        });
    }
}

async function api(path, options = {}) {
    const response = await fetch(path, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.message || `请求失败 (${response.status})`);
    }
    return data;
}

function switchTab(tab) {
    if (state.currentTab === tab) return;
    if (state.tabTransitionTimer) {
        clearTimeout(state.tabTransitionTimer);
        state.tabTransitionTimer = null;
    }

    const previousPanel = $(`#tab-${state.currentTab}`);
    const nextPanel = $(`#tab-${tab}`);
    if (!nextPanel) return;

    state.currentTab = tab;
    $$(".tab-button").forEach((button) => button.classList.toggle("is-active", button.dataset.tab === tab));

    $$(".tab-panel").forEach((panel) => {
        panel.classList.remove("is-entering", "is-leaving");
        if (panel !== previousPanel && panel !== nextPanel) panel.classList.remove("is-active");
    });

    if (previousPanel && previousPanel !== nextPanel) {
        previousPanel.classList.add("is-leaving");
        previousPanel.classList.remove("is-active");
    }

    nextPanel.classList.add("is-active", "is-entering");
    state.tabTransitionTimer = setTimeout(() => {
        if (previousPanel) previousPanel.classList.remove("is-leaving");
        nextPanel.classList.remove("is-entering");
        state.tabTransitionTimer = null;
    }, 170);

    if (tab === "config") loadConfig();
    if (tab === "log") loadLog();
    if (tab === "saves") loadSaves();
    if (tab === "update") loadUpdateStatus();
    if (tab === "install") loadInstallStatus();
    if (tab === "audit") loadAudit();
}

function renderStatus(data) {
    const { status, info } = data;
    const players = Array.isArray(info.online_players) ? info.online_players : [];
    const playerTotal = players.length;
    const maxPlayers = info.max_players || "0";
    const statusBadge = $("#statusBadge");

    statusBadge.textContent = status.running ? "运行中" : "已停止";
    statusBadge.className = `status-pill ${status.running ? "is-online" : "is-offline"}`;

    const statusText = status.running ? "运行中" : "已停止";
    const gameVersion = info.game_version || "-";
    const gamePort = info.port || "-";
    const playerCount = `${playerTotal} / ${maxPlayers}`;
    $("#statusText").textContent = statusText;
    $("#gameVersion").textContent = gameVersion;
    $("#gamePort").textContent = gamePort;
    $("#playerCount").textContent = playerCount;
    flashMetric("statusText", statusText);
    flashMetric("gameVersion", gameVersion);
    flashMetric("gamePort", gamePort);
    flashMetric("playerCount", playerCount);
    $("#serverName").textContent = info.server_name || "-";
    $("#serverDesc").textContent = info.server_description || "暂无服务器描述";
    const backendText = status.backend === "docker" ? "Docker" : "systemd";
    $("#serverUptime").textContent = status.start_time ? `模式：${backendText} · 启动时间：${status.start_time}` : `模式：${backendText}`;
    $("#playerCountBadge").textContent = `${playerTotal} 人`;

    updateActionButtons(status.running);
    renderPlayers(players);
}

function formatBytes(bytes) {
    const value = Number(bytes || 0);
    if (!value) return "-";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let size = value;
    let unit = 0;
    while (size >= 1024 && unit < units.length - 1) {
        size /= 1024;
        unit += 1;
    }
    return `${size.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}

function formatDuration(seconds) {
    const total = Math.max(0, Number(seconds || 0));
    const days = Math.floor(total / 86400);
    const hours = Math.floor((total % 86400) / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    if (days > 0) return `${days} 天 ${hours} 小时`;
    if (hours > 0) return `${hours} 小时 ${minutes} 分钟`;
    return `${minutes} 分钟`;
}

function appendSystemHistory(system) {
    const memory = system.memory || {};
    const disk = system.disk || {};
    const load = Array.isArray(system.load) ? system.load : [];
    state.systemHistory.push({
        ts: Date.now(),
        cpu: Number(system.cpu_percent || 0),
        memory: Number(memory.percent || 0),
        disk: Number(disk.percent || 0),
        load: Number(load[0] || 0),
    });
    state.systemHistory = state.systemHistory.slice(-30);
}

function drawTrendChart(canvas, values, color, maxValue = 100) {
    if (!canvas || !canvas.getContext) return;
    const ctx = canvas.getContext("2d");
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(160, Math.round(rect.width || canvas.width || 220));
    const height = Math.max(58, Math.round(rect.height || canvas.height || 72));
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);

    const padding = 8;
    const plotWidth = width - padding * 2;
    const plotHeight = height - padding * 2;
    const points = values.length ? values : [0];
    const scaleMax = Math.max(1, maxValue);

    ctx.strokeStyle = "rgba(154, 190, 255, 0.18)";
    ctx.lineWidth = 1;
    [0.25, 0.5, 0.75].forEach((ratio) => {
        const y = padding + plotHeight * ratio;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
    });

    const coords = points.map((value, index) => {
        const x = padding + (points.length === 1 ? plotWidth : (index / (points.length - 1)) * plotWidth);
        const y = padding + plotHeight - (Math.max(0, Math.min(value, scaleMax)) / scaleMax) * plotHeight;
        return [x, y];
    });

    const gradient = ctx.createLinearGradient(0, padding, 0, height - padding);
    gradient.addColorStop(0, color.replace("0.95", "0.22"));
    gradient.addColorStop(1, color.replace("0.95", "0"));
    ctx.beginPath();
    coords.forEach(([x, y], index) => {
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.lineTo(coords[coords.length - 1][0], height - padding);
    ctx.lineTo(coords[0][0], height - padding);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    ctx.beginPath();
    coords.forEach(([x, y], index) => {
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.stroke();
}

function renderSystemCharts() {
    const history = state.systemHistory;
    const loadMax = Math.max(1, ...history.map((item) => item.load), 1) * 1.2;
    drawTrendChart($("#systemCpuChart"), history.map((item) => item.cpu), "rgba(47, 111, 237, 0.95)");
    drawTrendChart($("#systemMemoryChart"), history.map((item) => item.memory), "rgba(124, 92, 255, 0.95)");
    drawTrendChart($("#systemDiskChart"), history.map((item) => item.disk), "rgba(21, 127, 92, 0.95)");
    drawTrendChart($("#systemLoadChart"), history.map((item) => item.load), "rgba(185, 107, 0, 0.95)", loadMax);
}

function renderSystem(data) {
    const system = data.system || {};
    const memory = system.memory || {};
    const disk = system.disk || {};
    const load = Array.isArray(system.load) ? system.load : [];
    const cpu = system.cpu_percent;
    const memoryPercent = memory.percent;
    const diskPercent = disk.percent;

    $("#systemCpu").textContent = cpu == null ? "-" : `${cpu}%`;
    $("#systemLoad").textContent = `负载：${load.length ? load.join(" / ") : "-"}`;
    $("#systemMemory").textContent = memoryPercent == null ? "-" : `${memoryPercent}%`;
    $("#systemMemoryDetail").textContent = `${formatBytes(memory.used)} / ${formatBytes(memory.total)}`;
    $("#systemDisk").textContent = diskPercent == null ? "-" : `${diskPercent}%`;
    $("#systemDiskDetail").textContent = `${formatBytes(disk.used)} / ${formatBytes(disk.total)}`;
    $("#systemUptime").textContent = formatDuration(system.uptime_seconds);
    $("#systemUpdated").textContent = `已刷新：${new Date().toLocaleTimeString()}`;

    appendSystemHistory(system);
    renderSystemCharts();

    flashMetric("systemCpu", $("#systemCpu").textContent);
    flashMetric("systemMemory", $("#systemMemory").textContent);
    flashMetric("systemDisk", $("#systemDisk").textContent);
    flashMetric("systemUptime", $("#systemUptime").textContent);
}

async function refreshSystem() {
    try {
        const data = await api("/api/system");
        renderSystem(data);
    } catch (error) {
        $("#systemUpdated").textContent = "机器状态读取失败";
    }
}

function updateActionButtons(isRunning) {
    const startButton = $('[data-action="start"]');
    const restartButton = $('[data-action="restart"]');
    const stopButton = $('[data-action="stop"]');

    if (startButton) {
        startButton.disabled = isRunning;
        startButton.title = isRunning ? "服务器已在运行" : "启动服务器";
    }
    if (restartButton) {
        restartButton.disabled = !isRunning;
        restartButton.title = isRunning ? "重启服务器" : "服务器停止时不可重启";
    }
    if (stopButton) {
        stopButton.disabled = !isRunning;
        stopButton.title = isRunning ? "停止服务器" : "服务器已停止";
    }
}

function renderPlayers(players) {
    const list = $("#playerList");
    if (!players.length) {
        list.innerHTML = `<tr><td colspan="3" class="empty">暂无在线玩家</td></tr>`;
        return;
    }
    list.replaceChildren(...players.map((player) => {
        const row = document.createElement("tr");
        [player.name, player.player_uid, player.steam_id].forEach((value) => {
            const cell = document.createElement("td");
            cell.textContent = value || "-";
            row.appendChild(cell);
        });
        return row;
    }));
}

async function refreshAll() {
    try {
        const data = await api("/api/status");
        renderStatus(data);
        refreshSystem();
    } catch (error) {
        $("#statusBadge").textContent = "连接失败";
        $("#statusBadge").className = "status-pill is-offline";
        updateActionButtons(false);
        setMessage($("#actionMsg"), error.message, "error");
        refreshSystem();
    }

    if (state.currentTab === "log" || state.logAutoRefresh) {
        loadLog();
    }
    if (state.currentTab === "saves") {
        loadSaves(false);
    }
    if (state.currentTab === "update") {
        loadUpdateStatus(false);
    }
    if (state.currentTab === "install") {
        loadInstallStatus(false);
    }
    if (state.currentTab === "audit") {
        loadAudit(false);
    }
}

async function serverAction(action) {
    if (state.loadingAction) return;
    if (action === "stop" || action === "restart") {
        const confirmed = await openDialog({
            eyebrow: "Server Action",
            title: action === "stop" ? "确认停止服务器" : "确认重启服务器",
            text: action === "stop"
                ? "停止后玩家会断开连接，直到你重新启动 Palworld 服务。"
                : "重启会短暂中断连接，适合应用配置或刷新服务器状态。",
            submitText: action === "stop" ? "确认停止" : "确认重启",
            danger: action === "stop",
        });
        if (!confirmed) return;
    }

    state.loadingAction = true;
    const activeButton = document.querySelector(`[data-action="${action}"]`);
    const heroPanel = $("#tab-dashboard .hero-panel");
    if (activeButton) activeButton.classList.add("is-busy");
    if (heroPanel) heroPanel.classList.add("is-working");
    $$("[data-action]").forEach((button) => button.disabled = true);
    setMessage($("#actionMsg"), "正在执行操作...");

    try {
        const data = await api(`/api/${action}`, { method: "POST" });
        setMessage($("#actionMsg"), data.message || "操作完成", data.success ? "success" : "error");
        showToast(data.message || "操作完成", data.success ? "success" : "error");
    } catch (error) {
        setMessage($("#actionMsg"), error.message, "error");
        showToast(error.message, "error");
    } finally {
        state.loadingAction = false;
        if (activeButton) activeButton.classList.remove("is-busy");
        if (heroPanel) heroPanel.classList.remove("is-working");
        setTimeout(refreshAll, action === "restart" ? 5000 : 2000);
    }
}

async function loadLog() {
    const log = $("#logContainer");
    try {
        const data = await api("/api/log?lines=80");
        renderLogLines(data.lines || []);
        log.scrollTop = log.scrollHeight;
    } catch (error) {
        renderLogLines([error.message]);
    }
}

function renderLogLines(lines) {
    const log = $("#logContainer");
    log.replaceChildren(...(lines.length ? lines : ["暂无日志"]).map((line) => {
        const row = document.createElement("span");
        row.className = `log-line ${classifyLogLine(line)}`.trim();
        row.textContent = line;
        return row;
    }));
}

function classifyLogLine(line) {
    const value = String(line).toLowerCase();
    if (value.includes("error") || value.includes("fail") || value.includes("exception")) return "error";
    if (value.includes("warn")) return "warn";
    if (value.includes("success") || value.includes("running") || value.includes("version")) return "success";
    return "";
}

const auditActionLabels = {
    "service.start": "启动服务",
    "service.stop": "停止服务",
    "service.restart": "重启服务",
    "config.save": "保存配置",
    "config.save_restart": "保存并重启",
    "rcon.command": "RCON 命令",
    "saves.backup_current": "备份当前存档",
    "saves.create_slot": "创建存档槽",
    "saves.import_slot": "导入存档",
    "saves.upload_slot": "上传存档",
    "saves.switch": "切换存档",
    "saves.delete_slot": "删除存档",
};

Object.assign(auditActionLabels, {
    "update.check": "检查更新",
    "update.apply": "执行更新",
    "update.failed": "更新失败",
    "install.check": "检查安装环境",
    "install.palworld": "安装 Palworld",
    "install.repair": "修复安装",
});

function formatAuditTime(value) {
    if (!value) return "-";
    const normalized = String(value).replace(/([+-]\d{2})(\d{2})$/, "$1:$2");
    const date = new Date(normalized);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
}

function auditDetails(record) {
    const details = [];
    if (record.message) details.push(record.message);
    if (record.command) details.push(`命令：${record.command}`);
    if (Array.isArray(record.changed_keys) && record.changed_keys.length) details.push(`配置项：${record.changed_keys.join(", ")}`);
    if (record.slot_id) details.push(`存档槽：${record.slot_id}`);
    if (record.backup_id) details.push(`备份：${record.backup_id}`);
    if (record.filename) details.push(`文件：${record.filename}`);
    if (record.source_path) details.push(`来源：${record.source_path}`);
    return details;
}

function renderAudit() {
    const list = $("#auditList");
    if (!list) return;
    const records = state.auditRecords.filter((record) => {
        if (state.auditFilter === "success") return record.success;
        if (state.auditFilter === "failed") return !record.success;
        return true;
    });

    $$(".audit-filter").forEach((button) => {
        button.classList.toggle("is-active", button.dataset.auditFilter === state.auditFilter);
    });

    if (!records.length) {
        const empty = document.createElement("div");
        empty.className = "empty audit-empty";
        empty.textContent = "暂无匹配的操作记录。";
        list.replaceChildren(empty);
        return;
    }

    list.replaceChildren(...records.map((record) => {
        const item = document.createElement("article");
        item.className = `audit-item ${record.success ? "is-success" : "is-error"}`;

        const header = document.createElement("div");
        header.className = "audit-item-head";
        const title = document.createElement("div");
        const label = document.createElement("h3");
        label.textContent = auditActionLabels[record.action] || record.action || "未知操作";
        const meta = document.createElement("p");
        meta.className = "muted";
        meta.textContent = `${formatAuditTime(record.time || record.ts)} · ${record.source_ip || "unknown"}`;
        title.append(label, meta);
        const badge = document.createElement("span");
        badge.className = `soft-pill ${record.success ? "is-success" : "is-error"}`;
        badge.textContent = record.success ? "成功" : "失败";
        header.append(title, badge);

        const detailWrap = document.createElement("div");
        detailWrap.className = "audit-detail-list";
        const details = auditDetails(record);
        detailWrap.replaceChildren(...(details.length ? details : ["无附加信息"]).map((detail) => {
            const chip = document.createElement("span");
            chip.textContent = detail;
            return chip;
        }));

        item.append(header, detailWrap);
        return item;
    }));
}

async function loadAudit(showLoading = true) {
    if (state.auditLoading) return;
    state.auditLoading = true;
    if (showLoading) setMessage($("#auditMsg"), "正在读取操作记录...");
    try {
        const data = await api("/api/audit?limit=80");
        state.auditRecords = data.records || [];
        renderAudit();
        if (showLoading) setMessage($("#auditMsg"), "操作记录已刷新。", "success");
    } catch (error) {
        setMessage($("#auditMsg"), error.message, "error");
        showToast(error.message, "error");
    } finally {
        state.auditLoading = false;
    }
}

function setAuditFilter(filter) {
    state.auditFilter = filter;
    renderAudit();
}

const updateStepLabels = {
    detect: "检测版本",
    notify: "通知玩家",
    save: "保存世界",
    backup: "备份存档",
    stop: "停止服务",
    update: "SteamCMD 更新",
    permissions: "修复权限",
    start: "启动服务",
    complete: "完成",
    failed: "失败",
};

function shortManifest(value) {
    const text = String(value || "-");
    return text.length > 16 ? `${text.slice(0, 8)}...${text.slice(-6)}` : text;
}

function renderUpdateStatus(status = {}) {
    state.updateStatus = status;
    const dockerMode = status.backend === "docker";
    $("#updateLocalManifest").textContent = shortManifest(status.local_manifest);
    $("#updateLocalBuild").textContent = status.local_buildid ? `Build ${status.local_buildid}` : "Build -";
    $("#updateLatestManifest").textContent = shortManifest(status.latest_manifest);
    $("#updateCheckedAt").textContent = status.checked_at ? `检查于 ${formatAuditTime(status.checked_at)}` : "尚未检查";
    $("#updateAvailability").textContent = status.running
        ? "更新进行中"
        : status.update_available
            ? "发现新版本"
            : status.success === false
                ? "上次失败"
                : "已是最新";
    $("#updateAutoState").textContent = dockerMode ? "Docker Compose 模式 · 自动检测关闭" : `自动更新 ${status.auto_update_enabled ? "开启" : "关闭"} · 倒计时 ${status.warn_minutes || 0} 分钟`;
    $("#updateServiceState").textContent = dockerMode ? "容器触发" : status.service_active ? "运行中" : "空闲";
    $("#updateTimerState").textContent = dockerMode ? "重启 Palworld 容器后自动 validate" : `Timer ${status.timer_active ? "已启用" : "未启用"}`;

    const applyButton = $("#applyUpdateBtn");
    if (applyButton) {
        const canApply = Boolean(status.update_available) && !status.running && !status.service_active;
        applyButton.disabled = !canApply;
        applyButton.textContent = status.running || status.service_active
            ? "更新进行中"
            : status.update_available
                ? dockerMode ? "重启容器更新" : "立即后台更新"
                : status.checked_at
                    ? "已是最新"
                    : "先检查更新";
        applyButton.title = canApply ? "启动后台更新流程" : "没有检测到新版本时不会启动后台更新";
    }

    const steps = Array.isArray(status.steps) ? status.steps : [];
    const stepWrap = $("#updateSteps");
    if (stepWrap) {
        stepWrap.replaceChildren(...(steps.length ? steps : [{ name: "detect", status: "idle", message: status.message || "等待检查" }]).map((step) => {
            const item = document.createElement("div");
            item.className = `update-step is-${step.status || "idle"}`;
            const dot = document.createElement("span");
            dot.className = "progress-dot";
            const text = document.createElement("div");
            const title = document.createElement("b");
            title.textContent = updateStepLabels[step.name] || step.name || "步骤";
            const msg = document.createElement("small");
            msg.textContent = step.message || step.status || "-";
            text.append(title, msg);
            item.append(dot, text);
            return item;
        }));
    }

    const log = $("#updateLog");
    if (log) {
        const lines = Array.isArray(status.log_tail) ? status.log_tail : [];
        log.textContent = lines.length ? lines.join("\n") : "等待更新日志...";
        log.scrollTop = log.scrollHeight;
    }

    const type = status.success === false ? "error" : status.update_available ? "warn" : status.running ? "" : "success";
    setMessage($("#updateMsg"), status.message || "更新状态已刷新", type);
}

async function loadUpdateStatus(showLoading = true) {
    if (state.updateLoading) return;
    state.updateLoading = true;
    if (showLoading) setMessage($("#updateMsg"), "正在读取更新状态...");
    try {
        const data = await api("/api/update/status");
        renderUpdateStatus(data.status || {});
    } catch (error) {
        setMessage($("#updateMsg"), error.message, "error");
        showToast(error.message, "error");
    } finally {
        state.updateLoading = false;
    }
}

async function checkUpdateNow() {
    const button = $("#checkUpdateBtn");
    if (button) button.classList.add("is-busy");
    setMessage($("#updateMsg"), "正在联网检查 Palworld 更新...");
    try {
        const data = await api("/api/update/check", { method: "POST" });
        renderUpdateStatus(data.status || {});
        showToast(data.message || "检查完成", data.success ? "success" : "error");
    } catch (error) {
        setMessage($("#updateMsg"), error.message, "error");
        showToast(error.message, "error");
        await loadUpdateStatus(false);
    } finally {
        if (button) button.classList.remove("is-busy");
    }
}

async function applyUpdateNow() {
    if (!state.updateStatus?.update_available) {
        showToast("当前没有检测到可用更新，请先检查更新", "info");
        setMessage($("#updateMsg"), "当前没有检测到可用更新，请先点击检查更新。", "info");
        return;
    }
    const confirmed = await openDialog({
        eyebrow: "Auto Update",
        title: "确认后台更新 Palworld",
        text: "如果检测到新版本，后台会广播倒计时、保存、备份、停止 Palworld、更新并重新启动。有人在线也会在倒计时结束后强制更新。",
        submitText: "启动后台更新",
        danger: true,
    });
    if (!confirmed) return;

    const button = $("#applyUpdateBtn");
    if (button) button.classList.add("is-busy");
    openProgressDialog("Palworld 后台更新", ["检测版本", "通知玩家", "保存世界", "备份存档", "停止服务", "SteamCMD 更新", "修复权限", "启动服务", "完成"], "更新会在 systemd 后台执行，面板会持续读取进度。");
    try {
        const data = await api("/api/update/apply", { method: "POST" });
        renderUpdateStatus(data.status || {});
        showToast(data.message || "后台更新已启动", "success");
        pollUpdateProgress();
    } catch (error) {
        finishProgressDialog(error.message, "error");
        setMessage($("#updateMsg"), error.message, "error");
        showToast(error.message, "error");
    } finally {
        if (button) button.classList.remove("is-busy");
    }
}

async function pollUpdateProgress() {
    const map = ["detect", "notify", "save", "backup", "stop", "update", "permissions", "start", "complete"];
    for (let attempt = 0; attempt < 240; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 3000));
        await loadUpdateStatus(false);
        const status = state.updateStatus || {};
        const steps = Array.isArray(status.steps) ? status.steps : [];
        steps.forEach((step) => {
            const index = map.indexOf(step.name);
            if (index >= 0) {
                setProgressStep(index, step.status === "done" ? "done" : step.status === "error" ? "error" : "active", step.message || "");
            }
        });
        if (!status.running && status.phase !== "running" && status.phase !== "checking") {
            if (status.success === false) {
                finishProgressDialog(status.message || "更新失败", "error");
            } else {
                setProgressStep(8, "done", status.message || "更新完成");
                finishProgressDialog(status.message || "更新完成", "success");
            }
            await refreshAll();
            return;
        }
    }
    finishProgressDialog("更新仍在后台运行，请稍后查看更新日志", "warn");
}

const installStepLabels = {
    environment: "环境检查",
    user: "运行用户",
    dependencies: "系统依赖",
    steamcmd: "SteamCMD",
    panel: "面板目录",
    palworld: "下载 Palworld",
    config: "生成配置",
    systemd: "安装服务",
    permissions: "修复权限",
    complete: "完成",
    failed: "失败",
};

const installCheckLabels = {
    docker_backend: "Docker 模式",
    os_supported: "Ubuntu/Debian",
    apt_get: "apt",
    systemd: "systemd",
    python3: "Python 3",
    curl: "curl",
    tar: "tar",
    steamcmd_installed: "SteamCMD",
    palworld_installed: "Palworld",
    palworld_manifest: "Steam Manifest",
    panel_installed: "面板文件",
    env_file: "环境变量",
    container_running: "Palworld 容器",
    palworld_service_active: "游戏服务",
    panel_service_active: "面板服务",
};

function boolText(value, yes = "已就绪", no = "未就绪") {
    return value ? yes : no;
}

function renderInstallStatus(status = {}) {
    state.installStatus = status;
    const checks = status.checks || {};
    const dockerMode = status.backend === "docker";
    const running = Boolean(status.running || status.service_active);

    $("#installPalworldDir").textContent = status.palworld_dir || "-";
    $("#installPalworldState").textContent = boolText(checks.palworld_installed, "已安装", "未安装");
    $("#installSteamcmdState").textContent = boolText(checks.steamcmd_installed, "已安装", "未安装");
    $("#installSteamcmdPath").textContent = status.steamcmd || "-";
    $("#installSystemState").textContent = dockerMode ? "Docker Compose" : checks.os_supported === false ? "系统不支持" : boolText(checks.systemd && checks.apt_get, "环境正常", "待检查");
    $("#installUserState").textContent = dockerMode ? "容器部署 · 无需 systemd 修复" : `用户 ${status.panel_user || "-"} · ${checks.python3 ? "Python 已就绪" : "Python 待检查"}`;
    $("#installServiceState").textContent = dockerMode ? boolText(checks.container_running, "容器运行中", "容器未运行") : running ? "任务运行中" : "空闲";
    $("#installPanelState").textContent = dockerMode ? "面板容器已加载" : boolText(checks.panel_installed, "面板已安装", "面板待安装");

    const checkWrap = $("#installChecks");
    if (checkWrap) {
        const entries = Object.entries(installCheckLabels);
        checkWrap.replaceChildren(...entries.map(([key, label]) => {
            const item = document.createElement("span");
            const value = checks[key];
            item.className = `install-check ${value ? "is-ok" : value === false ? "is-missing" : "is-unknown"}`;
            item.textContent = `${label}: ${value === undefined ? "待检查" : value ? "正常" : "缺失"}`;
            return item;
        }));
    }

    const stepWrap = $("#installSteps");
    if (stepWrap) {
        const steps = Array.isArray(status.steps) ? status.steps : [];
        const visibleSteps = steps.length ? steps : [{ name: "environment", status: "idle", message: status.message || "等待检查或安装" }];
        stepWrap.replaceChildren(...visibleSteps.map((step) => {
            const item = document.createElement("div");
            item.className = `update-step install-step is-${step.status || "idle"}`;
            const dot = document.createElement("span");
            dot.className = "progress-dot";
            const text = document.createElement("div");
            const title = document.createElement("b");
            title.textContent = installStepLabels[step.name] || step.name || "步骤";
            const msg = document.createElement("small");
            msg.textContent = step.message || step.status || "-";
            text.append(title, msg);
            item.append(dot, text);
            return item;
        }));
    }

    const log = $("#installLog");
    if (log) {
        const lines = Array.isArray(status.log_tail) ? status.log_tail : [];
        log.textContent = lines.length ? lines.join("\n") : "等待安装日志...";
        log.scrollTop = log.scrollHeight;
    }

    const checkButton = $("#checkInstallBtn");
    const installButton = $("#installPalworldBtn");
    const repairButton = $("#repairInstallBtn");
    if (checkButton) checkButton.disabled = running;
    if (installButton) {
        const installed = Boolean(checks.palworld_installed);
        installButton.disabled = dockerMode || running || installed;
        installButton.textContent = dockerMode ? "Docker 已接管" : running ? "安装中..." : installed ? "Palworld 已安装" : "安装 Palworld";
        installButton.title = dockerMode ? "Docker 模式由 docker compose 和容器 entrypoint 完成安装" : installed ? "检测到已有 Palworld，不会重复安装；如需修复请点修复安装" : "下载并安装 Palworld Dedicated Server";
    }
    if (repairButton) {
        repairButton.disabled = dockerMode || running;
        repairButton.textContent = dockerMode ? "无需修复" : "修复安装";
    }

    const type = status.success === false ? "error" : running ? "" : status.success ? "success" : "info";
    setMessage($("#installMsg"), status.message || "安装状态已刷新", type);
}

async function loadInstallStatus(showLoading = true) {
    if (state.installLoading) return;
    state.installLoading = true;
    if (showLoading) setMessage($("#installMsg"), "正在读取安装状态...");
    try {
        const data = await api("/api/install/status");
        renderInstallStatus(data.status || {});
    } catch (error) {
        setMessage($("#installMsg"), error.message, "error");
        showToast(error.message, "error");
    } finally {
        state.installLoading = false;
    }
}

async function checkInstallNow() {
    const button = $("#checkInstallBtn");
    if (button) button.classList.add("is-busy");
    setMessage($("#installMsg"), "正在检查系统环境和安装状态...");
    try {
        const data = await api("/api/install/check", { method: "POST" });
        renderInstallStatus(data.status || {});
        showToast(data.message || "环境检查完成", data.success ? "success" : "error");
    } catch (error) {
        setMessage($("#installMsg"), error.message, "error");
        showToast(error.message, "error");
        await loadInstallStatus(false);
    } finally {
        if (button) button.classList.remove("is-busy");
    }
}

async function startInstallAction(action) {
    const isRepair = action === "repair";
    const installed = Boolean(state.installStatus?.checks?.palworld_installed);
    if (!isRepair && installed) {
        showToast("检测到已有 Palworld，请使用修复安装。", "info");
        return;
    }

    const confirmed = await openDialog({
        eyebrow: "Installer",
        title: isRepair ? "确认修复安装" : "确认安装 Palworld 服务器",
        text: isRepair
            ? "修复会重新写入 systemd、sudoers、环境变量并修复权限，不会覆盖现有存档。"
            : "安装会下载 SteamCMD 和 Palworld Dedicated Server，生成配置、systemd 服务和面板环境变量。已有存档不会被覆盖。",
        submitText: isRepair ? "开始修复" : "开始安装",
        danger: false,
    });
    if (!confirmed) return;

    const button = isRepair ? $("#repairInstallBtn") : $("#installPalworldBtn");
    if (button) button.classList.add("is-busy");
    openProgressDialog(
        isRepair ? "修复安装" : "安装 Palworld",
        ["环境检查", "运行用户", "系统依赖", "SteamCMD", "下载 Palworld", "生成配置", "安装服务", "完成"],
        isRepair ? "后台会修复服务、权限和配置，不会触碰存档内容。" : "安装过程由 systemd 后台执行，下载可能需要较久。"
    );
    try {
        const endpoint = isRepair ? "/api/install/repair" : "/api/install/palworld";
        const data = await api(endpoint, { method: "POST" });
        renderInstallStatus(data.status || {});
        showToast(data.message || (isRepair ? "修复任务已启动" : "安装任务已启动"), "success");
        pollInstallProgress();
    } catch (error) {
        finishProgressDialog(error.message, "error");
        setMessage($("#installMsg"), error.message, "error");
        showToast(error.message, "error");
        await loadInstallStatus(false);
    } finally {
        if (button) button.classList.remove("is-busy");
    }
}

async function pollInstallProgress() {
    const map = ["environment", "user", "dependencies", "steamcmd", "palworld", "config", "systemd", "complete"];
    for (let attempt = 0; attempt < 240; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 3000));
        await loadInstallStatus(false);
        const status = state.installStatus || {};
        const steps = Array.isArray(status.steps) ? status.steps : [];
        steps.forEach((step) => {
            const mappedName = step.name === "panel" ? "user" : step.name;
            const index = map.indexOf(mappedName);
            if (index >= 0) {
                setProgressStep(index, step.status === "done" ? "done" : step.status === "error" ? "error" : "active", step.message || "");
            }
        });
        if (!status.running && !status.service_active && status.phase !== "installing" && status.phase !== "repair") {
            if (status.success === false) {
                finishProgressDialog(status.message || "安装任务失败", "error");
            } else {
                setProgressStep(7, "done", status.message || "安装任务完成");
                finishProgressDialog(status.message || "安装任务完成", "success");
            }
            await refreshAll();
            return;
        }
    }
    finishProgressDialog("安装任务仍在后台运行，请稍后查看安装日志", "warn");
}

function toggleLogAutoRefresh() {
    state.logAutoRefresh = !state.logAutoRefresh;
    $("#logAutoBtn").textContent = state.logAutoRefresh ? "自动刷新：开" : "自动刷新：关";
    $("#logAutoBtn").classList.toggle("is-on", state.logAutoRefresh);
}

function renderConfigForm() {
    const container = $("#configSections");
    container.replaceChildren(...configGroups.map((group) => {
        const section = document.createElement("section");
        section.className = "config-group";

        const title = document.createElement("h3");
        title.className = "config-title";
        const icon = document.createElement("span");
        icon.className = "config-icon";
        icon.textContent = group.icon || "•";
        const text = document.createElement("span");
        text.textContent = group.title;
        title.append(icon, text);
        section.appendChild(title);

        const grid = document.createElement("div");
        grid.className = "form-grid";
        group.fields.forEach((field) => grid.appendChild(createField(field)));
        section.appendChild(grid);
        return section;
    }));
}

function createField([key, label, type, meta]) {
    const wrapper = document.createElement("div");
    wrapper.className = "field";

    const labelEl = document.createElement("label");
    labelEl.htmlFor = `cfg_${key}`;
    labelEl.textContent = label;
    wrapper.appendChild(labelEl);

    let input;
    if (type === "bool") {
        input = document.createElement("select");
        [["True", "开启"], ["False", "关闭"]].forEach(([value, text]) => {
            const option = document.createElement("option");
            option.value = value;
            option.textContent = text;
            input.appendChild(option);
        });
    } else if (type === "select") {
        input = document.createElement("select");
        meta.forEach(([value, text]) => {
            const option = document.createElement("option");
            option.value = value;
            option.textContent = text;
            input.appendChild(option);
        });
    } else {
        input = document.createElement("input");
        input.type = type;
        if (typeof meta === "string") input.step = meta;
        if (meta && typeof meta === "object") {
            if (meta.step) input.step = meta.step;
            if (meta.min !== undefined) input.min = meta.min;
            if (meta.max !== undefined) input.max = meta.max;
        }
    }

    input.id = `cfg_${key}`;
    input.dataset.key = key;
    wrapper.appendChild(input);

    if (meta && typeof meta === "object" && meta.hint) {
        const hint = document.createElement("p");
        hint.className = "field-hint";
        if (meta.hint.includes("性能压力") || key.includes("Port")) hint.classList.add("is-warning");
        if (key.includes("Password")) hint.classList.add("is-danger");
        hint.textContent = meta.hint;
        wrapper.appendChild(hint);
    }
    return wrapper;
}

async function loadConfig() {
    try {
        const data = await api("/api/config");
        const settings = { ...configDefaults, ...(data.settings || {}) };
        state.currentConfig = {};
        $$("[data-key]").forEach((input) => {
            const value = settings[input.dataset.key];
            input.value = stripQuotes(value);
            state.currentConfig[input.dataset.key] = normalizeSubmitValue(input.dataset.key, value);
        });
    } catch (error) {
        setMessage($("#configMsg"), `读取配置失败：${error.message}`, "error");
    }
}

function collectConfig() {
    const config = {};
    $$("[data-key]").forEach((input) => {
        const key = input.dataset.key;
        config[key] = normalizeSubmitValue(key, input.value);
    });
    return config;
}

function getFieldLabel(key) {
    const input = $$("[data-key]").find((field) => field.dataset.key === key);
    return input?.closest(".field")?.querySelector("label")?.textContent || key;
}

function formatDiffValue(key, value) {
    const text = stringFields.has(key) ? stripQuotes(value) : String(value ?? "");
    return text === "" ? "空" : text;
}

function getConfigDiff(nextConfig) {
    return Object.keys(nextConfig)
        .filter((key) => String(state.currentConfig[key] ?? "") !== String(nextConfig[key] ?? ""))
        .sort((a, b) => getFieldLabel(a).localeCompare(getFieldLabel(b), "zh-CN"))
        .map((key) => ({
            key,
            label: getFieldLabel(key),
            oldValue: formatDiffValue(key, state.currentConfig[key]),
            newValue: formatDiffValue(key, nextConfig[key]),
        }));
}

function showConfigDiffConfirm(diffs, restart) {
    const modal = $("#configConfirmModal");
    const list = $("#configDiffList");
    $("#configConfirmTitle").textContent = restart ? "确认保存并重启" : "确认保存配置";
    $("#configConfirmText").textContent = restart
        ? "这些改动会保存到配置文件，并立即重启 Palworld 服务器。"
        : "这些改动会保存到配置文件，重启 Palworld 后生效。";
    $("#configConfirmSubmit").textContent = restart ? "确认保存并重启" : "确认保存";

    list.replaceChildren(...diffs.map((diff) => {
        const item = document.createElement("div");
        item.className = "diff-item";

        const label = document.createElement("span");
        label.className = "diff-label";
        label.textContent = diff.label;
        item.appendChild(label);

        const values = document.createElement("div");
        values.className = "diff-values";
        [diff.oldValue, "→", diff.newValue].forEach((value, index) => {
            const node = document.createElement("span");
            node.className = index === 1 ? "diff-arrow" : "diff-value";
            node.textContent = value;
            values.appendChild(node);
        });
        item.appendChild(values);
        return item;
    }));

    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");

    return new Promise((resolve) => {
        state.configConfirmResolve = resolve;
    });
}

function closeConfigDiffConfirm(result) {
    const modal = $("#configConfirmModal");
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    if (state.configConfirmResolve) {
        state.configConfirmResolve(result);
        state.configConfirmResolve = null;
    }
}

function validateConfig() {
    const errors = [];
    $$("[data-key]").forEach((input) => {
        if (input.type !== "number" || input.value.trim() === "") return;
        const value = Number(input.value);
        const min = input.min === "" ? null : Number(input.min);
        const max = input.max === "" ? null : Number(input.max);
        const label = input.closest(".field")?.querySelector("label")?.textContent || input.dataset.key;

        if (Number.isNaN(value)) {
            errors.push(`${label} 必须是数字`);
        } else if (min !== null && value < min) {
            errors.push(`${label} 不能低于 ${min}`);
        } else if (max !== null && value > max) {
            errors.push(`${label} 不能高于 ${max}`);
        }
    });
    return errors;
}

async function saveConfig(restart) {
    const saveButton = $("#saveConfigBtn");
    const restartButton = $("#saveRestartBtn");
    const configPanel = $("#tab-config .panel");
    const originalSaveText = saveButton.textContent;
    const originalRestartText = restartButton.textContent;

    saveButton.disabled = true;
    restartButton.disabled = true;
    const busyButton = restart ? restartButton : saveButton;
    busyButton.classList.add("is-busy");
    if (restart) restartButton.textContent = "保存并重启中...";
    else saveButton.textContent = "保存中...";

    const validationErrors = validateConfig();
    if (validationErrors.length) {
        setMessage($("#configMsg"), validationErrors.slice(0, 3).join("；"), "error");
        showToast("配置校验未通过", "error");
        saveButton.disabled = false;
        restartButton.disabled = false;
        busyButton.classList.remove("is-busy");
        saveButton.textContent = originalSaveText;
        restartButton.textContent = originalRestartText;
        return;
    }

    const config = collectConfig();
    const diffs = getConfigDiff(config);
    if (!diffs.length) {
        setMessage($("#configMsg"), "没有配置改动，不需要保存。");
        showToast("没有配置改动", "info");
        saveButton.disabled = false;
        restartButton.disabled = false;
        busyButton.classList.remove("is-busy");
        saveButton.textContent = originalSaveText;
        restartButton.textContent = originalRestartText;
        return;
    }

    const confirmed = await showConfigDiffConfirm(diffs, restart);
    if (!confirmed) {
        setMessage($("#configMsg"), "已取消保存，配置没有变化。");
        showToast("已取消保存", "info");
        saveButton.disabled = false;
        restartButton.disabled = false;
        busyButton.classList.remove("is-busy");
        saveButton.textContent = originalSaveText;
        restartButton.textContent = originalRestartText;
        return;
    }

    if (restart) {
        openProgressDialog("保存并重启", ["保存配置", "发送重启", "等待服务恢复", "刷新状态"], "配置会先写入文件，然后重启 Palworld 服务。");
        setProgressStep(0, "active", "正在保存配置...");
    }

    setMessage($("#configMsg"), restart ? "正在保存配置，并向服务器发送重启指令..." : "正在保存配置...");
    if (configPanel) configPanel.classList.add("is-working");
    try {
        const data = await api(restart ? "/api/config/apply_restart" : "/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(config),
        });
        if (!data.success) {
            setMessage($("#configMsg"), data.message || "保存失败", "error");
            showToast(data.message || "保存失败", "error");
            if (restart) {
                setProgressStep(0, "error", data.message || "保存失败");
                finishProgressDialog(data.message || "保存失败", "error");
            }
            return;
        }

        if (restart) {
            setProgressStep(0, "done", "配置已保存");
            setProgressStep(1, "done", "重启指令已发送");
            setProgressStep(2, "active", "正在等待服务恢复...");
            restartButton.textContent = "等待服务器恢复...";
            setMessage($("#configMsg"), "配置已保存，服务器正在重启；正在等待状态恢复...");
            state.currentConfig = { ...config };
            const restored = await waitForServerAfterRestart(true);
            if (restored) {
                setProgressStep(2, "done", "服务已恢复");
                setProgressStep(3, "done", "状态已刷新");
                finishProgressDialog("保存并重启完成，服务器已恢复运行。");
            }
        } else {
            state.currentConfig = { ...config };
            setMessage($("#configMsg"), "配置已保存。重启 Palworld 后配置才会生效。", "success");
            showToast("配置已保存", "success");
        }
    } catch (error) {
        setMessage($("#configMsg"), error.message, "error");
        showToast(error.message, "error");
        if (restart) {
            setProgressStep(2, "error", error.message);
            finishProgressDialog(error.message, "error");
        }
    } finally {
        saveButton.disabled = false;
        restartButton.disabled = false;
        busyButton.classList.remove("is-busy");
        if (configPanel) configPanel.classList.remove("is-working");
        saveButton.textContent = originalSaveText;
        restartButton.textContent = originalRestartText;
    }
}

async function waitForServerAfterRestart(updateProgress = false) {
    const startedAt = Date.now();
    const timeoutMs = 90000;
    let attempt = 0;

    while (Date.now() - startedAt < timeoutMs) {
        attempt += 1;
        await new Promise((resolve) => setTimeout(resolve, attempt < 3 ? 3000 : 5000));

        try {
            const data = await api("/api/status");
            renderStatus(data);
            if (data.status && data.status.running) {
                setMessage($("#configMsg"), "配置已保存，服务器重启完成并已恢复运行。", "success");
                showToast("服务器已恢复运行", "success");
                if (updateProgress) setProgressStep(3, "active", "正在刷新最终状态...");
                return true;
            }
            setMessage($("#configMsg"), "配置已保存，服务器仍在重启中...");
            if (updateProgress) setProgressStep(2, "active", `等待恢复中，第 ${attempt} 次检查`);
        } catch (error) {
            setMessage($("#configMsg"), `配置已保存，正在等待服务器恢复连接：${error.message}`);
            if (updateProgress) setProgressStep(2, "active", `等待连接恢复：${error.message}`);
        }
    }

    setMessage($("#configMsg"), "配置已保存，但 90 秒内没有确认服务器恢复。请查看实时日志或稍后刷新状态。", "error");
    showToast("未确认服务器恢复，请查看日志", "warn");
    if (updateProgress) {
        setProgressStep(2, "error", "90 秒内未确认恢复");
        finishProgressDialog("配置已保存，但未确认服务器恢复。请查看日志。", "error");
    }
    return false;
}

async function loadSaves(showLoading = true) {
    if (state.saveLoading) return;
    state.saveLoading = true;
    const msg = $("#saveMsg");
    if (showLoading) setMessage(msg, "正在读取存档信息...");
    try {
        const [statusData, slotsData] = await Promise.all([
            api("/api/saves/status"),
            api("/api/saves/slots"),
        ]);
        state.saveStatus = statusData;
        state.saveSlots = slotsData.slots || [];
        renderSaveStatus();
        renderSaveSlots();
        if (showLoading) setMessage(msg, "存档信息已刷新。", "success");
    } catch (error) {
        setMessage(msg, error.message, "error");
        showToast(error.message, "error");
    } finally {
        state.saveLoading = false;
    }
}

function setSaveControlsBusy(isBusy) {
    state.saveBusy = isBusy;
    const savePanel = $("#tab-saves .panel");
    if (savePanel) savePanel.classList.toggle("is-working", isBusy);
    [
        "#refreshSavesBtn",
        "#backupCurrentSaveBtn",
        "#createSaveSlotBtn",
        "#importSaveSlotBtn",
        "#uploadSaveSlotBtn",
    ].forEach((selector) => {
        const button = $(selector);
        if (!button) return;
        button.disabled = isBusy;
        button.classList.toggle("is-busy", isBusy);
    });
    $$("#saveSlotList button").forEach((button) => {
        button.disabled = isBusy || button.dataset.locked === "true";
        button.classList.toggle("is-busy", isBusy);
    });
}

function createSaveMeta(label, value) {
    const item = document.createElement("span");
    const key = document.createElement("b");
    key.textContent = label;
    const text = document.createElement("span");
    text.textContent = value;
    item.append(key, text);
    return item;
}

function renderSaveStatus() {
    const card = $("#activeSaveCard");
    if (!card) return;
    const active = state.saveStatus?.active || {};
    const service = state.saveStatus?.service || {};

    const title = document.createElement("div");
    const eyebrow = document.createElement("p");
    eyebrow.className = "eyebrow";
    eyebrow.textContent = "Active World";
    const name = document.createElement("h3");
    name.textContent = active.world_id || "未检测到当前世界 ID";
    const desc = document.createElement("p");
    desc.className = "muted";
    desc.textContent = active.path || "当前 SaveGames 目录暂无可识别存档";
    title.append(eyebrow, name, desc);

    const badge = document.createElement("span");
    badge.className = `status-pill ${service.running ? "is-online" : "is-offline"}`;
    badge.textContent = service.running ? "服务器运行中" : "服务器已停止";

    const meta = document.createElement("div");
    meta.className = "save-slot-meta";
    meta.append(
        createSaveMeta("大小", formatBytes(active.size_bytes)),
        createSaveMeta("更新时间", formatOptional(active.updated_at)),
        createSaveMeta("存档根目录", formatOptional(active.savegames_root))
    );

    card.replaceChildren(title, badge, meta);
}

function renderSaveSlots() {
    const list = $("#saveSlotList");
    if (!list) return;
    const slots = state.saveSlots || [];
    if (!slots.length) {
        const empty = document.createElement("div");
        empty.className = "empty save-empty";
        empty.textContent = "还没有存档槽。可以先创建新档，或把外部存档放到导入目录后导入。";
        list.replaceChildren(empty);
        return;
    }

    list.replaceChildren(...slots.map((slot) => {
        const card = document.createElement("article");
        card.className = `save-slot-card ${slot.is_active ? "is-active" : ""}`.trim();

        const header = document.createElement("div");
        header.className = "save-slot-head";
        const heading = document.createElement("div");
        const title = document.createElement("h3");
        title.textContent = slot.name || slot.id;
        const subtitle = document.createElement("p");
        subtitle.className = "muted";
        subtitle.textContent = slot.is_new ? "新世界槽，切换后由 Palworld 自动生成世界文件" : `World ID: ${slot.world_id || "-"}`;
        heading.append(title, subtitle);

        const badge = document.createElement("span");
        badge.className = `soft-pill ${slot.is_active ? "is-success" : ""}`.trim();
        badge.textContent = slot.is_active
            ? "当前使用"
            : (slot.is_same_world_copy ? "同世界副本" : (slot.source === "imported" ? "导入" : "备用"));
        header.append(heading, badge);

        const meta = document.createElement("div");
        meta.className = "save-slot-meta";
        meta.append(
            createSaveMeta("槽 ID", slot.id),
            createSaveMeta("大小", formatBytes(slot.size_bytes)),
            createSaveMeta("更新时间", formatOptional(slot.updated_at)),
            createSaveMeta("最近使用", formatOptional(slot.last_used_at, "未使用"))
        );

        const notes = document.createElement("p");
        notes.className = "save-notes";
        notes.textContent = slot.notes || "无备注";

        const actions = document.createElement("div");
        actions.className = "save-slot-actions";
        const switchButton = document.createElement("button");
        switchButton.className = "primary";
        switchButton.type = "button";
        switchButton.textContent = slot.is_active ? "当前存档" : "切换并启动";
        switchButton.disabled = slot.is_active;
        switchButton.dataset.locked = slot.is_active ? "true" : "false";
        switchButton.addEventListener("click", () => switchSaveSlot(slot.id, slot.name || slot.id));

        const deleteButton = document.createElement("button");
        deleteButton.className = "secondary danger-soft";
        deleteButton.type = "button";
        deleteButton.textContent = "删除";
        deleteButton.disabled = slot.is_active;
        deleteButton.dataset.locked = slot.is_active ? "true" : "false";
        deleteButton.addEventListener("click", () => deleteSaveSlot(slot.id, slot.name || slot.id));
        actions.append(switchButton, deleteButton);

        card.append(header, meta, notes, actions);
        return card;
    }));
}

async function backupCurrentSave() {
    if (state.saveBusy) return;
    const confirmed = await openDialog({
        eyebrow: "Save Backup",
        title: "确认备份当前存档",
        text: "手动备份要求 Palworld 服务已停止。请确认当前状态适合备份。",
        submitText: "开始备份",
    });
    if (!confirmed) return;
    setSaveControlsBusy(true);
    setMessage($("#saveMsg"), "正在备份当前存档...");
    try {
        const data = await api("/api/saves/backup_current", { method: "POST" });
        setMessage($("#saveMsg"), data.message || "当前存档已备份。", "success");
        showToast(data.message || "当前存档已备份", "success");
        await loadSaves(false);
    } catch (error) {
        setMessage($("#saveMsg"), error.message, "error");
        showToast(error.message, "error");
    } finally {
        setSaveControlsBusy(false);
    }
}

async function createSaveSlot() {
    if (state.saveBusy) return;
    const values = await openDialog({
        eyebrow: "New Save",
        title: "创建新存档槽",
        text: "切换到新存档槽后，Palworld 会自动生成新世界文件。",
        submitText: "创建存档",
        fields: [
            { name: "name", label: "存档名称", required: true, placeholder: "例如：新世界测试档" },
            { name: "notes", label: "备注", type: "textarea", placeholder: "可留空" },
        ],
    });
    if (!values) return;
    const name = values.name;
    const notes = values.notes || "";
    setSaveControlsBusy(true);
    setMessage($("#saveMsg"), "正在创建新存档槽...");
    try {
        const data = await api("/api/saves/create_slot", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: name.trim(), notes }),
        });
        setMessage($("#saveMsg"), data.message || "新存档槽已创建。", "success");
        showToast(data.message || "新存档槽已创建", "success");
        await loadSaves(false);
    } catch (error) {
        setMessage($("#saveMsg"), error.message, "error");
        showToast(error.message, "error");
    } finally {
        setSaveControlsBusy(false);
    }
}

async function importSaveSlot() {
    if (state.saveBusy) return;
    const hint = state.saveStatus?.import_hint || "/home/demo/palworld-panel/save-slots/imports";
    const values = await openDialog({
        eyebrow: "Import Save",
        title: "从服务器路径导入存档",
        text: "请输入服务器上的存档目录路径。建议先把外部存档放到导入目录。",
        submitText: "开始导入",
        fields: [
            { name: "sourcePath", label: "服务器存档路径", required: true, value: hint, hint: "可以是世界目录、SaveGames/0 目录或包含 SaveGames 的目录。" },
            { name: "name", label: "导入后的存档名称", required: true, placeholder: "例如：朋友发来的世界档" },
            { name: "notes", label: "备注", type: "textarea", placeholder: "可留空" },
        ],
    });
    if (!values) return;
    const sourcePath = values.sourcePath;
    const name = values.name;
    const notes = values.notes || "";
    setSaveControlsBusy(true);
    setMessage($("#saveMsg"), "正在导入存档...");
    try {
        const data = await api("/api/saves/import_slot", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source_path: sourcePath.trim(), name: name.trim(), notes }),
        });
        setMessage($("#saveMsg"), data.message || "存档已导入。", "success");
        showToast(data.message || "存档已导入", "success");
        await loadSaves(false);
    } catch (error) {
        setMessage($("#saveMsg"), error.message, "error");
        showToast(error.message, "error");
    } finally {
        setSaveControlsBusy(false);
    }
}

async function uploadSaveSlot() {
    if (state.saveBusy) return;
    const input = $("#saveUploadInput");
    const file = input?.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".zip")) {
        setMessage($("#saveMsg"), "请上传 .zip 格式的存档包。", "error");
        showToast("只支持 .zip 存档包", "error");
        input.value = "";
        return;
    }

    const defaultName = file.name.replace(/\.zip$/i, "");
    const values = await openDialog({
        eyebrow: "Upload Save",
        title: "上传并导入存档",
        text: `已选择：${file.name}`,
        submitText: "上传导入",
        fields: [
            { name: "name", label: "导入后的存档名称", required: true, value: defaultName },
            { name: "notes", label: "备注", type: "textarea", placeholder: "可留空" },
        ],
    });
    if (!values) {
        input.value = "";
        return;
    }
    const name = values.name;
    const notes = values.notes || "";
    const formData = new FormData();
    formData.append("file", file);
    formData.append("name", name.trim());
    formData.append("notes", notes);

    setSaveControlsBusy(true);
    openProgressDialog("上传并导入存档", ["选择文件", "上传 ZIP", "解压导入", "刷新列表"], "大存档可能需要一些时间，请保持页面打开。");
    setProgressStep(0, "done", file.name);
    setProgressStep(1, "active", "正在上传...");
    setMessage($("#saveMsg"), `正在上传并导入 ${file.name}，大存档可能需要一些时间...`);
    showToast("开始上传存档", "info");
    try {
        const data = await api("/api/saves/upload_slot", {
            method: "POST",
            body: formData,
        });
        setProgressStep(1, "done", "上传完成");
        setProgressStep(2, "done", "解压并导入完成");
        setProgressStep(3, "active", "正在刷新列表...");
        setMessage($("#saveMsg"), data.message || "存档上传并导入完成。", "success");
        showToast(data.message || "存档上传完成", "success");
        await loadSaves(false);
        setProgressStep(3, "done", "列表已刷新");
        finishProgressDialog(data.message || "存档上传并导入完成。");
    } catch (error) {
        setProgressStep(1, "error", error.message);
        finishProgressDialog(error.message, "error");
        setMessage($("#saveMsg"), error.message, "error");
        showToast(error.message, "error");
    } finally {
        input.value = "";
        setSaveControlsBusy(false);
    }
}

function renderSwitchSteps(steps = []) {
    if (!steps.length) return "切换完成。";
    return steps.map((item) => {
        const status = item.success ? "完成" : "失败";
        return `${item.step}: ${status}${item.message ? ` - ${item.message}` : ""}`;
    }).join("\n");
}

async function switchSaveSlot(slotId, name) {
    if (state.saveBusy) return;
    const confirmed = await openDialog({
        eyebrow: "Switch Save",
        title: `切换到“${name}”`,
        text: "流程会自动停止 Palworld、备份当前存档、替换存档、修正权限，然后重新启动服务器。",
        submitText: "切换并启动",
        danger: true,
    });
    if (!confirmed) return;
    setSaveControlsBusy(true);
    openProgressDialog("切换存档", ["停止服务", "备份当前存档", "替换存档", "修复权限", "启动服务", "完成"], `目标存档：${name}`);
    setProgressStep(0, "active", "正在停止 Palworld...");
    setMessage($("#saveMsg"), "正在切换存档：停服、备份、替换、启动中，请等待...");
    showToast("开始切换存档，请等待完成", "info");
    try {
        const data = await api("/api/saves/switch", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ slot_id: slotId }),
        });
        (data.steps || []).forEach((step, index) => {
            setProgressStep(index, step.success ? "done" : "error", step.message || (step.success ? "完成" : "失败"));
        });
        setProgressStep(5, data.success ? "done" : "error", data.message || "切换完成");
        setMessage($("#saveMsg"), `${data.message || "存档切换完成。"}\n${renderSwitchSteps(data.steps)}`, "success");
        showToast(data.message || "存档切换完成", "success");
        await refreshAll();
        await loadSaves(false);
        finishProgressDialog(data.message || "存档切换完成。", data.success ? "success" : "error");
    } catch (error) {
        setProgressStep(0, "error", error.message);
        finishProgressDialog(error.message, "error");
        setMessage($("#saveMsg"), error.message, "error");
        showToast(error.message, "error");
        await loadSaves(false);
    } finally {
        setSaveControlsBusy(false);
    }
}

async function deleteSaveSlot(slotId, name) {
    if (state.saveBusy) return;
    const confirmed = await openDialog({
        eyebrow: "Delete Save",
        title: `删除存档槽“${name}”`,
        text: "此操作不会删除当前正在使用的存档，但会删除该备用槽。删除后无法从面板恢复。",
        submitText: "确认删除",
        danger: true,
    });
    if (!confirmed) return;
    setSaveControlsBusy(true);
    setMessage($("#saveMsg"), "正在删除存档槽...");
    try {
        const data = await api(`/api/saves/slots/${encodeURIComponent(slotId)}`, { method: "DELETE" });
        setMessage($("#saveMsg"), data.message || "存档槽已删除。", "success");
        showToast(data.message || "存档槽已删除", "success");
        await loadSaves(false);
    } catch (error) {
        setMessage($("#saveMsg"), error.message, "error");
        showToast(error.message, "error");
    } finally {
        setSaveControlsBusy(false);
    }
}

function appendConsoleLine(text, className = "") {
    const output = $("#rconOutput");
    if (output.textContent === "等待命令...") output.textContent = "";
    const line = document.createElement("span");
    line.className = `console-line ${className || "response"}`.trim();
    line.textContent = text;
    output.appendChild(line);
    output.scrollTop = output.scrollHeight;
}

async function sendRcon(event) {
    event.preventDefault();
    const input = $("#rconInput");
    const command = input.value.trim();
    if (!command) return;

    appendConsoleLine(`> ${command}`, "command");
    input.value = "";

    try {
        const data = await api("/api/rcon", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ command }),
        });
        appendConsoleLine(data.response || data.message || "OK", data.success ? "response" : "error");
    } catch (error) {
        appendConsoleLine(`Error: ${error.message}`, "error");
        showToast(error.message, "error");
    }
}

function bindEvents() {
    $("#refreshBtn").addEventListener("click", refreshAll);
    $("#loadLogBtn").addEventListener("click", loadLog);
    $("#logAutoBtn").addEventListener("click", toggleLogAutoRefresh);
    $("#refreshSavesBtn").addEventListener("click", () => loadSaves(true));
    $("#backupCurrentSaveBtn").addEventListener("click", backupCurrentSave);
    $("#createSaveSlotBtn").addEventListener("click", createSaveSlot);
    $("#importSaveSlotBtn").addEventListener("click", importSaveSlot);
    $("#uploadSaveSlotBtn").addEventListener("click", () => {
        if (!state.saveBusy) $("#saveUploadInput").click();
    });
    $("#saveUploadInput").addEventListener("change", uploadSaveSlot);
    $("#saveConfigBtn").addEventListener("click", () => saveConfig(false));
    $("#saveRestartBtn").addEventListener("click", () => saveConfig(true));
    $("#checkUpdateBtn").addEventListener("click", checkUpdateNow);
    $("#applyUpdateBtn").addEventListener("click", applyUpdateNow);
    $("#checkInstallBtn").addEventListener("click", checkInstallNow);
    $("#installPalworldBtn").addEventListener("click", () => startInstallAction("install-palworld"));
    $("#repairInstallBtn").addEventListener("click", () => startInstallAction("repair"));
    $("#refreshAuditBtn").addEventListener("click", () => loadAudit(true));
    $$(".audit-filter").forEach((button) => {
        button.addEventListener("click", () => setAuditFilter(button.dataset.auditFilter));
    });
    $("#configConfirmCancel").addEventListener("click", () => closeConfigDiffConfirm(false));
    $("#configConfirmClose").addEventListener("click", () => closeConfigDiffConfirm(false));
    $("#configConfirmSubmit").addEventListener("click", () => closeConfigDiffConfirm(true));
    $("#configConfirmModal").addEventListener("click", (event) => {
        if (event.target.id === "configConfirmModal") closeConfigDiffConfirm(false);
    });
    $("#interactionModal").addEventListener("click", (event) => {
        if (event.target.id === "interactionModal" && !event.currentTarget.classList.contains("is-progress")) closeDialog(null);
    });
    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        if ($("#interactionModal")?.classList.contains("is-open") && !$("#interactionModal")?.classList.contains("is-progress")) {
            closeDialog(null);
        }
    });
    $("#rconForm").addEventListener("submit", sendRcon);
    $$(".tab-button").forEach((button) => {
        button.addEventListener("click", () => switchTab(button.dataset.tab));
    });
    $$("[data-action]").forEach((button) => {
        button.addEventListener("click", () => serverAction(button.dataset.action));
    });
    window.addEventListener("resize", renderSystemCharts);
}

renderConfigForm();
initParticles();
initCursorGlow();
bindEvents();
refreshAll();
setInterval(refreshAll, 10000);
