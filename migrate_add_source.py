"""
数据库迁移脚本：添加source字段
"""
import sqlite3
from pathlib import Path

def migrate_database():
    db_path = Path(__file__).parent / 'github_radar.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('PRAGMA table_info(repositories)')
        cols = [row[1] for row in cursor.fetchall()]
        
        if 'source' not in cols:
            print('添加source字段...')
            cursor.execute('ALTER TABLE repositories ADD COLUMN source TEXT DEFAULT "github"')
            
            cursor.execute('UPDATE repositories SET source = "github" WHERE source IS NULL')
            
            conn.commit()
            print('✅ 数据库迁移成功：source字段已添加')
        else:
            print('✅ source字段已存在，无需迁移')
        
        cursor.execute('SELECT source, COUNT(*) FROM repositories GROUP BY source')
        counts = cursor.fetchall()
        print(f'\n当前数据来源分布:')
        for source, count in counts:
            print(f'  {source}: {count}条')
            
    except Exception as e:
        print(f'❌ 迁移失败: {e}')
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database()
