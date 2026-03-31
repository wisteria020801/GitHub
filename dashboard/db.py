import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json

from .utils import parse_json_safe

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "github_radar.db"


CATEGORIES = {
    "AI/ML": ["machine-learning", "deep-learning", "ai", "llm", "gpt", "artificial-intelligence", 
              "neural-network", "tensorflow", "pytorch", "openai", "claude", "langchain"],
    "区块链/Web3": ["blockchain", "crypto", "web3", "defi", "nft", "ethereum", "bitcoin", 
                   "smart-contracts", "solana"],
    "开发者工具": ["cli", "devtools", "developer-tools", "tooling", "productivity", 
                  "automation", "framework"],
    "Web框架": ["web-framework", "frontend", "backend", "react", "vue", "angular", 
                "nextjs", "django", "flask", "fastapi"],
    "数据/数据库": ["database", "sql", "nosql", "data", "analytics", "visualization", 
                  "big-data", "etl"],
    "移动开发": ["mobile", "android", "ios", "flutter", "react-native", "swift", "kotlin"],
    "安全": ["security", "cybersecurity", "hacking", "penetration", "encryption", "privacy"],
    "DevOps": ["devops", "docker", "kubernetes", "ci-cd", "infrastructure", "cloud", "terraform"],
    "游戏": ["game", "game-engine", "unity", "unreal", "gamedev"],
}


def categorize_by_topics(topics_str: str) -> str:
    if not topics_str:
        return "其他"
    
    try:
        topics = json.loads(topics_str) if isinstance(topics_str, str) else topics_str
    except:
        return "其他"
    
    if not topics:
        return "其他"
    
    topics_lower = [t.lower() for t in topics]
    
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if keyword in topics_lower or any(keyword in t for t in topics_lower):
                return category
    
    return "其他"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def has_column(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table_name})")
    cols = [row["name"] for row in cur.fetchall()]
    return column_name in cols


def _source_column_sql(conn: sqlite3.Connection) -> str:
    return "r.source AS source" if has_column(conn, "repositories", "source") else "NULL AS source"


def get_available_sources() -> List[str]:
    conn = get_conn()
    try:
        if not has_column(conn, "repositories", "source"):
            return []
        cur = conn.execute(
            """
            SELECT DISTINCT source
            FROM repositories
            WHERE source IS NOT NULL AND TRIM(source) != ''
            ORDER BY source ASC
            """
        )
        return [row["source"] for row in cur.fetchall()]
    finally:
        conn.close()


def build_where_clause(query: Optional[str], source: Optional[str], language: Optional[str], conn: sqlite3.Connection) -> Tuple[str, List]:
    where = []
    params: List = []

    if query:
        q_like = f"%{query.strip()}%"
        where.append(
            """
            ( 
                r.full_name LIKE ? 
                OR r.name LIKE ? 
                OR r.description LIKE ? 
                OR r.topics LIKE ? 
                OR r.readme_content LIKE ? 
                OR la.problem_solved LIKE ? 
                OR la.target_audience LIKE ? 
                OR la.growth_reason LIKE ? 
                OR la.monetization_potential LIKE ? 
            ) 
            """
        )
        params.extend([q_like] * 9)

    if source and has_column(conn, "repositories", "source"):
        where.append("r.source = ?")
        params.append(source)

    if language:
        where.append("r.language = ?")
        params.append(language)

    if where:
        return "WHERE " + " AND ".join(where), params
    return "", params


def build_order_clause(sort_by: str, order: str) -> str:
    order = "ASC" if order.lower() == "asc" else "DESC"

    mapping = {
        "score": f"COALESCE(ls.total_score, 0) {order}",
        "stars": f"COALESCE(r.stars, 0) {order}",
        "forks": f"COALESCE(r.forks, 0) {order}",
        "hot": f"COALESCE(ls.score_growth, 0) {order}",
        "new": f"r.created_at {order}",
        "updated": f"r.pushed_at {order}",
        "first_seen": f"r.first_seen_at {order}",
    }
    return "ORDER BY " + mapping.get(sort_by, f"COALESCE(ls.total_score, 0) DESC")


def get_available_languages() -> List[str]:
    conn = get_conn()
    try:
        cur = conn.execute(
            """
            SELECT DISTINCT language
            FROM repositories
            WHERE language IS NOT NULL AND TRIM(language) != ''
            ORDER BY language ASC
            """
        )
        return [row["language"] for row in cur.fetchall()]
    finally:
        conn.close()


