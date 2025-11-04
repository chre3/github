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
- ✅ Read repository files (supports text and binary files)
- ✅ Create new files
- ✅ Update existing files
- ✅ Automatic base64 encoding/decoding for binary files

### 🌿 Branch Management
- ✅ Create new branches
- ✅ List all branches with details
- ✅ Create branches from specific commits or branches
- ✅ Support for branch protection status

### 🔀 Pull Request Management
- ✅ Create Pull Requests with title and description
- ✅ List Pull Requests (supports status filtering: open, closed, all)
- ✅ Get PR details (status, mergeability, changes, etc.)
- ✅ View PR statistics (additions, deletions, changed files)

### 📦 Repository Management
- ✅ Get repository detailed information
- ✅ View repository statistics (stars, forks, issues, etc.)
- ✅ Access repository metadata and settings

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
- ✅ **Secure**: Safe credential management with automatic token refresh

## 📋 Requirements

- Python 3.8+
- GitHub App created and installed
- GitHub App with necessary permissions:
  - Contents: Read and write
  - Pull requests: Read and write
  - Metadata: Read-only

## 🔑 Authentication Setup

### 1. Create GitHub App

1. Visit [GitHub Developer Settings](https://github.com/settings/apps)
2. Click "New GitHub App" to create a new app
3. Set app permissions:
   - **Repository permissions**:
     - Contents: Read and write
     - Pull requests: Read and write
     - Metadata: Read-only
4. Generate and download private key
5. Install app to repository or organization
6. Get App ID and Installation ID

### 2. Environment Variables

Set up authentication credentials in environment variables:

```bash
# GitHub App ID (required)
export GITHUB_APP_ID="your_app_id"

# GitHub App Private Key (required, choose one)
# Option 1: Set private key content directly
export GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."

# Option 2: Set private key file path
export GITHUB_APP_PRIVATE_KEY_PATH="/path/to/private-key.pem"

# GitHub App Installation ID (required)
export GITHUB_APP_INSTALLATION_ID="your_installation_id"
```

### 3. MCP Configuration

Add to MCP configuration:

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

## 📝 Usage Examples

### Read File
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

### Create Branch
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

### Create or Update File
```json
{
  "tool": "create_or_update_file",
  "arguments": {
    "owner": "octocat",
    "repo": "Hello-World",
    "path": "new-file.txt",
    "content": "File content",
    "message": "Add new file",
    "branch": "feature/new-feature"
  }
}
```

### Create Pull Request
```json
{
  "tool": "create_pull_request",
  "arguments": {
    "owner": "octocat",
    "repo": "Hello-World",
    "title": "New Feature",
    "body": "PR description",
    "head": "feature/new-feature",
    "base": "main"
  }
}
```

### List Pull Requests
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

## 🔒 Security Considerations

1. **Private Key Security**: 
   - Never commit private keys to version control
   - Use environment variables or secure key management services
   - Set private key file permissions to 600 (read/write for owner only)

2. **Minimal Permissions**:
   - Only grant the minimum permissions needed
   - Regularly review app permissions

3. **Token Management**:
   - Installation tokens are automatically managed
   - Tokens are automatically refreshed before expiration
   - Token validity is typically 1 hour

---

<div align="center">

**Made with ❤️ for GitHub automation**

[View Full Documentation](README_EN.md) | [查看完整文档](README_CN.md)

</div>
