# MCP GitHub App Server

<div align="center">

**🚀 Powerful GitHub App MCP Server | 强大的GitHub App MCP服务器**

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/chre3/mcp-github-app)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org)

**📖 Documentation | 文档**
- [English Documentation](README_EN.md) | [中文文档](README_CN.md)

</div>

---

## 🎯 Core Tools

| Tool | Function | Status |
|------|----------|--------|
| `read_file` | 📄 Read Repository Files | ✅ 100% |
| `create_branch` | 🌿 Branch Management | ✅ 100% |
| `create_or_update_file` | ✏️ File Management | ✅ 100% |
| `create_pull_request` | 🔀 Pull Request Management | ✅ 100% |
| `list_branches` | 📋 List Branches | ✅ 100% |
| `get_repository` | 📦 Repository Information | ✅ 100% |
| `list_pull_requests` | 📝 List Pull Requests | ✅ 100% |
| `get_pull_request` | 🔍 Get PR Details | ✅ 100% |
| `get_help` | ❓ Help Information | ✅ 100% |

## 📋 Feature Overview

### 📁 File Management
- ✅ Read repository files (text and binary)
- ✅ Create new files
- ✅ Update existing files

### 🌿 Branch Management
- ✅ Create new branches
- ✅ List all branches
- ✅ Create branches from specific commits or branches

### 🔀 Pull Request Management
- ✅ Create Pull Requests
- ✅ List Pull Requests (with status filtering)
- ✅ Get PR details and status

### 📦 Repository Management
- ✅ Get repository information
- ✅ View repository statistics

## ⚡ Quick Start

```bash
# Install
pip install -r requirements.txt

# Run
python -m mcp_github_app
```

## 🎯 Key Benefits

- ✅ **Complete Coverage**: All GitHub App core functions
- ✅ **Smart Authentication**: Automatic JWT and installation token management
- ✅ **AI Optimized**: Clear parameters & intelligent error handling
- ✅ **Full CRUD**: Complete create, read, update operations
- ✅ **Secure**: Safe credential management

## 📋 Requirements

- Python 3.8+
- GitHub App created and installed
- GitHub App with necessary permissions

## 🔑 Authentication Setup

Set up GitHub App credentials in environment variables:

```bash
export GITHUB_APP_ID="your_app_id"
export GITHUB_APP_PRIVATE_KEY_PATH="/path/to/private-key.pem"
export GITHUB_APP_INSTALLATION_ID="your_installation_id"
```

Or add to MCP configuration:

```json
{
  "mcpServers": {
    "github-app": {
      "command": "python",
      "args": ["-m", "mcp_github_app"],
      "env": {
        "GITHUB_APP_ID": "your_app_id",
        "GITHUB_APP_PRIVATE_KEY_PATH": "/path/to/private-key.pem",
        "GITHUB_APP_INSTALLATION_ID": "your_installation_id"
      }
    }
  }
}
```

---

<div align="center">

**Made with ❤️ for GitHub automation**

[View Full Documentation](README_EN.md) | [查看完整文档](README_CN.md)

</div>