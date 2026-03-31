#!/usr/bin/env python3
"""
GitHub Radar Web Dashboard 启动脚本
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dashboard.app import app

if __name__ == "__main__":
    print("=" * 60)
    print("GitHub Radar Web Dashboard")
    print("=" * 60)
    print(f"访问地址: http://127.0.0.1:5000/")
    print(f"统计页面: http://127.0.0.1:5000/stats")
    print(f"健康检查: http://127.0.0.1:5000/health")
    print("=" * 60)
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)
    
    app.run(debug=False, host="127.0.0.1", port=5000)
