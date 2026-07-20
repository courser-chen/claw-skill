---
name: op-redmine-sync
description: Sync OpenProject work packages and time entries to Redmine, or query OpenProject project info (members, work packages, time entries). Triggers: openproject, redmine, sync, work-package, time-entry, 同步, 工时, 条目.
license: Apache-2.0
metadata: { "openclaw": { "emoji": "🔄", "requires": { "bins": ["python3"], "env": ["HOME"] } } }
---

# OpenProject 与 Redmine 同步/查询助手

你是一个专业的项目管理数据同步和查询助手。支持以下功能：
1. **数据同步**：将 OpenProject 中的条目（Work Packages）同步到 Redmine
2. **数据查询**：查询 OpenProject 项目的各种信息（成员、条目、工时等）

## 核心功能

### 功能一：同步 OpenProject 条目到 Redmine

当用户需要将 OpenProject 中**指定用户和指定项目**的条目（Work Packages）同步到 Redmine 时使用。

#### 必要参数
在执行同步之前，必须确认用户提供以下参数：
1. **OpenProject 用户登录名** (`opUserLogin`)
2. **OpenProject 项目名称或标识符** (`opProjectId`)
3. **Redmine 用户登录名** (`redmineUserLogin`)
4. **Redmine 项目ID** (`redmineProjectId`)
5. **同步起始日期** (`startDate`)，格式：YYYY-MM-DD

#### 执行步骤
1. **查询项目ID**：通过 `/api/v3/projects` 接口，根据项目名称或标识符获取真实项目ID
2. **查询用户ID**：通过 `/api/v3/users` 接口，根据用户名获取用户ID
3. **获取工作包列表**：通过 `/api/v3/work_packages` 接口，筛选指定项目和用户的条目
4. **同步到 Redmine**：
   - 在 Redmine 中查找是否已存在对应条目（通过自定义字段 `openproject_id` 匹配）
   - 如已存在则更新，不存在则创建
5. **输出同步报告**：返回成功/失败数量及详情

#### 示例
- 用户需求："把 nan-yang-yin-xing-ren-li-xi-tong-xin-chuang 项目中用户 admin 的条目同步到 Redmine 项目 1"
- 调用：`sync_tasks("admin", "nan-yang-xing-ren-li-xi-tong-xin-chuang", "redmine_user", "1", "2026-01-01")`

---

### 功能二：查询 OpenProject 项目信息

当用户需要查询 OpenProject 项目的各种信息时使用。

#### 查询项目详情
通过项目名称或标识符查询项目基本信息。

**函数**：`get_project_info(project_identifier: str) -> dict`

**示例**：
```python
# 查询项目详情
project_info = get_project_info("nan-yang-yin-xing-ren-li-xi-tong-xin-chuang")
# 返回：项目ID、名称、描述、状态等
```

#### 查询项目成员
查询指定项目的所有成员列表。

**函数**：`get_project_members(project_id: int) -> list`

**API 端点**：`GET /api/v3/projects/{project_id}/memberships`

**返回字段**：
- 成员ID
- 成员名称
- 成员邮箱
- 成员角色

**示例**：
```python
# 查询项目成员
members = get_project_members(123)
for member in members:
    print(f"{member['name']} - {member['role']}")
```

#### 查询工作包/条目
查询指定项目的所有工作包（条目）列表。

**函数**：`get_work_packages(project_id: int, user_id: int = None) -> list`

**API 端点**：`GET /api/v3/work_packages`

**过滤参数**：
- `project`：项目ID
- `assigned_to`：负责人用户ID（可选）

**返回字段**：
- 条目ID
- 标题（subject）
- 描述（description）
- 状态（status）
- 优先级（priority）
- 负责人（assignee）
- 创建时间
- 更新时间

**示例**：
```python
# 查询项目的所有条目
work_packages = get_work_packages(123)

# 查询指定用户的条目
work_packages = get_work_packages(123, user_id=456)

for wp in work_packages:
    print(f"[{wp['id']}] {wp['subject']} - {wp['status']}")
```

#### 查询用户信息
根据用户名查询 OpenProject 用户详情。

**函数**：`get_user_info(user_login: str) -> dict`

**API 端点**：`GET /api/v3/users`

**示例**：
```python
# 查询用户信息
user = get_user_info("admin")
print(f"用户ID: {user['id']}, 姓名: {user['name']}, 邮箱: {user['email']}")
```

#### 查询工时记录
查询指定项目的工时记录列表。

**函数**：`get_time_entries(project_id: int, user_id: int = None, start_date: str = None) -> list`

**API 端点**：`GET /api/v3/time_entries`

**过滤参数**：
- `project`：项目ID
- `user`：用户ID（可选）
- `spent_on`：日期范围（可选）

**返回字段**：
- 工时ID
- 对应工作包
- 用户
- 活动类型
- 小时数
- 备注
- 日期

**示例**：
```python
# 查询项目工时
time_entries = get_time_entries(123)

# 查询指定用户某日期后的工时
time_entries = get_time_entries(123, user_id=456, start_date="2026-01-01")

for entry in time_entries:
    print(f"{entry['user']}: {entry['hours']}h - {entry['comment']}")
```

---

## 常见问题处理

### 参数缺失
- 同步功能缺少参数时，提示用户提供完整信息
- 查询功能支持部分参数，可使用默认值

### API 鉴权失败 (401/403)
- 检查 API Key 是否正确配置
- 检查账号是否有对应项目的访问权限

### 网络超时
- 请求超时时间设置为 30 秒
- 超时后自动重试 3 次

### 数据不存在
- 项目、用户不存在时抛出明确的错误信息
- 返回空列表而非异常

---

## OpenProject API 参考

### 基础信息
- **Base URL**: `http://113.207.49.168:8666`
- **认证方式**: Bearer Token
- **API 版本**: v3

### 常用端点
| 功能 | 端点 | 方法 |
|------|------|------|
| 查询项目 | `/api/v3/projects` | GET |
| 查询成员 | `/api/v3/projects/{id}/memberships` | GET |
| 查询用户 | `/api/v3/users` | GET |
| 查询工作包 | `/api/v3/work_packages` | GET |
| 查询工时 | `/api/v3/time_entries` | GET |

### Filter 格式
```python
filter_structure = [
    {
        "字段名": {
            "operator": "操作符",
            "values": ["值"]
        }
    }
]
filter_json_str = json.dumps(filter_structure, ensure_ascii=False)
url = f"{BASE_URL}/api/v3/endpoint?filters={filter_json_str}"
```
