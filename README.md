# 校园系统后端

本项目是校园系统的FastAPI后端服务，实现了微信小程序登录、用户绑定、歌曲搜索、点歌、管理员审核、歌曲播放等全流程功能，集成网易云音乐播放直链获取。

## 技术栈

- **Web框架**: FastAPI
- **ORM**: SQLAlchemy
- **数据库**: PostgreSQL
- **身份验证**: JWT
- **API集成**: node.js网易云音乐API

## 项目结构

```
ourapp_back/
├── app/                        # 应用主目录
│   ├── api/                    # 所有API路由的定义处
│   ├── core/
│   │   ├── config.py          # 应用配置
│   │   └── security.py        # 安全相关工具
│   ├── db/                     # 数据库相关
│   │   ├── models/            # 数据模型
│   │   ├── repositories/      # 数据访问层
│   │   └── session.py         # 数据库会话
│   ├── schemas/               # 请求/响应模式
│   ├── services/              # 业务逻辑服务
│   ├── static_admin/          # 点歌台播放面板（静态页面）
│   └── main.py                # 应用入口
├── .env.example                # 环境变量示例
├── student.db                  # 迁移用 SQLite 数据库
├── requirements.txt            # 依赖包列表
├── migrate.py                  # 数据库迁移脚本
└── run.py                      # 启动脚本
```

## 功能模块

### 微信小程序模块
- **登录**: 通过微信小程序code换取openid并生成JWT令牌
- **绑定**: 将微信用户与学生信息绑定
- **刷新令牌**: 支持访问令牌过期后使用刷新令牌获取新令牌

### 点歌模块
- **点歌**: 用户提交点歌请求
- **审核**: 审核点歌请求（管理员权限）

### 播放器模块
- **队列管理**: 获取待播放歌曲队列
- **状态更新**: 标记歌曲播放状态

### 音乐服务
- **歌曲搜索**: 搜索网易云音乐歌曲
- **获取直链**: 获取歌曲播放地址与试听片段信息
- **音频代理**: `/api/song/stream/{song_id}.mp3` 将网易云音频流转发为同源地址，支持 Range 请求与 CORS

### 小程序试听
- 点歌页的「试听」按钮先调用 `/api/geturl` 获取播放信息，再通过 `stream_url` 播放
- 未登录网易云或账号非会员时，接口会返回截取好的试听片段，并在 `free_trial_info` 中给出开始/结束时间（单位：秒）；前端会自动定位到片段起点并在结束处停止
- 如果后端登录的是会员账号，`/song/url` 可能返回完整歌曲；小程序端仍会把点歌页试听限制在前 30 秒
- `stream_url` 由后端代理音频流，可以规避两个小程序端限制：网易云返回的音频地址通常是 `http`，且无法为 `InnerAudioContext` 设置 `Referer` 等请求头
- 代理地址带 `.mp3` 后缀，兼容部分小程序音频解码器对 URL 扩展名的要求；响应同时带上 CORS 头，供开发者工具的 WebAudio 解码使用
- 代理请求不发送 `Referer`，避免网易云 CDN 因防盗链返回 403
- 生产环境需使用 HTTPS 的后端域名；如小程序后台限制了媒体域名，请将后端域名加入 `downloadFile` 合法域名（使用代理后无需再添加 `*.music.126.net`）

## 点歌台播放面板

后端内置一个网页版「点歌台播放器」，源码位于 `app/static_admin/`，由 FastAPI 直接托管，无需单独构建或部署前端。

- 访问地址：`http://localhost:8000/admin/`（需先启动后端）
- 登录密钥：`.env` 中的 `ADMIN_PANEL_TOKEN`，页面通过 `X-Admin-Token` 请求头校验；默认值 `change-me` 仅供本地调试，部署前务必修改
- 登录状态保存在浏览器 `sessionStorage`，更换标签页或密钥变更后需要重新登录

### 面板功能

**点歌队列与播放**

- 展示所有已审核通过（状态 `approved`）的歌曲，按点歌时间升序排列
- 队列每 20 秒自动刷新，也可以点击「刷新队列」手动更新
- 当前播放区显示封面、歌名、歌手、点歌人、队列位置和试听标记
- 支持播放/暂停、上一首、下一首，可勾选「自动连播」
- 播放结束会自动标记为已播放；若开启自动连播，会继续播放下一首
- 表格中可对任意歌曲执行「播放」或「标记已播」，标记后该歌曲移出队列
- 试听片段播放结束后会暂停，并提示切换到下一首

**网易云账号**

- 支持二维码登录和手机验证码登录，可查看登录状态、退出登录
- 登录 Cookie 保存在后端根目录的 `.netease_cookie`，重启后自动加载，该文件不提交到 Git
- 未登录或账号无会员时，多数歌曲只能获取试听片段
- 依赖网易云音乐 API 服务，默认地址为 `http://127.0.0.1:3000`（见 `MUSIC_API_BASE_URL`）

**用户与配置管理**

- 按姓名、学号、OpenID 搜索用户，并切换管理员权限
- 维护额外管理员 OpenID、接口限流参数，保存到 `app_config.json`

### 面板接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/admin/player/queue` | 获取待播放队列 |
| GET | `/api/admin/player/song/{song_id}` | 获取歌曲详情和播放地址 |
| POST | `/api/admin/player/played` | 标记歌曲为已播放 |
| GET | `/api/admin/music/login/status` | 查询网易云登录状态 |
| GET | `/api/admin/music/login/qr/key` | 获取二维码登录 key |
| GET | `/api/admin/music/login/qr/create` | 生成登录二维码 |
| GET | `/api/admin/music/login/qr/check` | 轮询扫码状态 |
| POST | `/api/admin/music/captcha/sent` | 发送短信验证码 |
| POST | `/api/admin/music/login/cellphone` | 手机验证码登录 |
| POST | `/api/admin/music/logout` | 退出网易云登录 |

所有 `/api/admin/*` 接口都需要在请求头中携带 `X-Admin-Token`。

如果使用独立的桌面播放器，也可以调用 `/api/player/queue` 和 `/api/player/played`，此时使用 `.env` 中的 `PLAYER_ACCESS_TOKEN`（请求头 `X-Player-Token`）。

## 快速开始

### 1. 环境准备

确保已安装Python 3.13。你可以使用poetry来搭建环境。

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

or

```bash
poetry install
```

### 3. 配置环境变量

本地配置文件不提交到 Git，仓库中只保留示例文件。首次使用请复制示例文件：

```bash
cp .env.example .env
```

然后编辑 `.env`，填入真实值。其中 `JWT_SECRET` 必须至少 32 字节，可以用下面的命令生成：

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

`.env` 已在 `.gitignore` 中忽略；网易云登录后自动生成的 `.netease_cookie` 同样不会提交。

### 4. 数据库相关

使用以下命令初始化数据库：

``` bash
# 导入初始数据
python migrate.py
```

当开发时需要删除数据库原来的数据并重新创建时，可以使用
``` bash
python migrate.py --delete
```

### 5. 启动服务
先启动node.js网易云音乐API服务，参考[网易云音乐API项目](https://github.com/Binaryify/NeteaseCloudMusicApi)
```bash
npx NeteaseCloudMusicApi@latest
```

```bash
# 使用run.py启动
python run.py
```

服务启动后，可访问 http://localhost:8000/docs 查看API文档，访问 http://localhost:8000/admin/ 使用点歌台播放面板。
