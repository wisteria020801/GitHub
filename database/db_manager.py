import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple
from contextlib import contextmanager

from database.models import Repository, AnalysisResult, Score, TelegramMessage, StarSnapshot
from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    def __init__(self, db_path: str = "github_radar.db"):
        self.db_path = Path(db_path)
        self._init_database()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def _init_database(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS repositories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    github_id INTEGER UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    html_url TEXT NOT NULL,
                    language TEXT,
                    topics TEXT,
                    stars INTEGER DEFAULT 0,
                    forks INTEGER DEFAULT 0,
                    open_issues INTEGER DEFAULT 0,
                    created_at DATETIME,
                    pushed_at DATETIME,
                    license_name TEXT,
                    readme_content TEXT,
                    readme_fetched_at DATETIME,
                    first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    source TEXT DEFAULT 'github'
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_id INTEGER NOT NULL,
                    problem_solved TEXT,
                    target_audience TEXT,
                    growth_reason TEXT,
                    copy_difficulty TEXT,
                    monetization_potential TEXT,
                    differentiation_ideas TEXT,
                    raw_llm_response TEXT,
                    analyzed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_fallback INTEGER DEFAULT 0,
                    FOREIGN KEY (repo_id) REFERENCES repositories(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_id INTEGER NOT NULL,
                    score_popularity REAL DEFAULT 0,
                    score_growth REAL DEFAULT 0,
                    score_copyability REAL DEFAULT 0,
                    score_monetization REAL DEFAULT 0,
                    score_differentiation REAL DEFAULT 0,
                    total_score REAL DEFAULT 0,
                    scored_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (repo_id) REFERENCES repositories(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS telegram_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_id INTEGER NOT NULL,
                    message_id INTEGER,
                    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (repo_id) REFERENCES repositories(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS star_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_id INTEGER NOT NULL,
                    stars INTEGER DEFAULT 0,
                    forks INTEGER DEFAULT 0,
                    snapshot_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (repo_id) REFERENCES repositories(id)
                )
            ''')

            cursor.execute('CREATE INDEX IF NOT EXISTS idx_repos_github_id ON repositories(github_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_repos_stars ON repositories(stars)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_scores_total ON scores(total_score)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_repo_date ON star_snapshots(repo_id, snapshot_at)')
            
            self._run_migrations(cursor)

            logger.info(f"Database initialized at {self.db_path}")

    def _run_migrations(self, cursor):
        try:
            cursor.execute("SELECT is_fallback FROM analysis_results LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE analysis_results ADD COLUMN is_fallback INTEGER DEFAULT 0")
            logger.info("Migration: added is_fallback column to analysis_results")
        
        try:
            cursor.execute("SELECT source FROM repositories LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE repositories ADD COLUMN source TEXT DEFAULT 'github'")
            logger.info("Migration: added source column to repositories")

    def insert_repository(self, repo: Repository) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO repositories 
                    (github_id, full_name, name, description, html_url, language, topics, 
                     stars, forks, open_issues, created_at, pushed_at, license_name, 
                     readme_content, readme_fetched_at, first_seen_at, last_updated_at, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    repo.github_id, repo.full_name, repo.name, repo.description,
                    repo.html_url, repo.language, repo.topics_json, repo.stars,
                    repo.forks, repo.open_issues, repo.created_at, repo.pushed_at,
                    repo.license_name, repo.readme_content, repo.readme_fetched_at,
                    repo.first_seen_at or datetime.now(), repo.last_updated_at or datetime.now(),
                    repo.source
                ))
                if cursor.lastrowid and cursor.lastrowid > 0:
                    return cursor.lastrowid
                existing = self.get_repository_by_github_id(repo.github_id)
                return existing.id if existing else 0
            except Exception as e:
                logger.error(f"Failed to insert repository {repo.full_name}: {e}")
                return 0

    def get_repository_by_github_id(self, github_id: int) -> Optional[Repository]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM repositories WHERE github_id = ?', (github_id,))
            row = cursor.fetchone()
            if row:
                return Repository.from_dict(dict(row))
            return None

    def get_repository_by_id(self, repo_id: int) -> Optional[Repository]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM repositories WHERE id = ?', (repo_id,))
            row = cursor.fetchone()
            if row:
                return Repository.from_dict(dict(row))
            return None

    def update_repository(self, repo: Repository) -> bool:
        if not repo.id:
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE repositories SET
                    stars = ?, forks = ?, open_issues = ?, description = ?,
                    readme_content = ?, readme_fetched_at = ?, last_updated_at = ?, source = ?
                WHERE id = ?
            ''', (
                repo.stars, repo.forks, repo.open_issues, repo.description,
                repo.readme_content, repo.readme_fetched_at, datetime.now(), repo.source, repo.id
            ))
            return cursor.rowcount > 0

    def get_unanalyzed_repositories(self, limit: int = 50) -> List[Repository]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.* FROM repositories r
                LEFT JOIN analysis_results a ON r.id = a.repo_id
                WHERE a.id IS NULL AND r.readme_content IS NOT NULL
                ORDER BY r.stars DESC
                LIMIT ?
            ''', (limit,))
            return [Repository.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_unscored_repositories(self, limit: int = 50) -> List[Repository]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.* FROM repositories r
                LEFT JOIN scores s ON r.id = s.repo_id
                WHERE s.id IS NULL
                ORDER BY r.stars DESC
                LIMIT ?
            ''', (limit,))
            return [Repository.from_dict(dict(row)) for row in cursor.fetchall()]

    def insert_analysis_result(self, result: AnalysisResult) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO analysis_results
                (repo_id, problem_solved, target_audience, growth_reason,
                 copy_difficulty, monetization_potential, differentiation_ideas,
                 raw_llm_response, analyzed_at, is_fallback)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.repo_id, result.problem_solved, result.target_audience,
                result.growth_reason, result.copy_difficulty, result.monetization_potential,
                result.differentiation_ideas_json, result.raw_llm_response,
                result.analyzed_at or datetime.now(),
                1 if result.is_fallback else 0
            ))
            return cursor.lastrowid

    def get_analysis_by_repo_id(self, repo_id: int) -> Optional[AnalysisResult]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM analysis_results WHERE repo_id = ?', (repo_id,))
            row = cursor.fetchone()
            if row:
                return AnalysisResult.from_dict(dict(row))
            return None

    def insert_score(self, score: Score) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO scores
                (repo_id, score_popularity, score_growth, score_copyability,
                 score_monetization, score_differentiation, total_score, scored_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                score.repo_id, score.score_popularity, score.score_growth,
                score.score_copyability, score.score_monetization,
                score.score_differentiation, score.total_score,
                score.scored_at or datetime.now()
            ))
            return cursor.lastrowid

    def get_score_by_repo_id(self, repo_id: int) -> Optional[Score]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM scores WHERE repo_id = ?', (repo_id,))
            row = cursor.fetchone()
            if row:
                return Score.from_dict(dict(row))
            return None

    def get_top_scored_repositories(
        self, min_score: float = 70, limit: int = 10, include_notified: bool = False,
        max_age_days: int = 0
    ) -> List[Tuple[Repository, Score, AnalysisResult]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            age_filter = ""
            age_params = []
            if max_age_days > 0:
                age_filter = f"AND r.created_at >= datetime('now', '-{max_age_days} days')"
            
            if include_notified:
                cursor.execute(f'''
                    SELECT r.*, s.*, a.*
                    FROM repositories r
                    JOIN scores s ON r.id = s.repo_id
                    JOIN analysis_results a ON r.id = a.repo_id
                    WHERE s.total_score >= ? {age_filter}
                    ORDER BY s.total_score DESC
                    LIMIT ?
                ''', (min_score, *age_params, limit))
            else:
                cursor.execute(f'''
                    SELECT r.*, s.*, a.*
                    FROM repositories r
                    JOIN scores s ON r.id = s.repo_id
                    JOIN analysis_results a ON r.id = a.repo_id
                    LEFT JOIN telegram_messages t ON r.id = t.repo_id
                    WHERE s.total_score >= ? AND t.id IS NULL {age_filter}
                    ORDER BY s.total_score DESC
                    LIMIT ?
                ''', (min_score, *age_params, limit))
            
            results = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                repo = Repository.from_dict(row_dict)
                score = Score.from_dict(row_dict)
                analysis = AnalysisResult.from_dict(row_dict)
                results.append((repo, score, analysis))
            return results

    def insert_telegram_message(self, msg: TelegramMessage) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO telegram_messages (repo_id, message_id, sent_at, status)
                VALUES (?, ?, ?, ?)
            ''', (
                msg.repo_id, msg.message_id, msg.sent_at or datetime.now(), msg.status
            ))
            return cursor.lastrowid

    def is_repo_notified(self, repo_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id FROM telegram_messages WHERE repo_id = ? AND status = ?',
                (repo_id, 'sent')
            )
            return cursor.fetchone() is not None

    def insert_star_snapshot(self, snapshot: StarSnapshot) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO star_snapshots (repo_id, stars, forks, snapshot_at)
                VALUES (?, ?, ?, ?)
            ''', (
                snapshot.repo_id, snapshot.stars, snapshot.forks,
                snapshot.snapshot_at or datetime.now()
            ))
            return cursor.lastrowid

    def get_latest_snapshot(self, repo_id: int) -> Optional[StarSnapshot]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM star_snapshots 
                WHERE repo_id = ? 
                ORDER BY snapshot_at DESC 
                LIMIT 1
            ''', (repo_id,))
            row = cursor.fetchone()
            if row:
                return StarSnapshot.from_dict(dict(row))
            return None

    def get_star_growth(self, repo_id: int, days: int = 7) -> Tuple[int, int]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT stars, snapshot_at FROM star_snapshots
                WHERE repo_id = ? AND snapshot_at >= datetime('now', ?)
                ORDER BY snapshot_at ASC
            ''', (repo_id, f'-{days} days'))
            rows = cursor.fetchall()
            
            if len(rows) < 2:
                return 0, 0
            
            first_stars = rows[0]['stars']
            last_stars = rows[-1]['stars']
            return last_stars - first_stars, last_stars

    def get_all_repositories(self, limit: int = 100) -> List[Repository]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM repositories ORDER BY stars DESC LIMIT ?', (limit,))
            return [Repository.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_repositories_by_stars(self, limit: int = 10) -> List[Repository]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM repositories ORDER BY stars DESC LIMIT ?', (limit,))
            return [Repository.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_repositories_by_date(self, limit: int = 10) -> List[Repository]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM repositories WHERE created_at IS NOT NULL ORDER BY created_at DESC LIMIT ?', (limit,))
            return [Repository.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_repositories_by_date_range(self, start_date, end_date) -> List[Repository]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM repositories 
                WHERE created_at BETWEEN ? AND ? 
                ORDER BY created_at DESC
            ''', (start_date, end_date))
            return [Repository.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_total_repositories(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM repositories')
            return cursor.fetchone()[0]

    def get_total_analyzed_repositories(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(DISTINCT repo_id) FROM analysis_results')
            return cursor.fetchone()[0]

    def get_today_repositories(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM repositories 
                WHERE DATE(first_seen_at) = DATE('now')
            ''')
            return cursor.fetchone()[0]

    def get_repositories_by_forks(self, limit: int = 10) -> List[Repository]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM repositories ORDER BY forks DESC LIMIT ?', (limit,))
            return [Repository.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_repositories_by_growth(self, limit: int = 10) -> List[Tuple[Repository, int]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.*, 
                    (SELECT COUNT(*) FROM star_snapshots s WHERE s.repo_id = r.id) as snapshot_count
                FROM repositories r
                WHERE r.id IN (SELECT DISTINCT repo_id FROM star_snapshots)
                ORDER BY snapshot_count DESC
                LIMIT ?
            ''', (limit,))
            results = []
            for row in cursor.fetchall():
                repo = Repository.from_dict(dict(row))
                growth = row['snapshot_count']
                results.append((repo, growth))
            return results
    
    def get_fastest_growing_repositories(self, days: int = 7, limit: int = 10) -> List[Tuple[Repository, int, float]]:
        """获取增长速度最快的项目
        
        Args:
            days: 统计天数
            limit: 返回数量
            
        Returns:
            项目列表，包含 (Repository, 增长数, 增长率) 元组
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.*
                FROM repositories r
                WHERE r.id IN (SELECT DISTINCT repo_id FROM star_snapshots)
                ORDER BY r.stars DESC
                LIMIT 100
            ''')
            
            results = []
            for row in cursor.fetchall():
                repo = Repository.from_dict(dict(row))
                growth, current_stars = self.get_star_growth(repo.id, days)
                
                if current_stars > 0 and growth > 0:
                    growth_rate = (growth / current_stars) * 100
                    results.append((repo, growth, growth_rate))
            
            # 按增长率排序
            results.sort(key=lambda x: x[2], reverse=True)
            return results[:limit]

    def get_notified_repo_ids(self) -> List[int]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT repo_id FROM telegram_messages WHERE status IN ("sent", "sent_summary")')
            return [row[0] for row in cursor.fetchall()]

    def get_repositories_by_source(self, source: str, limit: int = 10) -> List[Repository]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM repositories WHERE source = ? ORDER BY stars DESC LIMIT ?', (source, limit))
            return [Repository.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_repositories_by_language(self, language: str, limit: int = 10) -> List[Repository]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM repositories WHERE language = ? ORDER BY stars DESC LIMIT ?', (language, limit))
            return [Repository.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_available_sources(self) -> List[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT source FROM repositories WHERE source IS NOT NULL')
            return [row[0] for row in cursor.fetchall()]

    def get_available_languages(self) -> List[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT language FROM repositories WHERE language IS NOT NULL ORDER BY language')
            return [row[0] for row in cursor.fetchall()]

    def search_repositories(self, keyword: str, limit: int = 10) -> List[Repository]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM repositories 
                WHERE full_name LIKE ? OR description LIKE ?
                ORDER BY stars DESC
                LIMIT ?
            ''', (f'%{keyword}%', f'%{keyword}%', limit))
            return [Repository.from_dict(dict(row)) for row in cursor.fetchall()]
