"""
测试 MVP 生成器
"""
import sys
import os
from dotenv import load_dotenv

load_dotenv()

from generators.mvp_generator import MVPGenerator, generate_mvp_from_repo


def test_generator_basic():
    print("\n" + "=" * 60)
    print("测试1: 基础生成功能")
    print("=" * 60)
    
    generator = MVPGenerator()
    
    analysis = {
        "summary": "一个智能代码分析工具，帮助开发者快速理解代码库结构",
        "business_potential": "可作为SaaS服务出售给企业开发团队",
        "differentiation": "专注于中文代码注释分析和本地化支持",
        "monetization": "订阅制 + 企业版授权"
    }
    
    try:
        project = generator.generate(
            project_name="Code Analyzer Pro",
            project_type="api",
            analysis_result=analysis
        )
        
        print(f"✅ 项目生成成功!")
        print(f"   名称: {project.name}")
        print(f"   Slug: {project.slug}")
        print(f"   类型: {project.project_type}")
        print(f"   文件数: {len(project.files)}")
        print(f"   输出路径: {project.output_path}")
        
        generator.save_project_meta(project)
        
        print("\n   生成的文件:")
        for f in project.files[:5]:
            print(f"   - {f['path']}")
        if len(project.files) > 5:
            print(f"   ... 共 {len(project.files)} 个文件")
        
        return True
        
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_generator_cli():
    print("\n" + "=" * 60)
    print("测试2: CLI 工具生成")
    print("=" * 60)
    
    generator = MVPGenerator()
    
    analysis = {
        "summary": "一个命令行工具，用于自动化代码格式化和检查",
        "business_potential": "开源 + 付费高级功能",
        "differentiation": "支持自定义规则和团队配置共享",
        "monetization": "开源免费，企业版收费"
    }
    
    try:
        project = generator.generate(
            project_name="Code Formatter CLI",
            project_type="cli",
            analysis_result=analysis
        )
        
        print(f"✅ CLI 项目生成成功!")
        print(f"   名称: {project.name}")
        print(f"   输出路径: {project.output_path}")
        
        generator.save_project_meta(project)
        
        return True
        
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        return False


def test_list_projects():
    print("\n" + "=" * 60)
    print("测试3: 列出已生成项目")
    print("=" * 60)
    
    generator = MVPGenerator()
    
    try:
        projects = generator.list_generated_projects()
        
        print(f"✅ 找到 {len(projects)} 个已生成项目")
        
        for p in projects:
            print(f"   - {p['name']} ({p.get('project_type', 'unknown')})")
        
        return True
        
    except Exception as e:
        print(f"❌ 列出失败: {e}")
        return False


def test_generate_from_db():
    print("\n" + "=" * 60)
    print("测试4: 从数据库仓库生成")
    print("=" * 60)
    
    try:
        project = generate_mvp_from_repo(repo_id=1, project_type="api")
        
        if project:
            print(f"✅ 从数据库生成成功!")
            print(f"   名称: {project.name}")
            print(f"   输出路径: {project.output_path}")
            return True
        else:
            print("⚠️  数据库中没有 ID=1 的仓库，跳过此测试")
            return True
            
    except Exception as e:
        print(f"❌ 从数据库生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    print("\n" + "=" * 60)
    print("MVP 生成器测试套件")
    print("=" * 60)
    
    results = []
    
    results.append(("基础生成功能", test_generator_basic()))
    results.append(("CLI 工具生成", test_generator_cli()))
    results.append(("列出已生成项目", test_list_projects()))
    results.append(("从数据库生成", test_generate_from_db()))
    
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
