import sqlite3

conn = sqlite3.connect('github_radar.db')
cursor = conn.cursor()

cursor.execute('DELETE FROM repositories WHERE full_name = "test/test-hackernews-source"')
conn.commit()

print("✅ 测试数据已清理")

cursor.execute('SELECT source, COUNT(*) FROM repositories GROUP BY source')
counts = cursor.fetchall()
print("\n最终数据来源分布:")
for source, count in counts:
    print(f"  {source}: {count}条")

conn.close()
