from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from config import GitHubConfig
from collectors.github_collector import GitHubCollector, Repository
from collectors.hn_collector import HackerNewsCollector, HNStory
from collectors.ph_collector import ProductHuntCollector, PHPost
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TrendingItem:
    source: str
    title: str
    description: Optional[str]
    url: str
    score: int
    github_repo: Optional[str] = None
    raw_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.raw_data is None:
            self.raw_data = {}


class MultiSourceCollector:
    def __init__(
        self, 
        github_config: GitHubConfig,
        ph_api_token: Optional[str] = None
    ):
        self.github = GitHubCollector(github_config)
        self.hn = HackerNewsCollector()
        self.ph = ProductHuntCollector(api_token=ph_api_token)
    
    def collect_all(self, limit_per_source: int = 30) -> List[TrendingItem]:
        items = []
        
        items.extend(self.collect_github_trending(limit_per_source))
        items.extend(self.collect_hn_trending(limit_per_source))
        items.extend(self.collect_ph_trending(limit_per_source))
        
        items.sort(key=lambda x: x.score, reverse=True)
        logger.info(f"Collected {len(items)} trending items from all sources")
        
        return items
    
    def collect_github_trending(self, limit: int = 30) -> List[TrendingItem]:
        items = []
        try:
            result = self.github.search_trending_repositories(
                days=7,
                min_stars=50,
                max_results=limit
            )
            
            for repo in result.repositories:
                items.append(TrendingItem(
                    source='github',
                    title=repo.full_name,
                    description=repo.description,
                    url=repo.html_url,
                    score=repo.stars,
                    github_repo=repo.full_name,
                    raw_data={
                        'language': repo.language,
                        'topics': repo.topics,
                        'forks': repo.forks,
                        'open_issues': repo.open_issues,
                        'created_at': str(repo.created_at) if repo.created_at else None,
                    }
                ))
            
            logger.info(f"Collected {len(items)} items from GitHub")
        except Exception as e:
            logger.error(f"Failed to collect from GitHub: {e}")
        
        return items
    
    def collect_hn_trending(self, limit: int = 30) -> List[TrendingItem]:
        items = []
        try:
            stories = self.hn.get_trending_stories(
                min_score=100,
                limit=limit,
                hours=24
            )
            
            for story in stories:
                github_repo = None
                if story.url:
                    github_repo = self.hn.extract_github_repo(story.url)
                
                items.append(TrendingItem(
                    source='hackernews',
                    title=story.title,
                    description=None,
                    url=story.url or f"https://news.ycombinator.com/item?id={story.id}",
                    score=story.score,
                    github_repo=github_repo,
                    raw_data={
                        'author': story.by,
                        'comments': story.descendants,
                        'published_at': str(story.time),
                    }
                ))
            
            logger.info(f"Collected {len(items)} items from Hacker News")
        except Exception as e:
            logger.error(f"Failed to collect from Hacker News: {e}")
        
        return items
    
    def collect_ph_trending(self, limit: int = 30) -> List[TrendingItem]:
        items = []
        try:
            posts = self.ph.get_trending_posts(
                min_votes=50,
                limit=limit
            )
            
            for post in posts:
                github_repo = None
                if post.url and 'github.com' in post.url.lower():
                    import re
                    match = re.search(r'github\.com/([^/]+/[^/]+)', post.url)
                    if match:
                        github_repo = match.group(1).rstrip('/')
                
                items.append(TrendingItem(
                    source='producthunt',
                    title=post.name,
                    description=post.tagline,
                    url=post.url,
                    score=post.votes_count,
                    github_repo=github_repo,
                    raw_data={
                        'topics': post.topics,
                        'comments': post.comments_count,
                        'featured': post.featured,
                        'published_at': str(post.created_at),
                    }
                ))
            
            logger.info(f"Collected {len(items)} items from Product Hunt")
        except Exception as e:
            logger.error(f"Failed to collect from Product Hunt: {e}")
        
        return items
    
    def get_github_repos_from_external(self) -> Dict[str, TrendingItem]:
        external_githubs = {}
        
        hn_items = self.collect_hn_trending(50)
        for item in hn_items:
            if item.github_repo:
                external_githubs[item.github_repo] = item
        
        ph_items = self.collect_ph_trending(50)
        for item in ph_items:
            if item.github_repo:
                external_githubs[item.github_repo] = item
        
        logger.info(f"Found {len(external_githubs)} unique GitHub repos from external sources")
        return external_githubs
    
    def enrich_with_github_details(
        self, 
        repo_name: str, 
        source_item: TrendingItem
    ) -> Optional[Repository]:
        try:
            owner, name = repo_name.split('/')
            repo = self.github.get_repository_details(owner, name)
            
            if repo:
                readme = self.github.fetch_readme_for_repository(repo)
                if readme:
                    repo.readme_content = readme
                repo.source = source_item.source
            
            return repo
        except Exception as e:
            logger.warning(f"Failed to enrich {repo_name}: {e}")
            return None
