from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
import json


@dataclass
class Repository:
    id: Optional[int] = None
    github_id: int = 0
    full_name: str = ""
    name: str = ""
    description: Optional[str] = None
    html_url: str = ""
    language: Optional[str] = None
    topics: List[str] = None
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    created_at: Optional[datetime] = None
    pushed_at: Optional[datetime] = None
    license_name: Optional[str] = None
    readme_content: Optional[str] = None
    readme_fetched_at: Optional[datetime] = None
    first_seen_at: Optional[datetime] = None
    last_updated_at: Optional[datetime] = None
    source: str = "github"

    def __post_init__(self):
        if self.topics is None:
            self.topics = []

    @property
    def owner(self) -> str:
        if "/" in self.full_name:
            return self.full_name.split("/")[0]
        return ""

    @property
    def topics_json(self) -> str:
        return json.dumps(self.topics, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> 'Repository':
        topics = data.get('topics', [])
        if isinstance(topics, str):
            try:
                topics = json.loads(topics)
            except json.JSONDecodeError:
                topics = []

        def parse_date(date_str):
            if isinstance(date_str, str):
                try:
                    return datetime.fromisoformat(date_str)
                except:
                    pass
            return date_str

        return cls(
            id=data.get('id'),
            github_id=data.get('github_id', 0),
            full_name=data.get('full_name', ''),
            name=data.get('name', ''),
            description=data.get('description'),
            html_url=data.get('html_url', ''),
            language=data.get('language'),
            topics=topics,
            stars=data.get('stars', 0),
            forks=data.get('forks', 0),
            open_issues=data.get('open_issues', 0),
            created_at=parse_date(data.get('created_at')),
            pushed_at=parse_date(data.get('pushed_at')),
            license_name=data.get('license_name'),
            readme_content=data.get('readme_content'),
            readme_fetched_at=parse_date(data.get('readme_fetched_at')),
            first_seen_at=parse_date(data.get('first_seen_at')),
            last_updated_at=parse_date(data.get('last_updated_at')),
            source=data.get('source', 'github'),
        )


@dataclass
class AnalysisResult:
    id: Optional[int] = None
    repo_id: int = 0
    problem_solved: Optional[str] = None
    target_audience: Optional[str] = None
    growth_reason: Optional[str] = None
    copy_difficulty: Optional[str] = None
    monetization_potential: Optional[str] = None
    differentiation_ideas: List[str] = None
    raw_llm_response: Optional[str] = None
    analyzed_at: Optional[datetime] = None
    is_fallback: bool = False

    def __post_init__(self):
        if self.differentiation_ideas is None:
            self.differentiation_ideas = []

    @property
    def differentiation_ideas_json(self) -> str:
        return json.dumps(self.differentiation_ideas, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> 'AnalysisResult':
        ideas = data.get('differentiation_ideas', [])
        if isinstance(ideas, str):
            try:
                ideas = json.loads(ideas)
            except json.JSONDecodeError:
                ideas = []

        def parse_date(date_str):
            if isinstance(date_str, str):
                try:
                    return datetime.fromisoformat(date_str)
                except:
                    pass
            return date_str

        return cls(
            id=data.get('id'),
            repo_id=data.get('repo_id', 0),
            problem_solved=data.get('problem_solved'),
            target_audience=data.get('target_audience'),
            growth_reason=data.get('growth_reason'),
            copy_difficulty=data.get('copy_difficulty'),
            monetization_potential=data.get('monetization_potential'),
            differentiation_ideas=ideas,
            raw_llm_response=data.get('raw_llm_response'),
            analyzed_at=parse_date(data.get('analyzed_at')),
            is_fallback=bool(data.get('is_fallback', 0)),
        )


@dataclass
class Score:
    id: Optional[int] = None
    repo_id: int = 0
    score_popularity: float = 0.0
    score_growth: float = 0.0
    score_copyability: float = 0.0
    score_monetization: float = 0.0
    score_differentiation: float = 0.0
    total_score: float = 0.0
    scored_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'Score':
        def parse_date(date_str):
            if isinstance(date_str, str):
                try:
                    return datetime.fromisoformat(date_str)
                except:
                    pass
            return date_str

        return cls(
            id=data.get('id'),
            repo_id=data.get('repo_id', 0),
            score_popularity=data.get('score_popularity', 0.0),
            score_growth=data.get('score_growth', 0.0),
            score_copyability=data.get('score_copyability', 0.0),
            score_monetization=data.get('score_monetization', 0.0),
            score_differentiation=data.get('score_differentiation', 0.0),
            total_score=data.get('total_score', 0.0),
            scored_at=parse_date(data.get('scored_at')),
        )


@dataclass
class TelegramMessage:
    id: Optional[int] = None
    repo_id: int = 0
    message_id: Optional[int] = None
    sent_at: Optional[datetime] = None
    status: str = "pending"

    @classmethod
    def from_dict(cls, data: dict) -> 'TelegramMessage':
        def parse_date(date_str):
            if isinstance(date_str, str):
                try:
                    return datetime.fromisoformat(date_str)
                except:
                    pass
            return date_str

        return cls(
            id=data.get('id'),
            repo_id=data.get('repo_id', 0),
            message_id=data.get('message_id'),
            sent_at=parse_date(data.get('sent_at')),
            status=data.get('status', 'pending'),
        )


@dataclass
class StarSnapshot:
    id: Optional[int] = None
    repo_id: int = 0
    stars: int = 0
    forks: int = 0
    snapshot_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'StarSnapshot':
        def parse_date(date_str):
            if isinstance(date_str, str):
                try:
                    return datetime.fromisoformat(date_str)
                except:
                    pass
            return date_str

        return cls(
            id=data.get('id'),
            repo_id=data.get('repo_id', 0),
            stars=data.get('stars', 0),
            forks=data.get('forks', 0),
            snapshot_at=parse_date(data.get('snapshot_at')),
        )
