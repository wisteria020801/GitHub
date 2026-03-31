import sqlite3

conn = sqlite3.connect('github_radar.db')
cursor = conn.cursor()

print("=" * 60)
print("数据库实际验证")
print("=" * 60)

cursor.execute('PRAGMA table_info(repositories)')
cols = [row[1] for row in cursor.fetchall()]
print(f"\n1. repositories表字段列表:")
print(f"   {', '.join(cols)}")
print(f"   source字段存在: {'source' in cols}")

cursor.execute('SELECT source, COUNT(*) FROM repositories GROUP BY source')
results = cursor.fetchall()
print(f"\n2. 数据来源分布:")
for source, count in results:
    print(f"   {source}: {count}条")

cursor.execute('SELECT COUNT(*) FROM repositories WHERE source IS NULL')
null_count = cursor.fetchone()[0]
print(f"\n3. source为NULL的记录: {null_count}条")

cursor.execute('SELECT full_name, source FROM repositories ORDER BY id DESC LIMIT 5')
recent = cursor.fetchall()
print(f"\n4. 最近5条记录:")
for full_name, source in recent:
    print(f"   {full_name}: {source}")

conn.close()

print("\n" + "=" * 60)
print("验证完成")
print("=" * 60)
