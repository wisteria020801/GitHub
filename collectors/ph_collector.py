import requests
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from utils.logger import get_logger
from utils.helpers import retry_on_failure

logger = get_logger(__name__)


@dataclass
class PHPost:
    id: str
    name: str
    tagline: str
    url: str
    votes_count: int
    comments_count: int
    created_at: datetime
    featured: bool = False
    source: str = "producthunt"
    topics: List[str] = None
    
    def __post_init__(self):
        if self.topics is None:
            self.topics = []
    
    def to_repo_dict(self) -> dict:
        return {
            'source': 'producthunt',
            'external_id': self.id,
            'title': self.name,
            'description': self.tagline,
            'url': self.url,
            'score': self.votes_count,
            'comments': self.comments_count,
            'published_at': self.created_at,
            'topics': self.topics,
        }


class ProductHuntCollector:
    API_BASE = "https://api.producthunt.com/v2/api/graphql"
    
    def __init__(self, api_token: Optional[str] = None):
        self.session = requests.Session()
        self.api_token = api_token
        if api_token:
            self.session.headers.update({
                'Authorization': f'Bearer {api_token}',
                'Content-Type': 'application/json',
            })
        self.session.headers.update({
            'User-Agent': 'GitHub-Radar/1.0',
            'Accept': 'application/json',
        })
    
    def _make_graphql_request(self, query: str, variables: dict = None) -> dict:
        payload = {
            'query': query,
            'variables': variables or {}
        }
        
        response = self.session.post(
            self.API_BASE, 
            json=payload, 
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def get_posts_today(self, limit: int = 50) -> List[PHPost]:
        query = """
        query GetPosts($first: Int!) {
            posts(first: $first, order: RANKING) {
                edges {
                    node {
                        id
                        name
                        tagline
                        url
                        votesCount
                        commentsCount
                        createdAt
                        featured
                        topics(first: 5) {
                            edges {
                                node {
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        try:
            data = self._make_graphql_request(query, {'first': limit})
            posts = []
            
            edges = data.get('data', {}).get('posts', {}).get('edges', [])
            for edge in edges:
                node = edge.get('node', {})
                topics = [
                    t.get('node', {}).get('name', '')
                    for t in node.get('topics', {}).get('edges', [])
                ]
                
                post = PHPost(
                    id=node.get('id', ''),
                    name=node.get('name', ''),
                    tagline=node.get('tagline', ''),
                    url=node.get('url', ''),
                    votes_count=node.get('votesCount', 0),
                    comments_count=node.get('commentsCount', 0),
                    created_at=self._parse_date(node.get('createdAt')),
                    featured=node.get('featured', False),
                    topics=topics,
                )
                posts.append(post)
            
            logger.info(f"Found {len(posts)} posts from Product Hunt today")
            return posts
            
        except Exception as e:
            logger.error(f"Failed to fetch Product Hunt posts: {e}")
            return []
    
    def get_trending_posts(
        self, 
        min_votes: int = 100, 
        limit: int = 30
    ) -> List[PHPost]:
        posts = self.get_posts_today(limit * 2)
        
        trending = [
            p for p in posts 
            if p.votes_count >= min_votes
        ]
        
        trending.sort(key=lambda x: x.votes_count, reverse=True)
        return trending[:limit]
    
    def _parse_date(self, date_str: Optional[str]) -> datetime:
        if not date_str:
            return datetime.now()
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return datetime.now()
    
    def get_developer_tools(self, limit: int = 30) -> List[PHPost]:
        query = """
        query GetDeveloperPosts($first: Int!) {
            posts(first: $first, order: RANKING, topic: "developer-tools") {
                edges {
                    node {
                        id
                        name
                        tagline
                        url
                        votesCount
                        commentsCount
                        createdAt
                        featured
                        topics(first: 5) {
                            edges {
                                node {
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        try:
            data = self._make_graphql_request(query, {'first': limit})
            posts = []
            
            edges = data.get('data', {}).get('posts', {}).get('edges', [])
            for edge in edges:
                node = edge.get('node', {})
                topics = [
                    t.get('node', {}).get('name', '')
                    for t in node.get('topics', {}).get('edges', [])
                ]
                
                post = PHPost(
                    id=node.get('id', ''),
                    name=node.get('name', ''),
                    tagline=node.get('tagline', ''),
                    url=node.get('url', ''),
                    votes_count=node.get('votesCount', 0),
                    comments_count=node.get('commentsCount', 0),
                    created_at=self._parse_date(node.get('createdAt')),
                    featured=node.get('featured', False),
                    topics=topics,
                )
                posts.append(post)
            
            logger.info(f"Found {len(posts)} developer tool posts from Product Hunt")
            return posts
            
        except Exception as e:
            logger.error(f"Failed to fetch developer tools: {e}")
            return []