def list_repositories(
    query: Optional[str] = None,
    source: Optional[str] = None,
    language: Optional[str] = None,
    sort_by: str = "score",
    order: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Dict], int]:
    conn = get_conn()
    try:
        source_sql = _source_column_sql(conn)
        where_sql, params = build_where_clause(query, source, language, conn)

        base_sql = f"""
            WITH latest_scores AS ( 
                SELECT s1.* 
                FROM scores s1 
                JOIN ( 
                    SELECT repo_id, MAX(id) AS max_id 
                    FROM scores 
                    GROUP BY repo_id 
                ) s2 ON s1.id = s2.max_id 
            ), 
            latest_analysis AS ( 
                SELECT a1.* 
                FROM analysis_results a1 
                JOIN ( 
                    SELECT repo_id, MAX(id) AS max_id 
                    FROM analysis_results 
                    GROUP BY repo_id 
                ) a2 ON a1.id = a2.max_id 
            ), 
            latest_telegram AS ( 
                SELECT t1.* 
                FROM telegram_messages t1 
                JOIN ( 
                    SELECT repo_id, MAX(id) AS max_id 
                    FROM telegram_messages 
                    GROUP BY repo_id 
                ) t2 ON t1.id = t2.max_id 
            ) 
            SELECT 
                r.id, 
                r.github_id, 
                r.full_name, 
                r.name, 
                r.description, 
                r.html_url, 
                r.language, 
                r.topics, 
                r.stars, 
                r.forks, 
                r.open_issues, 
                r.created_at, 
                r.pushed_at, 
                r.license_name, 
                r.readme_content, 
                r.readme_fetched_at, 
                r.first_seen_at, 
                r.last_updated_at, 
                {source_sql}, 
                ls.total_score, 
                ls.score_popularity, 
                ls.score_growth, 
                ls.score_copyability, 
                ls.score_monetization, 
                ls.score_differentiation, 
                ls.scored_at, 
                la.problem_solved, 
                la.target_audience, 
                la.growth_reason, 
                la.copy_difficulty, 
                la.monetization_potential, 
                la.differentiation_ideas, 
                la.analyzed_at, 
                lt.message_id AS telegram_message_id, 
                lt.sent_at AS telegram_sent_at, 
                lt.status AS telegram_status 
            FROM repositories r 
            LEFT JOIN latest_scores ls ON ls.repo_id = r.id 
            LEFT JOIN latest_analysis la ON la.repo_id = r.id 
            LEFT JOIN latest_telegram lt ON lt.repo_id = r.id 
            {where_sql} 
        """

        count_sql = f"SELECT COUNT(*) AS cnt FROM ({base_sql}) x"
        count_row = conn.execute(count_sql, params).fetchone()
        total = int(count_row["cnt"]) if count_row else 0

        offset = max(page - 1, 0) * page_size
        order_sql = build_order_clause(sort_by, order)
        final_sql = f"{base_sql} {order_sql} LIMIT ? OFFSET ?"
        rows = conn.execute(final_sql, params + [page_size, offset]).fetchall()

        items = []
        for row in rows:
            item = dict(row)
            item["topics_list"] = parse_json_safe(item.get("topics"), [])
            item["differentiation_ideas_list"] = parse_json_safe(item.get("differentiation_ideas"), [])
            items.append(item)

        return items, total
    finally:
        conn.close()


