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
                    last_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
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

            logger.info(f"Database initialized at {self.db_path}")

    def insert_repository(self, repo: Repository) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO repositories 
                (github_id, full_name, name, description, html_url, language, topics, 
                 stars, forks, open_issues, created_at, pushed_at, license_name, 
                 readme_content, readme_fetched_at, first_seen_at, last_updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                repo.github_id, repo.full_name, repo.name, repo.description,
                repo.html_url, repo.language, repo.topics_json, repo.stars,
                repo.forks, repo.open_issues, repo.created_at, repo.pushed_at,
                repo.license_name, repo.readme_content, repo.readme_fetched_at,
                repo.first_seen_at or datetime.now(), repo.last_updated_at or datetime.now()
            ))
            return cursor.lastrowid

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
                    readme_content = ?, readme_fetched_at = ?, last_updated_at = ?
                WHERE id = ?
            ''', (
                repo.stars, repo.forks, repo.open_issues, repo.description,
                repo.readme_content, repo.readme_fetched_at, datetime.now(), repo.id
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
                 raw_llm_response, analyzed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.repo_id, result.problem_solved, result.target_audience,
                result.growth_reason, result.copy_difficulty, result.monetization_potential,
                result.differentiation_ideas_json, result.raw_llm_response,
                result.analyzed_at or datetime.now()
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
        self, min_score: float = 70, limit: int = 10
    ) -> List[Tuple[Repository, Score, AnalysisResult]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.*, s.*, a.*
                FROM repositories r
                JOIN scores s ON r.id = s.repo_id
                JOIN analysis_results a ON r.id = a.repo_id
                LEFT JOIN telegram_messages t ON r.id = t.repo_id
                WHERE s.total_score >= ? AND t.id IS NULL
                ORDER BY s.total_score DESC
                LIMIT ?
            ''', (min_score, limit))
            
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
