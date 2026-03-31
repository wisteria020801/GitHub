import sqlite3

conn = sqlite3.connect('github_radar.db')
cursor = conn.cursor()

cursor.execute('SELECT full_name, source FROM repositories WHERE full_name LIKE "%neovim%" OR full_name LIKE "%claude-code%"')
results = cursor.fetchall()

print("检查特定仓库的source值:")
for full_name, source in results:
    print(f"  {full_name}: {source}")

cursor.execute('SELECT full_name, source FROM repositories ORDER BY id DESC LIMIT 5')
recent = cursor.fetchall()

print("\n最近添加的5个仓库:")
for full_name, source in recent:
    print(f"  {full_name}: {source}")

conn.close()
