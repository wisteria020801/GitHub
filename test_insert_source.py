"""
测试插入新的仓库，验证source字段
"""
import sqlite3
from datetime import datetime
from database.models import Repository
from database.db_manager import DatabaseManager
from config import config

db = DatabaseManager(config.database.path)

test_repo = Repository(
    github_id=999999999,
    full_name="test/test-hackernews-source",
    name="test-hackernews-source",
    description="Test repository from Hacker News",
    html_url="https://github.com/test/test-hackernews-source",
    language="Python",
    topics=["test"],
    stars=1000,
    forks=100,
    open_issues=10,
    created_at=datetime.now(),
    pushed_at=datetime.now(),
    license_name="MIT",
    source="hackernews"
)

print("测试插入新仓库:")
print(f"  full_name: {test_repo.full_name}")
print(f"  source: {test_repo.source}")

repo_id = db.insert_repository(test_repo)
if repo_id:
    print(f"  ✅ 插入成功, ID: {repo_id}")
    
    conn = sqlite3.connect('github_radar.db')
    cursor = conn.cursor()
    cursor.execute('SELECT full_name, source FROM repositories WHERE id = ?', (repo_id,))
    result = cursor.fetchone()
    conn.close()
    
    print(f"  验证数据库: {result[0]} - source: {result[1]}")
    
    if result[1] == "hackernews":
        print("  ✅ source字段保存正确！")
    else:
        print(f"  ❌ source字段错误，期望 'hackernews'，实际 '{result[1]}'")
else:
    print("  ℹ️  仓库已存在")

print("\n测试更新仓库source字段:")
test_repo.source = "producthunt"
success = db.update_repository(test_repo)
if success:
    print("  ✅ 更新成功")
    
    conn = sqlite3.connect('github_radar.db')
    cursor = conn.cursor()
    cursor.execute('SELECT full_name, source FROM repositories WHERE id = ?', (repo_id,))
    result = cursor.fetchone()
    conn.close()
    
    print(f"  验证数据库: {result[0]} - source: {result[1]}")
    
    if result[1] == "producthunt":
        print("  ✅ source字段更新正确！")
    else:
        print(f"  ❌ source字段错误，期望 'producthunt'，实际 '{result[1]}'")
