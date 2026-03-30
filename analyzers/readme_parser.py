import re
from typing import Optional, List, Tuple
from dataclasses import dataclass

from utils.logger import get_logger
from utils.helpers import clean_text, truncate_text

logger = get_logger(__name__)


@dataclass
class ParsedReadme:
    title: str
    description: str
    features: List[str]
    installation: Optional[str]
    usage: Optional[str]
    tech_stack: List[str]
    raw_content: str
    is_valid: bool
    quality_score: float


class ReadmeParser:
    MIN_CONTENT_LENGTH = 100
    MIN_QUALITY_SCORE = 0.3

    TECH_KEYWORDS = [
        'python', 'javascript', 'typescript', 'node', 'react', 'vue', 'angular',
        'go', 'rust', 'java', 'kotlin', 'swift', 'ruby', 'php', 'c++', 'c#',
        'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'mongodb', 'postgresql',
        'redis', 'elasticsearch', 'graphql', 'rest', 'api', 'cli', 'gui',
        'machine learning', 'deep learning', 'ai', 'llm', 'gpt', 'transformer',
        'automation', 'bot', 'scraper', 'crawler', 'framework', 'library',
        'saas', 'web app', 'mobile', 'desktop', 'extension', 'plugin'
    ]

    def parse(self, content: Optional[str]) -> ParsedReadme:
        if not content:
            return self._empty_result("No content provided")

        content = content.strip()
        
        if len(content) < self.MIN_CONTENT_LENGTH:
            return self._empty_result(f"Content too short: {len(content)} chars")

        title = self._extract_title(content)
        description = self._extract_description(content)
        features = self._extract_features(content)
        installation = self._extract_section(content, ['installation', 'install', 'getting started', 'quick start'])
        usage = self._extract_section(content, ['usage', 'how to use', 'example', 'examples'])
        tech_stack = self._extract_tech_stack(content)
        
        quality_score = self._calculate_quality_score(
            content, title, description, features, tech_stack
        )
        
        is_valid = quality_score >= self.MIN_QUALITY_SCORE

        return ParsedReadme(
            title=title,
            description=description,
            features=features,
            installation=installation,
            usage=usage,
            tech_stack=tech_stack,
            raw_content=truncate_text(content, 8000),
            is_valid=is_valid,
            quality_score=quality_score
        )

    def _empty_result(self, reason: str) -> ParsedReadme:
        logger.debug(f"Empty README result: {reason}")
        return ParsedReadme(
            title="",
            description="",
            features=[],
            installation=None,
            usage=None,
            tech_stack=[],
            raw_content="",
            is_valid=False,
            quality_score=0.0
        )

    def _extract_title(self, content: str) -> str:
        h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if h1_match:
            return clean_text(h1_match.group(1))
        
        title_match = re.search(r'^\*\*(.+?)\*\*', content, re.MULTILINE)
        if title_match:
            return clean_text(title_match.group(1))
        
        return ""

    def _extract_description(self, content: str) -> str:
        lines = content.split('\n')
        description_lines = []
        found_title = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('#'):
                if not found_title:
                    found_title = True
                continue
            
            if found_title and len(description_lines) < 3:
                if not line.startswith(('-', '*', '>', '`', '[')):
                    clean_line = clean_text(line)
                    if len(clean_line) > 20:
                        description_lines.append(clean_line)
            
            if len(description_lines) >= 3:
                break
        
        return ' '.join(description_lines)

    def _extract_features(self, content: str) -> List[str]:
        features = []
        
        feature_section = self._extract_section(content, ['features', 'key features', 'highlights', 'what it does'])
        if feature_section:
            lines = feature_section.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith(('-', '*', '+')):
                    feature = clean_text(line.lstrip('-*+').strip())
                    if feature and len(feature) > 5:
                        features.append(feature)
        
        if not features:
            list_items = re.findall(r'^[-*+]\s+(.+)$', content, re.MULTILINE)
            for item in list_items[:10]:
                clean_item = clean_text(item)
                if len(clean_item) > 10 and len(clean_item) < 200:
                    features.append(clean_item)
        
        return features[:10]

    def _extract_section(self, content: str, headers: List[str]) -> Optional[str]:
        header_pattern = '|'.join(re.escape(h) for h in headers)
        pattern = rf'#+\s*({header_pattern})\s*\n(.*?)(?=\n#|\Z)'
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        
        if match:
            return clean_text(match.group(2))
        return None

    def _extract_tech_stack(self, content: str) -> List[str]:
        content_lower = content.lower()
        found_tech = []
        
        for tech in self.TECH_KEYWORDS:
            if tech in content_lower:
                found_tech.append(tech)
        
        return list(set(found_tech))[:15]

    def _calculate_quality_score(
        self,
        content: str,
        title: str,
        description: str,
        features: List[str],
        tech_stack: List[str]
    ) -> float:
        score = 0.0
        
        if title:
            score += 0.2
        
        if description and len(description) > 50:
            score += 0.2
        
        if features:
            score += min(0.2, len(features) * 0.04)
        
        if tech_stack:
            score += min(0.2, len(tech_stack) * 0.02)
        
        if len(content) > 500:
            score += 0.1
        elif len(content) > 200:
            score += 0.05
        
        if re.search(r'```', content):
            score += 0.1
        
        return min(1.0, score)

    def is_valid_for_analysis(self, content: Optional[str]) -> Tuple[bool, str]:
        if not content:
            return False, "No README content"
        
        parsed = self.parse(content)
        
        if not parsed.is_valid:
            return False, f"Quality score too low: {parsed.quality_score:.2f}"
        
        return True, "Valid for analysis"
