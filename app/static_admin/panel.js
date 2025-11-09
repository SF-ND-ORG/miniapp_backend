const API_BASE = window.location.origin + "/api/admin";
const TOKEN_KEY = "admin-panel-token";

const tokenForm = document.getElementById("token-form");
const tokenInput = document.getElementById("token");
const loginStatus = document.getElementById("login-status");
const panel = document.getElementById("panel");
const usersTable = document.getElementById("users");
const statusText = document.getElementById("status");
const refreshBtn = document.getElementById("refresh");
const logoutBtn = document.getElementById("logout");
const searchForm = document.getElementById("search-form");
const searchInput = document.getElementById("search");
const configForm = document.getElementById("config-form");
const configStatus = document.getElementById("config-status");
const configAdminOpenids = document.getElementById("config-admin-openids");
const configRateLimitMax = document.getElementById("config-rate-limit-max");
const configRateLimitWindow = document.getElementById("config-rate-limit-window");

let lastQuery = "";

const resolveNumericFieldValue = (raw) => {
    if (typeof raw === "number" && Number.isFinite(raw)) {
        return String(raw);
    }
    if (typeof raw === "string" && raw.trim()) {
        const parsed = Number(raw.trim());
        if (Number.isFinite(parsed)) {
            return String(parsed);
        }
    }
    return "";
};

const setStatus = (message, isError = false) => {
    statusText.textContent = message || "";
    statusText.classList.toggle("panel__status--error", Boolean(message) && isError);
};

const setLoginStatus = (message, isError = false) => {
    loginStatus.textContent = message || "";
    loginStatus.classList.toggle("login-status--error", Boolean(message) && isError);
};

const setConfigStatus = (message, isError = false) => {
    configStatus.textContent = message || "";
    configStatus.classList.toggle("panel__status--error", Boolean(message) && isError);
};

const getStoredToken = () => sessionStorage.getItem(TOKEN_KEY) || "";
const storeToken = (token) => sessionStorage.setItem(TOKEN_KEY, token);
const clearToken = () => sessionStorage.removeItem(TOKEN_KEY);

const resetPanelState = () => {
    lastQuery = "";
    usersTable.innerHTML = "";
    searchInput.value = "";
    setStatus("");
    setConfigStatus("");
    configForm.reset();
    configAdminOpenids.value = "";
    configRateLimitMax.value = "";
    configRateLimitWindow.value = "";
};

const requireToken = () => {
    const token = getStoredToken();
    if (!token) {
        throw new Error("missing token");
    }
    return token;
};

const handleUnauthorized = () => {
    clearToken();
    resetPanelState();
    panel.classList.add("hidden");
    tokenForm.classList.remove("hidden");
    setLoginStatus("访问令牌失效或已过期，请重新登录。", true);
    tokenInput.focus();
};

const renderUsers = (users) => {
    if (!Array.isArray(users) || users.length === 0) {
        usersTable.innerHTML = '<tr><td colspan="6" class="table__empty">未找到匹配的用户。</td></tr>';
        return;
    }

    usersTable.innerHTML = "";
    users.forEach((user) => {
        const tr = document.createElement("tr");
        const adminBadgeClass = user.is_admin ? "badge badge--admin" : "badge badge--user";
        const adminBadgeText = user.is_admin ? "管理员" : "普通用户";

        tr.innerHTML = `
            <td>${user.id}</td>
            <td>${user.name || "-"}</td>
            <td>${user.student_id || "-"}</td>
            <td>${user.wechat_openid ? "已绑定" : "未绑定"}</td>
            <td><span class="${adminBadgeClass}">${adminBadgeText}</span></td>
            <td>
                <button class="table__button ${user.is_admin ? "table__button--revoke" : ""}" data-id="${user.id}" data-admin="${user.is_admin}">
                    ${user.is_admin ? "撤销管理员" : "设为管理员"}
                </button>
            </td>
        `;

        usersTable.appendChild(tr);
    });
};

const fetchUsers = async (query) => {
    const keyword = typeof query === "string" ? query.trim() : searchInput.value.trim();

    if (!keyword) {
        setStatus("请输入搜索关键词。", true);
        usersTable.innerHTML = '';
        return;
    }

    setStatus("搜索中...");

    try {
        const token = requireToken();
        const response = await fetch(`${API_BASE}/users?q=${encodeURIComponent(keyword)}`, {
            headers: {
                "X-Admin-Token": token,
            },
        });

        if (response.status === 401) {
            handleUnauthorized();
            throw new Error("unauthorized");
        }

        if (!response.ok) {
            throw new Error(`加载失败: ${response.status}`);
        }

        const users = await response.json();
        lastQuery = keyword;
        searchInput.value = keyword;
        renderUsers(users);
        setStatus(users.length ? `共 ${users.length} 名匹配用户` : "未找到匹配的用户。", users.length === 0);
    } catch (error) {
        if (error.message === "missing token") {
            setStatus("请先登录后再进行搜索。", true);
            return;
        }
        if (error.message === "unauthorized") {
            return;
        }
        console.error(error);
        setStatus("无法加载用户，请稍后重试。", true);
    }
};

