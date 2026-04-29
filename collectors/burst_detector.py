import time
import requests
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BurstEvent:
    keyword: str
    current_count: int
    previous_count: int
    growth_rate: float
    sample_repos: List[str]
    detected_at: datetime


class BurstDetector:
    BURST_KEYWORDS = {
        'source_leak': ['source code leak', 'source leak', '源码泄露', '源码泄漏'],
        'new_release': ['just released', 'new release', 'v1.0', 'v2.0', 'launch'],
        'viral': ['going viral', 'trending', '爆火', '刷屏'],
        'security': ['vulnerability', 'exploit', 'CVE', 'zero-day', '漏洞'],
        'breakthrough': ['breakthrough', 'state-of-the-art', 'SOTA', '突破'],
    }
    
    TRENDING_TOPICS = [
        'claude', 'gpt', 'openai', 'anthropic', 'cursor', 'copilot',
        'mcp', 'agent', 'rag', 'llm', 'deepseek', 'llama',
        'sora', 'bun', 'deno', 'rust', 'zig',
        'kubernetes', 'docker', 'react', 'vue',
        'blockchain', 'defi',
    ]
    
    def __init__(self, github_token: str):
        self.github_token = github_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Radar/1.0'
        })
        self._baseline: Dict[str, int] = {}
    
    def detect_bursts(self) -> List[BurstEvent]:
        logger.info("Running burst detection...")
        events = []
        
        import random
        topics = random.sample(self.TRENDING_TOPICS, min(15, len(self.TRENDING_TOPICS)))
        
        for topic in topics:
            event = self._check_topic_burst(topic)
            if event:
                events.append(event)
            time.sleep(0.5)
        
        hn_events = self._check_hn_bursts()
        events.extend(hn_events)
        
        events.sort(key=lambda x: x.growth_rate, reverse=True)
        
        if events:
            logger.info(f"Detected {len(events)} burst events")
            for e in events[:5]:
                logger.info(f"  Burst: {e.keyword} (+{e.growth_rate:.0f}%)")
        
        return events
    
    def _check_topic_burst(self, topic: str) -> Optional[BurstEvent]:
        try:
            now = datetime.now()
            
            recent_count = self._search_count(topic, days=1)
            previous_count = self._search_count(topic, days=2, offset_days=1)
            
            self._baseline[topic] = previous_count
            
            if previous_count > 0:
                growth_rate = ((recent_count - previous_count) / previous_count) * 100
            elif recent_count > 0:
                growth_rate = 100.0
            else:
                return None
            
            threshold = 50.0
            if recent_count >= 5 and growth_rate >= threshold:
                sample_repos = self._get_sample_repos(topic, limit=3)
                
                return BurstEvent(
                    keyword=topic,
                    current_count=recent_count,
                    previous_count=previous_count,
                    growth_rate=growth_rate,
                    sample_repos=sample_repos,
                    detected_at=now
                )
        
        except Exception as e:
            logger.warning(f"Failed to check burst for '{topic}': {e}")
        
        return None
    
    def _search_count(self, keyword: str, days: int = 1, offset_days: int = 0) -> int:
        try:
            from utils.helpers import get_github_search_date
            
            end_date = datetime.now() - timedelta(days=offset_days)
            start_date = end_date - timedelta(days=days)
            
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            query = f'{keyword} created:{start_str}..{end_str}'
            
            url = 'https://api.github.com/search/repositories'
            params = {
                'q': query,
                'per_page': 1
            }
            
            response = self.session.get(url, params=params, timeout=10)
            if response.ok:
                data = response.json()
                return data.get('total_count', 0)
        except Exception as e:
            logger.warning(f"Search count failed for '{keyword}': {e}")
        
        return 0
    
    def _get_sample_repos(self, keyword: str, limit: int = 3) -> List[str]:
        try:
            date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            query = f'{keyword} created:>{date_str} sort:stars'
            
            url = 'https://api.github.com/search/repositories'
            params = {
                'q': query,
                'sort': 'stars',
                'order': 'desc',
                'per_page': limit
            }
            
            response = self.session.get(url, params=params, timeout=10)
            if response.ok:
                data = response.json()
                repos = []
                for item in data.get('items', []):
                    repos.append(item.get('full_name', ''))
                return repos
        except Exception as e:
            logger.warning(f"Sample repos failed for '{keyword}': {e}")
        
        return []
    
    def _check_hn_bursts(self) -> List[BurstEvent]:
        events = []
        try:
            url = 'https://hacker-news.firebaseio.com/v0/topstories.json'
            response = requests.get(url, timeout=10)
            if not response.ok:
                return events
            
            story_ids = response.json()[:30]
            
            github_pattern = re.compile(r'github\.com/([^/]+/[^/?]+)')
            keyword_counts: Dict[str, int] = {}
            keyword_repos: Dict[str, List[str]] = {}
            
            for sid in story_ids:
                try:
                    story_url = f'https://hacker-news.firebaseio.com/v0/item/{sid}.json'
                    story_resp = requests.get(story_url, timeout=5)
                    if not story_resp.ok:
                        continue
                    
                    story = story_resp.json()
                    title = story.get('title', '').lower()
                    url_str = story.get('url', '')
                    
                    match = github_pattern.search(url_str)
                    if match:
                        repo_name = match.group(1)
                        for topic in self.TRENDING_TOPICS:
                            if topic.lower() in title:
                                keyword_counts[topic] = keyword_counts.get(topic, 0) + 1
                                if topic not in keyword_repos:
                                    keyword_repos[topic] = []
                                keyword_repos[topic].append(repo_name)
                except:
                    continue
            
            for topic, count in keyword_counts.items():
                if count >= 2:
                    events.append(BurstEvent(
                        keyword=f"HN: {topic}",
                        current_count=count,
                        previous_count=0,
                        growth_rate=999.0,
                        sample_repos=keyword_repos.get(topic, [])[:3],
                        detected_at=datetime.now()
                    ))
        
        except Exception as e:
            logger.warning(f"HN burst detection failed: {e}")
        
        return events
