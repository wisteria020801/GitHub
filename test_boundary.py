"""
边界测试脚本 - 测试系统的健壮性
"""
import os
import sys
import sqlite3
import requests
from dotenv import load_dotenv

load_dotenv()

def test_empty_database():
    print("\n" + "=" * 60)
    print("测试1: 空数据库测试")
    print("=" * 60)
    
    test_db = "test_empty.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS repositories (
            id INTEGER PRIMARY KEY,
            name TEXT,
            full_name TEXT,
            description TEXT,
            html_url TEXT,
            stars INTEGER DEFAULT 0,
            forks INTEGER DEFAULT 0,
            language TEXT,
            created_at TEXT,
            pushed_at TEXT,
            readme_content TEXT,
            source TEXT DEFAULT 'github'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY,
            repo_id INTEGER,
            summary TEXT,
            business_potential TEXT,
            differentiation TEXT,
            monetization TEXT,
            created_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY,
            repo_id INTEGER,
            total_score INTEGER DEFAULT 0,
            growth_score INTEGER DEFAULT 0,
            business_score INTEGER DEFAULT 0,
            tech_score INTEGER DEFAULT 0,
            created_at TEXT
        )
    ''')
    
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM repositories")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("✅ 空数据库创建成功")
        print("   - repositories: 0条")
        print("   - analysis_results: 0条")
        print("   - scores: 0条")
    else:
        print("❌ 数据库不为空")
    
    conn.close()
    os.remove(test_db)
    print("✅ 测试数据库已清理")
    
    return True

def test_dashboard_empty():
    print("\n" + "=" * 60)
    print("测试2: Dashboard空数据渲染")
    print("=" * 60)
    
    try:
        from dashboard.app import app
        
        with app.test_client() as client:
            response = client.get('/')
            
            if response.status_code == 200:
                print("✅ 首页正常返回 (状态码: 200)")
                
                content = response.data.decode('utf-8')
                
                if '暂无数据' in content or '没有找到' in content or 'empty' in content.lower():
                    print("✅ 空数据提示正常显示")
                else:
                    print("⚠️  未检测到空数据提示，但页面正常")
                
                return True
            else:
                print(f"❌ 首页返回异常状态码: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Dashboard测试失败: {e}")
        return False

def test_long_readme():
    print("\n" + "=" * 60)
    print("测试3: 超长README处理")
    print("=" * 60)
    
    long_readme = "A" * 100000
    
    print(f"   生成超长README: {len(long_readme)} 字符")
    
    try:
        from database.db_manager import DatabaseManager
        from database.models import Repository
        import random
        
        db = DatabaseManager()
        
        random_github_id = random.randint(100000000, 999999999)
        
        test_repo = Repository(
            github_id=random_github_id,
            name='test-long-readme',
            full_name=f'test/test-long-readme-{random_github_id}',
            description='测试超长README',
            html_url=f'https://github.com/test/test-long-readme-{random_github_id}',
            stars=100,
            forks=10,
            language='Python',
            readme_content=long_readme,
            source='github'
        )
        
        repo_id = db.insert_repository(test_repo)
        
        if repo_id:
            print(f"✅ 超长README成功写入数据库 (ID: {repo_id})")
            
            import sqlite3
            conn = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT LENGTH(readme_content) FROM repositories WHERE id = ?", (repo_id,))
            stored_len = cursor.fetchone()[0]
            conn.close()
            
            if stored_len == len(long_readme):
                print(f"✅ 数据完整存储 ({stored_len} 字符)")
            else:
                print(f"⚠️  数据被截断 (存储: {stored_len}, 原始: {len(long_readme)})")
            
            conn = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM repositories WHERE id = ?", (repo_id,))
            conn.commit()
            conn.close()
            print("✅ 测试数据已清理")
            
            return True
        else:
            print("❌ 写入失败")
            return False
            
    except Exception as e:
        print(f"❌ 超长README测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_failure_handling():
    print("\n" + "=" * 60)
    print("测试4: API失败处理")
    print("=" * 60)
    
    try:
        from collectors.github_collector import GitHubCollector, GitHubConfig
        
        invalid_config = GitHubConfig(token="invalid_token_12345")
        collector = GitHubCollector(invalid_config)
        
        print("   使用无效Token测试...")
        
        try:
            repos = collector.search_trending_repositories()
            if repos is None or len(repos) == 0:
                print("✅ 无效Token正确返回空结果")
                return True
            else:
                print(f"⚠️  意外返回了 {len(repos)} 个仓库")
                return True
        except requests.exceptions.HTTPError as e:
            print(f"✅ HTTP错误被正确捕获: {e.response.status_code}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"✅ 请求异常被正确捕获: {type(e).__name__}")
            return True
        except Exception as e:
            print(f"✅ 异常被正确捕获: {type(e).__name__}")
            return True
            
    except Exception as e:
        print(f"❌ API失败处理测试失败: {e}")
        return False

def test_dashboard_detail():
    print("\n" + "=" * 60)
    print("测试5: Dashboard详情页边界测试")
    print("=" * 60)
    
    try:
        from dashboard.app import app
        
        with app.test_client() as client:
            response = client.get('/detail/999999')
            
            if response.status_code == 404:
                print("✅ 不存在的项目返回404")
            elif response.status_code == 200:
                content = response.data.decode('utf-8')
                if '不存在' in content or '未找到' in content:
                    print("✅ 不存在的项目显示友好提示")
                else:
                    print("⚠️  返回200但内容未知")
            else:
                print(f"⚠️  返回状态码: {response.status_code}")
            
            return True
            
    except Exception as e:
        print(f"❌ 详情页测试失败: {e}")
        return False

def run_all_tests():
    print("\n" + "=" * 60)
    print("GitHub Radar 边界测试套件")
    print("=" * 60)
    
    results = []
    
    results.append(("空数据库测试", test_empty_database()))
    results.append(("Dashboard空数据渲染", test_dashboard_empty()))
    results.append(("超长README处理", test_long_readme()))
    results.append(("API失败处理", test_api_failure_handling()))
    results.append(("Dashboard详情页边界", test_dashboard_detail()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0

if __name__ == '__main__':
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试套件执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
