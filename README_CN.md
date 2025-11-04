# MCP GitHub App 服务器

<div align="center">

**🚀 强大的GitHub App MCP服务器 | Powerful GitHub App MCP Server**

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/chre3/mcp-github-app)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org)

**📖 Documentation | 文档**
- [English Documentation](README_EN.md) | [中文文档](README_CN.md)

</div>

---

## 🎯 核心工具

| 工具 | 功能 | 状态 |
|------|------|------|
| `read_file` | 📄 读取仓库文件 | ✅ 100% |
| `create_branch` | 🌿 分支管理 | ✅ 100% |
| `create_or_update_file` | ✏️ 文件管理 | ✅ 100% |
| `create_pull_request` | 🔀 Pull Request管理 | ✅ 100% |
| `list_branches` | 📋 列出分支 | ✅ 100% |
| `get_repository` | 📦 仓库信息 | ✅ 100% |
| `list_pull_requests` | 📝 列出Pull Request | ✅ 100% |
| `get_pull_request` | 🔍 获取PR详情 | ✅ 100% |
| `get_help` | ❓ 帮助信息 | ✅ 100% |

## 📋 功能概览

### 📁 文件管理
- ✅ 读取仓库文件（支持文本和二进制文件）
- ✅ 创建新文件
- ✅ 更新现有文件
- ✅ 二进制文件自动base64编码/解码

### 🌿 分支管理
- ✅ 创建新分支
- ✅ 列出所有分支及详情
- ✅ 基于指定提交或分支创建分支
- ✅ 支持分支保护状态查看

### 🔀 Pull Request管理
- ✅ 创建Pull Request（包含标题和描述）
- ✅ 列出Pull Request（支持状态过滤：open, closed, all）
- ✅ 获取PR详情（状态、可合并性、更改等）
- ✅ 查看PR统计信息（新增、删除、更改文件数）

### 📦 仓库管理
- ✅ 获取仓库详细信息
- ✅ 查看仓库统计信息（星标、分支、问题等）
- ✅ 访问仓库元数据和设置

## ⚡ 快速开始

```bash
# 安装
pip install -r requirements.txt

# 运行
python -m mcp_github_app
```

## 🎯 关键优势

- ✅ **完整覆盖**: GitHub App所有核心功能
- ✅ **智能认证**: 自动JWT和安装令牌管理
- ✅ **AI优化**: 清晰的参数和智能错误处理
- ✅ **完整CRUD**: 支持创建、读取、更新操作
- ✅ **安全可靠**: 安全的凭证管理，自动令牌刷新

## 📋 要求

- Python 3.8+
- GitHub App已创建并安装
- GitHub App具有必要权限：
  - Contents: 读取和写入
  - Pull requests: 读取和写入
  - Metadata: 只读

## 🔑 认证设置

### 1. 创建GitHub App

1. 访问 [GitHub开发者设置](https://github.com/settings/apps)
2. 点击 "New GitHub App" 创建新应用
3. 设置应用权限：
   - **仓库权限**:
     - Contents: 读取和写入
     - Pull requests: 读取和写入
     - Metadata: 只读
4. 生成并下载私钥
5. 安装应用到仓库或组织
6. 获取App ID和Installation ID

### 2. 环境变量

在环境变量中设置认证凭据：

```bash
# GitHub App ID（必需）
export GITHUB_APP_ID="your_app_id"

# GitHub App私钥（必需，二选一）
# 方式1: 直接设置私钥内容
export GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."

# 方式2: 设置私钥文件路径
export GITHUB_APP_PRIVATE_KEY_PATH="/path/to/private-key.pem"

# GitHub App安装ID（必需）
export GITHUB_APP_INSTALLATION_ID="your_installation_id"
```

### 3. MCP配置

在MCP配置文件中添加：

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

## 📝 使用示例

### 读取文件
```json
{
  "tool": "read_file",
  "arguments": {
    "owner": "octocat",
    "repo": "Hello-World",
    "path": "README.md",
    "ref": "main"
  }
}
```

### 创建分支
```json
{
  "tool": "create_branch",
  "arguments": {
    "owner": "octocat",
    "repo": "Hello-World",
    "branch_name": "feature/new-feature",
    "source_branch": "main"
  }
}
```

### 创建或更新文件
```json
{
  "tool": "create_or_update_file",
  "arguments": {
    "owner": "octocat",
    "repo": "Hello-World",
    "path": "new-file.txt",
    "content": "文件内容",
    "message": "添加新文件",
    "branch": "feature/new-feature"
  }
}
```

### 创建Pull Request
```json
{
  "tool": "create_pull_request",
  "arguments": {
    "owner": "octocat",
    "repo": "Hello-World",
    "title": "新功能",
    "body": "PR描述",
    "head": "feature/new-feature",
    "base": "main"
  }
}
```

### 列出Pull Request
```json
{
  "tool": "list_pull_requests",
  "arguments": {
    "owner": "octocat",
    "repo": "Hello-World",
    "state": "open"
  }
}
```

## 🔒 安全注意事项

1. **私钥安全**: 
   - 永远不要将私钥提交到版本控制系统
   - 使用环境变量或安全的密钥管理服务
   - 私钥文件权限应设置为600（仅所有者可读写）

2. **权限最小化**:
   - 只授予应用所需的最小权限
   - 定期审查应用权限

3. **令牌管理**:
   - Installation token会自动管理
   - Token会在过期前自动刷新
   - Token有效期通常为1小时

---

<div align="center">

**为GitHub自动化而制作 ❤️**

[View Full Documentation](README_EN.md) | [查看完整文档](README_CN.md)

</div>