def get_repository_detail(repo_id: int) -> Optional[Dict]:
    conn = get_conn()
    try:
        source_sql = _source_column_sql(conn)
        sql = f"""
            WITH latest_scores AS ( 
                SELECT s1.* 
                FROM scores s1 
                JOIN ( 
                    SELECT repo_id, MAX(id) AS max_id 
                    FROM scores 
                    GROUP BY repo_id 
                ) s2 ON s1.id = s2.max_id 
            ), 
            latest_analysis AS ( 
                SELECT a1.* 
                FROM analysis_results a1 
                JOIN ( 
                    SELECT repo_id, MAX(id) AS max_id 
                    FROM analysis_results 
                    GROUP BY repo_id 
                ) a2 ON a1.id = a2.max_id 
            ), 
            latest_telegram AS ( 
                SELECT t1.* 
                FROM telegram_messages t1 
                JOIN ( 
                    SELECT repo_id, MAX(id) AS max_id 
                    FROM telegram_messages 
                    GROUP BY repo_id 
                ) t2 ON t1.id = t2.max_id 
            ) 
            SELECT 
                r.*, 
                {source_sql}, 
                ls.total_score, 
                ls.score_popularity, 
                ls.score_growth, 
                ls.score_copyability, 
                ls.score_monetization, 
                ls.score_differentiation, 
                ls.scored_at, 
                la.problem_solved, 
                la.target_audience, 
                la.growth_reason, 
                la.copy_difficulty, 
                la.monetization_potential, 
                la.differentiation_ideas, 
                la.raw_llm_response, 
                la.analyzed_at, 
                lt.message_id AS telegram_message_id, 
                lt.sent_at AS telegram_sent_at, 
                lt.status AS telegram_status 
            FROM repositories r 
            LEFT JOIN latest_scores ls ON ls.repo_id = r.id 
            LEFT JOIN latest_analysis la ON la.repo_id = r.id 
            LEFT JOIN latest_telegram lt ON lt.repo_id = r.id 
            WHERE r.id = ? 
            LIMIT 1 
        """
        row = conn.execute(sql, (repo_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["topics_list"] = parse_json_safe(item.get("topics"), [])
        item["differentiation_ideas_list"] = parse_json_safe(item.get("differentiation_ideas"), [])
        return item
    finally:
        conn.close()


def get_stats() -> Dict:
    conn = get_conn()
    try:
        total_repos = conn.execute("SELECT COUNT(*) AS cnt FROM repositories").fetchone()["cnt"]
        analyzed = conn.execute("SELECT COUNT(DISTINCT repo_id) AS cnt FROM analysis_results").fetchone()["cnt"]
        scored = conn.execute("SELECT COUNT(DISTINCT repo_id) AS cnt FROM scores").fetchone()["cnt"]
        notified = conn.execute("SELECT COUNT(DISTINCT repo_id) AS cnt FROM telegram_messages").fetchone()["cnt"]

        avg_score_row = conn.execute(
            "SELECT ROUND(AVG(total_score), 2) AS avg_score FROM scores"
        ).fetchone()
        avg_score = avg_score_row["avg_score"] if avg_score_row else None

        top_score = conn.execute(
            """
            SELECT r.full_name, s.total_score 
            FROM scores s 
            JOIN repositories r ON r.id = s.repo_id 
            ORDER BY s.total_score DESC 
            LIMIT 1 
            """
        ).fetchone()

        stats = {
            "total_repos": total_repos,
            "analyzed_repos": analyzed,
            "scored_repos": scored,
            "notified_repos": notified,
            "avg_score": avg_score,
            "top_repo_name": top_score["full_name"] if top_score else None,
            "top_repo_score": top_score["total_score"] if top_score else None,
            "sources": [],
        }

        if has_column(conn, "repositories", "source"):
            rows = conn.execute(
                """
                SELECT COALESCE(source, 'unknown') AS source, COUNT(*) AS cnt 
                FROM repositories 
                GROUP BY COALESCE(source, 'unknown') 
                ORDER BY cnt DESC 
                """
            ).fetchall()
            stats["sources"] = [dict(row) for row in rows]

        stats["categories"] = get_category_stats()

        return stats
    finally:
        conn.close()


def get_category_stats() -> List[Dict]:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id, topics FROM repositories WHERE topics IS NOT NULL AND topics != '[]'"
        ).fetchall()
        
        category_counts = {cat: 0 for cat in CATEGORIES.keys()}
        category_counts["其他"] = 0
        
        for row in rows:
            category = categorize_by_topics(row["topics"])
            category_counts[category] = category_counts.get(category, 0) + 1
        
        return [
            {"category": cat, "count": count}
            for cat, count in sorted(category_counts.items(), key=lambda x: -x[1])
            if count > 0
        ]
    finally:
        conn.close()


def get_repos_by_category(category: str, limit: int = 10) -> List[Dict]:
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT r.id, r.name, r.full_name, r.stars, r.description, r.html_url, r.topics,
                   s.total_score
            FROM repositories r
            LEFT JOIN scores s ON r.id = s.repo_id
            WHERE r.topics IS NOT NULL AND r.topics != '[]'
            ORDER BY COALESCE(s.total_score, 0) DESC
            """
        ).fetchall()
        
        results = []
        for row in rows:
            category_match = categorize_by_topics(row["topics"])
            if category_match == category:
                item = dict(row)
                item["category"] = category
                results.append(item)
                if len(results) >= limit:
                    break
        
        return results
    finally:
        conn.close()


def compare_repositories(repo_ids: List[int]) -> Dict:
    conn = get_conn()
    try:
        repos = []
        for repo_id in repo_ids:
            repo = get_repository_detail(repo_id)
            if repo:
                repo["category"] = categorize_by_topics(repo.get("topics", "[]"))
                repos.append(repo)
        
        comparison = {
            "repos": repos,
            "metrics": {}
        }
        
        if repos:
            metrics = ["stars", "forks", "open_issues", "total_score", "score_popularity", 
                      "score_growth", "score_monetization", "score_differentiation"]
            
            for metric in metrics:
                values = []
                for repo in repos:
                    val = repo.get(metric)
                    if val is not None:
                        try:
                            values.append(float(val))
                        except:
                            pass
                
                if values:
                    comparison["metrics"][metric] = {
                        "max": max(values) if values else 0,
                        "min": min(values) if values else 0,
                        "avg": sum(values) / len(values) if values else 0
                    }
        
        return comparison
    finally:
        conn.close()


def get_available_categories() -> List[str]:
    return list(CATEGORIES.keys()) + ["其他"]


def get_all_repos(limit: int = 1000) -> List[Dict]:
    conn = get_conn()
    try:
        source_sql = _source_column_sql(conn)
        sql = f"""
            SELECT 
                r.id,
                r.name,
                r.full_name,
                r.description,
                r.language,
                r.stars,
                r.forks,
                r.topics,
                {source_sql},
                ls.total_score
            FROM repositories r
            LEFT JOIN (
                SELECT s1.* 
                FROM scores s1 
                JOIN (
                    SELECT repo_id, MAX(id) AS max_id 
                    FROM scores 
                    GROUP BY repo_id
                ) s2 ON s1.id = s2.max_id
            ) ls ON ls.repo_id = r.id
            ORDER BY r.id DESC
            LIMIT ?
        """
        rows = conn.execute(sql, (limit,)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def add_favorite(repo_id: int, note: str = "") -> bool:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO favorites (repo_id, note) VALUES (?, ?)",
            (repo_id, note)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding favorite: {e}")
        return False
    finally:
        conn.close()


def remove_favorite(repo_id: int) -> bool:
    conn = get_conn()
    try:
        conn.execute("DELETE FROM favorites WHERE repo_id = ?", (repo_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error removing favorite: {e}")
        return False
    finally:
        conn.close()


def is_favorite(repo_id: int) -> bool:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id FROM favorites WHERE repo_id = ?", (repo_id,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def get_favorite_repos(limit: int = 50, offset: int = 0) -> List[Dict]:
    conn = get_conn()
    try:
        source_sql = _source_column_sql(conn)
        sql = f"""
            SELECT 
                r.id,
                r.name,
                r.full_name,
                r.description,
                r.language,
                r.stars,
                r.forks,
                r.html_url,
                r.topics,
                {source_sql},
                ls.total_score,
                f.created_at AS favorited_at,
                f.note AS favorite_note
            FROM favorites f
            JOIN repositories r ON r.id = f.repo_id
            LEFT JOIN (
                SELECT s1.* 
                FROM scores s1 
                JOIN (
                    SELECT repo_id, MAX(id) AS max_id 
                    FROM scores 
                    GROUP BY repo_id
                ) s2 ON s1.id = s2.max_id
            ) ls ON ls.repo_id = r.id
            ORDER BY f.created_at DESC
            LIMIT ? OFFSET ?
        """
        rows = conn.execute(sql, (limit, offset)).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["topics_list"] = parse_json_safe(item.get("topics"), [])
            items.append(item)
        return items
    finally:
        conn.close()


def get_favorites_count() -> int:
    conn = get_conn()
    try:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM favorites").fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


def update_favorite_note(repo_id: int, note: str) -> bool:
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE favorites SET note = ? WHERE repo_id = ?",
            (note, repo_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating favorite note: {e}")
        return False
    finally:
        conn.close()
