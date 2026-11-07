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

const playerStatus = document.getElementById("player-status");
const playerRefreshBtn = document.getElementById("player-refresh");
const playerAutoplay = document.getElementById("player-autoplay");
const playerArtImg = document.getElementById("player-art-img");
const playerArtPlaceholder = document.getElementById("player-art-placeholder");
const playerTitle = document.getElementById("player-title");
const playerMeta = document.getElementById("player-meta");
const playerTrial = document.getElementById("player-trial");
const playerPosition = document.getElementById("player-position");
const playerToggleBtn = document.getElementById("player-toggle");
const playerPrevBtn = document.getElementById("player-prev");
const playerNextBtn = document.getElementById("player-next");
const playerPlayedBtn = document.getElementById("player-played");
const playerQueueCount = document.getElementById("player-queue-count");
const playerQueueTable = document.getElementById("player-queue");
const audio = document.getElementById("player-audio");

const neteaseStatus = document.getElementById("netease-status");
const neteaseRefreshStatusBtn = document.getElementById("netease-refresh-status");
const neteaseLogoutBtn = document.getElementById("netease-logout");
const neteaseAccount = document.getElementById("netease-account");
const neteaseAvatar = document.getElementById("netease-avatar");
const neteaseNickname = document.getElementById("netease-nickname");
const neteaseAccountMeta = document.getElementById("netease-account-meta");
const neteaseLoginArea = document.getElementById("netease-login-area");
const neteaseTabQrBtn = document.getElementById("netease-tab-qr");
const neteaseTabPhoneBtn = document.getElementById("netease-tab-phone");
const neteasePanelQr = document.getElementById("netease-panel-qr");
const neteasePanelPhone = document.getElementById("netease-panel-phone");
const neteaseQrStartBtn = document.getElementById("netease-qr-start");
const neteaseQrBox = document.getElementById("netease-qr-box");
const neteaseQrImg = document.getElementById("netease-qr-img");
const neteaseQrStatus = document.getElementById("netease-qr-status");
const neteasePhoneForm = document.getElementById("netease-phone-form");
const neteaseCountrycodeInput = document.getElementById("netease-countrycode");
const neteasePhoneInput = document.getElementById("netease-phone");
const neteaseCaptchaInput = document.getElementById("netease-captcha");
const neteaseSendCaptchaBtn = document.getElementById("netease-send-captcha");
const neteasePhoneSubmitBtn = document.getElementById("netease-phone-submit");
const neteasePhoneStatus = document.getElementById("netease-phone-status");

const PLAYER_POLL_INTERVAL_MS = 20000;
const NETEASE_QR_POLL_INTERVAL_MS = 2000;
const NETEASE_CAPTCHA_COOLDOWN_SECONDS = 60;

const playerState = {
    queue: [],
    current: null,
    loading: false,
    pollTimer: null,
    trialEnded: false,
};

const neteaseState = {
    loggedIn: false,
    activeTab: "qr",
    qrKey: "",
    qrPolling: false,
    qrTimer: null,
    qrLoading: false,
    sendCaptchaLoading: false,
    loginLoading: false,
    captchaRemaining: 0,
    captchaTimer: null,
};

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
    resetPlayerState();
    resetNeteaseState();
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

const setPlayerStatus = (message, isError = false) => {
    playerStatus.textContent = message || "";
    playerStatus.classList.toggle("panel__status--error", Boolean(message) && isError);
};

const formatDateTime = (value) => {
    if (!value) {
        return "-";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return "-";
    }
    return date.toLocaleString("zh-CN", { hour12: false });
};

