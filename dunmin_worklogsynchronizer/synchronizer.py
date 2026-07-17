import requests
import json
import os

# 获取配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

# 从配置文件加载配置
def _load_config() -> dict:
    """加载配置文件"""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# 获取配置
_config = _load_config()

OPENPROJECT_KEY = _config["openproject"]["api_key"]
OPENPROJECT_URL = _config["openproject"]["base_url"]
REDMINE_KEY = _config["redmine"]["api_key"]
REDMINE_URL = _config["redmine"]["base_url"]


def _get_headers() -> dict:
    """获取 OpenProject API 请求头"""
    return {
        "Authorization": f"Bearer {OPENPROJECT_KEY}",
        "Content-Type": "application/json"
    }


# ==================== 查询功能 ====================

def get_tasks(opUserLogin:str,project_identifier: str) -> dict:
    """
    查询项目详情

    Args:
        opUserLogin: 用户登录名
        project_identifier: 项目名称或标识符

    Returns:
        项目信息字典，包含 id, name, identifier, description, status 等
    """
    user_id = get_user_info(opUserLogin)["id"]
    project_id = get_project_info(project_identifier)["id"]
    return get_work_packages(project_id,user_id)

def get_project_info(project_identifier: str) -> dict:
    """
    查询项目详情
    
    Args:
        project_identifier: 项目名称或标识符
        
    Returns:
        项目信息字典，包含 id, name, identifier, description, status 等
    """
    headers = _get_headers()
    
    filter_structure = [
        {
            "name_and_identifier": {
                "operator": "=",
                "values": [project_identifier]
            }
        }
    ]
    filter_json_str = json.dumps(filter_structure, ensure_ascii=False)
    
    response = requests.get(
        f"{OPENPROJECT_URL}/api/v3/projects?filters={filter_json_str}",
        headers=headers
    )
    response.raise_for_status()
    data = response.json()
    
    projects = data.get("_embedded", {}).get("elements", [])
    if not projects:
        raise ValueError(f"未找到项目: {project_identifier}")
    
    project = projects[0]
    return {
        "id": project.get("id"),
        "name": project.get("name"),
        "identifier": project.get("identifier"),
        "description": project.get("description", {}).get("raw", ""),
        "status": project.get("status"),
        "created_at": project.get("createdAt"),
        "updated_at": project.get("updatedAt")
    }


def get_project_members(project_id: int) -> list:
    """
    查询项目成员列表
    
    Args:
        project_id: 项目ID
        
    Returns:
        成员列表，每项包含 id, name, email, role
    """
    headers = _get_headers()
    
    response = requests.get(
        f"{OPENPROJECT_URL}/api/v3/projects/{project_id}/memberships",
        headers=headers
    )
    response.raise_for_status()
    data = response.json()
    
    members = []
    for membership in data.get("_embedded", {}).get("memberships", []):
        principal = membership.get("_embedded", {}).get("principal", {})
        roles = membership.get("_embedded", {}).get("roles", [])
        
        member = {
            "id": principal.get("id"),
            "name": principal.get("name"),
            "email": principal.get("email"),
            "login": principal.get("login"),
            "roles": [role.get("name") for role in roles]
        }
        members.append(member)
    
    return members


