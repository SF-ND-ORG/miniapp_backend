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
│   └── main.py                # 应用入口
├── database.db                 # SQLite数据库文件
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
- **获取直链**: 获取歌曲播放地址
- **获取歌词**: 获取歌曲歌词

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

你可以这样创建JWT_SECRET：
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

在项目根目录创建`.env`文件：

``` dotenv
# JWT配置
JWT_SECRET=your_secure_jwt_secret_key

# 微信小程序配置
WECHAT_APPID=your_wechat_appid
WECHAT_SECRET=your_wechat_secret

# 数据库配置（如使用PostgreSQL）
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=miniapp
```

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

服务启动后，可访问 http://localhost:8000/docs 查看API文档。
