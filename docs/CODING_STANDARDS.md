# AI 智能对话助手 — 编码规范

---

## 1. Python 代码风格

### 1.1 基础规范

- 遵循 [PEP 8](https://peps.python.org/pep-0008/) 标准
- 行宽上限：**100 字符**（FastAPI 社区惯例，略宽于 PEP 8 的 79 字符）
- 缩进：4 个空格，禁止使用 Tab
- 文件末尾：一个空行
- 字符串：统一使用双引号 `"`（与 FastAPI 官方文档保持一致）
- 推荐使用 [Black](https://github.com/psf/black) 自动格式化：`black --line-length 100 .`

### 1.2 类型注解

所有函数**必须**添加类型注解：

```python
# ✅ 正确
def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()

# ❌ 错误
def get_user_by_email(db, email):
    return db.query(User).filter(User.email == email).first()
```

常用注解导入：

```python
from typing import Optional  # Python 3.10+ 可用 | None 替代
from datetime import datetime
from pydantic import BaseModel, EmailStr
```

### 1.3 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 类名 | PascalCase | `ConversationService`, `UserCreate` |
| 函数/方法 | snake_case | `create_user()`, `get_conversation_by_id()` |
| 变量 | snake_case | `user_id`, `message_list` |
| 常量 | UPPER_SNAKE_CASE | `JWT_EXPIRE_MINUTES`, `MAX_MESSAGE_LENGTH` |
| 私有属性 | _leading_underscore | `_password`, `_validate_token()` |
| 模块名 | snake_case | `auth_service.py`, `conversation_router.py` |

---

## 2. 项目文件组织

### 2.1 分层职责

```
app/
├── models/      → SQLAlchemy 数据库模型（纯表定义，无业务逻辑）
├── schemas/     → Pydantic 请求/响应模型（纯数据结构，无逻辑）
├── routers/     → API 路由（薄层：只做参数提取 → 调用 service → 返回）
├── services/    → 核心业务逻辑（所有业务规则在此）
├── middleware/   → 请求拦截（认证校验、CORS、日志等）
└── utils/       → 工具函数（Token 生成、密码哈希、缓存封装等）
```

**调用链**：`router → service → model / utils`

**禁止事项**：
- `router` 中不得直接写数据库查询
- `model` 中不得包含业务逻辑
- `schema` 只做数据校验，不调用外部服务

### 2.2 `__init__.py` 规范

每个包通过 `__init__.py` 做**显式导出**，方便其他模块引用：

```python
# app/services/__init__.py
from app.services.auth_service import AuthService
from app.services.conversation_service import ConversationService
from app.services.ai_service import AIService

__all__ = ["AuthService", "ConversationService", "AIService"]
```

### 2.3 导入顺序

```python
# 1. 标准库
import os
from datetime import datetime

# 2. 第三方库
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

# 3. 项目内模块
from app.config import settings
from app.models.user import User
```

---

## 3. FastAPI 规范

### 3.1 路由定义

```python
# ✅ 正确示例
from fastapi import APIRouter, Depends, status

router = APIRouter(prefix="/api/auth", tags=["认证"])

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
)
async def register(
    data: UserCreate,
    db: Session = Depends(get_db),
) -> UserResponse:
    """创建新用户账号。用户名和邮箱必须唯一。"""
    service = AuthService(db)
    return service.register(data)
```

**必须遵守**：
- 每个路由函数声明 `tags`（Swagger 文档分组）
- 写 `response_model`（明确响应结构）
- 写 `summary`（简短中文描述）
- 复杂接口写 docstring

### 3.2 错误处理

统一使用 FastAPI 的 `HTTPException`：

```python
from fastapi import HTTPException, status

# 404
raise HTTPException(status_code=404, detail="用户不存在")

# 401
raise HTTPException(status_code=401, detail="邮箱或密码错误")

# 403
raise HTTPException(status_code=403, detail="无权访问此对话")

# 400
raise HTTPException(status_code=400, detail="消息内容不能为空")
```

**原则**：
- 所有错误响应格式统一为 `{"detail": "描述"}`
- 不在错误信息中泄露敏感数据（如数据库报错原文）
- 业务错误用 4xx，服务器错误用 5xx

### 3.3 依赖注入

数据库会话和认证检查统一通过 `Depends` 注入：

```python
# app/database.py
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# app/middleware/auth_middleware.py
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    ...
```

### 3.4 敏感信息保护

- 密码**绝不**出现在响应中
- Pydantic Schema 区分 `Create`（含密码）和 `Response`（不含密码）

```python
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str          # 仅用于接收

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime   # 不含 password

    model_config = ConfigDict(from_attributes=True)
```

---

## 4. Git 规范

### 4.1 分支策略

```
main              ← 主分支（可运行的代码）
├── phase-01-skeleton    ← 阶段一分支
├── phase-02-auth        ← 阶段二分支
├── ...
└── phase-07-finish      ← 阶段七分支
```

### 4.2 Commit 格式

```
[阶段一] 初始化项目目录结构和配置文件
[阶段二] 实现用户注册接口
[阶段二] 实现 JWT 登录认证
[阶段三] 对接 DeepSeek API 实现流式对话
```

- 使用中文
- 标注所属阶段
- 每完成一个独立功能点提交一次

### 4.3 提交频率

- 每完成一个接口 → commit
- 每完成一个阶段 → push
- 每天结束前必须 push 当前进度

---

## 5. 安全规范

### 5.1 密码安全

```python
import bcrypt

def hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )
```

### 5.2 JWT 安全

- 密钥从环境变量读取，不硬编码
- Token 设置合理过期时间（默认 24 小时）
- 不在 JWT payload 中存储密码等敏感信息

### 5.3 敏感配置

- `.env` 文件**绝不提交**到 Git
- 提供 `.env.example` 作为模板（不含真实密钥值）
- `.gitignore` 必须包含 `.env`

### 5.4 数据库安全

- 所有查询使用 SQLAlchemy 参数化查询，禁止拼接 SQL
- 用户输入使用 Pydantic 校验后再入库

### 5.5 CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # 明确指定，不用 "*"
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

## 6. 代码注释规范

### 6.1 模块头

每个 `.py` 文件首行写模块用途：

```python
"""用户认证服务：处理注册、登录、Token 签发与验证。"""
```

### 6.2 函数 docstring

使用 Google 风格：

```python
def create_conversation(
    db: Session,
    user_id: int,
    title: str | None = None,
    model_name: str = "deepseek-chat",
) -> Conversation:
    """为用户创建一个新的对话会话。

    Args:
        db: 数据库会话。
        user_id: 当前登录用户的 ID。
        title: 对话标题，默认为"新对话"。
        model_name: 使用的 AI 模型名称。

    Returns:
        新创建的 Conversation 实例。

    Raises:
        ValueError: 当 model_name 不在可用列表中时抛出。
    """
    ...
```

### 6.3 关键逻辑注释

```python
# 缓存优先：先查 Redis，未命中再查数据库
cached = redis_client.get(cache_key)
if cached:
    return json.loads(cached)

# 调用 AI API，stream=True 实现逐 token 返回
response = client.chat.completions.create(
    model=model_name,
    messages=messages,
    stream=True,
)
```

---

## 7. 依赖版本

```text
# requirements.txt
fastapi==0.115.*
uvicorn[standard]==0.30.*
sqlalchemy==2.0.*
pymysql==1.1.*
cryptography==42.*
redis==5.1.*
python-jose[cryptography]==3.3.*
bcrypt==4.1.*
pydantic[email]==2.*
python-dotenv==1.0.*
openai==1.*              # OpenAI SDK，兼容 DeepSeek
httpx==0.27.*
```

> 使用 `.*` 表示允许补丁版本升级，主版本锁定以保证兼容性。
