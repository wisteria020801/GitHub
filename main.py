import time
import signal
import sys
from datetime import datetime
from typing import List, Tuple

from config import config
from database.models import Repository, AnalysisResult, Score, StarSnapshot, TelegramMessage
from database.db_manager import DatabaseManager
from collectors.github_collector import GitHubCollector
from analyzers.readme_parser import ReadmeParser
from analyzers.llm_analyzer import LLMAnalyzer
from scorers.scorer import Scorer
from notifiers.telegram_notifier import TelegramNotifier
from utils.logger import get_logger

logger = get_logger(__name__)


class GitHubRadar:
    def __init__(self):
        self.db = DatabaseManager(config.database.path)
        self.collector = GitHubCollector(config.github)
        self.readme_parser = ReadmeParser()
        self.llm_analyzer = LLMAnalyzer(config.llm)
        self.scorer = Scorer()
        self.notifier = TelegramNotifier(config.telegram)
        
        self.running = True
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal, stopping...")
            self.running = False
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def run_once(self) -> dict:
        logger.info("=" * 50)
        logger.info(f"Starting scan at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        stats = {
            'collected': 0,
            'new': 0,
            'analyzed': 0,
            'scored': 0,
            'notified': 0,
            'errors': 0
        }
        
        try:
            stats['collected'], stats['new'] = self._collect_repositories()
            self._fetch_readmes()
            stats['analyzed'] = self._analyze_repositories()
            stats['scored'] = self._score_repositories()
            stats['notified'] = self._notify_top_projects()
            
        except Exception as e:
            logger.error(f"Error during scan: {e}")
            stats['errors'] += 1
        
        logger.info(f"Scan completed: {stats}")
        return stats

    def run_forever(self):
        logger.info("Starting GitHub Radar in continuous mode")
        logger.info(f"Scan interval: {config.system.scan_interval_minutes} minutes")
        
        self._test_connections()
        
        while self.running:
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
            
            if self.running:
                logger.info(f"Sleeping for {config.system.scan_interval_minutes} minutes...")
                time.sleep(config.system.scan_interval_minutes * 60)

    def _test_connections(self):
        logger.info("Testing connections...")
        
        if not self.collector.check_rate_limit():
            logger.warning("GitHub API rate limit is low!")
        
        if not self.notifier.test_connection():
            logger.warning("Telegram connection failed!")
        
        logger.info("Connection tests completed")

    def _collect_repositories(self) -> Tuple[int, int]:
        logger.info("Collecting repositories from GitHub...")
        
        result = self.collector.search_trending_repositories(
            days=7,
            min_stars=50,
            max_results=config.github.max_results
        )
        
        new_count = 0
        for repo in result.repositories:
            existing = self.db.get_repository_by_github_id(repo.github_id)
            if existing:
                self._save_star_snapshot(existing)
                repo.id = existing.id
                self.db.update_repository(repo)
            else:
                repo_id = self.db.insert_repository(repo)
                if repo_id:
                    repo.id = repo_id
                    new_count += 1
                    self._save_star_snapshot(repo)
        
        logger.info(f"Collected {result.total_count} repos, {new_count} new")
        return result.total_count, new_count

    def _save_star_snapshot(self, repo: Repository):
        if not repo.id:
            return
        
        snapshot = StarSnapshot(
            repo_id=repo.id,
            stars=repo.stars,
            forks=repo.forks
        )
        self.db.insert_star_snapshot(snapshot)

    def _fetch_readmes(self):
        logger.info("Fetching READMEs for repositories without content...")
        
        repos = self.db.get_all_repositories(limit=50)
        for repo in repos:
            if not repo.readme_content:
                readme = self.collector.fetch_readme_for_repository(repo)
                if readme:
                    parsed = self.readme_parser.parse(readme)
                    if parsed.is_valid:
                        repo.readme_content = parsed.raw_content
                        repo.readme_fetched_at = datetime.now()
                        self.db.update_repository(repo)
                        logger.debug(f"Fetched README for {repo.full_name}")

    def _analyze_repositories(self) -> int:
        logger.info("Analyzing repositories with LLM...")
        
        repos = self.db.get_unanalyzed_repositories(limit=20)
        analyzed_count = 0
        
        for repo in repos:
            if not repo.readme_content:
                continue
            
            try:
                llm_result = self.llm_analyzer.analyze_repository(repo)
                if llm_result:
                    analysis = self.llm_analyzer.to_analysis_result(llm_result, repo.id)
                    self.db.insert_analysis_result(analysis)
                    analyzed_count += 1
                    logger.info(f"Analyzed {repo.full_name}")
            except Exception as e:
                logger.error(f"Failed to analyze {repo.full_name}: {e}")
        
        logger.info(f"Analyzed {analyzed_count} repositories")
        return analyzed_count

    def _score_repositories(self) -> int:
        logger.info("Scoring repositories...")
        
        repos = self.db.get_unscored_repositories(limit=50)
        scored_count = 0
        
        for repo in repos:
            analysis = self.db.get_analysis_by_repo_id(repo.id)
            growth, _ = self.db.get_star_growth(repo.id, days=7)
            
            score = self.scorer.calculate_score(repo, analysis, growth)
            self.db.insert_score(score)
            scored_count += 1
            logger.debug(f"Scored {repo.full_name}: {score.total_score}")
        
        logger.info(f"Scored {scored_count} repositories")
        return scored_count

    def _notify_top_projects(self) -> int:
        logger.info("Notifying top projects...")
        
        top_projects = self.db.get_top_scored_repositories(
            min_score=config.scoring.min_score_to_notify,
            limit=config.scoring.max_results_per_day
        )
        
        if not top_projects:
            logger.info("No projects meet notification threshold")
            return 0
        
        notified_count = 0
        for repo, score, analysis in top_projects:
            try:
                msg_id = self.notifier.notify_project(repo, score, analysis)
                if msg_id:
                    telegram_msg = TelegramMessage(
                        repo_id=repo.id,
                        message_id=msg_id,
                        status='sent'
                    )
                    self.db.insert_telegram_message(telegram_msg)
                    notified_count += 1
                    logger.info(f"Notified {repo.full_name} (score: {score.total_score})")
            except Exception as e:
                logger.error(f"Failed to notify {repo.full_name}: {e}")
        
        logger.info(f"Notified {notified_count} projects")
        return notified_count


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='GitHub Radar - Trending Project Analyzer')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--test', action='store_true', help='Test connections and exit')
    args = parser.parse_args()
    
    radar = GitHubRadar()
    
    if args.test:
        radar._test_connections()
        return
    
    if args.once:
        radar.run_once()
    else:
        radar.run_forever()


if __name__ == '__main__':
    main()
