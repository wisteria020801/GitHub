"""
获取 Product Hunt Access Token

Product Hunt 使用 OAuth 2.0，需要通过 API Key 和 Secret 获取 Access Token
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def get_producthunt_token():
    api_key = os.getenv('PRODUCTHUNT_API_KEY')
    api_secret = os.getenv('PRODUCTHUNT_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ 错误：请在 .env 文件中配置 PRODUCTHUNT_API_KEY 和 PRODUCTHUNT_API_SECRET")
        return None
    
    print("=" * 60)
    print("获取 Product Hunt Access Token")
    print("=" * 60)
    print(f"API Key: {api_key[:20]}...")
    print(f"API Secret: {api_secret[:20]}...")
    
    url = "https://api.producthunt.com/v2/oauth/token"
    
    data = {
        "client_id": api_key,
        "client_secret": api_secret,
        "grant_type": "client_credentials"
    }
    
    try:
        print("\n正在请求 Access Token...")
        response = requests.post(url, data=data)
        response.raise_for_status()
        
        result = response.json()
        access_token = result.get('access_token')
        
        if access_token:
            print("✅ 成功获取 Access Token！")
            print(f"\nAccess Token: {access_token[:40]}...")
            print(f"\n请将以下内容添加到 .env 文件：")
            print(f"PRODUCTHUNT_API_TOKEN={access_token}")
            
            return access_token
        else:
            print("❌ 响应中没有找到 access_token")
            print(f"响应内容: {result}")
            return None
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP 错误: {e}")
        print(f"响应内容: {response.text}")
        return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None

if __name__ == '__main__':
    token = get_producthunt_token()
    
    if token:
        print("\n" + "=" * 60)
        print("下一步：")
        print("1. 复制上面的 PRODUCTHUNT_API_TOKEN 行")
        print("2. 粘贴到 .env 文件中")
        print("3. 运行 python test_producthunt.py 测试")
        print("=" * 60)