def get_work_packages(project_id: int, user_id: int = None) -> list:
    """
    查询工作包/条目列表
    
    Args:
        project_id: 项目ID
        user_id: 负责人用户ID（可选）
        
    Returns:
        工作包列表，每项包含 id, subject, description, status, priority, assignee, created_at, updated_at
    """
    headers = _get_headers()
    
    filter_structure = [
        {
            "project": {
                "operator": "=",
                "values": [str(project_id)]
            }
        }
    ]
    
    if user_id:
        filter_structure.append({
            "assigned_to": {
                "operator": "=",
                "values": [str(user_id)]
            }
        })
    
    filter_json_str = json.dumps(filter_structure, ensure_ascii=False)
    
    response = requests.get(
        f"{OPENPROJECT_URL}/api/v3/work_packages?filters={filter_json_str}",
        headers=headers
    )
    response.raise_for_status()
    data = response.json()
    
    work_packages = []
    for wp in data.get("_embedded", {}).get("elements", []):
        assignee = wp.get("_embedded", {}).get("assignee", {})
        
        work_package = {
            "id": wp.get("id"),
            "subject": wp.get("subject"),
            "description": wp.get("description", {}).get("raw", ""),
            "status": wp.get("status", {}).get("name"),
            "priority": wp.get("priority", {}).get("name"),
            "type": wp.get("type", {}).get("name"),
            "assignee": {
                "id": assignee.get("id"),
                "name": assignee.get("name"),
                "login": assignee.get("login")
            } if assignee else None,
            "start_date": wp.get("startDate"),
            "due_date": wp.get("dueDate"),
            "created_at": wp.get("createdAt"),
            "updated_at": wp.get("updatedAt")
        }
        work_packages.append(work_package)
    
    return work_packages


def get_user_info(user_login: str) -> dict:
    """
    查询用户信息
    
    Args:
        user_login: 用户登录名
        
    Returns:
        用户信息字典，包含 id, name, email, login
    """
    headers = _get_headers()
    
    filter_structure = [
        {
            "login": {
                "operator": "=",
                "values": [user_login]
            }
        }
    ]
    filter_json_str = json.dumps(filter_structure, ensure_ascii=False)
    
    response = requests.get(
        f"{OPENPROJECT_URL}/api/v3/users?filters={filter_json_str}",
        headers=headers
    )
    response.raise_for_status()
    data = response.json()
    
    users = data.get("_embedded", {}).get("elements", [])
    if not users:
        raise ValueError(f"未找到用户: {user_login}")
    
    user = users[0]
    return {
        "id": user.get("id"),
        "name": user.get("name"),
        "email": user.get("email"),
        "login": user.get("login"),
        "admin": user.get("admin"),
        "status": user.get("status")
    }


def get_time_entries(project_id: int, user_id: int = None, start_date: str = None) -> list:
    """
    查询工时记录列表
    
    Args:
        project_id: 项目ID
        user_id: 用户ID（可选）
        start_date: 起始日期，格式 YYYY-MM-DD（可选）
        
    Returns:
        工时记录列表，每项包含 id, work_package, user, hours, comment, spent_on, activity
    """
    headers = _get_headers()
    
    filter_structure = [
        {
            "project": {
                "operator": "=",
                "values": [str(project_id)]
            }
        }
    ]
    
    if user_id:
        filter_structure.append({
            "user": {
                "operator": "=",
                "values": [str(user_id)]
            }
        })
    
    if start_date:
        filter_structure.append({
            "spent_on": {
                "operator": ">=",
                "values": [start_date]
            }
        })
    
    filter_json_str = json.dumps(filter_structure, ensure_ascii=False)
    
    response = requests.get(
        f"{OPENPROJECT_URL}/api/v3/time_entries?filters={filter_json_str}",
        headers=headers
    )
    response.raise_for_status()
    data = response.json()
    
    time_entries = []
    for entry in data.get("_embedded", {}).get("elements", []):
        work_package = entry.get("_embedded", {}).get("workPackage", {})
        user = entry.get("_embedded", {}).get("user", {})
        activity = entry.get("_embedded", {}).get("activity", {})
        
        time_entry = {
            "id": entry.get("id"),
            "hours": entry.get("hours"),
            "comment": entry.get("comment"),
            "spent_on": entry.get("spentOn"),
            "work_package": {
                "id": work_package.get("id"),
                "subject": work_package.get("subject")
            } if work_package else None,
            "user": {
                "id": user.get("id"),
                "name": user.get("name"),
                "login": user.get("login")
            } if user else None,
            "activity": {
                "id": activity.get("id"),
                "name": activity.get("name")
            } if activity else None
        }
        time_entries.append(time_entry)
    
    return time_entries

