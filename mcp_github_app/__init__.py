"""
MCP GitHub App - GitHub App MCP服务器

这是一个功能完整的MCP服务器，提供GitHub App的完整功能，
包括仓库访问、文件读取、创建分支、提交PR等操作。

特性:
- 🎯 完整的GitHub App API功能支持
- 🚀 优化的工具结构
- 🔐 支持GitHub App认证
- 📁 仓库文件管理：读取、创建、更新文件
- 🌿 分支管理：创建、列出分支
- 🔀 Pull Request管理：创建、查看、更新PR
- 📝 提交管理：创建提交、查看提交历史
- 🎯 AI大模型友好，参数描述清晰

作者: chre3
版本: 1.0.0
许可证: MIT
"""

__version__ = "1.0.0"
__author__ = "chre3"
__email__ = "chremata3@gmail.com"
__description__ = "GitHub App MCP服务器，提供完整的GitHub操作功能"

from .server import MCPGitHubAppServer

__all__ = ["MCPGitHubAppServer"]
