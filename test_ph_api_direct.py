"""
直接测试 Product Hunt GraphQL API
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_ph_api_directly():
    print("=" * 60)
    print("直接测试 Product Hunt GraphQL API")
    print("=" * 60)
    
    api_token = os.getenv('PRODUCTHUNT_API_TOKEN')
    if not api_token:
        print("❌ 错误：未找到 PRODUCTHUNT_API_TOKEN")
        return
    
    print(f"API Token: {api_token[:20]}...")
    
    headers = {
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json',
    }
    
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
                }
            }
        }
    }
    """
    
    url = "https://api.producthunt.com/v2/api/graphql"
    
    print("\n1. 测试获取产品列表...")
    try:
        response = requests.post(
            url,
            json={'query': query, 'variables': {'first': 10}},
            headers=headers
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            posts = data.get('data', {}).get('posts', {}).get('edges', [])
            
            print(f"✅ 成功获取 {len(posts)} 个产品")
            
            if posts:
                for i, edge in enumerate(posts[:5], 1):
                    node = edge.get('node', {})
                    print(f"\n   产品 {i}:")
                    print(f"   - 名称: {node.get('name')}")
                    print(f"   - 投票数: {node.get('votesCount')}")
                    print(f"   - 创建时间: {node.get('createdAt')}")
                    print(f"   - URL: {node.get('url')}")
            else:
                print("   ℹ️  当前没有产品")
                print(f"\n   完整响应: {data}")
        else:
            print(f"❌ 请求失败")
            print(f"响应: {response.text}")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == '__main__':
    test_ph_api_directly()
