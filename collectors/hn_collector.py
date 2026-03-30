import requests
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from utils.logger import get_logger
from utils.helpers import retry_on_failure

logger = get_logger(__name__)


@dataclass
class HNStory:
    id: int
    title: str
    url: Optional[str]
    score: int
    by: str
    time: datetime
    descendants: int = 0
    source: str = "hackernews"
    
    def to_repo_dict(self) -> dict:
        return {
            'source': 'hackernews',
            'external_id': self.id,
            'title': self.title,
            'url': self.url,
            'score': self.score,
            'author': self.by,
            'published_at': self.time,
            'comments': self.descendants,
        }


class HackerNewsCollector:
    API_BASE = "https://hacker-news.firebaseio.com/v0"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GitHub-Radar/1.0'
        })
    
    @retry_on_failure(max_retries=3, delay=1.0, exceptions=(requests.RequestException,))
    def _make_request(self, endpoint: str) -> Any:
        url = f"{self.API_BASE}/{endpoint}"
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def get_top_stories(self, limit: int = 100) -> List[int]:
        logger.info("Fetching top stories from Hacker News")
        story_ids = self._make_request("topstories.json")
        return story_ids[:limit]
    
    def get_new_stories(self, limit: int = 100) -> List[int]:
        logger.info("Fetching new stories from Hacker News")
        story_ids = self._make_request("newstories.json")
        return story_ids[:limit]
    
    def get_best_stories(self, limit: int = 100) -> List[int]:
        logger.info("Fetching best stories from Hacker News")
        story_ids = self._make_request("beststories.json")
        return story_ids[:limit]
    
    def get_story(self, story_id: int) -> Optional[HNStory]:
        try:
            data = self._make_request(f"item/{story_id}.json")
            if not data or data.get('type') != 'story':
                return None
            
            if data.get('deleted') or data.get('dead'):
                return None
            
            return HNStory(
                id=data.get('id', 0),
                title=data.get('title', ''),
                url=data.get('url'),
                score=data.get('score', 0),
                by=data.get('by', ''),
                time=datetime.fromtimestamp(data.get('time', 0)),
                descendants=data.get('descendants', 0),
            )
        except Exception as e:
            logger.warning(f"Failed to fetch story {story_id}: {e}")
            return None
    
    def get_trending_stories(
        self, 
        min_score: int = 100, 
        limit: int = 50,
        hours: int = 24
    ) -> List[HNStory]:
        story_ids = self.get_top_stories(limit * 2)
        
        stories = []
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for story_id in story_ids[:limit * 2]:
            story = self.get_story(story_id)
            if story and story.score >= min_score and story.time >= cutoff_time:
                stories.append(story)
            
            if len(stories) >= limit:
                break
        
        stories.sort(key=lambda x: x.score, reverse=True)
        logger.info(f"Found {len(stories)} trending stories from Hacker News")
        return stories
    
    def get_github_links(self, stories: List[HNStory]) -> List[HNStory]:
        github_stories = []
        for story in stories:
            if story.url and 'github.com' in story.url.lower():
                github_stories.append(story)
        
        logger.info(f"Found {len(github_stories)} GitHub links from HN stories")
        return github_stories
    
    def extract_github_repo(self, url: str) -> Optional[str]:
        import re
        pattern = r'github\.com/([^/]+/[^/]+)'
        match = re.search(pattern, url)
        if match:
            return match.group(1).rstrip('/')
        return None
