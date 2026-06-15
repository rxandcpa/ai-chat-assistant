# AI 智能对话助手

> 基于 FastAPI + MySQL + Redis 构建的多轮 AI 对话应用，支持流式输出与多模型切换。

---

## 功能

- **用户系统**：注册、登录、JWT 认证
- **多轮对话**：创建对话，发送消息，AI 回复支持流式输出（SSE）
- **对话管理**：对话列表、历史消息回看、删除对话
- **多模型**：支持切换 DeepSeek / 通义千问等大模型
- **Redis 缓存**：最近对话缓存，提升响应速度

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python + FastAPI |
| 数据库 | MySQL + SQLAlchemy ORM |
| 缓存 | Redis |
| 认证 | JWT (bcrypt) |
| AI 接口 | DeepSeek / 通义千问 API |
| 前端 | HTML + CSS + JavaScript（原生） |
| 工具链 | Git, pip, venv |

---

## 项目结构

```
ai-chat-assistant/
├── backend/                  # 后端代码
│   ├── app/
│   │   ├── main.py           # FastAPI 入口
│   │   ├── config.py         # 配置管理
│   │   ├── database.py       # 数据库连接
│   │   ├── models/           # SQLAlchemy 模型
│   │   ├── schemas/          # Pydantic 请求/响应
│   │   ├── routers/          # API 路由
│   │   ├── services/         # 业务逻辑
│   │   ├── middleware/       # 中间件
│   │   └── utils/            # 工具函数
│   ├── requirements.txt
│   └── .env.example
├── frontend/                 # 前端页面
│   ├── index.html            # 对话主界面
│   ├── login.html            # 登录页
│   ├── register.html         # 注册页
│   ├── css/style.css
│   └── js/
│       ├── api.js            # API 请求封装
│       ├── auth.js            # 认证逻辑
│       └── chat.js            # 对话逻辑
├── docs/                     # 项目文档
│   ├── PROJECT_PLAN.md       # 项目计划书
│   └── CODING_STANDARDS.md   # 编码规范
├── .gitignore
└── README.md
```

---

## 快速启动

> 详细步骤将在项目开发完成后补充。

```bash
# 1. 后端
cd backend
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
cp .env.example .env       # 编辑 .env 填入配置
uvicorn app.main:app --reload

# 2. 前端
cd frontend
python -m http.server 8080  # 或用 Live Server 打开
```

---

## API 端点一览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/register | 用户注册 |
| POST | /api/auth/login | 用户登录 |
| GET | /api/users/me | 当前用户信息 |
| POST | /api/conversations | 新建对话 |
| GET | /api/conversations | 对话列表 |
| GET | /api/conversations/{id} | 对话详情 |
| DELETE | /api/conversations/{id} | 删除对话 |
| POST | /api/conversations/{id}/messages | 发送消息（SSE） |
| GET | /api/models | 可用模型列表 |

启动后端后访问 `http://localhost:8000/docs` 查看完整的 Swagger API 文档。

---

## 开发阶段

- [ ] 阶段一：项目骨架搭建（目录结构、配置文件、依赖）
- [ ] 阶段二：用户认证模块（注册、登录、JWT 中间件）
- [ ] 阶段三：对话核心 + AI API（发送消息、流式输出、保存历史）
- [ ] 阶段四：对话管理（列表、详情、删除、Redis 缓存）
- [ ] 阶段五：前端页面（登录/注册页、对话界面、流式显示）
- [ ] 阶段六：测试与优化（全流程联调、错误处理）
- [ ] 阶段七：项目收尾（README 完善、代码整理）

---

## License

MIT
