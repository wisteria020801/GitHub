import requests
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from utils.logger import get_logger
from utils.helpers import retry_on_failure

logger = get_logger(__name__)


@dataclass
class HFModel:
    id: str
    author: str
    model_id: str
    likes: int
    downloads: int
    tags: List[str]
    created_at: Optional[datetime]
    url: str
    description: Optional[str] = None
    source: str = "huggingface"
    card_data: Dict[str, Any] = None


class HuggingFaceCollector:
    API_BASE = "https://huggingface.co/api"
    
    KNOWN_GITHUB_ORGS = {
        'deepseek-ai': 'deepseek-ai',
        'black-forest-labs': 'black-forest-labs',
        'stabilityai': 'Stability-AI',
        'meta-llama': 'meta-llama',
        'openai': 'openai',
        'google': 'google',
        'microsoft': 'microsoft',
        'facebook': 'facebookresearch',
        'anthropic': 'anthropics',
        'mistralai': 'mistralai',
        'bigcode-project': 'bigcode-project',
        'open-mmlm': 'open-mmlab',
        'THUDM': 'THUDM',
        'Qwen': 'QwenLM',
        'baichuan-inc': 'baichuan-inc',
        '01-ai': '01-ai',
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GitHub-Radar/1.0'
        })
    
    @retry_on_failure(max_retries=3, delay=1.0, exceptions=(requests.RequestException,))
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        url = f"{self.API_BASE}/{endpoint}"
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def get_trending_models(
        self,
        min_likes: int = 50,
        limit: int = 30,
        days: int = 7
    ) -> List[HFModel]:
        logger.info("Fetching trending models from Hugging Face")
        
        try:
            data = self._make_request("models", params={
                'sort': 'likes',
                'direction': '-1',
                'limit': limit * 2
            })
            
            models = []
            cutoff_time = datetime.now() - timedelta(days=days)
            
            for item in data:
                likes = item.get('likes', 0)
                if likes < min_likes:
                    continue
                
                created_at = None
                created_str = item.get('createdAt')
                if created_str:
                    try:
                        created_at = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        pass
                
                model_id = item.get('id', '')
                author = model_id.split('/')[0] if '/' in model_id else ''
                
                tags = item.get('tags', [])
                downloads = item.get('downloads', 0)
                
                url = f"https://huggingface.co/{model_id}"
                
                model = HFModel(
                    id=model_id,
                    author=author,
                    model_id=model_id,
                    likes=likes,
                    downloads=downloads,
                    tags=tags,
                    created_at=created_at,
                    url=url,
                    description=item.get('pipeline_tag', ''),
                    card_data=item.get('cardData', {})
                )
                models.append(model)
            
            models.sort(key=lambda x: x.likes, reverse=True)
            logger.info(f"Found {len(models)} trending models from Hugging Face")
            return models[:limit]
            
        except Exception as e:
            logger.error(f"Failed to fetch Hugging Face models: {e}")
            return []
    
    def get_trending_spaces(
        self,
        limit: int = 20
    ) -> List[HFModel]:
        logger.info("Fetching trending spaces from Hugging Face")
        
        try:
            data = self._make_request("spaces", params={
                'sort': 'likes',
                'direction': '-1',
                'limit': limit
            })
            
            spaces = []
            for item in data:
                space_id = item.get('id', '')
                author = space_id.split('/')[0] if '/' in space_id else ''
                likes = item.get('likes', 0)
                
                url = f"https://huggingface.co/spaces/{space_id}"
                
                space = HFModel(
                    id=space_id,
                    author=author,
                    model_id=space_id,
                    likes=likes,
                    downloads=0,
                    tags=item.get('tags', []),
                    created_at=None,
                    url=url,
                    description=item.get('pipeline_tag', ''),
                    card_data=item.get('cardData', {})
                )
                spaces.append(space)
            
            logger.info(f"Found {len(spaces)} trending spaces from Hugging Face")
            return spaces
            
        except Exception as e:
            logger.error(f"Failed to fetch Hugging Face spaces: {e}")
            return []
    
    def extract_github_repo(self, model: HFModel) -> Optional[str]:
        # 1. 检查tags中的github:前缀
        for tag in model.tags:
            if tag.startswith('github:'):
                return tag[7:]
        
        # 2. 检查card_data中的github链接
        if model.card_data:
            # 检查homepage
            homepage = model.card_data.get('homepage', '')
            if homepage and 'github.com' in homepage:
                match = re.search(r'github\.com/([^/]+/[^/]+)', homepage)
                if match:
                    return match.group(1).rstrip('/')
            
            # 检查repository
            repo_url = model.card_data.get('repo', '') or model.card_data.get('repository', '')
            if repo_url and 'github.com' in repo_url:
                match = re.search(r'github\.com/([^/]+/[^/]+)', repo_url)
                if match:
                    return match.group(1).rstrip('/')
        
        # 3. 基于已知组织映射推断
        if model.author in self.KNOWN_GITHUB_ORGS:
            github_org = self.KNOWN_GITHUB_ORGS[model.author]
            model_name = model.model_id.split('/')[-1]
            return f"{github_org}/{model_name}"
        
        return None
