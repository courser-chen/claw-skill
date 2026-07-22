"""
阿里云 SLS 日志查询模块
"""
import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

try:
    from aliyun.log import LogServiceClient
    from aliyun.log.getlogsrequest import GetLogsRequest
    from aliyun.log.exceptions import LogException
except ImportError:
    raise ImportError("请安装 aliyun-log-python-sdk: pip install aliyun-log-python-sdk")

# 获取配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")


def _config_exists() -> bool:
    """检查配置文件是否存在且包含必要的凭证"""
    if not os.path.exists(CONFIG_FILE):
        return False
    try:
        config = _load_config()
        access_key_id = config.get("aliyun", {}).get("access_key_id", "").strip()
        access_key_secret = config.get("aliyun", {}).get("access_key_secret", "").strip()
        # 检查是否已配置（不是占位符且不为空）
        if (access_key_id and access_key_secret
                and access_key_id != "your-access-key-id"
                and access_key_secret != "your-access-key-secret"):
            return True
        return False
    except Exception:
        return False


def _ask_user_for_credentials() -> dict:
    """
    询问用户输入阿里云凭证信息
    
    在 AI 助手调用此函数时，应该向用户询问 AccessKey ID 和 AccessKey Secret，
    并询问 SLS 服务 endpoint。
    
    Returns:
        包含凭证的字典
    """
    print("=" * 60)
    print("首次使用阿里云 SLS 查询插件，需要配置阿里云凭证信息")
    print("=" * 60)
    print()
    print("请提供以下信息：")
    print("1. AccessKey ID")
    print("2. AccessKey Secret")
    print("3. SLS 服务 Endpoint（如：https://cn-hangzhou.log.aliyuncs.com）")
    print()
    print("获取方式：")
    print("- 登录阿里云控制台：https://ram.console.aliyun.com/manage/ak")
    print("- 创建或查看 AccessKey")
    print()
    
    access_key_id = input("请输入 AccessKey ID: ").strip()
    access_key_secret = input("请输入 AccessKey Secret: ").strip()
    endpoint = input("请输入 SLS Endpoint（默认 https://cn-hangzhou.log.aliyuncs.com）: ").strip()
    
    if not endpoint:
        endpoint = "https://cn-hangzhou.log.aliyuncs.com"
    
    if not access_key_id or not access_key_secret:
        raise ValueError("AccessKey ID 和 AccessKey Secret 不能为空")
    
    config = {
        "aliyun": {
            "access_key_id": access_key_id,
            "access_key_secret": access_key_secret,
            "endpoint": endpoint
        }
    }
    
    # 保存到配置文件
    _save_config(config)
    print()
    print(f"✓ 配置已保存到: {CONFIG_FILE}")
    
    return config


def _save_config(config: dict) -> None:
    """保存配置到文件"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _load_config() -> dict:
    """
    加载配置文件
    
    如果配置文件不存在或凭证未配置，会提示用户输入凭证信息
    """
    if not _config_exists():
        return _ask_user_for_credentials()
    
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _parse_time(time_str: str) -> int:
    """
    解析时间字符串为 Unix 时间戳
    
    Args:
        time_str: 时间字符串，支持 Unix 时间戳或 ISO 8601 格式
        
    Returns:
        Unix 时间戳（秒）
    """
    # 如果是数字字符串，直接返回
    if time_str.isdigit():
        return int(time_str)
    
    # 尝试解析 ISO 8601 格式
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return int(dt.timestamp())
    except ValueError:
        pass
    
    # 尝试解析相对时间
    if time_str.endswith("h"):
        hours = int(time_str[:-1])
        return int((datetime.now() - timedelta(hours=hours)).timestamp())
    elif time_str.endswith("m"):
        minutes = int(time_str[:-1])
        return int((datetime.now() - timedelta(minutes=minutes)).timestamp())
    elif time_str.endswith("d"):
        days = int(time_str[:-1])
        return int((datetime.now() - timedelta(days=days)).timestamp())
    
    raise ValueError(f"无法解析时间字符串: {time_str}")


def _get_sls_client() -> LogServiceClient:
    """获取 SLS 客户端"""
    config = _load_config()
    
    access_key_id = config["aliyun"]["access_key_id"]
    access_key_secret = config["aliyun"]["access_key_secret"]
    endpoint = config["aliyun"]["endpoint"]
    
    return LogServiceClient(
        endpoint=endpoint,
        access_key_id=access_key_id,
        access_key_secret=access_key_secret
    )


def init_credentials() -> Dict[str, Any]:
    """
    手动初始化凭证信息
    
    如果需要在代码中设置凭证（而非交互式询问），可调用此函数。
    
    Args:
        通常由 AI 助手通过 AskUserQuestion 工具获取用户输入后调用
        
    Returns:
        配置结果状态
    """
    config = _ask_user_for_credentials()
    return {
        "status": "success",
        "message": "凭证已保存",
        "config_path": CONFIG_FILE,
        "endpoint": config["aliyun"]["endpoint"]
    }


def query_logs(
    project_name: str,
    logstore_name: str,
    query: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    查询阿里云 SLS 日志
    
    Args:
        project_name: SLS 项目名称
        logstore_name: 日志库名称
        query: 查询语句，支持 SLS 语法
        start_time: 查询开始时间（Unix 时间戳或 ISO 8601 格式）。可选，默认 24 小时前
        end_time: 查询结束时间（Unix 时间戳或 ISO 8601 格式）。可选，默认为当前时间
        limit: 返回日志条数上限，默认 100，最大 1000
        
    Returns:
        查询结果字典，包含 total_count 和 logs 列表
        
    Example:
        >>> result = query_logs(
        ...     "my-project",
        ...     "my-logstore",
        ...     "level:ERROR"
        ... )
        >>> print(f"找到 {result['total_count']} 条日志")
    """
    # 如果未指定时间，默认查询 24 小时内的日志
    now = datetime.now()
    if end_time is None:
        end_timestamp = int(now.timestamp())
    else:
        end_timestamp = _parse_time(end_time)
    
    if start_time is None:
        start_timestamp = int((now - timedelta(hours=24)).timestamp())
    else:
        start_timestamp = _parse_time(start_time)
    
    # 限制返回条数
    limit = min(limit, 1000)
    
    # 获取客户端并查询
    client = _get_sls_client()
    
    request = GetLogsRequest(
        project_name=project_name,
        logstore_name=logstore_name,
        start_time=start_timestamp,
        end_time=end_timestamp,
        query=query,
        line=limit,
        offset=0
    )
    
    try:
        response = client.get_logs(request)
        
        logs = []
        for log in response.logs:
            log_entry = dict(log)
            logs.append(log_entry)
        
        return {
            "total_count": response.count,
            "logs": logs
        }
        
    except LogException as e:
        raise Exception(f"SLS 查询失败: {e.message}")
    except Exception as e:
        raise Exception(f"查询异常: {str(e)}")


def query_recent_logs(
    project_name: str,
    logstore_name: str,
    query: str,
    hours: int = 1,
    limit: int = 100
) -> Dict[str, Any]:
    """
    查询最近一段时间的日志（便捷方法）
    
    Args:
        project_name: SLS 项目名称
        logstore_name: 日志库名称
        query: 查询语句
        hours: 查询过去多少小时的日志，默认 1
        limit: 返回条数上限
        
    Returns:
        查询结果字典
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    return query_logs(
        project_name=project_name,
        logstore_name=logstore_name,
        start_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
        end_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
        query=query,
        limit=limit
    )
