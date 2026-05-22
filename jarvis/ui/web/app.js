// J.A.R.V.I.S. — клиентский JS

const ui = {
    messages: document.getElementById("messages"),
    chatForm: document.getElementById("chat-form"),
    chatInput: document.getElementById("chat-input"),
    btnClear: document.getElementById("btn-clear"),
    statusPill: document.getElementById("status-pill"),
    voicePill: document.getElementById("voice-pill"),
    memoryList: document.getElementById("memory-list"),
    memoryForm: document.getElementById("memory-form"),
    memoryInput: document.getElementById("memory-input"),
    skillsList: document.getElementById("skills-list"),
    settingsForm: document.getElementById("settings-form"),
    settingsSaved: document.getElementById("settings-saved"),
};

// ---------- Tabs ----------
document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
        document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
        document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));
        tab.classList.add("active");
        document.getElementById("tab-" + tab.dataset.tab).classList.add("active");

        if (tab.dataset.tab === "memory") loadMemory();
        if (tab.dataset.tab === "settings") loadSettings();
        if (tab.dataset.tab === "skills") loadStatus();
    });
});

// ---------- Helpers ----------
function addMessage(kind, text) {
    const div = document.createElement("div");
    div.className = "msg msg-" + kind;
    div.textContent = text;
    ui.messages.appendChild(div);
    ui.messages.scrollTop = ui.messages.scrollHeight;
}

function setStatus(state, text) {
    ui.statusPill.textContent = text;
    ui.statusPill.classList.remove("pill-ok", "pill-warn", "pill-err");
    ui.statusPill.classList.add(
        state === "ok" ? "pill-ok" : state === "warn" ? "pill-warn" : "pill-err"
    );
}

function setVoiceStatus(status, detail) {
    if (!ui.voicePill) return;
    const labels = {
        listening: "🎤 Слушаю",
        hearing: "🎤 Слышу...",
        transcribing: "🎤 Распознаю...",
        wake_word_ready: "🎤 Ожидаю «Джарвис»",
        error: "🎤 Ошибка",
    };
    ui.voicePill.textContent = labels[status] || ("🎤 " + (detail || status));
    ui.voicePill.classList.remove(
        "pill-voice-listen", "pill-voice-hear",
        "pill-voice-think", "pill-voice-err"
    );
    if (status === "listening" || status === "wake_word_ready")
        ui.voicePill.classList.add("pill-voice-listen");
    else if (status === "hearing")
        ui.voicePill.classList.add("pill-voice-hear");
    else if (status === "transcribing")
        ui.voicePill.classList.add("pill-voice-think");
    else if (status === "error")
        ui.voicePill.classList.add("pill-voice-err");
}

// ---------- WebSocket ----------
let ws = null;
let wsReconnectTimer = null;

