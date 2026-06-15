# AI 智能对话助手 — 项目计划书

---

## 1. 系统架构

### 整体架构

```
+-------------------+       +------------------+       +----------------+
|    浏览器 / 前端    |  HTTP  |   FastAPI 后端    |       |   MySQL 数据库  |
|                    | <---> |                  | <---> |                |
| HTML + CSS + JS   |  SSE   |  routers         |       | users          |
|                    |        |  services        |       | conversations  |
| 登录/注册/对话界面  |        |  middleware      |       | messages       |
|                    |        |                  |       +----------------+
+-------------------+        |                  |
                              |        |         |       +----------------+
                              |        v         |       |    Redis        |
                              |  +-----------+   | <---> |                 |
                              |  | AI API    |   |       | session cache   |
                              |  | (DeepSeek/|   |       | response cache  |
                              |  |  通义千问)  |   |       | counter         |
                              |  +-----------+   |       +----------------+
                              +------------------+
```

### 请求链路（一次对话）

```
用户输入消息
    │
    ▼
[前端] JS 发起 POST /api/conversations/{id}/messages (EventSource)
    │
    ▼
[中间件] JWT Token 校验 → 解析 user_id
    │
    ▼
[Router] conversations.py → 调用 service
    │
    ▼
[Service] conversation_service.py
    ├── 保存用户消息到 MySQL (messages 表)
    ├── 查询历史消息 (构建上下文)
    ├── 调用 ai_service.py → 大模型 API (stream=True)
    │
    ▼
[SSE 流式返回] 逐 token 推送到前端
    │
    ▼
[Service] 流结束后保存 AI 回复到 MySQL
    │
    ▼
[前端] 逐字显示 AI 回复
```

### 技术选型理由

| 技术 | 理由 |
|------|------|
| FastAPI | 原生异步支持，自动生成 API 文档，类型注解驱动 |
| SQLAlchemy | Python 最成熟的 ORM，与 FastAPI 集成良好 |
| MySQL | 关系型数据（用户/对话/消息）天然适合，社区成熟 |
| Redis | 高性能缓存，降低数据库压力，适合会话和热数据 |
| JWT | 无状态认证，适合前后端分离架构 |
| SSE | 单向流式推送，比 WebSocket 简单，适合 AI 流式输出 |
| 原生前端 | 项目聚焦后端能力，避免引入前端框架的复杂度 |
| DeepSeek API | 国内可用，价格低廉，OpenAI 兼容接口 |

---

## 2. 数据库设计

### ER 图

```
┌──────┐       ┌──────────────┐       ┌──────────┐
│ users│ 1───* │conversations │ 1───* │ messages │
└──────┘       └──────────────┘       └──────────┘
 用户表           对话表                  消息表
```

### users — 用户表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 用户 ID |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 用户名 |
| email | VARCHAR(100) | UNIQUE, NOT NULL | 邮箱 |
| hashed_password | VARCHAR(255) | NOT NULL | bcrypt 哈希密码 |
| created_at | DATETIME | DEFAULT NOW() | 注册时间 |
| updated_at | DATETIME | ON UPDATE NOW() | 更新时间 |

```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### conversations — 对话表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 对话 ID |
| user_id | INT | FK → users.id, NOT NULL | 所属用户 |
| title | VARCHAR(200) | DEFAULT '新对话' | 对话标题 |
| model_name | VARCHAR(50) | DEFAULT 'deepseek-chat' | 使用的模型 |
| created_at | DATETIME | DEFAULT NOW() | 创建时间 |
| updated_at | DATETIME | ON UPDATE NOW() | 最后活跃时间 |

```sql
CREATE TABLE conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(200) DEFAULT '新对话',
    model_name VARCHAR(50) DEFAULT 'deepseek-chat',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### messages — 消息表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 消息 ID |
| conversation_id | INT | FK → conversations.id, NOT NULL | 所属对话 |
| role | VARCHAR(20) | NOT NULL, CHECK(user/assistant/system) | 角色 |
| content | TEXT | NOT NULL | 消息内容 |
| token_count | INT | DEFAULT 0 | token 消耗估算 |
| created_at | DATETIME | DEFAULT NOW() | 发送时间 |

```sql
CREATE TABLE messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    token_count INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);
```

### 索引设计

```sql
-- 加速用户查询
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- 加速对话列表查询
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_updated_at ON conversations(updated_at DESC);

-- 加速消息历史查询
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
```

### Redis 缓存设计

| Key | 类型 | 过期时间 | 说明 |
|-----|------|---------|------|
| `session:{user_id}` | String (JSON) | 30min | 用户会话信息 |
| `conv_list:{user_id}` | String (JSON) | 5min | 对话列表缓存 |
| `recent_conv:{conv_id}` | String (JSON) | 10min | 最近对话消息缓存 |
| `api_count:{user_id}` | String | 1hour | API 调用计数 |

---

## 3. API 端点详细设计

### 3.1 认证模块

#### POST /api/auth/register

```
请求体：
{
    "username": "alice",
    "email": "alice@example.com",
    "password": "secret123"
}

响应 (201)：
{
    "id": 1,
    "username": "alice",
    "email": "alice@example.com",
    "created_at": "2026-06-15T10:00:00"
}

错误 (400): {"detail": "用户名已存在"}
错误 (422): {"detail": [{...}]}  ← Pydantic 自动校验
```

#### POST /api/auth/login