const updateAdmin = async (userId, isAdmin) => {
    try {
        const token = requireToken();
        const response = await fetch(`${API_BASE}/users/${userId}/admin?is_admin=${isAdmin}`, {
            method: "PUT",
            headers: {
                "X-Admin-Token": token,
            },
        });

        if (response.status === 401) {
            handleUnauthorized();
            throw new Error("unauthorized");
        }

        if (!response.ok) {
            throw new Error(`更新失败: ${response.status}`);
        }

        await fetchUsers(lastQuery || searchInput.value);
        setStatus("权限已更新。", false);
    } catch (error) {
        if (error.message === "missing token") {
            setStatus("请登录后再更新权限。", true);
            return;
        }
        if (error.message === "unauthorized") {
            return;
        }
        console.error(error);
        setStatus("更新失败，请重试。", true);
    }
};

const populateConfigForm = (config) => {
    const openids = Array.isArray(config?.admin_openids) ? config.admin_openids : [];
    configAdminOpenids.value = openids.join("\n");

    configRateLimitMax.value = resolveNumericFieldValue(config?.rate_limit_max_requests);
    configRateLimitWindow.value = resolveNumericFieldValue(config?.rate_limit_window_seconds);
};

const loadConfig = async () => {
    setConfigStatus("加载配置中...");
    try {
        const token = requireToken();
        const response = await fetch(`${API_BASE}/config`, {
            headers: {
                "X-Admin-Token": token,
            },
        });

        if (response.status === 401) {
            handleUnauthorized();
            throw new Error("unauthorized");
        }

        if (!response.ok) {
            throw new Error(`加载失败: ${response.status}`);
        }

        const config = await response.json();
        populateConfigForm(config);
        setConfigStatus("配置已加载。", false);
    } catch (error) {
        if (error.message === "missing token") {
            setConfigStatus("请先登录以查看配置。", true);
            return;
        }
        if (error.message === "unauthorized") {
            return;
        }
        console.error(error);
        setConfigStatus("无法加载配置，请稍后重试。", true);
    }
};

const buildConfigPayload = () => {
    const payload = {};

    const openids = configAdminOpenids.value
        .split(/\r?\n/)
        .map((item) => item.trim())
        .filter(Boolean);
    payload.admin_openids = openids.length ? openids : null;

    const maxRequestsStr = configRateLimitMax.value.trim();
    if (maxRequestsStr) {
        const maxRequests = Number(maxRequestsStr);
        if (!Number.isInteger(maxRequests) || maxRequests < 1) {
            throw new Error("速率限制的最大请求数必须为正整数。");
        }
        payload.rate_limit_max_requests = maxRequests;
    } else {
        payload.rate_limit_max_requests = null;
    }

    const windowSecondsStr = configRateLimitWindow.value.trim();
    if (windowSecondsStr) {
        const windowSeconds = Number(windowSecondsStr);
        if (!Number.isInteger(windowSeconds) || windowSeconds < 1) {
            throw new Error("速率限制的窗口长度必须为正整数。");
        }
        payload.rate_limit_window_seconds = windowSeconds;
    } else {
        payload.rate_limit_window_seconds = null;
    }

    return payload;
};

const saveConfig = async () => {
    try {
        const payload = buildConfigPayload();
        setConfigStatus("保存中...");

        const token = requireToken();
        const response = await fetch(`${API_BASE}/config`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                "X-Admin-Token": token,
            },
            body: JSON.stringify(payload),
        });

        if (response.status === 401) {
            handleUnauthorized();
            throw new Error("unauthorized");
        }

        if (!response.ok) {
            const errorBody = await response.json().catch(() => ({}));
            const message = errorBody?.detail || `保存失败: ${response.status}`;
            throw new Error(message);
        }

        const config = await response.json();
        populateConfigForm(config);
        setConfigStatus("配置已保存。", false);
    } catch (error) {
        if (error.message === "missing token") {
            setConfigStatus("请登录后再保存配置。", true);
            return;
        }
        if (error.message === "unauthorized") {
            return;
        }
        console.error(error);
        setConfigStatus(error.message || "保存失败，请稍后重试。", true);
    }
};

usersTable.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLButtonElement)) {
        return;
    }

    const userId = Number(target.dataset.id);
    const isAdmin = target.dataset.admin === "true";
    if (!Number.isFinite(userId)) {
        setStatus("无法解析用户信息，请刷新后重试。", true);
        return;
    }

    updateAdmin(userId, !isAdmin);
});

searchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    fetchUsers(searchInput.value);
});

refreshBtn.addEventListener("click", () => {
    if (lastQuery) {
        fetchUsers(lastQuery);
        return;
    }
    if (searchInput.value.trim()) {
        fetchUsers(searchInput.value);
        return;
    }
    setStatus("请输入关键词后再刷新。", true);
});

configForm.addEventListener("submit", (event) => {
    event.preventDefault();
    saveConfig();
});

tokenForm.addEventListener("submit", (event) => {
    event.preventDefault();
    setLoginStatus("");
    const token = tokenInput.value.trim();
    if (!token) {
        setLoginStatus("请输入有效的访问密钥。", true);
        return;
    }

    storeToken(token);
    tokenInput.value = "";
    tokenForm.classList.add("hidden");
    panel.classList.remove("hidden");
    setStatus("请输入关键词搜索用户。");
    loadConfig();
    searchInput.focus();
});

logoutBtn.addEventListener("click", () => {
    clearToken();
    resetPanelState();
    panel.classList.add("hidden");
    tokenForm.classList.remove("hidden");
    setLoginStatus("已退出。请重新输入访问密钥以继续。");
    tokenInput.focus();
});

const bootstrap = () => {
    const token = getStoredToken();
    if (!token) {
        return;
    }

    tokenForm.classList.add("hidden");
    panel.classList.remove("hidden");
    setStatus("请输入关键词搜索用户。");
    loadConfig();
    searchInput.focus();
};

bootstrap();