def sync_tasks(opUserLogin:str, opProjectId:str, redmineUserLogin:str, redmineProjectId:str, startDate:str) -> None:
    """
    从OpenProject同步任务到Redmine
    
    Args:
        opUserLogin: OpenProject用户名
        opProjectId: OpenProject项目名称或标识符
        redmineUserLogin: Redmine用户名
        redmineProjectId: Redmine项目ID
        startDate: 同步起始日期 (格式: YYYY-MM-DD)
    """
    headers = {
        "Authorization": f"Bearer {OPENPROJECT_KEY}",
        "Content-Type": "application/json"
    }

    # 1. 通过项目名称/标识符查询真实项目ID
    real_project_id = _get_openproject_project_id(opProjectId, headers)
    
    # 2. 从OpenProject获取任务列表
    op_work_packages = _fetch_openproject_tasks(
        opUserLogin, 
        real_project_id, 
        startDate,
        headers
    )
    
    # 3. 获取Redmine项目信息
    redmine_project = _get_redmine_project(redmineProjectId)
    
    # 4. 同步每个任务到Redmine
    for work_package in op_work_packages:
        _sync_single_task(
            work_package,
            redmineProjectId,
            redmine_project,
            headers
        )

def _get_openproject_project_id(project_identifier: str, headers: dict) -> int:
    """
    通过项目名称/标识符查询真实的OpenProject项目ID
    
    Args:
        project_identifier: 项目名称或标识符
        headers: 请求头
        
    Returns:
        项目ID
    """
    filter_structure = [
        {
          "name_and_identifier":{
            "operator": "=",  # 对应文档中的操作符
            "values": [project_identifier]  # 值必须是一个列表
          }
        }
    ]
    filter_json_str = json.dumps(filter_structure, ensure_ascii=False)

    response = requests.get(
        f"{OPENPROJECT_URL}/api/v3/projects?filters={filter_json_str}",
        headers=headers
    )
    response.raise_for_status()
    data = response.json()
    
    projects = data.get("_embedded", {}).get("elements", [])
    if projects:
        return projects[0]["id"]

    
    raise ValueError(f"未找到项目: {project_identifier}")

def _fetch_openproject_tasks(user_login: str, project_id: str, start_date: str, headers: dict) -> list:
    """从OpenProject API获取任务列表"""
    # 获取用户ID
    user_id = _get_openproject_user_id(user_login, project_id, headers)

    filter_structure = [
        {
            "project": {
                "operator": "=",  # 对应文档中的操作符
                "values": [project_id]  # 值必须是一个列表
            }
        },
        {
            "assigned_to": {
                "operator": "=",  # 对应文档中的操作符
                "values": [user_id]  # 值必须是一个列表
            }
        }
    ]
    filter_json_str = json.dumps(filter_structure, ensure_ascii=False)

    response = requests.get(
        f"{OPENPROJECT_URL}/api/v3/work_packages?filters={filter_json_str}",
        headers=headers
    )

    response.raise_for_status()
    data = response.json()
    
    return data.get("_embedded", {}).get("elements", [])



def _get_openproject_user_id(user_login: str, project_id: str, headers: dict) -> int:
    filter_structure = [
        {
            "login": {
                "operator": "=",  # 对应文档中的操作符
                "values": [user_login]  # 值必须是一个列表
            }
        }
    ]
    filter_json_str = json.dumps(filter_structure, ensure_ascii=False)

    response = requests.get(
        f"{OPENPROJECT_URL}/api/v3/users?filters={filter_json_str}", headers=headers
    )


    response.raise_for_status()
    data = response.json()
    users = data.get("_embedded", {}).get("elements", [])
    if len(users)>0:
        return users[0]["id"]

    raise ValueError(f"未找到用户: {user_login}")

def _get_redmine_project(project_id: str) -> dict:
    """获取Redmine项目信息"""
    response = requests.get(
        f"{REDMINE_URL}/projects/{project_id}.json",
        headers={"X-Redmine-API-Key": REDMINE_KEY}
    )
    response.raise_for_status()
    return response.json().get("project", {})

