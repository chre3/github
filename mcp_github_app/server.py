#!/usr/bin/env python3
"""
MCP GitHub App 服务器 - 包含所有GitHub App功能
支持仓库访问、文件读取、创建分支、提交PR等完整功能
"""

import os
import sys
import json
import time
import base64
import binascii
import re
import random
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

# GitHub App认证相关
import jwt
import requests
from github import Github
from github.GithubException import GithubException

class MCPGitHubAppServer:
    """GitHub App MCP服务器"""
    
    def __init__(self):
        self.app_id = os.getenv("GITHUB_APP_ID")
        self.private_key_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
        self.private_key = os.getenv("GITHUB_APP_PRIVATE_KEY")
        self.installation_id = os.getenv("GITHUB_APP_INSTALLATION_ID")
        self.github = None
        self._installation_token = None
        self._token_expires_at = None
        
        print("🎯 MCP GitHub App v1.0 已初始化", file=sys.stderr)
        print(f"   📦 App ID: {self.app_id if self.app_id else '未设置'}", file=sys.stderr)
        print(f"   🔑 Installation ID: {self.installation_id if self.installation_id else '未设置'}", file=sys.stderr)
        print("   🚀 GitHub App功能支持!", file=sys.stderr)

    def _load_private_key(self) -> str:
        """加载私钥"""
        if self.private_key:
            return self.private_key
        elif self.private_key_path and os.path.exists(self.private_key_path):
            with open(self.private_key_path, 'r') as f:
                return f.read()
        else:
            raise ValueError("未设置GITHUB_APP_PRIVATE_KEY或GITHUB_APP_PRIVATE_KEY_PATH")

    def _generate_jwt(self) -> str:
        """生成JWT token用于GitHub App认证"""
        try:
            private_key = self._load_private_key()
            
            # JWT payload
            now = int(time.time())
            payload = {
                'iat': now - 60,  # 提前60秒，避免时钟偏差
                'exp': now + (10 * 60),  # 10分钟有效期
                'iss': self.app_id  # App ID
            }
            
            # 生成JWT
            token = jwt.encode(payload, private_key, algorithm='RS256')
            return token
        except Exception as e:
            raise ValueError(f"无法生成JWT: {str(e)}")

    def _get_installation_token(self) -> str:
        """获取installation access token"""
        # 如果token还在有效期内，直接返回
        if self._installation_token and self._token_expires_at:
            if time.time() < self._token_expires_at - 60:  # 提前1分钟刷新
                return self._installation_token
        
        try:
            jwt_token = self._generate_jwt()
            
            # 获取installation access token
            url = f"https://api.github.com/app/installations/{self.installation_id}/access_tokens"
            headers = {
                'Authorization': f'Bearer {jwt_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.post(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            self._installation_token = data['token']
            # token有效期通常是1小时，我们设置55分钟过期
            expires_at_str = data.get('expires_at', '')
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                self._token_expires_at = expires_at.timestamp()
            else:
                self._token_expires_at = time.time() + (55 * 60)
            
            return self._installation_token
        except Exception as e:
            raise ValueError(f"无法获取installation token: {str(e)}")

    def _get_github_client(self) -> Github:
        """获取GitHub客户端"""
        if self.github is None:
            token = self._get_installation_token()
            self.github = Github(token)
        return self.github

    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理MCP初始化请求"""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {
                    "listChanged": True
                },
                "resources": {
                    "subscribe": True,
                    "listChanged": True
                },
                "prompts": {
                    "listChanged": True
                }
            },
            "serverInfo": {
                "name": "github-app",
                "version": "1.0.0",
                "description": "GitHub App MCP服务器，提供完整的GitHub操作功能"
            }
        }

    def handle_tools_list(self) -> Dict[str, Any]:
        """处理工具列表请求"""
        tools = [
            # 读取文件工具
            {
                "name": "read_file",
                "description": "读取GitHub仓库中的文件内容。支持文本文件和二进制文件的base64编码。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "仓库所有者（用户名或组织名）"
                        },
                        "repo": {
                            "type": "string",
                            "description": "仓库名称"
                        },
                        "path": {
                            "type": "string",
                            "description": "文件路径（相对于仓库根目录）"
                        },
                        "ref": {
                            "type": "string",
                            "description": "分支、标签或提交SHA（可选，默认为默认分支）"
                        }
                    },
                    "required": ["owner", "repo", "path"]
                }
            },
            
            # 创建分支工具
            {
                "name": "create_branch",
                "description": "在GitHub仓库中创建新分支。基于指定的源分支或提交创建。⚠️ 重要规则：1) 严格禁止：如果用户要求'从X分支提交PR'或'提交PR'，绝对不要创建新分支！必须使用现有分支。只有在用户明确说'创建新分支'或'创建feature分支'时才使用此工具。2) 分支命名规则：所有新创建的分支名称必须以 'c3/' 开头（例如：c3/update-readme, c3/fix-issue-123）。如果提供的分支名不是以 'c3/' 开头，系统会自动添加 'c3/' 前缀。3) 在提交PR的场景中，创建新分支会导致PR失败，因为新分支和源分支相同。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "仓库所有者（用户名或组织名）"
                        },
                        "repo": {
                            "type": "string",
                            "description": "仓库名称"
                        },
                        "branch_name": {
                            "type": "string",
                            "description": "新分支名称。必须遵循规则：分支名必须以 'c3/' 开头（例如：c3/update-readme, c3/fix-issue-123）。如果提供的名称不是以 'c3/' 开头，系统会自动添加 'c3/' 前缀。"
                        },
                        "source_branch": {
                            "type": "string",
                            "description": "源分支名称（可选，默认为默认分支，通常是main或master）"
                        },
                        "source_sha": {
                            "type": "string",
                            "description": "源提交SHA（可选，如果提供则优先于source_branch）"
                        }
                    },
                    "required": ["owner", "repo", "branch_name"]
                }
            },
            
            # 创建或更新文件工具
            {
                "name": "create_or_update_file",
                "description": "在GitHub仓库中创建或更新文件。如果文件不存在则创建，存在则更新。⚠️ 重要：如果用户要求'从X分支提交PR并更新文件'，应该：1) 在指定的分支（branch参数）上更新文件。2) 不要创建新分支，直接更新现有分支。3) 更新后，从该分支创建PR到其他分支。如果不指定branch参数，文件将提交到默认分支（通常是main）。避免重复调用，一次调用即可完成文件更新。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "仓库所有者（用户名或组织名）"
                        },
                        "repo": {
                            "type": "string",
                            "description": "仓库名称"
                        },
                        "path": {
                            "type": "string",
                            "description": "文件路径（相对于仓库根目录）"
                        },
                        "content": {
                            "type": "string",
                            "description": "文件内容（文本内容或base64编码的二进制内容）"
                        },
                        "message": {
                            "type": "string",
                            "description": "提交消息"
                        },
                        "branch": {
                            "type": "string",
                            "description": "目标分支（可选，默认为默认分支）"
                        },
                        "is_base64": {
                            "type": "boolean",
                            "description": "内容是否为base64编码（可选，默认为false）"
                        }
                    },
                    "required": ["owner", "repo", "path", "content", "message"]
                }
            },
            
            # 创建Pull Request工具
            {
                "name": "create_pull_request",
                "description": "创建GitHub Pull Request。将源分支（head）的更改合并到目标分支（base）。⚠️ 重要规则：1) 如果用户要求'从X分支提交PR'或'提交PR'，必须使用指定的head分支作为head参数。2) 如果base未指定，会自动选择其他分支作为base（如果head是main，base会选择test/google_ads等其他分支）。3) 如果用户要求更新文件，应该先调用create_or_update_file在head分支上更新文件，然后再调用create_pull_request。4) 本工具会自动检查是否已存在相同head->base组合的PR（例如main->test），如果已存在，会自动创建新分支（分支名格式：c3/YYYY-MM-DD/HHMMSS，例如c3/2025-11-04/171045），然后从新分支创建PR。注意：同一个分支可以创建多个PR到不同的目标分支（例如main可以同时创建到test、google_ads等），只对相同head->base组合的PR自动创建新分支。5) 避免重复调用，一次调用即可完成PR创建。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "仓库所有者（用户名或组织名）"
                        },
                        "repo": {
                            "type": "string",
                            "description": "仓库名称"
                        },
                        "title": {
                            "type": "string",
                            "description": "PR标题（描述PR的主要目的）"
                        },
                        "body": {
                            "type": "string",
                            "description": "PR描述/正文（可选，详细说明更改内容）"
                        },
                        "head": {
                            "type": "string",
                            "description": "源分支名称（可选，包含更改的分支。重要：如果用户明确指定了分支（如'从main提交PR'），必须提供head参数。如果不指定且用户也未明确要求，才自动选择最新有提交的分支）"
                        },
                        "base": {
                            "type": "string",
                            "description": "目标分支名称（可选，要合并到的分支，默认是main。如果用户说'从X提交PR'，X通常是head，base需要指定或自动选择其他分支）"
                        }
                    },
                    "required": ["owner", "repo", "title"]
                }
            },
            
            # 列出分支工具
            {
                "name": "list_branches",
                "description": "列出GitHub仓库的所有分支及其最后提交时间。用于确定哪个分支有最新提交，以便创建PR。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "仓库所有者（用户名或组织名）"
                        },
                        "repo": {
                            "type": "string",
                            "description": "仓库名称"
                        }
                    },
                    "required": ["owner", "repo"]
                }
            },
            
            # 获取仓库信息工具
            {
                "name": "get_repository",
                "description": "获取GitHub仓库的详细信息。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "仓库所有者（用户名或组织名）"
                        },
                        "repo": {
                            "type": "string",
                            "description": "仓库名称"
                        }
                    },
                    "required": ["owner", "repo"]
                }
            },
            
            # 列出PR工具
            {
                "name": "list_pull_requests",
                "description": "列出GitHub仓库的Pull Request。支持按状态过滤。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "仓库所有者（用户名或组织名）"
                        },
                        "repo": {
                            "type": "string",
                            "description": "仓库名称"
                        },
                        "state": {
                            "type": "string",
                            "enum": ["open", "closed", "all"],
                            "description": "PR状态：open(打开的), closed(关闭的), all(全部)",
                            "default": "open"
                        }
                    },
                    "required": ["owner", "repo"]
                }
            },
            
            # 获取PR详情工具
            {
                "name": "get_pull_request",
                "description": "获取GitHub Pull Request的详细信息。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "仓库所有者（用户名或组织名）"
                        },
                        "repo": {
                            "type": "string",
                            "description": "仓库名称"
                        },
                        "pr_number": {
                            "type": "integer",
                            "description": "PR编号"
                        }
                    },
                    "required": ["owner", "repo", "pr_number"]
                }
            },
            
            # 列出仓库工具
            {
                "name": "list_repositories",
                "description": "列出GitHub仓库。可以列出当前GitHub App安装可访问的所有仓库，或者指定用户/组织的仓库。支持按类型（all/public/private）和排序方式过滤。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "用户或组织名（可选，如果不提供则列出App安装可访问的所有仓库）"
                        },
                        "type": {
                            "type": "string",
                            "enum": ["all", "owner", "public", "private", "member"],
                            "description": "仓库类型：all(全部), owner(拥有的), public(公开), private(私有), member(成员)",
                            "default": "all"
                        },
                        "sort": {
                            "type": "string",
                            "enum": ["created", "updated", "pushed", "full_name"],
                            "description": "排序方式：created(创建时间), updated(更新时间), pushed(推送时间), full_name(名称)",
                            "default": "updated"
                        },
                        "direction": {
                            "type": "string",
                            "enum": ["asc", "desc"],
                            "description": "排序方向：asc(升序), desc(降序)",
                            "default": "desc"
                        }
                    },
                    "required": []
                }
            },
            
            # 帮助工具
            {
                "name": "get_help",
                "description": "获取GitHub App MCP服务器帮助信息和使用指南",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        ]
        
        return {"tools": tools}

    def handle_tools_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理工具调用请求"""
        try:
            if name == "get_help":
                return self.get_help()
            elif name == "read_file":
                return self.read_file(
                    arguments.get("owner"),
                    arguments.get("repo"),
                    arguments.get("path"),
                    arguments.get("ref")
                )
            elif name == "create_branch":
                return self.create_branch(
                    arguments.get("owner"),
                    arguments.get("repo"),
                    arguments.get("branch_name"),
                    arguments.get("source_branch"),
                    arguments.get("source_sha")
                )
            elif name == "create_or_update_file":
                return self.create_or_update_file(
                    arguments.get("owner"),
                    arguments.get("repo"),
                    arguments.get("path"),
                    arguments.get("content"),
                    arguments.get("message"),
                    arguments.get("branch"),
                    arguments.get("is_base64", False)
                )
            elif name == "create_pull_request":
                return self.create_pull_request(
                    arguments.get("owner"),
                    arguments.get("repo"),
                    arguments.get("title"),
                    arguments.get("head"),  # head 是可选的，如果未指定会自动选择
                    arguments.get("base"),  # base 是可选的，默认是main
                    arguments.get("body")   # body 是可选的
                )
            elif name == "list_branches":
                return self.list_branches(
                    arguments.get("owner"),
                    arguments.get("repo")
                )
            elif name == "get_repository":
                return self.get_repository(
                    arguments.get("owner"),
                    arguments.get("repo")
                )
            elif name == "list_pull_requests":
                return self.list_pull_requests(
                    arguments.get("owner"),
                    arguments.get("repo"),
                    arguments.get("state", "open")
                )
            elif name == "get_pull_request":
                return self.get_pull_request(
                    arguments.get("owner"),
                    arguments.get("repo"),
                    arguments.get("pr_number")
                )
            elif name == "list_repositories":
                return self.list_repositories(
                    arguments.get("owner"),
                    arguments.get("type", "all"),
                    arguments.get("sort", "updated"),
                    arguments.get("direction", "desc")
                )
            else:
                return {"error": f"Unknown tool: {name}"}
        except Exception as e:
            return {"error": str(e)}

    def get_help(self) -> Dict[str, Any]:
        """获取帮助信息"""
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "success": True,
                        "message": "GitHub App MCP服务器帮助",
                        "data": {
                            "server": "🎯 MCP GitHub App",
                            "version": "1.0.0",
                            "total_functions": 10,
                            "tools": [
                                {"name": "read_file", "description": "读取仓库文件内容"},
                                {"name": "create_branch", "description": "创建新分支"},
                                {"name": "create_or_update_file", "description": "创建或更新文件"},
                                {"name": "create_pull_request", "description": "创建Pull Request"},
                                {"name": "list_branches", "description": "列出所有分支"},
                                {"name": "get_repository", "description": "获取仓库信息"},
                                {"name": "list_repositories", "description": "列出仓库列表（支持列出用户/组织的仓库或App安装可访问的所有仓库）"},
                                {"name": "list_pull_requests", "description": "列出Pull Request"},
                                {"name": "get_pull_request", "description": "获取PR详情"},
                                {"name": "get_help", "description": "帮助信息"}
                            ],
                            "environment_variables": {
                                "GITHUB_APP_ID": "GitHub App ID（必需）",
                                "GITHUB_APP_PRIVATE_KEY": "GitHub App私钥内容（必需，或使用GITHUB_APP_PRIVATE_KEY_PATH）",
                                "GITHUB_APP_PRIVATE_KEY_PATH": "GitHub App私钥文件路径（可选）",
                                "GITHUB_APP_INSTALLATION_ID": "GitHub App安装ID（必需）"
                            },
                            "usage_tips": [
                                "使用 list_repositories 列出所有可访问的仓库（不提供owner参数时列出App安装的所有仓库）",
                                "使用 list_repositories 并指定owner参数列出特定用户/组织的仓库",
                                "使用 read_file 读取仓库文件",
                                "使用 create_branch 创建新分支",
                                "使用 create_or_update_file 创建或更新文件",
                                "使用 create_pull_request 创建PR",
                                "使用 list_branches 查看所有分支",
                                "使用 list_pull_requests 查看PR列表"
                            ]
                        },
                        "timestamp": datetime.now().isoformat()
                    }, ensure_ascii=False, indent=2)
                }
            ]
        }

    def read_file(self, owner: str, repo: str, path: str, ref: str = None) -> Dict[str, Any]:
        """读取仓库文件"""
        try:
            github = self._get_github_client()
            repository = github.get_repo(f"{owner}/{repo}")
            
            # 如果 ref 未指定，使用默认分支
            if not ref:
                ref = repository.default_branch
            
            try:
                file_content = repository.get_contents(path, ref=ref)
            except GithubException as e:
                # 如果文件不存在，返回明确的错误信息
                if hasattr(e, 'status') and e.status == 404:
                    error_msg = e.data.get('message', 'Not Found') if hasattr(e, 'data') and isinstance(e.data, dict) else str(e)
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({
                                    "success": False,
                                    "error": f"文件 '{path}' 在分支 '{ref}' 中不存在: {error_msg}",
                                    "status": 404,
                                    "error_type": type(e).__name__
                                }, ensure_ascii=False, indent=2)
                            }
                        ]
                    }
                else:
                    raise  # 重新抛出其他 GithubException
            
            result = {
                "success": True,
                "owner": owner,
                "repo": repo,
                "path": path,
                "ref": ref or repository.default_branch,
                "size": file_content.size,
                "sha": file_content.sha,
                "encoding": file_content.encoding,
                "type": file_content.type
            }
            
            # 处理文件内容
            # PyGithub的get_contents返回的对象有decoded_content属性（解码后的字节）
            # 和content属性（base64编码的字符串）
            try:
                if hasattr(file_content, 'decoded_content') and file_content.decoded_content:
                    # 尝试解码为UTF-8文本
                    try:
                        decoded_text = file_content.decoded_content.decode('utf-8')
                        result["content"] = decoded_text
                        result["is_binary"] = False
                    except UnicodeDecodeError:
                        # 如果无法解码为UTF-8，可能是二进制文件
                        result["content_base64"] = base64.b64encode(file_content.decoded_content).decode('utf-8')
                        result["is_binary"] = True
                elif file_content.content:
                    # 如果没有decoded_content，尝试从base64编码的content解码
                    try:
                        content_clean = file_content.content.replace('\n', '').replace('\r', '')
                        decoded_bytes = base64.b64decode(content_clean)
                        decoded_text = decoded_bytes.decode('utf-8')
                        result["content"] = decoded_text
                        result["is_binary"] = False
                    except (binascii.Error, UnicodeDecodeError):
                        # 解码失败，返回base64编码
                        result["content_base64"] = file_content.content
                        result["is_binary"] = True
                else:
                    result["content"] = ""
                    result["is_binary"] = False
            except Exception as e:
                # 如果所有方法都失败，返回base64编码的内容
                result["content_base64"] = file_content.content if hasattr(file_content, 'content') else ""
                result["is_binary"] = True
                result["decode_error"] = str(e)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, indent=2)
                    }
                ]
            }
        except GithubException as e:
            # 获取更详细的错误信息
            error_msg = str(e) if str(e) else "Unknown error"
            if hasattr(e, 'data') and isinstance(e.data, dict):
                error_msg = e.data.get('message', error_msg)
            elif hasattr(e, 'message') and e.message:
                error_msg = e.message
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": f"GitHub API错误: {error_msg}",
                            "status": e.status if hasattr(e, 'status') else None,
                            "error_type": type(e).__name__
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }
        except Exception as e:
            # 获取详细的错误信息
            error_msg = str(e) if str(e) else f"Unknown error: {type(e).__name__}"
            error_type = type(e).__name__
            
            # 如果是 AssertionError 或其他非 GitHubException，尝试获取更多信息
            if error_type == "AssertionError":
                # AssertionError 通常没有详细信息，尝试从异常属性获取
                error_msg = f"Assertion failed: {error_msg}. This may indicate a GitHub API issue or internal error."
            elif hasattr(e, 'args') and e.args:
                error_msg = str(e.args[0]) if e.args else error_msg
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": error_msg,
                            "error_type": error_type
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }

    def create_branch(self, owner: str, repo: str, branch_name: str, 
                     source_branch: str = None, source_sha: str = None) -> Dict[str, Any]:
        """创建新分支"""
        try:
            github = self._get_github_client()
            repository = github.get_repo(f"{owner}/{repo}")
            
            # 验证并规范化分支名称：必须遵循 c3/xxx 格式
            original_branch_name = branch_name
            normalized_branch_name = branch_name.strip()
            
            # 如果分支名不是以 c3/ 开头，自动添加前缀
            if not normalized_branch_name.startswith('c3/'):
                # 移除可能存在的其他前缀（如 feature/, fix/ 等）
                if '/' in normalized_branch_name:
                    # 如果已经有前缀，只保留最后一个部分
                    parts = normalized_branch_name.split('/')
                    normalized_branch_name = f"c3/{parts[-1]}"
                else:
                    # 如果没有前缀，直接添加 c3/
                    normalized_branch_name = f"c3/{normalized_branch_name}"
            
            # 验证分支名称格式（不能包含特殊字符）
            # GitHub分支名规则：不能包含空格、连续的点、特殊字符等
            # 移除不允许的字符
            normalized_branch_name = re.sub(r'[^\w\-/]', '-', normalized_branch_name)
            # 移除连续的斜杠和点
            normalized_branch_name = re.sub(r'[/]{2,}', '/', normalized_branch_name)
            normalized_branch_name = re.sub(r'\.{2,}', '.', normalized_branch_name)
            # 移除开头和结尾的斜杠、点、连字符
            normalized_branch_name = normalized_branch_name.strip('/.-')
            
            # 确保仍然以 c3/ 开头
            if not normalized_branch_name.startswith('c3/'):
                normalized_branch_name = f"c3/{normalized_branch_name}"
            
            # 确定源引用
            if source_sha:
                source_ref = source_sha
            elif source_branch:
                source_ref = repository.get_branch(source_branch).commit.sha
            else:
                # 使用默认分支
                default_branch = repository.default_branch
                source_ref = repository.get_branch(default_branch).commit.sha
            
            # 创建新分支
            repository.create_git_ref(
                ref=f"refs/heads/{normalized_branch_name}",
                sha=source_ref
            )
            
            # 构建返回消息
            message = f"分支 {normalized_branch_name} 已成功创建"
            if original_branch_name != normalized_branch_name:
                message += f"（原始名称: {original_branch_name}，已自动规范化）"
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": True,
                            "owner": owner,
                            "repo": repo,
                            "branch_name": normalized_branch_name,
                            "original_branch_name": original_branch_name if original_branch_name != normalized_branch_name else None,
                            "source_ref": source_ref,
                            "message": message,
                            "note": "分支名称已自动规范化，遵循 c3/xxx 命名规则"
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }
        except GithubException as e:
            # 获取更详细的错误信息
            error_msg = str(e) if str(e) else "Unknown error"
            if hasattr(e, 'data') and isinstance(e.data, dict):
                error_msg = e.data.get('message', error_msg)
            elif hasattr(e, 'message') and e.message:
                error_msg = e.message
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": f"GitHub API错误: {error_msg}",
                            "status": e.status if hasattr(e, 'status') else None,
                            "error_type": type(e).__name__
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }
        except Exception as e:
            # 获取详细的错误信息
            error_msg = str(e) if str(e) else f"Unknown error: {type(e).__name__}"
            error_type = type(e).__name__
            
            # 如果是 AssertionError 或其他非 GitHubException，尝试获取更多信息
            if error_type == "AssertionError":
                # AssertionError 通常没有详细信息，尝试从异常属性获取
                error_msg = f"Assertion failed: {error_msg}. This may indicate a GitHub API issue or internal error."
            elif hasattr(e, 'args') and e.args:
                error_msg = str(e.args[0]) if e.args else error_msg
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": error_msg,
                            "error_type": error_type
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }

    def create_or_update_file(self, owner: str, repo: str, path: str, 
                              content: str, message: str, branch: str = None,
                              is_base64: bool = False) -> Dict[str, Any]:
        """创建或更新文件"""
        try:
            github = self._get_github_client()
            repository = github.get_repo(f"{owner}/{repo}")
            
            if not branch:
                branch = repository.default_branch
            
            # 检查文件是否存在
            try:
                file_content = repository.get_contents(path, ref=branch)
                sha = file_content.sha
                action = "updated"
            except GithubException:
                sha = None
                action = "created"
            
            # 准备内容
            if is_base64:
                file_content_base64 = content
            else:
                file_content_base64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            # 创建或更新文件
            if sha:
                result = repository.update_file(
                    path=path,
                    message=message,
                    content=file_content_base64,
                    sha=sha,
                    branch=branch
                )
            else:
                result = repository.create_file(
                    path=path,
                    message=message,
                    content=file_content_base64,
                    branch=branch
                )
            
            # 安全地获取commit信息
            commit_obj = result.get("commit")
            commit_info = {}
            if commit_obj:
                commit_info["sha"] = commit_obj.sha
                commit_info["url"] = commit_obj.html_url
                # commit.commit 可能是 None，需要安全访问
                if hasattr(commit_obj, 'commit') and commit_obj.commit:
                    commit_info["message"] = commit_obj.commit.message
                else:
                    # 如果没有 commit.commit，使用传入的 message
                    commit_info["message"] = message
            
            # 安全地获取content信息
            content_obj = result.get("content")
            content_info = {}
            if content_obj:
                content_info["sha"] = content_obj.sha
                content_info["url"] = content_obj.html_url
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": True,
                            "owner": owner,
                            "repo": repo,
                            "path": path,
                            "branch": branch,
                            "action": action,
                            "commit": commit_info,
                            "content": content_info
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }
        except GithubException as e:
            # 获取更详细的错误信息
            error_msg = str(e) if str(e) else "Unknown error"
            if hasattr(e, 'data') and isinstance(e.data, dict):
                error_msg = e.data.get('message', error_msg)
            elif hasattr(e, 'message') and e.message:
                error_msg = e.message
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": f"GitHub API错误: {error_msg}",
                            "status": e.status if hasattr(e, 'status') else None,
                            "error_type": type(e).__name__
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }
        except Exception as e:
            # 获取详细的错误信息
            error_msg = str(e) if str(e) else f"Unknown error: {type(e).__name__}"
            error_type = type(e).__name__
            
            # 如果是 AssertionError 或其他非 GitHubException，尝试获取更多信息
            if error_type == "AssertionError":
                # AssertionError 通常没有详细信息，尝试从异常属性获取
                error_msg = f"Assertion failed: {error_msg}. This may indicate a GitHub API issue or internal error."
            elif hasattr(e, 'args') and e.args:
                error_msg = str(e.args[0]) if e.args else error_msg
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": error_msg,
                            "error_type": error_type
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }

    def create_pull_request(self, owner: str, repo: str, title: str, 
                           head: str = None, base: str = None, body: str = None) -> Dict[str, Any]:
        """创建Pull Request"""
        try:
            github = self._get_github_client()
            repository = github.get_repo(f"{owner}/{repo}")
            
            # 如果base未指定，使用默认分支
            if not base:
                base = repository.default_branch
            
            # 如果head未指定，自动选择最新有提交的分支（排除base分支）
            # 注意：只有在用户未明确指定head时才自动选择
            if not head:
                # 获取所有分支，按最后提交时间排序
                branches = list(repository.get_branches())
                if not branches:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({
                                    "success": False,
                                    "error": "仓库中没有分支，无法创建PR"
                                }, ensure_ascii=False, indent=2)
                            }
                        ]
                    }
                
                # 排除base分支，然后按最后提交时间排序
                branches_with_commits = []
                for branch in branches:
                    if branch.name != base:
                        try:
                            # 获取分支的最后提交时间
                            commit = branch.commit
                            pushed_at = None
                            
                            # 尝试从commit获取提交时间
                            if hasattr(commit, 'commit') and commit.commit:
                                if hasattr(commit.commit, 'committer') and commit.commit.committer:
                                    pushed_at = commit.commit.committer.date
                                elif hasattr(commit.commit, 'author') and commit.commit.author:
                                    pushed_at = commit.commit.author.date
                            
                            # 如果还是None，使用当前时间作为fallback
                            if pushed_at is None:
                                pushed_at = datetime.now()
                            
                            branches_with_commits.append({
                                'name': branch.name,
                                'commit_sha': commit.sha,
                                'pushed_at': pushed_at
                            })
                        except Exception as e:
                            # 如果获取分支信息失败，跳过
                            continue
                
                if not branches_with_commits:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({
                                    "success": False,
                                    "error": f"除了默认分支 '{base}' 外，没有其他分支可以创建PR",
                                    "available_branches": [b.name for b in branches],
                                    "suggestion": "请先在其他分支上创建提交，或者指定一个分支来创建PR"
                                }, ensure_ascii=False, indent=2)
                            }
                        ]
                    }
                
                # 按提交时间排序，选择最新的
                branches_with_commits.sort(key=lambda x: x['pushed_at'] if x['pushed_at'] else datetime.min, reverse=True)
                
                # 选择最新有提交的分支（不检查是否已有PR，允许创建多个PR）
                head = branches_with_commits[0]['name']
            
            # 如果head和base相同，需要自动选择base为其他分支
            if head == base:
                # 获取所有分支，选择一个不同于head的分支作为base
                # 优先选择非默认分支，且按最后提交时间排序
                branches = list(repository.get_branches())
                other_branches = []
                
                for branch in branches:
                    if branch.name != head:
                        try:
                            commit = branch.commit
                            pushed_at = None
                            
                            if hasattr(commit, 'commit') and commit.commit:
                                if hasattr(commit.commit, 'committer') and commit.commit.committer:
                                    pushed_at = commit.commit.committer.date
                                elif hasattr(commit.commit, 'author') and commit.commit.author:
                                    pushed_at = commit.commit.author.date
                            
                            if pushed_at is None:
                                pushed_at = datetime.now()
                            
                            other_branches.append({
                                'name': branch.name,
                                'pushed_at': pushed_at,
                                'is_default': branch.name == repository.default_branch
                            })
                        except:
                            other_branches.append({
                                'name': branch.name,
                                'pushed_at': datetime.now(),
                                'is_default': branch.name == repository.default_branch
                            })
                
                if not other_branches:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({
                                    "success": False,
                                    "error": f"无法创建PR：源分支 '{head}' 和目标分支 '{base}' 相同，且仓库中没有其他分支",
                                    "suggestion": "请指定一个不同的目标分支，或者先创建其他分支"
                                }, ensure_ascii=False, indent=2)
                            }
                        ]
                    }
                
                # 优先选择非默认分支，然后按提交时间排序
                other_branches.sort(key=lambda x: (x['is_default'], -(x['pushed_at'].timestamp() if hasattr(x['pushed_at'], 'timestamp') else 0)), reverse=False)
                base = other_branches[0]['name']
            
            try:
                base_branch = repository.get_branch(base)
            except GithubException as e:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({
                                "success": False,
                                "error": f"目标分支 '{base}' 不存在: {e.data.get('message', str(e)) if hasattr(e, 'data') and isinstance(e.data, dict) else str(e)}",
                                "status": e.status if hasattr(e, 'status') else None,
                                "error_type": type(e).__name__
                            }, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            
            # 检查是否已经存在相同的PR（head -> base）
            # 如果已存在，自动创建新分支（使用c3/YYYY-MM-DD/HHMMSS格式）然后创建PR
            new_branch_created = False
            original_head = head
            try:
                # 先获取head分支，以便后续使用
                head_branch = repository.get_branch(head)
                
                # 获取所有打开的PR，然后检查是否有相同head和base的PR
                all_prs = list(repository.get_pulls(state='open'))
                for existing_pr in all_prs:
                    # 检查head和base是否匹配
                    # 注意：head可能是 "owner:branch" 格式或 "branch" 格式
                    existing_head = existing_pr.head.ref if hasattr(existing_pr.head, 'ref') else str(existing_pr.head)
                    existing_base = existing_pr.base.ref if hasattr(existing_pr.base, 'ref') else str(existing_pr.base)
                    
                    # 比较分支名称（忽略owner前缀）
                    if existing_head == head and existing_base == base:
                        # 如果已存在相同的PR，自动创建新分支（使用c3/YYYY-MM-DD/HHMMSS格式）
                        # 生成新分支名称：c3/YYYY-MM-DD/HHMMSS
                        now = datetime.now()
                        date_str = now.strftime('%Y-%m-%d')
                        time_str = now.strftime('%H%M%S')
                        new_branch_name = f"c3/{date_str}/{time_str}"
                        
                        # 从head分支创建新分支
                        head_sha = head_branch.commit.sha
                        
                        try:
                            # 创建新分支
                            repository.create_git_ref(
                                ref=f"refs/heads/{new_branch_name}",
                                sha=head_sha
                            )
                            new_branch_created = True
                        except GithubException as branch_error:
                            # 如果分支已存在（极小概率），添加时间戳后缀
                            if hasattr(branch_error, 'status') and branch_error.status == 422:
                                new_branch_name = f"c3/{date_str}/{time_str}{random.randint(10, 99)}"
                                repository.create_git_ref(
                                    ref=f"refs/heads/{new_branch_name}",
                                    sha=head_sha
                                )
                                new_branch_created = True
                            else:
                                raise
                        
                        # 使用新创建的分支作为head来创建PR
                        head = new_branch_name
                        break  # 跳出循环，继续创建PR
            except Exception as e:
                # 如果检查失败，继续尝试创建PR
                pass
            
            # 重新获取head分支（可能已经更新为新分支）
            try:
                head_branch = repository.get_branch(head)
            except GithubException as e:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({
                                "success": False,
                                "error": f"源分支 '{head}' 不存在: {e.data.get('message', str(e)) if hasattr(e, 'data') and isinstance(e.data, dict) else str(e)}",
                                "status": e.status if hasattr(e, 'status') else None,
                                "error_type": type(e).__name__
                            }, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            
            # 检查分支是否有差异（通过比较SHA）
            if head_branch.commit.sha == base_branch.commit.sha:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({
                                "success": False,
                                "error": f"分支 '{head}' 和 '{base}' 没有差异，无法创建 PR。两个分支指向相同的提交。",
                                "head_sha": head_branch.commit.sha,
                                "base_sha": base_branch.commit.sha,
                                "suggestion": "请确保源分支包含新的提交，或者先在新分支上进行修改后再创建PR。"
                            }, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            
            # 检查源分支的所有提交是否已经在目标分支中
            # 通过比较分支历史来判断
            try:
                # 获取两个分支的提交历史
                head_commits = list(repository.get_commits(sha=head_branch.commit.sha))
                base_commits = list(repository.get_commits(sha=base_branch.commit.sha))
                
                # 检查head分支的提交是否都在base分支中
                head_commit_shas = {commit.sha for commit in head_commits[:10]}  # 检查最近10个提交
                base_commit_shas = {commit.sha for commit in base_commits[:10]}
                
                # 如果head的所有提交都在base中，说明没有新提交
                if head_commit_shas.issubset(base_commit_shas) and head_branch.commit.sha != base_branch.commit.sha:
                    # 进一步检查head分支是否有base分支没有的提交
                    head_only_commits = []
                    for commit in head_commits:
                        if commit.sha not in base_commit_shas:
                            head_only_commits.append(commit.sha)
                            if len(head_only_commits) >= 5:
                                break
                    
                    if not head_only_commits:
                        return {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps({
                                        "success": False,
                                        "error": f"分支 '{head}' 相对于 '{base}' 没有新的提交。无法创建 PR。",
                                        "head_sha": head_branch.commit.sha,
                                        "base_sha": base_branch.commit.sha,
                                        "suggestion": "源分支的所有提交已经包含在目标分支中。请先在新分支上创建新的提交，然后再创建PR。"
                                    }, ensure_ascii=False, indent=2)
                                }
                            ]
                        }
            except Exception as e:
                # 如果检查历史失败，继续尝试创建PR，让GitHub API来判断
                pass
            
            # 创建PR
            pr = repository.create_pull(
                title=title,
                body=body or "",
                head=head,
                base=base
            )
            
            # 构建返回结果
            result = {
                "success": True,
                "owner": owner,
                "repo": repo,
                "pull_request": {
                    "number": pr.number,
                    "title": pr.title,
                    "body": pr.body,
                    "state": pr.state,
                    "head": pr.head.ref,
                    "base": pr.base.ref,
                    "url": pr.html_url,
                    "created_at": pr.created_at.isoformat() if pr.created_at else None
                }
            }
            
            # 如果创建了新分支，在返回结果中说明
            if new_branch_created:
                result["message"] = f"已存在相同方向的PR（{original_head} -> {base}），已自动创建新分支 {head} 并创建PR"
                result["new_branch"] = head
                result["original_head"] = original_head
                result["note"] = "分支命名遵循 c3/YYYY-MM-DD/HHMMSS 格式"
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, indent=2)
                    }
                ]
            }
        except GithubException as e:
            # 获取更详细的错误信息
            error_msg = str(e) if str(e) else "Unknown error"
            if hasattr(e, 'data') and isinstance(e.data, dict):
                error_msg = e.data.get('message', error_msg)
            elif hasattr(e, 'message') and e.message:
                error_msg = e.message
            
            # 提取详细的错误信息（特别是422错误中的errors数组）
            error_details = []
            is_duplicate_pr = False
            if hasattr(e, 'data') and isinstance(e.data, dict):
                if 'errors' in e.data and isinstance(e.data['errors'], list):
                    for err in e.data['errors']:
                        if isinstance(err, dict):
                            err_msg = err.get('message', '')
                            if err_msg:
                                error_details.append(err_msg)
                                # 检查是否是重复PR的错误
                                if 'pull request already exists' in err_msg.lower() or 'already exists' in err_msg.lower():
                                    is_duplicate_pr = True
                                # 如果错误消息提到"No commits"，使用更友好的提示
                                if 'No commits' in err_msg or 'no commits' in err_msg.lower():
                                    error_msg = f"源分支 '{head}' 相对于目标分支 '{base}' 没有新的提交。所有提交已经包含在目标分支中。"
            
            # 注意：重复PR错误现在会在创建PR前自动处理（创建新分支），所以这里不需要特殊处理
            
            response_data = {
                "success": False,
                "error": f"GitHub API错误: {error_msg}",
                "status": e.status if hasattr(e, 'status') else None,
                "error_type": type(e).__name__
            }
            
            if error_details:
                response_data["error_details"] = error_details
            
            # 如果是422错误，添加建议
            if hasattr(e, 'status') and e.status == 422:
                if is_duplicate_pr:
                    response_data["suggestion"] = "已存在相同方向的PR。如果确实需要创建新PR，请先关闭或合并现有PR，或者使用不同的分支。"
                else:
                    response_data["suggestion"] = "请确保源分支包含目标分支没有的新提交。如果需要创建PR，请先在新分支上进行修改并提交。"
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(response_data, ensure_ascii=False, indent=2)
                    }
                ]
            }
        except Exception as e:
            # 获取详细的错误信息
            error_msg = str(e) if str(e) else f"Unknown error: {type(e).__name__}"
            error_type = type(e).__name__
            
            # 如果是 AssertionError 或其他非 GitHubException，尝试获取更多信息
            if error_type == "AssertionError":
                # AssertionError 通常没有详细信息，尝试从异常属性获取
                error_msg = f"Assertion failed: {error_msg}. This may indicate a GitHub API issue or internal error."
            elif hasattr(e, 'args') and e.args:
                error_msg = str(e.args[0]) if e.args else error_msg
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": error_msg,
                            "error_type": error_type
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }

    def list_branches(self, owner: str, repo: str) -> Dict[str, Any]:
        """列出所有分支"""
        try:
            github = self._get_github_client()
            repository = github.get_repo(f"{owner}/{repo}")
            
            branches = []
            for branch in repository.get_branches():
                commit = branch.commit
                pushed_at = None
                
                # 获取最后提交时间
                if hasattr(commit, 'commit') and commit.commit:
                    if hasattr(commit.commit, 'committer') and commit.commit.committer:
                        pushed_at = commit.commit.committer.date.isoformat() if commit.commit.committer.date else None
                    elif hasattr(commit.commit, 'author') and commit.commit.author:
                        pushed_at = commit.commit.author.date.isoformat() if commit.commit.author.date else None
                
                branches.append({
                    "name": branch.name,
                    "sha": branch.commit.sha,
                    "protected": branch.protected,
                    "last_commit_at": pushed_at,
                    "is_default": branch.name == repository.default_branch
                })
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": True,
                            "owner": owner,
                            "repo": repo,
                            "branches": branches,
                            "total": len(branches)
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }
        except GithubException as e:
            # 获取更详细的错误信息
            error_msg = str(e) if str(e) else "Unknown error"
            if hasattr(e, 'data') and isinstance(e.data, dict):
                error_msg = e.data.get('message', error_msg)
            elif hasattr(e, 'message') and e.message:
                error_msg = e.message
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": f"GitHub API错误: {error_msg}",
                            "status": e.status if hasattr(e, 'status') else None,
                            "error_type": type(e).__name__
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }
        except Exception as e:
            # 获取详细的错误信息
            error_msg = str(e) if str(e) else f"Unknown error: {type(e).__name__}"
            error_type = type(e).__name__
            
            # 如果是 AssertionError 或其他非 GitHubException，尝试获取更多信息
            if error_type == "AssertionError":
                # AssertionError 通常没有详细信息，尝试从异常属性获取
                error_msg = f"Assertion failed: {error_msg}. This may indicate a GitHub API issue or internal error."
            elif hasattr(e, 'args') and e.args:
                error_msg = str(e.args[0]) if e.args else error_msg
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": error_msg,
                            "error_type": error_type
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }

    def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """获取仓库信息"""
        try:
            github = self._get_github_client()
            repository = github.get_repo(f"{owner}/{repo}")
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": True,
                            "repository": {
                                "id": repository.id,
                                "name": repository.name,
                                "full_name": repository.full_name,
                                "owner": repository.owner.login,
                                "description": repository.description,
                                "url": repository.html_url,
                                "default_branch": repository.default_branch,
                                "private": repository.private,
                                "fork": repository.fork,
                                "archived": repository.archived,
                                "created_at": repository.created_at.isoformat() if repository.created_at else None,
                                "updated_at": repository.updated_at.isoformat() if repository.updated_at else None,
                                "pushed_at": repository.pushed_at.isoformat() if repository.pushed_at else None,
                                "stargazers_count": repository.stargazers_count,
                                "watchers_count": repository.watchers_count,
                                "forks_count": repository.forks_count,
                                "open_issues_count": repository.open_issues_count,
                                "language": repository.language
                            }
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }
        except GithubException as e:
            # 获取更详细的错误信息
            error_msg = str(e) if str(e) else "Unknown error"
            if hasattr(e, 'data') and isinstance(e.data, dict):
                error_msg = e.data.get('message', error_msg)
            elif hasattr(e, 'message') and e.message:
                error_msg = e.message
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": f"GitHub API错误: {error_msg}",
                            "status": e.status if hasattr(e, 'status') else None,
                            "error_type": type(e).__name__
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }
        except Exception as e:
            # 获取详细的错误信息
            error_msg = str(e) if str(e) else f"Unknown error: {type(e).__name__}"
            error_type = type(e).__name__
            
            # 如果是 AssertionError 或其他非 GitHubException，尝试获取更多信息
            if error_type == "AssertionError":
                # AssertionError 通常没有详细信息，尝试从异常属性获取
                error_msg = f"Assertion failed: {error_msg}. This may indicate a GitHub API issue or internal error."
            elif hasattr(e, 'args') and e.args:
                error_msg = str(e.args[0]) if e.args else error_msg
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": error_msg,
                            "error_type": error_type
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }

    def list_pull_requests(self, owner: str, repo: str, state: str = "open") -> Dict[str, Any]:
        """列出Pull Request"""
        try:
            github = self._get_github_client()
            repository = github.get_repo(f"{owner}/{repo}")
            
            prs = []
            for pr in repository.get_pulls(state=state):
                prs.append({
                    "number": pr.number,
                    "title": pr.title,
                    "state": pr.state,
                    "head": pr.head.ref,
                    "base": pr.base.ref,
                    "url": pr.html_url,
                    "created_at": pr.created_at.isoformat() if pr.created_at else None,
                    "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
                    "user": pr.user.login if pr.user else None
                })
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": True,
                            "owner": owner,
                            "repo": repo,
                            "state": state,
                            "pull_requests": prs,
                            "total": len(prs)
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }
        except GithubException as e:
            # 获取更详细的错误信息
            error_msg = str(e) if str(e) else "Unknown error"
            if hasattr(e, 'data') and isinstance(e.data, dict):
                error_msg = e.data.get('message', error_msg)
            elif hasattr(e, 'message') and e.message:
                error_msg = e.message
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": f"GitHub API错误: {error_msg}",
                            "status": e.status if hasattr(e, 'status') else None,
                            "error_type": type(e).__name__
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }
        except Exception as e:
            # 获取详细的错误信息
            error_msg = str(e) if str(e) else f"Unknown error: {type(e).__name__}"
            error_type = type(e).__name__
            
            # 如果是 AssertionError 或其他非 GitHubException，尝试获取更多信息
            if error_type == "AssertionError":
                # AssertionError 通常没有详细信息，尝试从异常属性获取
                error_msg = f"Assertion failed: {error_msg}. This may indicate a GitHub API issue or internal error."
            elif hasattr(e, 'args') and e.args:
                error_msg = str(e.args[0]) if e.args else error_msg
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": error_msg,
                            "error_type": error_type
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }

    def get_pull_request(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """获取Pull Request详情"""
        try:
            github = self._get_github_client()
            repository = github.get_repo(f"{owner}/{repo}")
            pr = repository.get_pull(pr_number)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": True,
                            "owner": owner,
                            "repo": repo,
                            "pull_request": {
                                "number": pr.number,
                                "title": pr.title,
                                "body": pr.body,
                                "state": pr.state,
                                "head": pr.head.ref,
                                "base": pr.base.ref,
                                "url": pr.html_url,
                                "created_at": pr.created_at.isoformat() if pr.created_at else None,
                                "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
                                "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                                "merged": pr.merged,
                                "mergeable": pr.mergeable,
                                "user": pr.user.login if pr.user else None,
                                "draft": pr.draft,
                                "additions": pr.additions,
                                "deletions": pr.deletions,
                                "changed_files": pr.changed_files
                            }
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }
        except GithubException as e:
            # 获取更详细的错误信息
            error_msg = str(e) if str(e) else "Unknown error"
            if hasattr(e, 'data') and isinstance(e.data, dict):
                error_msg = e.data.get('message', error_msg)
            elif hasattr(e, 'message') and e.message:
                error_msg = e.message
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": f"GitHub API错误: {error_msg}",
                            "status": e.status if hasattr(e, 'status') else None,
                            "error_type": type(e).__name__
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }
        except Exception as e:
            # 获取详细的错误信息
            error_msg = str(e) if str(e) else f"Unknown error: {type(e).__name__}"
            error_type = type(e).__name__
            
            # 如果是 AssertionError 或其他非 GitHubException，尝试获取更多信息
            if error_type == "AssertionError":
                # AssertionError 通常没有详细信息，尝试从异常属性获取
                error_msg = f"Assertion failed: {error_msg}. This may indicate a GitHub API issue or internal error."
            elif hasattr(e, 'args') and e.args:
                error_msg = str(e.args[0]) if e.args else error_msg
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": error_msg,
                            "error_type": error_type
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }

    def list_repositories(self, owner: str = None, repo_type: str = "all", 
                         sort: str = "updated", direction: str = "desc") -> Dict[str, Any]:
        """列出仓库"""
        try:
            github = self._get_github_client()
            repositories = []
            
            if owner:
                # 列出指定用户或组织的仓库
                # 对于 GitHub App installation token，我们需要先获取所有可访问的仓库，然后过滤
                # 因为 installation token 可能无法直接访问任意用户的仓库列表
                try:
                    # 首先尝试直接获取用户/组织的仓库（如果 installation 有权限）
                    try:
                        user = github.get_user(owner)
                        for repo in user.get_repos(type=repo_type, sort=sort, direction=direction):
                            repositories.append({
                                "id": repo.id,
                                "name": repo.name,
                                "full_name": repo.full_name,
                                "owner": repo.owner.login,
                                "description": repo.description,
                                "url": repo.html_url,
                                "default_branch": repo.default_branch,
                                "private": repo.private,
                                "fork": repo.fork,
                                "archived": repo.archived,
                                "created_at": repo.created_at.isoformat() if repo.created_at else None,
                                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                                "pushed_at": repo.pushed_at.isoformat() if repo.pushed_at else None,
                                "stargazers_count": repo.stargazers_count,
                                "watchers_count": repo.watchers_count,
                                "forks_count": repo.forks_count,
                                "open_issues_count": repo.open_issues_count,
                                "language": repo.language
                            })
                    except GithubException:
                        # 如果获取用户失败，尝试作为组织
                        try:
                            org = github.get_organization(owner)
                            for repo in org.get_repos(type=repo_type, sort=sort, direction=direction):
                                repositories.append({
                                    "id": repo.id,
                                    "name": repo.name,
                                    "full_name": repo.full_name,
                                    "owner": repo.owner.login,
                                    "description": repo.description,
                                    "url": repo.html_url,
                                    "default_branch": repo.default_branch,
                                    "private": repo.private,
                                    "fork": repo.fork,
                                    "archived": repo.archived,
                                    "created_at": repo.created_at.isoformat() if repo.created_at else None,
                                    "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                                    "pushed_at": repo.pushed_at.isoformat() if repo.pushed_at else None,
                                    "stargazers_count": repo.stargazers_count,
                                    "watchers_count": repo.watchers_count,
                                    "forks_count": repo.forks_count,
                                    "open_issues_count": repo.open_issues_count,
                                    "language": repo.language
                                })
                        except GithubException:
                            # 如果直接获取失败，尝试从安装的仓库中过滤
                            # 获取所有安装可访问的仓库，然后过滤出指定 owner 的仓库
                            token = self._get_installation_token()
                            headers = {
                                'Authorization': f'token {token}',
                                'Accept': 'application/vnd.github.v3+json'
                            }
                            url = "https://api.github.com/installation/repositories"
                            page = 1
                            per_page = 100
                            while True:
                                params = {"page": page, "per_page": per_page}
                                response = requests.get(url, headers=headers, params=params)
                                response.raise_for_status()
                                data = response.json()
                                repos_data = data.get("repositories", [])
                                if not repos_data:
                                    break
                                # 过滤出指定 owner 的仓库
                                for repo_data in repos_data:
                                    repo_owner_login = None
                                    if isinstance(repo_data.get("owner"), dict):
                                        repo_owner_login = repo_data.get("owner", {}).get("login")
                                    elif repo_data.get("owner"):
                                        repo_owner_login = repo_data.get("owner")
                                    if repo_owner_login and repo_owner_login.lower() == owner.lower():
                                        repositories.append({
                                            "id": repo_data.get("id"),
                                            "name": repo_data.get("name"),
                                            "full_name": repo_data.get("full_name"),
                                            "owner": repo_owner_login,
                                            "description": repo_data.get("description"),
                                            "url": repo_data.get("html_url"),
                                            "default_branch": repo_data.get("default_branch"),
                                            "private": repo_data.get("private", False),
                                            "fork": repo_data.get("fork", False),
                                            "archived": repo_data.get("archived", False),
                                            "created_at": repo_data.get("created_at"),
                                            "updated_at": repo_data.get("updated_at"),
                                            "pushed_at": repo_data.get("pushed_at"),
                                            "stargazers_count": repo_data.get("stargazers_count", 0),
                                            "watchers_count": repo_data.get("watchers_count", 0),
                                            "forks_count": repo_data.get("forks_count", 0),
                                            "open_issues_count": repo_data.get("open_issues_count", 0),
                                            "language": repo_data.get("language")
                                        })
                                total_count = data.get("total_count", 0)
                                if len(repos_data) < per_page:
                                    break
                                page += 1
                except Exception as e:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({
                                    "success": False,
                                    "error": f"无法获取用户/组织 {owner} 的仓库: {str(e)}",
                                    "status": e.status if hasattr(e, 'status') else None
                                }, ensure_ascii=False, indent=2)
                            }
                        ]
                    }
            else:
                # 列出GitHub App安装可访问的所有仓库
                # 使用 GitHub API 的 /installation/repositories endpoint
                try:
                    token = self._get_installation_token()
                    headers = {
                        'Authorization': f'token {token}',
                        'Accept': 'application/vnd.github.v3+json'
                    }
                    
                    # 使用 /installation/repositories endpoint 获取 installation 可访问的所有仓库
                    url = "https://api.github.com/installation/repositories"
                    
                    # 处理分页
                    page = 1
                    per_page = 100
                    while True:
                        params = {"page": page, "per_page": per_page}
                        response = requests.get(url, headers=headers, params=params)
                        response.raise_for_status()
                        
                        data = response.json()
                        repos_data = data.get("repositories", [])
                        
                        if not repos_data:
                            break
                        
                        for repo_data in repos_data:
                            # 处理 owner 字段（可能是对象或字符串）
                            owner_login = None
                            if isinstance(repo_data.get("owner"), dict):
                                owner_login = repo_data.get("owner", {}).get("login")
                            elif repo_data.get("owner"):
                                owner_login = repo_data.get("owner")
                            
                            repositories.append({
                                "id": repo_data.get("id"),
                                "name": repo_data.get("name"),
                                "full_name": repo_data.get("full_name"),
                                "owner": owner_login,
                                "description": repo_data.get("description"),
                                "url": repo_data.get("html_url"),
                                "default_branch": repo_data.get("default_branch"),
                                "private": repo_data.get("private", False),
                                "fork": repo_data.get("fork", False),
                                "archived": repo_data.get("archived", False),
                                "created_at": repo_data.get("created_at"),
                                "updated_at": repo_data.get("updated_at"),
                                "pushed_at": repo_data.get("pushed_at"),
                                "stargazers_count": repo_data.get("stargazers_count", 0),
                                "watchers_count": repo_data.get("watchers_count", 0),
                                "forks_count": repo_data.get("forks_count", 0),
                                "open_issues_count": repo_data.get("open_issues_count", 0),
                                "language": repo_data.get("language")
                            })
                        
                        # 检查是否还有更多页面
                        # GitHub API 可能返回 total_count，我们可以用它来判断
                        total_count = data.get("total_count", 0)
                        if len(repositories) >= total_count or len(repos_data) < per_page:
                            break
                        page += 1
                    
                    # 按指定方式排序
                    if sort == "updated":
                        repositories.sort(key=lambda x: x["updated_at"] or "", reverse=(direction == "desc"))
                    elif sort == "created":
                        repositories.sort(key=lambda x: x["created_at"] or "", reverse=(direction == "desc"))
                    elif sort == "pushed":
                        repositories.sort(key=lambda x: x["pushed_at"] or "", reverse=(direction == "desc"))
                    elif sort == "full_name":
                        repositories.sort(key=lambda x: x["full_name"] or "", reverse=(direction == "desc"))
                    
                    # 过滤类型
                    if repo_type == "public":
                        repositories = [r for r in repositories if not r["private"]]
                    elif repo_type == "private":
                        repositories = [r for r in repositories if r["private"]]
                    
                except Exception as e:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({
                                    "success": False,
                                    "error": f"无法获取GitHub App安装的仓库: {str(e)}"
                                }, ensure_ascii=False, indent=2)
                            }
                        ]
                    }
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": True,
                            "owner": owner or "GitHub App Installation",
                            "type": repo_type,
                            "sort": sort,
                            "direction": direction,
                            "repositories": repositories,
                            "total": len(repositories)
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }
        except GithubException as e:
            # 获取更详细的错误信息
            error_msg = str(e) if str(e) else "Unknown error"
            if hasattr(e, 'data') and isinstance(e.data, dict):
                error_msg = e.data.get('message', error_msg)
            elif hasattr(e, 'message') and e.message:
                error_msg = e.message
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": f"GitHub API错误: {error_msg}",
                            "status": e.status if hasattr(e, 'status') else None,
                            "error_type": type(e).__name__
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }
        except Exception as e:
            # 获取详细的错误信息
            error_msg = str(e) if str(e) else f"Unknown error: {type(e).__name__}"
            error_type = type(e).__name__
            
            # 如果是 AssertionError 或其他非 GitHubException，尝试获取更多信息
            if error_type == "AssertionError":
                # AssertionError 通常没有详细信息，尝试从异常属性获取
                error_msg = f"Assertion failed: {error_msg}. This may indicate a GitHub API issue or internal error."
            elif hasattr(e, 'args') and e.args:
                error_msg = str(e.args[0]) if e.args else error_msg
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "success": False,
                            "error": error_msg,
                            "error_type": error_type
                        }, ensure_ascii=False, indent=2)
                    }
                ]
            }

def main():
    """主函数 - MCP协议服务器"""
    server = MCPGitHubAppServer()
    
    try:
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            
            try:
                request = json.loads(line.strip())
                method = request.get("method")
                params = request.get("params", {})
                request_id = request.get("id")
                
                if method == "initialize":
                    result = server.handle_initialize(params)
                elif method == "tools/list":
                    result = server.handle_tools_list()
                elif method == "tools/call":
                    result = server.handle_tools_call(
                        params.get("name"),
                        params.get("arguments", {})
                    )
                else:
                    result = {"error": f"Unknown method: {method}"}
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
                
                print(json.dumps(response))
                sys.stdout.flush()
                
            except json.JSONDecodeError:
                continue
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id") if "request" in locals() else None,
                    "error": {"code": -32603, "message": str(e)}
                }
                print(json.dumps(error_response))
                sys.stdout.flush()
                
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
