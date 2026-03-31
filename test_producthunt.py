"""
测试 Product Hunt 数据源
"""
import sys
import os
from dotenv import load_dotenv

load_dotenv()

from collectors.ph_collector import ProductHuntCollector
from utils.logger import get_logger

logger = get_logger(__name__)

def test_producthunt():
    print("=" * 60)
    print("测试 Product Hunt 数据源")
    print("=" * 60)
    
    api_token = os.getenv('PRODUCTHUNT_API_TOKEN')
    if not api_token:
        print("❌ 错误：请在 .env 文件中配置 PRODUCTHUNT_API_TOKEN")
        return
    
    print(f"API Token: {api_token[:20]}...")
    
    collector = ProductHuntCollector(api_token=api_token)
    
    print("\n1. 测试获取热门产品...")
    try:
        posts = collector.get_trending_posts(min_votes=50, limit=10)
        print(f"✅ 成功获取 {len(posts)} 个产品")
        
        for i, post in enumerate(posts[:5], 1):
            print(f"\n   产品 {i}:")
            print(f"   - 名称: {post.name}")
            print(f"   - 标语: {post.tagline}")
            print(f"   - 投票数: {post.votes_count}")
            print(f"   - 评论数: {post.comments_count}")
            print(f"   - URL: {post.url}")
            
            if post.url and 'github.com' in post.url.lower():
                print(f"   - 🎯 包含 GitHub 链接！")
    except Exception as e:
        print(f"❌ 获取失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n2. 测试数据转换...")
    try:
        from collectors.multi_source import MultiSourceCollector
        from config import config
        
        multi_collector = MultiSourceCollector(config.github, api_token)
        items = multi_collector.collect_ph_trending(limit=5)
        
        print(f"✅ 成功转换 {len(items)} 个产品为统一格式")
        
        for item in items[:3]:
            print(f"\n   - 标题: {item.title}")
            print(f"   - 分数: {item.score}")
            print(f"   - 来源: {item.source}")
            if item.github_repo:
                print(f"   - GitHub: {item.github_repo}")
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == '__main__':
    try:
        test_producthunt()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
