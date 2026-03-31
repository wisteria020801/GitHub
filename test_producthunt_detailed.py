"""
测试 Product Hunt 数据源 - 调整参数
"""
import sys
import os
from dotenv import load_dotenv

load_dotenv()

from collectors.ph_collector import ProductHuntCollector
from utils.logger import get_logger

logger = get_logger(__name__)

def test_producthunt_detailed():
    print("=" * 60)
    print("详细测试 Product Hunt 数据源")
    print("=" * 60)
    
    api_token = os.getenv('PRODUCTHUNT_API_TOKEN')
    if not api_token:
        print("❌ 错误：请在 .env 文件中配置 PRODUCTHUNT_API_TOKEN")
        return
    
    print(f"API Token: {api_token[:20]}...")
    
    collector = ProductHuntCollector(api_token=api_token)
    
    print("\n1. 测试获取今天的产品（无投票限制）...")
    try:
        posts = collector.get_trending_posts(min_votes=0, limit=10)
        print(f"✅ 成功获取 {len(posts)} 个产品")
        
        if posts:
            for i, post in enumerate(posts[:5], 1):
                print(f"\n   产品 {i}:")
                print(f"   - 名称: {post.name}")
                print(f"   - 标语: {post.tagline}")
                print(f"   - 投票数: {post.votes_count}")
                print(f"   - URL: {post.url}")
        else:
            print("   ℹ️  今天还没有产品发布")
    except Exception as e:
        print(f"❌ 获取失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n2. 测试获取开发者工具...")
    try:
        posts = collector.get_developer_tools(limit=10)
        print(f"✅ 成功获取 {len(posts)} 个开发者工具")
        
        if posts:
            for i, post in enumerate(posts[:3], 1):
                print(f"\n   产品 {i}:")
                print(f"   - 名称: {post.name}")
                print(f"   - 投票数: {post.votes_count}")
                if post.url and 'github.com' in post.url.lower():
                    print(f"   - 🎯 包含 GitHub 链接: {post.url}")
        else:
            print("   ℹ️  没有找到开发者工具")
    except Exception as e:
        print(f"❌ 获取失败: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == '__main__':
    try:
        test_producthunt_detailed()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
