import requests
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from config import GitHubConfig
from database.models import Repository
from utils.logger import get_logger
from utils.helpers import retry_on_failure, parse_github_date, get_github_search_date

logger = get_logger(__name__)


@dataclass
class SearchResult:
    total_count: int
    repositories: List[Repository]


class GitHubCollector:
    def __init__(self, config: GitHubConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {config.token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Radar/1.0'
        })

    @retry_on_failure(max_retries=3, delay=1.0, exceptions=(requests.RequestException,))
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        response = self.session.get(url, params=params, timeout=self.config.request_timeout)
        response.raise_for_status()
        return response.json()

    def search_trending_repositories(
        self,
        days: int = 7,
        min_stars: int = 50,
        max_results: int = 50,
        language: Optional[str] = None,
        topics: Optional[List[str]] = None
    ) -> SearchResult:
        date_str = get_github_search_date(days)
        
        query_parts = [f'created:>{date_str}', f'stars:>{min_stars}']
        
        if language:
            query_parts.append(f'language:{language}')
        
        if topics:
            for topic in topics:
                query_parts.append(f'topic:{topic}')
        
        query = ' '.join(query_parts)
        logger.info(f"Searching repositories with query: {query}")
        
        params = {
            'q': query,
            'sort': 'stars',
            'order': 'desc',
            'per_page': min(max_results, 100)
        }
        
        url = f'{self.config.api_base_url}/search/repositories'
        data = self._make_request(url, params)
        
        repositories = []
        for item in data.get('items', []):
            repo = self._parse_repository(item)
            repositories.append(repo)
        
        logger.info(f"Found {len(repositories)} repositories")
        return SearchResult(
            total_count=data.get('total_count', 0),
            repositories=repositories
        )

    def search_by_activity(
        self,
        days: int = 7,
        min_stars: int = 100,
        max_results: int = 50
    ) -> SearchResult:
        date_str = get_github_search_date(days)
        
        query = f'pushed:>{date_str} stars:>{min_stars} sort:stars'
        
        params = {
            'q': query,
            'sort': 'stars',
            'order': 'desc',
            'per_page': min(max_results, 100)
        }
        
        url = f'{self.config.api_base_url}/search/repositories'
        data = self._make_request(url, params)
        
        repositories = []
        for item in data.get('items', []):
            repo = self._parse_repository(item)
            repositories.append(repo)
        
        return SearchResult(
            total_count=data.get('total_count', 0),
            repositories=repositories
        )

    def get_repository_details(self, owner: str, repo_name: str) -> Optional[Repository]:
        url = f'{self.config.api_base_url}/repos/{owner}/{repo_name}'
        try:
            data = self._make_request(url)
            return self._parse_repository(data)
        except requests.HTTPError as e:
            logger.error(f"Failed to get repository {owner}/{repo_name}: {e}")
            return None

    def get_readme(self, owner: str, repo_name: str) -> Optional[str]:
        url = f'{self.config.api_base_url}/repos/{owner}/{repo_name}/readme'
        try:
            response = self.session.get(url, timeout=self.config.request_timeout)
            if response.status_code == 200:
                data = response.json()
                import base64
                content = data.get('content', '')
                if content:
                    return base64.b64decode(content).decode('utf-8', errors='ignore')
            return None
        except Exception as e:
            logger.warning(f"Failed to get README for {owner}/{repo_name}: {e}")
            return None

    def fetch_readme_for_repository(self, repo: Repository) -> Optional[str]:
        if not repo.owner or not repo.name:
            return None
        return self.get_readme(repo.owner, repo.name)

    def _parse_repository(self, data: Dict[str, Any]) -> Repository:
        license_name = None
        if data.get('license'):
            license_name = data['license'].get('spdx_id') or data['license'].get('name')
        
        return Repository(
            github_id=data.get('id', 0),
            full_name=data.get('full_name', ''),
            name=data.get('name', ''),
            description=data.get('description'),
            html_url=data.get('html_url', ''),
            language=data.get('language'),
            topics=data.get('topics', []),
            stars=data.get('stargazers_count', 0),
            forks=data.get('forks_count', 0),
            open_issues=data.get('open_issues_count', 0),
            created_at=parse_github_date(data.get('created_at')),
            pushed_at=parse_github_date(data.get('pushed_at')),
            license_name=license_name,
        )

    def get_rate_limit(self) -> Dict[str, Any]:
        url = f'{self.config.api_base_url}/rate_limit'
        return self._make_request(url)

    def check_rate_limit(self) -> bool:
        try:
            rate_limit = self.get_rate_limit()
            core = rate_limit.get('resources', {}).get('core', {})
            remaining = core.get('remaining', 0)
            logger.info(f"GitHub API rate limit remaining: {remaining}")
            return remaining > 10
        except Exception as e:
            logger.error(f"Failed to check rate limit: {e}")
            return False
