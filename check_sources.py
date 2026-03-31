import sqlite3

conn = sqlite3.connect('github_radar.db')
cursor = conn.cursor()

cursor.execute('PRAGMA table_info(repositories)')
cols = [row[1] for row in cursor.fetchall()]
print('数据库字段:', cols)
print('source字段存在:', 'source' in cols)

if 'source' in cols:
    cursor.execute('SELECT DISTINCT source FROM repositories WHERE source IS NOT NULL')
    sources = [row[0] for row in cursor.fetchall()]
    print('数据来源:', sources)
    
    cursor.execute('SELECT source, COUNT(*) FROM repositories GROUP BY source')
    counts = cursor.fetchall()
    print('各来源数量:', counts)

conn.close()