def _sync_single_task(work_package: dict, redmine_project_id: str, redmine_project: dict, headers: dict) -> None:
    """同步单个任务到Redmine"""
    # 映射OpenProject状态到Redmine状态
    status_mapping = {
        "open": "New",
        "in_progress": "In Progress",
        "closed": "Closed",
        "resolved": "Resolved"
    }
    
    op_status = work_package.get("status", {}).get("name", "open").lower()
    redmine_status = status_mapping.get(op_status, "New")
    
    # 获取或创建主题
    subject = work_package.get("subject", "")
    description = work_package.get("description", {}).get("raw", "")
    
    # 构建Redmine问题数据
    issue_data = {
        "issue": {
            "project_id": redmine_project_id,
            "subject": subject,
            "description": description,
            "status_name": redmine_status,
            "tracker_id": 1,  # 默认使用Bug tracker，可根据需要调整
            "priority_id": _map_priority(work_package.get("priority", {}).get("name", "normal"))
        }
    }
    
    # 处理负责人
    assignee = work_package.get("_embedded", {}).get("assignee", {})
    if assignee:
        redmine_user_id = _get_redmine_user_by_login(assignee.get("login"))
        if redmine_user_id:
            issue_data["issue"]["assigned_to_id"] = redmine_user_id
    
    # 尝试通过自定义字段匹配现有任务
    op_id = work_package.get("id")
    existing_issue = _find_existing_redmine_issue(redmine_project_id, op_id)
    
    if existing_issue:
        # 更新现有任务
        _update_redmine_issue(existing_issue["id"], issue_data)
    else:
        # 创建新任务
        issue_data["issue"]["custom_fields"] = [
            {"id": 1, "value": str(op_id)}  # 假设自定义字段1存储OpenProject ID
        ]
        _create_redmine_issue(issue_data)

def _map_priority(op_priority: str) -> int:
    """映射OpenProject优先级到Redmine优先级ID"""
    priority_map = {
        "low": 1,
        "normal": 2,
        "high": 3,
        "urgent": 4,
        "immediate": 5
    }
    return priority_map.get(op_priority.lower(), 2)

def _get_redmine_user_by_login(login: str) -> int:
    """根据登录名获取Redmine用户ID"""
    response = requests.get(
        f"{REDMINE_URL}/users.json?login={login}",
        headers={"X-Redmine-API-Key": REDMINE_KEY}
    )
    if response.status_code == 200:
        users = response.json().get("users", [])
        if users:
            return users[0]["id"]
    return None

def _find_existing_redmine_issue(project_id: str, op_id: int) -> dict:
    """在Redmine中查找对应的任务"""
    response = requests.get(
        f"{REDMINE_URL}/issues.json?project_id={project_id}",
        headers={"X-Redmine-API-Key": REDMINE_KEY}
    )
    
    if response.status_code == 200:
        issues = response.json().get("issues", [])
        for issue in issues:
            custom_fields = issue.get("custom_fields", [])
            for cf in custom_fields:
                if cf.get("id") == 1 and str(op_id) in str(cf.get("value", "")):
                    return issue
    return None

def _create_redmine_issue(issue_data: dict) -> dict:
    """在Redmine创建任务"""
    response = requests.post(
        f"{REDMINE_URL}/issues.json",
        headers={"X-Redmine-API-Key": REDMINE_KEY},
        json=issue_data
    )
    response.raise_for_status()
    return response.json().get("issue", {})

def _update_redmine_issue(issue_id: int, issue_data: dict) -> dict:
    """更新Redmine任务"""
    response = requests.put(
        f"{REDMINE_URL}/issues/{issue_id}.json",
        headers={"X-Redmine-API-Key": REDMINE_KEY},
        json=issue_data
    )
    response.raise_for_status()
    return response.json().get("issue", {})