function connectWS() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws`);

    ws.addEventListener("open", () => {
        setStatus("ok", "онлайн");
        loadStatus();
    });

    ws.addEventListener("message", (e) => {
        let data;
        try { data = JSON.parse(e.data); } catch { return; }

        switch (data.type) {
            case "hello":
                addMessage("system", `Подключён. Скиллов: ${(data.skills || []).length}`);
                break;
            case "user":
            case "user_voice":
                if (data.type === "user_voice") addMessage("system", "🎤 " + data.text);
                else addMessage("user", data.text);
                break;
            case "assistant":
                addMessage("assistant", data.text);
                break;
            case "skill":
                addMessage("skill", `→ ${data.skill}(${JSON.stringify(data.args)})`);
                break;
            case "skill_result":
                addMessage("skill", `${data.skill} → ${data.result}`);
                break;
            case "voice_status":
                setVoiceStatus(data.status, data.detail);
                if (data.status === "error")
                    addMessage("system", "🎤 " + (data.detail || "Ошибка микрофона"));
                break;
            case "wake_word":
                addMessage("system", "🎤 Wake word: «" + data.word + "»");
                break;
            case "error":
                addMessage("system", "Ошибка: " + (data.error || "?"));
                break;
        }
    });

    ws.addEventListener("close", () => {
        setStatus("err", "оффлайн");
        if (wsReconnectTimer) clearTimeout(wsReconnectTimer);
        wsReconnectTimer = setTimeout(connectWS, 2000);
    });

    ws.addEventListener("error", () => {
        setStatus("warn", "ошибка соединения");
    });
}

connectWS();

// ---------- Chat ----------
ui.chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = ui.chatInput.value.trim();
    if (!text) return;
    ui.chatInput.value = "";

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ message: text }));
    } else {
        fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text }),
        }).then((r) => r.json()).then((d) => {
            addMessage("user", text);
            if (d.response) addMessage("assistant", d.response);
        });
    }
});

ui.btnClear.addEventListener("click", async () => {
    if (!confirm("Очистить историю?")) return;
    await fetch("/api/reset", { method: "POST" });
    ui.messages.innerHTML = "";
    addMessage("system", "История очищена");
});

// ---------- Memory ----------
async function loadMemory() {
    const r = await fetch("/api/memory");
    const d = await r.json();
    ui.memoryList.innerHTML = "";
    (d.facts || []).forEach((fact) => {
        const li = document.createElement("li");
        const span = document.createElement("span");
        span.textContent = fact;
        const btn = document.createElement("button");
        btn.textContent = "×";
        btn.title = "Забыть";
        btn.addEventListener("click", async () => {
            await fetch("/api/memory", {
                method: "DELETE",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ fact }),
            });
            loadMemory();
        });
        li.appendChild(span);
        li.appendChild(btn);
        ui.memoryList.appendChild(li);
    });
    if (!d.facts?.length) {
        const li = document.createElement("li");
        li.textContent = "Пока ничего не запомнено. Скажи Джарвису 'запомни …'.";
        li.style.justifyContent = "center";
        li.style.color = "var(--text-dim)";
        ui.memoryList.appendChild(li);
    }
}

ui.memoryForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fact = ui.memoryInput.value.trim();
    if (!fact) return;
    ui.memoryInput.value = "";
    await fetch("/api/memory", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fact }),
    });
    loadMemory();
});

// ---------- Settings ----------
function setFormValues(obj, prefix = "") {
    Object.entries(obj || {}).forEach(([k, v]) => {
        const path = prefix ? `${prefix}.${k}` : k;
        if (v && typeof v === "object" && !Array.isArray(v)) {
            setFormValues(v, path);
            return;
        }
        const el = ui.settingsForm.querySelector(`[name="${path}"]`);
        if (!el) return;
        if (el.type === "checkbox") el.checked = !!v;
        else el.value = v ?? "";
    });
}

function gatherFormValues() {
    const out = {};
    new FormData(ui.settingsForm).forEach((val, key) => {
        const [section, k] = key.split(".");
        out[section] = out[section] || {};
        out[section][k] = val;
    });
    // Checkboxes (FormData skips unchecked)
    ui.settingsForm.querySelectorAll("input[type=checkbox]").forEach((el) => {
        const [section, k] = el.name.split(".");
        out[section] = out[section] || {};
        out[section][k] = el.checked;
    });
    return out;
}

async function loadSettings() {
    const r = await fetch("/api/config");
    const d = await r.json();
    setFormValues(d);
}

ui.settingsForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = gatherFormValues();
    const r = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
    if (r.ok) {
        ui.settingsSaved.classList.remove("hidden");
        setTimeout(() => ui.settingsSaved.classList.add("hidden"), 2000);
    }
});

// ---------- Status / Skills ----------
async function loadStatus() {
    try {
        const r = await fetch("/api/status");
        const d = await r.json();
        ui.skillsList.innerHTML = "";
        (d.skills || []).forEach((s) => {
            const li = document.createElement("li");
            li.innerHTML = `<span>${s}</span><small>активен</small>`;
            ui.skillsList.appendChild(li);
        });
    } catch (e) {
        console.warn(e);
    }
}
