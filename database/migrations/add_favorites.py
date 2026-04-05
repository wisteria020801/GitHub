
"""
添加收藏功能数据库迁移

创建 favorites 表用于存储用户收藏的项目
"""
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "github_radar.db"


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            note TEXT,
            FOREIGN KEY (repo_id) REFERENCES repositories(id),
            UNIQUE(repo_id)
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_favorites_repo_id ON favorites(repo_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_favorites_created_at ON favorites(created_at)
    """)
    
    conn.commit()
    conn.close()
    
    print("Migration completed: favorites table created")


if __name__ == "__main__":
    migrate()