```
请求体：
{
    "email": "alice@example.com",
    "password": "secret123"
}

响应 (200)：
{
    "access_token": "eyJhbGc...",
    "token_type": "bearer",
    "user": {
        "id": 1,
        "username": "alice",
        "email": "alice@example.com"
    }
}

错误 (401): {"detail": "邮箱或密码错误"}
```

### 3.2 用户模块

#### GET /api/users/me

```
Headers: Authorization: Bearer <token>

响应 (200)：
{
    "id": 1,
    "username": "alice",
    "email": "alice@example.com",
    "created_at": "2026-06-15T10:00:00"
}

错误 (401): {"detail": "未登录或 token 已过期"}
```

### 3.3 对话模块

#### POST /api/conversations

```
Headers: Authorization: Bearer <token>

请求体（可选）：
{
    "title": "学习 Python",
    "model_name": "deepseek-chat"
}

响应 (201)：
{
    "id": 1,
    "title": "学习 Python",
    "model_name": "deepseek-chat",
    "created_at": "2026-06-15T10:30:00"
}
```

#### GET /api/conversations

```
Headers: Authorization: Bearer <token>

Query: ?page=1&page_size=10

响应 (200)：
{
    "items": [
        {
            "id": 1,
            "title": "学习 Python",
            "model_name": "deepseek-chat",
            "message_count": 12,
            "last_message": "好的，我们来学习装饰器...",
            "updated_at": "2026-06-15T11:00:00"
        }
    ],
    "total": 1,
    "page": 1,
    "page_size": 10
}
```

#### GET /api/conversations/{id}

```
Headers: Authorization: Bearer <token>

响应 (200)：
{
    "id": 1,
    "title": "学习 Python",
    "model_name": "deepseek-chat",
    "messages": [
        {
            "id": 1,
            "role": "user",
            "content": "什么是装饰器？",
            "created_at": "2026-06-15T10:30:00"
        },
        {
            "id": 2,
            "role": "assistant",
            "content": "装饰器是一种...",
            "token_count": 150,
            "created_at": "2026-06-15T10:30:15"
        }
    ],
    "created_at": "2026-06-15T10:30:00",
    "updated_at": "2026-06-15T10:30:15"
}

错误 (404): {"detail": "对话不存在"}
错误 (403): {"detail": "无权访问此对话"}
```

#### DELETE /api/conversations/{id}

```
Headers: Authorization: Bearer <token>

响应 (204): (无内容)

错误 (404): {"detail": "对话不存在"}
错误 (403): {"detail": "无权删除此对话"}
```

#### POST /api/conversations/{id}/messages

```
Headers: Authorization: Bearer <token>
Content-Type: application/json

请求体：
{
    "content": "什么是 Python 装饰器？"
}

响应：SSE 流式 (text/event-stream)

event: delta
data: {"content": "装饰"}

event: delta
data: {"content": "器是"}

event: delta
data: {"content": "一种..."}
  ...
event: done
data: {"message_id": 3, "token_count": 150}

错误 (404): {"detail": "对话不存在"}
错误 (400): {"detail": "消息内容不能为空"}
```

### 3.4 模型模块

#### GET /api/models

```
响应 (200)：
{
    "models": [
        {
            "id": "deepseek-chat",
            "name": "DeepSeek Chat",
            "provider": "deepseek",
            "description": "通用对话模型，性价比高"
        },
        {
            "id": "qwen-turbo",
            "name": "通义千问 Turbo",
            "provider": "alibaba",
            "description": "阿里云大模型，中文能力强"
        }
    ],
    "default": "deepseek-chat"
}
```

---

## 4. 开发阶段

### 阶段一：项目骨架搭建
**产出物：**
- 完整的 backend/ 和 frontend/ 目录结构
- `requirements.txt` 包含所有依赖
- `.env.example` 配置模板
- FastAPI 应用能启动并访问 `/docs`
- `.gitignore` 配置

### 阶段二：用户认证模块
**产出物：**
- users 表通过 SQLAlchemy 自动创建
- `/api/auth/register` 接口（密码 bcrypt 哈希）
- `/api/auth/login` 接口（返回 JWT）
- `/api/users/me` 接口（需认证）
- JWT 认证中间件

### 阶段三：对话核心 + AI API
**产出物：**
- conversations 和 messages 表
- `/api/conversations` POST 创建对话
- `/api/conversations/{id}/messages` POST 发送消息
- ai_service 对接大模型 API（支持 stream）
- SSE 流式响应实现

### 阶段四：对话管理
**产出物：**
- `/api/conversations` GET 对话列表（分页）
- `/api/conversations/{id}` GET 对话详情
- `/api/conversations/{id}` DELETE 删除对话
- Redis 缓存集成

### 阶段五：前端页面
**产出物：**
- `login.html` + `auth.js` 登录/注册功能
- `index.html` 对话主界面（对话列表 + 聊天窗口）
- `chat.js` SSE 流式接收与显示
- `style.css` 基础样式

### 阶段六：测试与优化
**产出物：**
- 全流程联调（注册→登录→对话→查看历史→删除）
- 错误处理完善
- UI 细节优化（加载状态、错误提示、响应式）

### 阶段七：项目收尾
**产出物：**
- README 补充完成
- 代码检查与整理
- 最终提交与 push

---

## 5. 环境变量设计

```bash
# .env.example
# 数据库
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=ai_chat

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# AI API
DEEPSEEK_API_KEY=sk-your-deepseek-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
QWEN_API_KEY=sk-your-qwen-key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# App
APP_NAME=AI Chat Assistant
APP_DEBUG=true
```
