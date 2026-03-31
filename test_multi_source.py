"""
测试多数据源采集功能
"""
import sys
from config import config
from collectors.multi_source import MultiSourceCollector
from database.db_manager import DatabaseManager
from utils.logger import get_logger

logger = get_logger(__name__)

def test_multi_source():
    print("=" * 60)
    print("测试多数据源采集功能")
    print("=" * 60)
    
    db = DatabaseManager(config.database.path)
    
    ph_token = getattr(config, 'producthunt_api_token', None)
    collector = MultiSourceCollector(config.github, ph_token)
    
    print("\n1. 测试GitHub采集...")
    github_items = collector.collect_github_trending(limit=5)
    print(f"   ✅ GitHub采集: {len(github_items)}条")
    for item in github_items[:2]:
        print(f"      - {item.title} (score: {item.score})")
    
    print("\n2. 测试Hacker News采集...")
    hn_items = collector.collect_hn_trending(limit=5)
    print(f"   ✅ Hacker News采集: {len(hn_items)}条")
    for item in hn_items[:2]:
        print(f"      - {item.title} (score: {item.score}, source: {item.source})")
    
    print("\n3. 测试Product Hunt采集...")
    try:
        ph_items = collector.collect_ph_trending(limit=5)
        print(f"   ✅ Product Hunt采集: {len(ph_items)}条")
        for item in ph_items[:2]:
            print(f"      - {item.title} (score: {item.score}, source: {item.source})")
    except Exception as e:
        print(f"   ⚠️  Product Hunt采集失败: {e}")
    
    print("\n4. 测试外部GitHub仓库提取...")
    external_githubs = collector.get_github_repos_from_external()
    print(f"   ✅ 找到 {len(external_githubs)} 个外部GitHub仓库")
    for repo_name, item in list(external_githubs.items())[:3]:
        print(f"      - {repo_name} (from {item.source})")
    
    print("\n5. 测试完整采集流程...")
    all_items = collector.collect_all(limit_per_source=10)
    print(f"   ✅ 总共采集: {len(all_items)}条")
    
    source_counts = {}
    for item in all_items:
        source_counts[item.source] = source_counts.get(item.source, 0) + 1
    
    print("   来源分布:")
    for source, count in source_counts.items():
        print(f"      - {source}: {count}条")
    
    print("\n6. 测试数据库保存...")
    if external_githubs:
        repo_name, item = list(external_githubs.items())[0]
        print(f"   测试保存: {repo_name} (from {item.source})")
        
        repo = collector.enrich_with_github_details(repo_name, item)
        if repo:
            print(f"   ✅ 仓库详情获取成功")
            print(f"      - full_name: {repo.full_name}")
            print(f"      - stars: {repo.stars}")
            print(f"      - source: {repo.source}")
            
            repo_id = db.insert_repository(repo)
            if repo_id:
                print(f"   ✅ 数据库保存成功, ID: {repo_id}")
            else:
                print(f"   ℹ️  仓库已存在")
        else:
            print(f"   ❌ 仓库详情获取失败")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == '__main__':
    try:
        test_multi_source()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
