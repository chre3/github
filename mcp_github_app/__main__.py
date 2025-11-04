#!/usr/bin/env python3
"""
MCP GitHub App 主入口点
"""

import sys
import os
import json

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入GitHub App服务器
from .server import MCPGitHubAppServer

def main():
    """主函数 - 处理MCP协议"""
    try:
        # 创建GitHub App服务器实例
        github_server = MCPGitHubAppServer()
        
        # 处理MCP协议
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
                    result = github_server.handle_initialize(params)
                elif method == "tools/list":
                    result = github_server.handle_tools_list()
                elif method == "tools/call":
                    result = github_server.handle_tools_call(
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
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
