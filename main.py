import time
import signal
import sys
from datetime import datetime
from typing import List, Tuple, Optional
import os

from config import config
from database.models import Repository, AnalysisResult, Score, StarSnapshot, TelegramMessage
from database.db_manager import DatabaseManager
from collectors.github_collector import GitHubCollector
from collectors.hn_collector import HackerNewsCollector
from collectors.ph_collector import ProductHuntCollector
from collectors.multi_source import MultiSourceCollector, TrendingItem
from analyzers.readme_parser import ReadmeParser
from analyzers.llm_analyzer import LLMAnalyzer
from scorers.scorer import Scorer
from notifiers.telegram_notifier import TelegramNotifier
from notifiers.telegram_command_bot import TelegramCommandBot
from utils.logger import get_logger

logger = get_logger(__name__)


class GitHubRadar:
    def __init__(self, use_multi_source: bool = True):
        self.db = DatabaseManager(config.database.path)
        self.collector = GitHubCollector(config.github)
        self.readme_parser = ReadmeParser()
        self.llm_analyzer = LLMAnalyzer(config.llm)
        self.scorer = Scorer()
        self.notifier = TelegramNotifier(config.telegram)
        
        self.use_multi_source = use_multi_source
        if use_multi_source:
            ph_token = os.getenv('PRODUCTHUNT_API_TOKEN')
            self.multi_collector = MultiSourceCollector(
                github_config=config.github,
                ph_api_token=ph_token
            )
            self.hn_collector = HackerNewsCollector()
            self.ph_collector = ProductHuntCollector(api_token=ph_token)
        
        self.running = True
        self._setup_signal_handlers()
        
        # Initialize Telegram command bot
        self.command_bot = TelegramCommandBot(config.telegram, self.db)
        self.command_bot.start()

    def _setup_signal_handlers(self):
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal, stopping...")
            self.running = False
            if hasattr(self, 'command_bot'):
                self.command_bot.stop()
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
            'errors': 0,
            'sources': {
                'github': 0,
                'hackernews': 0,
                'producthunt': 0
            }
        }
        
        try:
            logger.info("Step 1: Collecting repositories...")
            if self.use_multi_source:
                stats['collected'], stats['new'], stats['sources'] = self._collect_from_all_sources()
            else:
                stats['collected'], stats['new'] = self._collect_repositories()
            
            logger.info("Step 2: Fetching READMEs...")
            self._fetch_readmes()
            
            logger.info("Step 3: Analyzing repositories...")
            stats['analyzed'] = self._analyze_repositories()
            
            logger.info("Step 4: Scoring repositories...")
            stats['scored'] = self._score_repositories()
            
            logger.info("Step 5: Notifying top projects...")
            stats['notified'] = self._notify_top_projects()
            
        except Exception as e:
            logger.error(f"Error during scan: {e}")
            import traceback
            logger.error(traceback.format_exc())
            stats['errors'] += 1
        
        logger.info(f"Scan completed: {stats}")
        return stats

    def run_forever(self):
        logger.info("Starting GitHub Radar in continuous mode")
        logger.info(f"Scan interval: {config.system.scan_interval_minutes} minutes")
        logger.info(f"Multi-source mode: {self.use_multi_source}")
        
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
        
        if self.use_multi_source:
            try:
                hn_stories = self.hn_collector.get_top_stories(limit=1)
                if hn_stories:
                    logger.info("Hacker News API: OK")
            except Exception as e:
                logger.warning(f"Hacker News API: FAILED ({e})")
        
        logger.info("Connection tests completed")

    def _collect_from_all_sources(self) -> Tuple[int, int, dict]:
        logger.info("Collecting from all sources...")
        
        total_collected = 0
        new_count = 0
        source_stats = {'github': 0, 'hackernews': 0, 'producthunt': 0}
        
        result = self.collector.search_trending_repositories(
            days=7,
            min_stars=50,
            max_results=config.github.max_results
        )
        
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
        
        source_stats['github'] = len(result.repositories)
        total_collected += len(result.repositories)
        
        external_githubs = self.multi_collector.get_github_repos_from_external()
        
        for repo_name, item in external_githubs.items():
            try:
                repo = self.multi_collector.enrich_with_github_details(repo_name, item)
                if repo:
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
                    
                    source_stats[item.source] += 1
                    total_collected += 1
            except Exception as e:
                logger.warning(f"Failed to process external repo {repo_name}: {e}")
        
        logger.info(f"Collected {total_collected} repos ({new_count} new) from all sources")
        logger.info(f"Source breakdown: GitHub={source_stats['github']}, "
                   f"HN={source_stats['hackernews']}, PH={source_stats['producthunt']}")
        
        return total_collected, new_count, source_stats

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
        
        # 1. 首先尝试推送高分项目
        top_projects = self.db.get_top_scored_repositories(
            min_score=config.scoring.min_score_to_notify,
            limit=config.scoring.max_results_per_day
        )
        
        if top_projects:
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
            
            logger.info(f"Notified {notified_count} high-score projects")
            return notified_count
        
        # 2. 没有高分项目，尝试推送增长速度快的项目（排除已通知的）
        logger.info("No high-score projects, checking for fast-growing projects...")
        fast_growing_projects = self.db.get_fastest_growing_repositories(days=7, limit=5)
        
        # 过滤掉已经通知过的项目
        notified_repo_ids = self.db.get_notified_repo_ids()
        unnotified_fast_growing = [
            (repo, growth, growth_rate) 
            for repo, growth, growth_rate in fast_growing_projects 
            if repo.id not in notified_repo_ids
        ]
        
        if unnotified_fast_growing:
            logger.info(f"Found {len(unnotified_fast_growing)} unnotified fast growing projects")
            msg_ids = self.notifier.notify_fast_growing_projects(unnotified_fast_growing)
            
            # 记录通知
            for repo, growth, growth_rate in unnotified_fast_growing:
                for msg_id in msg_ids:
                    if msg_id:
                        telegram_msg = TelegramMessage(
                            repo_id=repo.id,
                            message_id=msg_id,
                            status='sent'
                        )
                        self.db.insert_telegram_message(telegram_msg)
            
            logger.info(f"Notified {len(msg_ids)} fast growing projects")
            return len(msg_ids)
        
        # 3. 都没有，发送无新项目通知（确保一定会发送）
        logger.info("No new projects to notify, sending status message...")
        msg_id = self.notifier.notify_no_new_projects()
        if msg_id:
            logger.info("Sent 'no new projects' notification")
            return 1
        else:
            logger.error("Failed to send 'no new projects' notification!")
            return 0


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='GitHub Radar - Trending Project Analyzer')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--test', action='store_true', help='Test connections and exit')
    parser.add_argument('--single-source', action='store_true', help='Only use GitHub as source')
    args = parser.parse_args()
    
    use_multi_source = not args.single_source
    radar = GitHubRadar(use_multi_source=use_multi_source)
    
    if args.test:
        radar._test_connections()
        return
    
    if args.once:
        radar.run_once()
    else:
        radar.run_forever()


if __name__ == '__main__':
    main()