const formatClock = (value) => {
    const seconds = Number(value);
    if (!Number.isFinite(seconds) || seconds < 0) {
        return "";
    }
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${String(secs).padStart(2, "0")}`;
};

const describeTrial = (trial) => {
    if (!trial) {
        return "";
    }
    const start = formatClock(trial.start || 0);
    const end = formatClock(trial.end);
    if (end) {
        return `试听片段 ${start}-${end}`;
    }
    return "试听片段";
};

const renderQueue = () => {
    const queue = playerState.queue;
    playerQueueCount.textContent = String(queue.length);
    playerQueueTable.innerHTML = "";

    if (!queue.length) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = 5;
        td.className = "table__empty";
        td.textContent = "暂无待播放歌曲。";
        tr.appendChild(td);
        playerQueueTable.appendChild(tr);
        return;
    }

    queue.forEach((item, index) => {
        const tr = document.createElement("tr");
        if (playerState.current && playerState.current.requestId === item.id) {
            tr.classList.add("player-queue__row--active");
        }

        const indexCell = document.createElement("td");
        indexCell.textContent = String(index + 1);

        const songCell = document.createElement("td");
        const title = document.createElement("span");
        title.className = "player-queue__song";
        title.textContent = item.title || "未知歌曲";
        const artist = document.createElement("span");
        artist.className = "player-queue__artist";
        artist.textContent = item.artist || "未知艺术家";
        songCell.append(title, artist);

        const requesterCell = document.createElement("td");
        requesterCell.textContent = item.requester_name || "未知用户";

        const timeCell = document.createElement("td");
        timeCell.textContent = formatDateTime(item.created_at);

        const actionCell = document.createElement("td");
        actionCell.className = "player-queue__actions";

        const playBtn = document.createElement("button");
        playBtn.type = "button";
        playBtn.className = "table__button";
        playBtn.dataset.action = "play";
        playBtn.dataset.requestId = String(item.id);
        playBtn.textContent = "播放";

        const playedBtn = document.createElement("button");
        playedBtn.type = "button";
        playedBtn.className = "table__button table__button--success";
        playedBtn.dataset.action = "played";
        playedBtn.dataset.requestId = String(item.id);
        playedBtn.textContent = "标记已播";

        actionCell.append(playBtn, playedBtn);

        tr.append(indexCell, songCell, requesterCell, timeCell, actionCell);
        playerQueueTable.appendChild(tr);
    });
};

const updatePlayerUi = () => {
    const current = playerState.current;
    const queueSize = playerState.queue.length;

    if (current) {
        playerTitle.textContent = current.title || "未知歌曲";
        const metaParts = [];
        if (current.artist) {
            metaParts.push(current.artist);
        }
        metaParts.push(`点歌人：${current.requester || "未知用户"}`);
        playerMeta.textContent = metaParts.join(" · ");

        if (current.cover) {
            playerArtImg.src = current.cover;
            playerArtImg.classList.remove("hidden");
            playerArtPlaceholder.classList.add("hidden");
        } else {
            playerArtImg.removeAttribute("src");
            playerArtImg.classList.add("hidden");
            playerArtPlaceholder.classList.remove("hidden");
        }

        if (current.isTrial) {
            playerTrial.textContent = describeTrial(current.trial);
            playerTrial.classList.remove("hidden");
        } else {
            playerTrial.classList.add("hidden");
        }

        const index = playerState.queue.findIndex((item) => item.id === current.requestId);
        if (index >= 0) {
            playerPosition.textContent = `队列第 ${index + 1} 位`;
            playerPosition.classList.remove("hidden");
        } else {
            playerPosition.classList.add("hidden");
        }
    } else {
        playerTitle.textContent = "暂无播放";
        playerMeta.textContent = queueSize
            ? `队列中有 ${queueSize} 首歌等待播放。`
            : "队列为空，等待同学点歌。";
        playerArtImg.removeAttribute("src");
        playerArtImg.classList.add("hidden");
        playerArtPlaceholder.classList.remove("hidden");
        playerTrial.classList.add("hidden");
        playerPosition.classList.add("hidden");
    }

    playerToggleBtn.textContent = current && !audio.paused ? "暂停" : "播放";
    playerPlayedBtn.disabled = !current;
    playerPrevBtn.disabled = !current && queueSize === 0;
    playerNextBtn.disabled = queueSize === 0;
};

const fetchPlayerQueue = async ({ silent = false } = {}) => {
    if (!getStoredToken()) {
        return;
    }
    if (!silent) {
        setPlayerStatus("正在刷新队列...");
    }

    try {
        const token = requireToken();
        const response = await fetch(`${API_BASE}/player/queue`, {
            headers: {
                "X-Admin-Token": token,
            },
        });

        if (response.status === 401) {
            handleUnauthorized();
            return;
        }

        if (!response.ok) {
            throw new Error(`加载失败: ${response.status}`);
        }

        const data = await response.json();
        playerState.queue = Array.isArray(data.queue) ? data.queue : [];
        renderQueue();
        updatePlayerUi();
        if (!silent) {
            setPlayerStatus(playerState.queue.length
                ? `队列中共 ${playerState.queue.length} 首歌`
                : "队列为空，等待同学点歌。");
        }
    } catch (error) {
        console.error(error);
        if (!silent) {
            setPlayerStatus("无法加载点歌队列，请稍后重试。", true);
        }
    }
};

const stopPlayerPolling = () => {
    if (playerState.pollTimer) {
        clearInterval(playerState.pollTimer);
        playerState.pollTimer = null;
    }
};

const startPlayerPolling = () => {
    stopPlayerPolling();
    playerState.pollTimer = setInterval(() => {
        fetchPlayerQueue({ silent: true });
    }, PLAYER_POLL_INTERVAL_MS);
};

const clearCurrentSong = () => {
    playerState.current = null;
    playerState.trialEnded = false;
    audio.pause();
    audio.removeAttribute("src");
    audio.load();
    updatePlayerUi();
};

const applyTrialStart = () => {
    const current = playerState.current;
    if (!current || !current.trial) {
        return;
    }
    const start = Number(current.trial.start);
    if (Number.isFinite(start) && start > 0 && audio.currentTime < start) {
        try {
            audio.currentTime = start;
        } catch (error) {
            console.warn(error);
        }
    }
};

const playItem = async (item) => {
    if (!item || playerState.loading) {
        return;
    }

    playerState.loading = true;
    playerState.trialEnded = false;
    setPlayerStatus(`正在获取「${item.title || item.song_name || "歌曲"}」的播放地址...`);

    try {
        const token = requireToken();
        const response = await fetch(`${API_BASE}/player/song/${encodeURIComponent(item.song_id)}`, {
            headers: {
                "X-Admin-Token": token,
            },
        });

        if (response.status === 401) {
            handleUnauthorized();
            return;
        }

        if (!response.ok) {
            throw new Error(`获取播放信息失败: ${response.status}`);
        }

        const data = await response.json();
        const playback = data.playback || {};
        if (!playback.url) {
            setPlayerStatus("无法获取播放地址：该歌曲可能受版权限制，或需要登录网易云会员。", true);
            return;
        }

        playerState.current = {
            requestId: item.id,
            songId: item.song_id,
            title: data.song?.name || item.title || "未知歌曲",
            artist: Array.isArray(data.song?.artists)
                ? data.song.artists.join(" / ")
                : (item.artist || ""),
            requester: item.requester_name || "未知用户",
            cover: data.song?.cover || "",
            trial: playback.free_trial_info || null,
            isTrial: Boolean(playback.is_trial),
        };

        updatePlayerUi();
        renderQueue();

        audio.src = playback.url;
        audio.load();

        try {
            await audio.play();
            setPlayerStatus(playerState.current.isTrial
                ? `正在播放试听片段：${playerState.current.title}`
                : `正在播放：${playerState.current.title}`);
        } catch (error) {
            console.warn(error);
            setPlayerStatus("已获取播放地址，请点击播放按钮开始播放。");
        }
    } catch (error) {
        if (error.message === "missing token") {
            setPlayerStatus("请先登录后再使用点歌台。", true);
            return;
        }
        if (error.message === "unauthorized") {
            return;
        }
        console.error(error);
        setPlayerStatus("获取播放地址失败，请稍后重试。", true);
    } finally {
        playerState.loading = false;
    }
};

const togglePlayback = () => {
    if (!playerState.current) {
        const first = playerState.queue[0];
        if (!first) {
            setPlayerStatus("队列为空，暂无可播放的歌曲。", true);
            return;
        }
        playItem(first);
        return;
    }

    if (audio.paused) {
        const trialEnd = Number(playerState.current.trial?.end);
        if (playerState.current.isTrial
            && Number.isFinite(trialEnd)
            && trialEnd > 0
            && audio.currentTime >= trialEnd) {
            setPlayerStatus("试听片段已结束，请点击「下一首」继续播放。", true);
            return;
        }
        audio.play().catch((error) => {
            console.error(error);
            setPlayerStatus("播放失败，请重试。", true);
        });
    } else {
        audio.pause();
    }
};

const playRelative = (offset) => {
    if (!playerState.queue.length) {
        setPlayerStatus("队列为空，暂无可播放的歌曲。", true);
        return;
    }

    let index = -1;
    if (playerState.current) {
        index = playerState.queue.findIndex((item) => item.id === playerState.current.requestId);
    }

    if (index < 0) {
        playItem(playerState.queue[0]);
        return;
    }

    const targetIndex = index + offset;
    if (targetIndex < 0 || targetIndex >= playerState.queue.length) {
        setPlayerStatus(offset > 0 ? "已经是队列最后一首。" : "已经是队列第一首。");
        return;
    }

    playItem(playerState.queue[targetIndex]);
};

const markPlayed = async (item, { autoAdvance = false } = {}) => {
    const target = item || playerState.current;
    if (!target) {
        setPlayerStatus("当前没有可标记的歌曲。", true);
        return;
    }

    const requestId = Number(target.requestId ?? target.id);
    if (!Number.isFinite(requestId)) {
        return;
    }

    const queueIndex = playerState.queue.findIndex((entry) => entry.id === requestId);
    const nextItem = queueIndex >= 0
        ? (playerState.queue[queueIndex + 1] || null)
        : (playerState.queue[0] || null);
    const wasCurrent = Boolean(playerState.current && playerState.current.requestId === requestId);

    try {
        const token = requireToken();
        const response = await fetch(`${API_BASE}/player/played`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Admin-Token": token,
            },
            body: JSON.stringify({ request_id: requestId }),
        });

        if (response.status === 401) {
            handleUnauthorized();
            return;
        }

        if (!response.ok) {
            const errorBody = await response.json().catch(() => ({}));
            throw new Error(errorBody?.detail || `操作失败: ${response.status}`);
        }

        playerState.queue = playerState.queue.filter((entry) => entry.id !== requestId);
        if (wasCurrent) {
            clearCurrentSong();
        }
        renderQueue();
        updatePlayerUi();
        setPlayerStatus("已标记为已播放。");

        if (wasCurrent && autoAdvance && playerAutoplay.checked && nextItem) {
            playItem(nextItem);
        } else {
            fetchPlayerQueue({ silent: true });
        }
    } catch (error) {
        if (error.message === "missing token") {
            setPlayerStatus("请先登录后再操作。", true);
            return;
        }
        console.error(error);
        setPlayerStatus(error.message || "标记失败，请稍后重试。", true);
    }
};

const handleAudioEnded = () => {
    const current = playerState.current;
    if (!current) {
        return;
    }
    if (current.isTrial) {
        playerState.trialEnded = true;
        setPlayerStatus("试听片段已结束，可点击「下一首」继续播放。", true);
        return;
    }
    markPlayed(current, { autoAdvance: true });
};

const resetPlayerState = () => {
    stopPlayerPolling();
    playerState.queue = [];
    playerState.current = null;
    playerState.loading = false;
    playerState.trialEnded = false;
    audio.pause();
    audio.removeAttribute("src");
    audio.load();
    renderQueue();
    updatePlayerUi();
    setPlayerStatus("");
};

const setNeteaseStatus = (message, isError = false) => {
    neteaseStatus.textContent = message || "";
    neteaseStatus.classList.toggle("panel__status--error", Boolean(message) && isError);
};

const setNeteaseQrStatus = (message, isError = false) => {
    neteaseQrStatus.textContent = message || "";
    neteaseQrStatus.classList.toggle("netease-qr__status--error", Boolean(message) && isError);
};

const setNeteasePhoneStatus = (message, isError = false) => {
    neteasePhoneStatus.textContent = message || "";
    neteasePhoneStatus.classList.toggle("panel__status--error", Boolean(message) && isError);
};

const adminFetch = async (path, options = {}) => {
    const token = requireToken();
    const headers = new Headers(options.headers || {});
    headers.set("X-Admin-Token", token);
    const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (response.status === 401) {
        handleUnauthorized();
        throw new Error("unauthorized");
    }
    return response;
};

const stopQrPolling = () => {
    neteaseState.qrPolling = false;
    if (neteaseState.qrTimer) {
        clearTimeout(neteaseState.qrTimer);
        neteaseState.qrTimer = null;
    }
};

const updateQrButton = () => {
    if (neteaseState.qrLoading) {
        neteaseQrStartBtn.disabled = true;
        neteaseQrStartBtn.textContent = "正在获取二维码...";
        return;
    }
    neteaseQrStartBtn.disabled = false;
    neteaseQrStartBtn.textContent = neteaseState.qrKey ? "刷新二维码" : "获取登录二维码";
};

const updateCaptchaButton = () => {
    if (neteaseState.sendCaptchaLoading) {
        neteaseSendCaptchaBtn.disabled = true;
        neteaseSendCaptchaBtn.textContent = "发送中...";
        return;
    }
    if (neteaseState.captchaRemaining > 0) {
        neteaseSendCaptchaBtn.disabled = true;
        neteaseSendCaptchaBtn.textContent = `重新发送 (${neteaseState.captchaRemaining}s)`;
        return;
    }
    neteaseSendCaptchaBtn.disabled = false;
    neteaseSendCaptchaBtn.textContent = "发送验证码";
};

const startCaptchaCooldown = (seconds = NETEASE_CAPTCHA_COOLDOWN_SECONDS) => {
    neteaseState.captchaRemaining = seconds;
    updateCaptchaButton();
    if (neteaseState.captchaTimer) {
        clearInterval(neteaseState.captchaTimer);
        neteaseState.captchaTimer = null;
    }
    neteaseState.captchaTimer = setInterval(() => {
        neteaseState.captchaRemaining -= 1;
        if (neteaseState.captchaRemaining <= 0) {
            neteaseState.captchaRemaining = 0;
            clearInterval(neteaseState.captchaTimer);
            neteaseState.captchaTimer = null;
        }
        updateCaptchaButton();
    }, 1000);
};

const applyNeteaseProfile = (data) => {
    const profile = data && typeof data.profile === "object" ? data.profile : {};
    const account = data && typeof data.account === "object" ? data.account : {};
    const loggedIn = Boolean(data && data.logged_in);
    const wasLoggedIn = neteaseState.loggedIn;

    neteaseState.loggedIn = loggedIn;
    neteaseLogoutBtn.classList.toggle("hidden", !loggedIn);
    neteaseAccount.classList.toggle("hidden", !loggedIn);
    neteaseLoginArea.classList.toggle("hidden", loggedIn);

    if (loggedIn) {
        const nickname = profile.nickname || profile.userName || "网易云用户";
        neteaseNickname.textContent = nickname;

        const meta = [];
        const userId = account.id || profile.userId;
        if (userId) {
            meta.push(`UID: ${userId}`);
        }
        if (Number(profile.vipType) > 0) {
            meta.push("VIP");
        }
        neteaseAccountMeta.textContent = meta.join(" · ") || "已登录";

        if (profile.avatarUrl) {
            neteaseAvatar.src = profile.avatarUrl;
            neteaseAvatar.classList.remove("hidden");
        } else {
            neteaseAvatar.removeAttribute("src");
            neteaseAvatar.classList.add("hidden");
        }

        setNeteaseStatus(`已登录：${nickname}`);
        if (!wasLoggedIn && playerState.current) {
            setPlayerStatus("网易云已登录，重新点击播放可获取完整歌曲。");
        }
        stopQrPolling();
    } else {
        neteaseNickname.textContent = "";
        neteaseAccountMeta.textContent = "";
        neteaseAvatar.removeAttribute("src");
        neteaseAvatar.classList.add("hidden");
        setNeteaseStatus("未登录（试听模式）");
    }

    updateCaptchaButton();
};

const loadNeteaseStatus = async ({ silent = false } = {}) => {
    if (!getStoredToken()) {
        return;
    }
    if (!silent) {
        setNeteaseStatus("正在查询网易云登录状态...");
    }

    try {
        const response = await adminFetch("/music/login/status");
        if (!response.ok) {
            throw new Error(`加载失败: ${response.status}`);
        }
        const data = await response.json();
        applyNeteaseProfile(data);
        if (!data.logged_in && data.code === 500) {
            setNeteaseStatus(data.message || "无法获取网易云登录状态。", true);
        }
    } catch (error) {
        if (error.message === "unauthorized" || error.message === "missing token") {
            return;
        }
        console.error(error);
        setNeteaseStatus("无法获取网易云登录状态。", true);
    }
};

const switchNeteaseTab = (tab) => {
    const isQr = tab === "qr";
    neteaseState.activeTab = tab;
    neteaseTabQrBtn.classList.toggle("netease-tab--active", isQr);
    neteaseTabPhoneBtn.classList.toggle("netease-tab--active", !isQr);
    neteaseTabQrBtn.setAttribute("aria-selected", String(isQr));
    neteaseTabPhoneBtn.setAttribute("aria-selected", String(!isQr));
    neteasePanelQr.classList.toggle("hidden", !isQr);
    neteasePanelPhone.classList.toggle("hidden", isQr);
    if (isQr) {
        if (neteaseState.qrKey && !neteaseState.qrPolling) {
            neteaseState.qrPolling = true;
            pollQrStatus();
        }
    } else {
        stopQrPolling();
    }
};

const pollQrStatus = async () => {
    if (!neteaseState.qrPolling || !neteaseState.qrKey) {
        return;
    }

    try {
        const response = await adminFetch(`/music/login/qr/check?key=${encodeURIComponent(neteaseState.qrKey)}`);
        if (!response.ok) {
            throw new Error(`二维码状态查询失败: ${response.status}`);
        }
        const data = await response.json();

        if (data.code === 800) {
            stopQrPolling();
            neteaseState.qrKey = "";
            updateQrButton();
            setNeteaseQrStatus(data.message || "二维码已过期，请重新获取。", true);
            return;
        }
        if (data.code === 803) {
            stopQrPolling();
            setNeteaseQrStatus("登录成功");
            await loadNeteaseStatus({ silent: true });
            return;
        }
        if (data.code === 802) {
            setNeteaseQrStatus("已扫码，请在手机上确认登录");
        } else if (data.code === 801) {
            setNeteaseQrStatus("等待扫码...");
        } else {
            setNeteaseQrStatus(data.message || "等待扫码...", Number(data.code) >= 500);
        }
    } catch (error) {
        if (error.message === "unauthorized" || error.message === "missing token") {
            return;
        }
        console.error(error);
        setNeteaseQrStatus("二维码状态查询失败，正在重试...", true);
    } finally {
        if (neteaseState.qrPolling) {
            neteaseState.qrTimer = setTimeout(pollQrStatus, NETEASE_QR_POLL_INTERVAL_MS);
        }
    }
};

const startQrLogin = async () => {
    if (neteaseState.qrLoading) {
        return;
    }
    if (neteaseState.loggedIn) {
        setNeteaseStatus("已登录，如需切换账号请先退出登录。", true);
        return;
    }

    neteaseState.qrLoading = true;
    updateQrButton();
    stopQrPolling();
    setNeteaseQrStatus("正在获取二维码...");

    try {
        const keyResponse = await adminFetch("/music/login/qr/key");
        if (!keyResponse.ok) {
            throw new Error(`获取二维码失败: ${keyResponse.status}`);
        }
        const keyData = await keyResponse.json();
        if (!keyData.success || !keyData.key) {
            throw new Error(keyData.message || "获取二维码失败");
        }

        const createResponse = await adminFetch(
            `/music/login/qr/create?key=${encodeURIComponent(keyData.key)}`
        );
        if (!createResponse.ok) {
            throw new Error(`生成二维码失败: ${createResponse.status}`);
        }
        const qrData = await createResponse.json();
        if (!qrData.success || !qrData.qrimg) {
            throw new Error(qrData.message || "生成二维码失败");
        }

        neteaseState.qrKey = keyData.key;
        neteaseQrImg.src = qrData.qrimg;
        neteaseQrBox.classList.remove("hidden");
        setNeteaseQrStatus("请使用网易云音乐 App 扫码登录");
        neteaseState.qrPolling = true;
        updateQrButton();
        pollQrStatus();
    } catch (error) {
        if (error.message === "unauthorized" || error.message === "missing token") {
            return;
        }
        console.error(error);
        setNeteaseQrStatus(error.message || "获取二维码失败，请稍后重试。", true);
    } finally {
        neteaseState.qrLoading = false;
        updateQrButton();
    }
};

const sendNeteaseCaptcha = async () => {
    if (neteaseState.sendCaptchaLoading || neteaseState.captchaRemaining > 0) {
        return;
    }

    const phone = neteasePhoneInput.value.trim().replace(/[\s-]/g, "");
    const ctcode = (neteaseCountrycodeInput.value.trim() || "86").replace(/^\+/, "");
    if (!/^\d{5,20}$/.test(phone)) {
        setNeteasePhoneStatus("请输入有效的手机号码。", true);
        return;
    }
    if (!/^\d{1,5}$/.test(ctcode)) {
        setNeteasePhoneStatus("请输入有效的国家码。", true);
        return;
    }

    neteaseState.sendCaptchaLoading = true;
    updateCaptchaButton();
    setNeteasePhoneStatus("正在发送验证码...");

    try {
        const response = await adminFetch("/music/captcha/sent", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ phone, ctcode }),
        });
        if (!response.ok) {
            throw new Error(`验证码发送失败: ${response.status}`);
        }
        const data = await response.json();
        if (data.success) {
            setNeteasePhoneStatus(data.message || "验证码已发送，请注意查收。");
            startCaptchaCooldown();
        } else {
            setNeteasePhoneStatus(data.message || "验证码发送失败，请稍后重试。", true);
        }
    } catch (error) {
        if (error.message === "unauthorized" || error.message === "missing token") {
            return;
        }
        console.error(error);
        setNeteasePhoneStatus("验证码发送失败，请稍后重试。", true);
    } finally {
        neteaseState.sendCaptchaLoading = false;
        updateCaptchaButton();
    }
};

const submitNeteasePhoneLogin = async () => {
    if (neteaseState.loginLoading) {
        return;
    }

    const phone = neteasePhoneInput.value.trim().replace(/[\s-]/g, "");
    const captcha = neteaseCaptchaInput.value.trim();
    const countrycode = (neteaseCountrycodeInput.value.trim() || "86").replace(/^\+/, "");
    if (!/^\d{5,20}$/.test(phone)) {
        setNeteasePhoneStatus("请输入有效的手机号码。", true);
        return;
    }
    if (!/^\d{1,5}$/.test(countrycode)) {
        setNeteasePhoneStatus("请输入有效的国家码。", true);
        return;
    }
    if (!/^\d{1,10}$/.test(captcha)) {
        setNeteasePhoneStatus("请输入短信验证码。", true);
        return;
    }

    neteaseState.loginLoading = true;
    neteasePhoneSubmitBtn.disabled = true;
    setNeteasePhoneStatus("正在登录...");

    try {
        const response = await adminFetch("/music/login/cellphone", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ phone, captcha, countrycode }),
        });
        if (!response.ok) {
            const errorBody = await response.json().catch(() => ({}));
            throw new Error(errorBody?.detail || `登录失败: ${response.status}`);
        }
        const data = await response.json();
        if (data.success) {
            neteaseCaptchaInput.value = "";
            setNeteasePhoneStatus("登录成功");
            await loadNeteaseStatus({ silent: true });
        } else {
            setNeteasePhoneStatus(data.message || "登录失败，请检查验证码。", true);
        }
    } catch (error) {
        if (error.message === "unauthorized" || error.message === "missing token") {
            return;
        }
        console.error(error);
        setNeteasePhoneStatus(error.message || "登录失败，请稍后重试。", true);
    } finally {
        neteaseState.loginLoading = false;
        neteasePhoneSubmitBtn.disabled = false;
    }
};

const logoutNetease = async () => {
    if (!window.confirm("确定要退出网易云登录吗？")) {
        return;
    }

    setNeteaseStatus("正在退出网易云登录...");
    try {
        const response = await adminFetch("/music/logout", { method: "POST" });
        if (!response.ok) {
            throw new Error(`退出失败: ${response.status}`);
        }
        stopQrPolling();
        neteaseState.qrKey = "";
        neteaseQrBox.classList.add("hidden");
        neteaseQrImg.removeAttribute("src");
        setNeteaseQrStatus("");
        setNeteasePhoneStatus("");
        applyNeteaseProfile({ logged_in: false, account: {}, profile: {} });
        setNeteaseStatus("已退出网易云登录。");
    } catch (error) {
        if (error.message === "unauthorized" || error.message === "missing token") {
            return;
        }
        console.error(error);
        setNeteaseStatus("退出网易云登录失败，请稍后重试。", true);
    }
};

const resetNeteaseState = () => {
    stopQrPolling();
    if (neteaseState.captchaTimer) {
        clearInterval(neteaseState.captchaTimer);
        neteaseState.captchaTimer = null;
    }
    neteaseState.loggedIn = false;
    neteaseState.qrKey = "";
    neteaseState.qrLoading = false;
    neteaseState.sendCaptchaLoading = false;
    neteaseState.loginLoading = false;
    neteaseState.captchaRemaining = 0;
    neteaseQrBox.classList.add("hidden");
    neteaseQrImg.removeAttribute("src");
    setNeteaseQrStatus("");
    setNeteasePhoneStatus("");
    neteasePhoneForm.reset();
    neteaseCountrycodeInput.value = "86";
    neteasePhoneSubmitBtn.disabled = false;
    updateQrButton();
    updateCaptchaButton();
    applyNeteaseProfile({ logged_in: false, account: {}, profile: {} });
    setNeteaseStatus("");
};

audio.addEventListener("loadedmetadata", applyTrialStart);
audio.addEventListener("play", updatePlayerUi);
audio.addEventListener("pause", updatePlayerUi);
audio.addEventListener("ended", handleAudioEnded);
audio.addEventListener("error", () => {
    if (!audio.getAttribute("src")) {
        return;
    }
    setPlayerStatus("音频加载失败：播放地址可能已过期或受防盗链限制。", true);
});
audio.addEventListener("timeupdate", () => {
    const current = playerState.current;
    if (!current || !current.trial) {
        return;
    }
    const end = Number(current.trial.end);
    if (!Number.isFinite(end) || end <= 0) {
        return;
    }
    if (audio.currentTime >= end) {
        if (!audio.paused) {
            audio.pause();
        }
        if (!playerState.trialEnded) {
            playerState.trialEnded = true;
            setPlayerStatus(`试听片段已结束（${formatClock(end)}），可点击「下一首」继续播放。`, true);
        }
    } else {
        playerState.trialEnded = false;
    }
});

playerRefreshBtn.addEventListener("click", () => {
    fetchPlayerQueue();
});

playerToggleBtn.addEventListener("click", togglePlayback);

playerPrevBtn.addEventListener("click", () => {
    playRelative(-1);
});

playerNextBtn.addEventListener("click", () => {
    playRelative(1);
});

playerPlayedBtn.addEventListener("click", () => {
    markPlayed(playerState.current);
});

playerQueueTable.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
        return;
    }
    const button = target.closest("button[data-action]");
    if (!(button instanceof HTMLButtonElement)) {
        return;
    }

    const requestId = Number(button.dataset.requestId);
    const item = playerState.queue.find((entry) => entry.id === requestId);
    if (!item) {
        return;
    }

    if (button.dataset.action === "play") {
        playItem(item);
    } else if (button.dataset.action === "played") {
        markPlayed(item);
    }
});

neteaseRefreshStatusBtn.addEventListener("click", () => {
    loadNeteaseStatus();
});

neteaseLogoutBtn.addEventListener("click", logoutNetease);

neteaseTabQrBtn.addEventListener("click", () => {
    switchNeteaseTab("qr");
});

neteaseTabPhoneBtn.addEventListener("click", () => {
    switchNeteaseTab("phone");
});

neteaseQrStartBtn.addEventListener("click", startQrLogin);

neteaseSendCaptchaBtn.addEventListener("click", sendNeteaseCaptcha);

neteasePhoneForm.addEventListener("submit", (event) => {
    event.preventDefault();
    submitNeteasePhoneLogin();
});

document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
        stopQrPolling();
        return;
    }
    if (!neteaseState.loggedIn && neteaseState.activeTab === "qr" && neteaseState.qrKey) {
        neteaseState.qrPolling = true;
        pollQrStatus();
    }
});

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
    fetchPlayerQueue();
    startPlayerPolling();
    loadNeteaseStatus({ silent: true });
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
    fetchPlayerQueue();
    startPlayerPolling();
    loadNeteaseStatus({ silent: true });
    searchInput.focus();
};

bootstrap();
