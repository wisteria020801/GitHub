from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

from database.models import Repository, AnalysisResult, Score
from utils.logger import get_logger

logger = get_logger(__name__)


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
    "其他": []
}


@dataclass
class ScoringWeights:
    popularity: float = 25.0
    growth: float = 20.0
    activity: float = 10.0
    copyability: float = 15.0
    monetization: float = 15.0
    differentiation: float = 15.0


@dataclass
class TrendingScore:
    repo_id: int
    trending_score: float
    stars_component: float
    growth_component: float
    activity_component: float
    category: str
    category_rank: int
    calculated_at: datetime


def categorize_repo(topics: List[str]) -> str:
    if not topics:
        return "其他"
    
    topics_lower = [t.lower() for t in topics]
    
    for category, keywords in CATEGORIES.items():
        if category == "其他":
            continue
        for keyword in keywords:
            if keyword in topics_lower or any(keyword in t for t in topics_lower):
                return category
    
    return "其他"


class Scorer:
    def __init__(self, weights: Optional[ScoringWeights] = None):
        self.weights = weights or ScoringWeights()

    def calculate_score(
        self,
        repo: Repository,
        analysis: Optional[AnalysisResult] = None,
        star_growth: int = 0
    ) -> Score:
        score_popularity = self._calculate_popularity_score(repo)
        score_growth = self._calculate_growth_score(repo, star_growth)
        score_activity = self._calculate_activity_score(repo)
        
        score_copyability = 0.0
        score_monetization = 0.0
        score_differentiation = 0.0
        
        is_fallback = False
        if analysis:
            is_fallback = getattr(analysis, 'is_fallback', False)
            score_copyability = self._calculate_copyability_score(analysis)
            score_monetization = self._calculate_monetization_score(analysis)
            score_differentiation = self._calculate_differentiation_score(analysis)
            
            if is_fallback:
                score_copyability *= 0.5
                score_monetization *= 0.5
                score_differentiation *= 0.5

        total_score = (
            score_popularity * (self.weights.popularity / 25.0) +
            score_growth * (self.weights.growth / 20.0) +
            score_activity * (self.weights.activity / 10.0) +
            score_copyability * (self.weights.copyability / 15.0) +
            score_monetization * (self.weights.monetization / 15.0) +
            score_differentiation * (self.weights.differentiation / 15.0)
        )

        return Score(
            repo_id=repo.id or 0,
            score_popularity=round(score_popularity, 2),
            score_growth=round(score_growth, 2),
            score_copyability=round(score_copyability, 2),
            score_monetization=round(score_monetization, 2),
            score_differentiation=round(score_differentiation, 2),
            total_score=round(total_score, 2),
            scored_at=datetime.now()
        )

    def calculate_trending_score(
        self,
        repo: Repository,
        star_growth: int = 0,
        category: str = "其他"
    ) -> TrendingScore:
        stars_component = self._calculate_stars_trending(repo)
        growth_component = self._calculate_growth_trending(repo, star_growth)
        activity_component = self._calculate_activity_trending(repo)
        
        trending_score = (
            stars_component * 0.3 +
            growth_component * 0.4 +
            activity_component * 0.3
        )
        
        return TrendingScore(
            repo_id=repo.id or 0,
            trending_score=round(trending_score, 2),
            stars_component=round(stars_component, 2),
            growth_component=round(growth_component, 2),
            activity_component=round(activity_component, 2),
            category=category,
            category_rank=0,
            calculated_at=datetime.now()
        )

    def _calculate_stars_trending(self, repo: Repository) -> float:
        stars = repo.stars
        if stars >= 10000:
            return 100.0
        elif stars >= 5000:
            return 80.0
        elif stars >= 1000:
            return 60.0
        elif stars >= 500:
            return 40.0
        elif stars >= 100:
            return 20.0
        else:
            return 10.0

    def _calculate_growth_trending(self, repo: Repository, star_growth: int = 0) -> float:
        if star_growth > 0:
            if star_growth >= 1000:
                return 100.0
            elif star_growth >= 500:
                return 80.0
            elif star_growth >= 100:
                return 60.0
            elif star_growth >= 50:
                return 40.0
            else:
                return 20.0 + (star_growth / 50) * 20.0
        
        if repo.pushed_at:
            days_since_push = (datetime.now() - repo.pushed_at).days
            if days_since_push <= 1:
                return 80.0
            elif days_since_push <= 7:
                return 60.0
            elif days_since_push <= 30:
                return 40.0
            else:
                return 20.0
        return 30.0

    def _calculate_activity_trending(self, repo: Repository) -> float:
        score = 0.0
        
        if repo.open_issues and repo.open_issues > 0:
            score += min(30.0, repo.open_issues / 10)
        
        if repo.forks and repo.forks > 0:
            score += min(30.0, repo.forks / 50)
        
        if repo.pushed_at:
            days_since_push = (datetime.now() - repo.pushed_at).days
            if days_since_push <= 1:
                score += 40.0
            elif days_since_push <= 7:
                score += 30.0
            elif days_since_push <= 30:
                score += 20.0
            else:
                score += 10.0
        
        return min(100.0, score)

    def _calculate_activity_score(self, repo: Repository) -> float:
        if repo.pushed_at:
            days_since_push = (datetime.now() - repo.pushed_at).days
            
            if days_since_push <= 1:
                return 10.0
            elif days_since_push <= 7:
                return 8.0
            elif days_since_push <= 30:
                return 6.0
            elif days_since_push <= 90:
                return 4.0
            else:
                return 2.0
        
        return 5.0

    def _calculate_popularity_score(self, repo: Repository) -> float:
        stars = repo.stars
        
        if stars >= 10000:
            base_score = 25.0
        elif stars >= 5000:
            base_score = 22.0
        elif stars >= 1000:
            base_score = 18.0
        elif stars >= 500:
            base_score = 14.0
        elif stars >= 100:
            base_score = 10.0
        else:
            base_score = 5.0

        fork_bonus = min(3.0, repo.forks / 100)
        
        return min(25.0, base_score + fork_bonus)

    def _calculate_growth_score(self, repo: Repository, star_growth: int = 0) -> float:
        if star_growth > 0:
            if star_growth >= 1000:
                return 20.0
            elif star_growth >= 500:
                return 17.0
            elif star_growth >= 100:
                return 14.0
            elif star_growth >= 50:
                return 11.0
            else:
                return 8.0 + (star_growth / 50) * 3.0
        
        if repo.pushed_at:
            days_since_push = (datetime.now() - repo.pushed_at).days
            
            if days_since_push <= 1:
                return 15.0
            elif days_since_push <= 7:
                return 12.0
            elif days_since_push <= 30:
                return 8.0
            else:
                return 5.0
        
        return 10.0

    def _calculate_copyability_score(self, analysis: AnalysisResult) -> float:
        difficulty_text = (analysis.copy_difficulty or '').lower()
        
        if '低' in difficulty_text or '简单' in difficulty_text or 'easy' in difficulty_text:
            return 15.0
        elif '高' in difficulty_text or '困难' in difficulty_text or 'hard' in difficulty_text or '复杂' in difficulty_text:
            return 5.0
        elif '中' in difficulty_text or 'medium' in difficulty_text:
            return 10.0
        
        return 10.0

    def _calculate_monetization_score(self, analysis: AnalysisResult) -> float:
        monetization_text = (analysis.monetization_potential or '').lower()
        
        high_keywords = ['付费', '订阅', '企业', 'saas', 'api', '自动化', '数据', 'extract', 'automation']
        medium_keywords = ['工具', 'tool', '效率', 'productivity', '团队']
        low_keywords = ['娱乐', '学习', '教程', 'tutorial', 'demo', '示例']
        
        for keyword in high_keywords:
            if keyword in monetization_text:
                return 18.0
        
        for keyword in medium_keywords:
            if keyword in monetization_text:
                return 12.0
        
        for keyword in low_keywords:
            if keyword in monetization_text:
                return 6.0
        
        return 10.0

    def _calculate_differentiation_score(self, analysis: AnalysisResult) -> float:
        ideas_count = len(analysis.differentiation_ideas or [])
        
        if ideas_count >= 5:
            return 18.0
        elif ideas_count >= 3:
            return 15.0
        elif ideas_count >= 1:
            return 12.0
        
        return 8.0

    def get_score_level(self, total_score: float) -> str:
        if total_score >= 80:
            return "🌟 优秀"
        elif total_score >= 70:
            return "👍 良好"
        elif total_score >= 60:
            return "😊 一般"
        elif total_score >= 50:
            return "🤔 待观察"
        else:
            return "⚠️ 不推荐"
