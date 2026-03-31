import csv
import io
import json
from datetime import datetime
from flask import Flask, abort, render_template, request, url_for, redirect, flash, jsonify, Response

from .db import (
    get_repository_detail, get_stats, get_available_sources, list_repositories,
    get_category_stats, get_repos_by_category, compare_repositories, get_available_categories,
    categorize_by_topics, get_all_repos,
    add_favorite, remove_favorite, is_favorite, get_favorite_repos, get_favorites_count, update_favorite_note
)
from .utils import human_datetime, parse_json_safe, safe_float, truncate_text

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)

app.jinja_env.filters["humandate"] = human_datetime
app.jinja_env.filters["truncate_text"] = truncate_text
app.jinja_env.filters["categorize"] = categorize_by_topics


@app.route("/")
def index():
    q = request.args.get("q", "").strip() or None
    source = request.args.get("source", "").strip() or None
    sort_by = request.args.get("sort", "score").strip() or "score"
    order = request.args.get("order", "desc").strip() or "desc"
    page = int(request.args.get("page", 1))
    page_size = min(max(int(request.args.get("page_size", 20)), 5), 100)

    items, total = list_repositories(
        query=q,
        source=source,
        sort_by=sort_by,
        order=order,
        page=page,
        page_size=page_size,
    )

    total_pages = max((total + page_size - 1) // page_size, 1)
    sources = get_available_sources()

    return render_template(
        "index.html",
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        q=q or "",
        source=source or "",
        sort_by=sort_by,
        order=order,
        sources=sources,
    )


@app.route("/repo/<int:repo_id>")
def detail(repo_id: int):
    repo = get_repository_detail(repo_id)
    if not repo:
        abort(404)
    return render_template("detail.html", repo=repo)


@app.route("/stats")
def stats():
    return render_template("stats.html", stats=get_stats())


@app.route("/api/charts/score_distribution")
def api_score_distribution():
    repos = get_all_repos(limit=1000)
    
    score_ranges = {
        "0-20": 0,
        "20-40": 0,
        "40-60": 0,
        "60-80": 0,
        "80-100": 0
    }
    
    for repo in repos:
        score = repo.get("total_score", 0) or 0
        if score < 20:
            score_ranges["0-20"] += 1
        elif score < 40:
            score_ranges["20-40"] += 1
        elif score < 60:
            score_ranges["40-60"] += 1
        elif score < 80:
            score_ranges["60-80"] += 1
        else:
            score_ranges["80-100"] += 1
    
    return jsonify({
        "labels": list(score_ranges.keys()),
        "data": list(score_ranges.values())
    })


@app.route("/api/charts/source_distribution")
def api_source_distribution():
    stats_data = get_stats()
    sources = stats_data.get("sources", [])
    
    labels = [s["source"] for s in sources]
    data = [s["cnt"] for s in sources]
    
    return jsonify({
        "labels": labels,
        "data": data
    })


@app.route("/api/charts/category_distribution")
def api_category_distribution():
    stats_data = get_stats()
    categories = stats_data.get("categories", [])
    
    top_categories = sorted(categories, key=lambda x: x["count"], reverse=True)[:10]
    
    labels = [c["category"] for c in top_categories]
    data = [c["count"] for c in top_categories]
    
    return jsonify({
        "labels": labels,
        "data": data
    })


@app.route("/api/charts/language_distribution")
def api_language_distribution():
    repos = get_all_repos(limit=1000)
    
    languages = {}
    for repo in repos:
        lang = repo.get("language") or "Unknown"
        languages[lang] = languages.get(lang, 0) + 1
    
    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return jsonify({
        "labels": [l[0] for l in sorted_langs],
        "data": [l[1] for l in sorted_langs]
    })


@app.route("/api/charts/stars_distribution")
def api_stars_distribution():
    repos = get_all_repos(limit=1000)
    
    star_ranges = {
        "0-100": 0,
        "100-500": 0,
        "500-1k": 0,
        "1k-5k": 0,
        "5k-10k": 0,
        "10k+": 0
    }
    
    for repo in repos:
        stars = repo.get("stars", 0) or 0
        if stars < 100:
            star_ranges["0-100"] += 1
        elif stars < 500:
            star_ranges["100-500"] += 1
        elif stars < 1000:
            star_ranges["500-1k"] += 1
        elif stars < 5000:
            star_ranges["1k-5k"] += 1
        elif stars < 10000:
            star_ranges["5k-10k"] += 1
        else:
            star_ranges["10k+"] += 1
    
    return jsonify({
        "labels": list(star_ranges.keys()),
        "data": list(star_ranges.values())
    })


@app.route("/api/favorites", methods=["GET"])
def api_list_favorites():
    page = request.args.get("page", 1, type=int)
    limit = 20
    offset = (page - 1) * limit
    
    repos = get_favorite_repos(limit=limit, offset=offset)
    total = get_favorites_count()
    
    return jsonify({
        "repos": repos,
        "total": total,
        "page": page,
        "has_more": offset + limit < total
    })


@app.route("/api/favorites/<int:repo_id>", methods=["POST"])
def api_add_favorite(repo_id: int):
    note = request.json.get("note", "") if request.json else ""
    success = add_favorite(repo_id, note)
    
    if success:
        return jsonify({"success": True, "message": "已添加到收藏"})
    else:
        return jsonify({"success": False, "message": "添加失败"}), 400


@app.route("/api/favorites/<int:repo_id>", methods=["DELETE"])
def api_remove_favorite(repo_id: int):
    success = remove_favorite(repo_id)
    
    if success:
        return jsonify({"success": True, "message": "已取消收藏"})
    else:
        return jsonify({"success": False, "message": "取消失败"}), 400


@app.route("/api/favorites/<int:repo_id>", methods=["GET"])
def api_check_favorite(repo_id: int):
    favorite = is_favorite(repo_id)
    return jsonify({"is_favorite": favorite})


@app.route("/api/favorites/<int:repo_id>/note", methods=["PUT"])
def api_update_favorite_note(repo_id: int):
    note = request.json.get("note", "") if request.json else ""
    success = update_favorite_note(repo_id, note)
    
    if success:
        return jsonify({"success": True, "message": "备注已更新"})
    else:
        return jsonify({"success": False, "message": "更新失败"}), 400


@app.route("/favorites")
def favorites_view():
    repos = get_favorite_repos(limit=50)
    total = get_favorites_count()
    
    return render_template(
        "favorites.html",
        repos=repos,
        total=total
    )


@app.route("/export/csv")
def export_csv():
    query = request.args.get("q", "")
    source = request.args.get("source", "")
    sort_by = request.args.get("sort", "score")
    
    repos, _ = list_repositories(
        query=query,
        source=source if source else None,
        sort_by=sort_by,
        order="desc",
        page=1,
        page_size=1000
    )
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "项目名称", "完整名称", "描述", "语言", "Stars", "Forks",
        "Issues", "总分", "热度", "增长", "可复制性", "变现", "差异化",
        "来源", "GitHub链接", "创建时间", "更新时间"
    ])
    
    for repo in repos:
        writer.writerow([
            repo.get("name", ""),
            repo.get("full_name", ""),
            repo.get("description", ""),
            repo.get("language", ""),
            repo.get("stars", 0),
            repo.get("forks", 0),
            repo.get("open_issues", 0),
            round(repo.get("total_score", 0) or 0, 2),
            round(repo.get("score_popularity", 0) or 0, 2),
            round(repo.get("score_growth", 0) or 0, 2),
            round(repo.get("score_copyability", 0) or 0, 2),
            round(repo.get("score_monetization", 0) or 0, 2),
            round(repo.get("score_differentiation", 0) or 0, 2),
            repo.get("source", ""),
            repo.get("html_url", ""),
            repo.get("created_at", ""),
            repo.get("pushed_at", "")
        ])
    
    output.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=github_radar_{timestamp}.csv"
        }
    )


@app.route("/export/json")
def export_json():
    query = request.args.get("q", "")
    source = request.args.get("source", "")
    sort_by = request.args.get("sort", "score")
    
    repos, total = list_repositories(
        query=query,
        source=source if source else None,
        sort_by=sort_by,
        order="desc",
        page=1,
        page_size=1000
    )
    
    export_data = {
        "exported_at": datetime.now().isoformat(),
        "total": total,
        "filters": {
            "query": query,
            "source": source,
            "sort_by": sort_by
        },
        "repositories": []
    }
    
    for repo in repos:
        export_data["repositories"].append({
            "name": repo.get("name"),
            "full_name": repo.get("full_name"),
            "description": repo.get("description"),
            "language": repo.get("language"),
            "stars": repo.get("stars"),
            "forks": repo.get("forks"),
            "open_issues": repo.get("open_issues"),
            "html_url": repo.get("html_url"),
            "source": repo.get("source"),
            "topics": repo.get("topics_list", []),
            "scores": {
                "total": round(repo.get("total_score", 0) or 0, 2),
                "popularity": round(repo.get("score_popularity", 0) or 0, 2),
                "growth": round(repo.get("score_growth", 0) or 0, 2),
                "copyability": round(repo.get("score_copyability", 0) or 0, 2),
                "monetization": round(repo.get("score_monetization", 0) or 0, 2),
                "differentiation": round(repo.get("score_differentiation", 0) or 0, 2)
            },
            "analysis": {
                "problem_solved": repo.get("problem_solved"),
                "target_audience": repo.get("target_audience"),
                "growth_reason": repo.get("growth_reason"),
                "monetization_potential": repo.get("monetization_potential"),
                "differentiation_ideas": repo.get("differentiation_ideas_list", [])
            },
            "dates": {
                "created_at": repo.get("created_at"),
                "pushed_at": repo.get("pushed_at"),
                "first_seen_at": repo.get("first_seen_at")
            }
        })
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    return Response(
        jsonify(export_data).get_data(as_text=True),
        mimetype="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=github_radar_{timestamp}.json"
        }
    )


@app.route("/export/favorites/csv")
def export_favorites_csv():
    repos = get_favorite_repos(limit=1000)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "项目名称", "完整名称", "描述", "语言", "Stars", "Forks",
        "总分", "来源", "GitHub链接", "收藏时间", "备注"
    ])
    
    for repo in repos:
        writer.writerow([
            repo.get("name", ""),
            repo.get("full_name", ""),
            repo.get("description", ""),
            repo.get("language", ""),
            repo.get("stars", 0),
            repo.get("forks", 0),
            round(repo.get("total_score", 0) or 0, 2),
            repo.get("source", ""),
            repo.get("html_url", ""),
            repo.get("favorited_at", ""),
            repo.get("favorite_note", "")
        ])
    
    output.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=favorites_{timestamp}.csv"
        }
    )


@app.route("/export/favorites/json")
def export_favorites_json():
    repos = get_favorite_repos(limit=1000)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    return Response(
        json.dumps(repos, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=favorites_{timestamp}.json"
        }
    )


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/category/<path:category>")
def category_view(category: str):
    repos = get_repos_by_category(category, limit=20)
    categories = get_available_categories()
    
    return render_template(
        "category.html",
        category=category,
        repos=repos,
        categories=categories
    )


@app.route("/compare")
def compare_view():
    repo_ids_str = request.args.get("repos", "")
    repo_ids = []
    
    if repo_ids_str:
        try:
            repo_ids = [int(x.strip()) for x in repo_ids_str.split(",") if x.strip()]
        except ValueError:
            pass
    
    comparison = compare_repositories(repo_ids) if repo_ids else {"repos": [], "metrics": {}}
    
    return render_template(
        "compare.html",
        comparison=comparison,
        selected_ids=repo_ids_str
    )


@app.route("/compare/add/<int:repo_id>")
def compare_add(repo_id: int):
    repo_ids_str = request.args.get("repos", "")
    repo_ids = []
    
    if repo_ids_str:
        try:
            repo_ids = [int(x.strip()) for x in repo_ids_str.split(",") if x.strip()]
        except ValueError:
            pass
    
    if repo_id not in repo_ids:
        repo_ids.append(repo_id)
    
    return redirect(url_for("compare_view", repos=",".join(map(str, repo_ids))))


@app.route("/compare/remove/<int:repo_id>")
def compare_remove(repo_id: int):
    repo_ids_str = request.args.get("repos", "")
    repo_ids = []
    
    if repo_ids_str:
        try:
            repo_ids = [int(x.strip()) for x in repo_ids_str.split(",") if x.strip()]
        except ValueError:
            pass
    
    if repo_id in repo_ids:
        repo_ids.remove(repo_id)
    
    if repo_ids:
        return redirect(url_for("compare_view", repos=",".join(map(str, repo_ids))))
    return redirect(url_for("index"))


@app.route("/generate_multi/<int:repo_id>", methods=["GET", "POST"])
def generate_multi_versions(repo_id: int):
    repo = get_repository_detail(repo_id)
    if not repo:
        abort(404)
    
    from generators.differentiated_generator import DIFFERENTIATION_TEMPLATES
    
    if request.method == "POST":
        selected_versions = request.form.getlist("versions")
        
        if not selected_versions:
            return render_template(
                "generate_multi.html",
                repo=repo,
                version_templates=DIFFERENTIATION_TEMPLATES,
                error="请至少选择一个版本类型"
            )
        
        from generators.differentiated_generator import generate_differentiated_mvps
        
        try:
            result = generate_differentiated_mvps(
                repo_id=repo_id,
                selected_versions=selected_versions
            )
            
            if result:
                return render_template(
                    "generate_multi_result.html",
                    result=result,
                    repo=repo
                )
            else:
                return render_template(
                    "generate_multi.html",
                    repo=repo,
                    version_templates=DIFFERENTIATION_TEMPLATES,
                    error="生成失败，请检查项目分析结果"
                )
        except Exception as e:
            return render_template(
                "generate_multi.html",
                repo=repo,
                version_templates=DIFFERENTIATION_TEMPLATES,
                error=str(e)
            )
    
    return render_template(
        "generate_multi.html",
        repo=repo,
        version_templates=DIFFERENTIATION_TEMPLATES
    )


@app.route("/api/categories")
def api_categories():
    return jsonify(get_category_stats())


@app.route("/generate/<int:repo_id>", methods=["GET", "POST"])
def generate_mvp(repo_id: int):
    repo = get_repository_detail(repo_id)
    if not repo:
        abort(404)
    
    if request.method == "POST":
        project_type = request.form.get("project_type", "api")
        project_name = request.form.get("project_name", repo.get("name", "new-project"))
        
        from generators.mvp_generator import MVPGenerator
        
        generator = MVPGenerator()
        
        analysis = repo.get("analysis") or {}
        
        try:
            project = generator.generate(
                project_name=project_name,
                project_type=project_type,
                analysis_result={
                    "summary": repo.get("description", ""),
                    "business_potential": analysis.get("target_audience", ""),
                    "differentiation": "\n".join(analysis.get("differentiation_ideas", [])),
                    "monetization": analysis.get("monetization_potential", ""),
                }
            )
            
            generator.save_project_meta(project)
            
            return render_template(
                "generate_result.html",
                project=project,
                repo=repo
            )
        except Exception as e:
            return render_template(
                "generate.html",
                repo=repo,
                error=str(e)
            )
    
    return render_template("generate.html", repo=repo)


@app.route("/generated")
def list_generated():
    from generators.mvp_generator import MVPGenerator
    
    generator = MVPGenerator()
    projects = generator.list_generated_projects()
    
    return render_template("generated_list.html", projects=projects)


@app.route("/generated/<slug>")
def generated_detail(slug: str):
    from pathlib import Path
    
    project_dir = Path(__file__).parent.parent / "generated_mvps" / slug
    
    if not project_dir.exists():
        abort(404)
    
    meta_file = project_dir / ".meta.json"
    if meta_file.exists():
        import json
        with open(meta_file, "r", encoding="utf-8") as f:
            project = json.load(f)
    else:
        project = {"name": slug, "slug": slug}
    
    files = []
    for f in project_dir.rglob("*"):
        if f.is_file() and f.name != ".meta.json":
            rel_path = f.relative_to(project_dir)
            try:
                content = f.read_text(encoding="utf-8")
            except:
                content = "[Binary file]"
            
            files.append({
                "path": str(rel_path),
                "content": content,
                "size": f.stat().st_size
            })
    
    project["files"] = files
    project["output_path"] = str(project_dir)
    
    return render_template("generated_detail.html", project=project)


@app.route("/generate_enhanced/<int:repo_id>", methods=["GET", "POST"])
def generate_enhanced(repo_id: int):
    repo = get_repository_detail(repo_id)
    if not repo:
        abort(404)
    
    if request.method == "POST":
        project_type = request.form.get("project_type", "api")
        project_name = request.form.get("project_name", repo.get("name", "new-project"))
        use_llm = request.form.get("use_llm", "true").lower() == "true"
        
        from generators.enhanced_generator import EnhancedMVPGenerator
        
        generator = EnhancedMVPGenerator(use_llm=use_llm)
        
        try:
            if use_llm:
                result = generator.generate_with_llm(
                    project_name=project_name,
                    description=repo.get("description", ""),
                    stars=repo.get("stars", 0),
                    language=repo.get("language", "Python"),
                    topics=repo.get("topics", []),
                    readme_preview=repo.get("readme_content", "")[:2000],
                    project_type=project_type
                )
            else:
                result = generator.analyze_and_generate(
                    project_name=project_name,
                    description=repo.get("description", ""),
                    target_audience=repo.get("target_audience", "开发者"),
                    core_features=[],
                    tech_stack=repo.get("language", "Python"),
                    monetization_potential=repo.get("monetization_potential", ""),
                    differentiation_ideas=repo.get("differentiation_ideas_list", []),
                    problem_solved=repo.get("problem_solved", ""),
                    project_type=project_type
                )
            
            return render_template(
                "generate_enhanced_result.html",
                result=result,
                repo=repo,
                use_llm=use_llm
            )
        except Exception as e:
            return render_template(
                "generate_enhanced.html",
                repo=repo,
                error=str(e)
            )
    
    return render_template("generate_enhanced.html", repo=repo)


@app.route("/prompts/<slug>")
def view_prompts(slug: str):
    from pathlib import Path
    import json
    
    prompts_dir = Path(__file__).parent.parent / "generated_mvps" / slug / ".prompts"
    
    if not prompts_dir.exists():
        abort(404)
    
    prompts = {}
    for f in prompts_dir.glob("*.md"):
        if f.name != "README.md":
            with open(f, "r", encoding="utf-8") as file:
                prompts[f.stem] = file.read()
    
    llm_analysis = None
    llm_analysis_file = prompts_dir / "llm_analysis.json"
    if llm_analysis_file.exists():
        try:
            with open(llm_analysis_file, "r", encoding="utf-8") as f:
                llm_analysis = json.load(f)
        except:
            pass
    
    return render_template(
        "prompts_view.html",
        slug=slug,
        prompts=prompts,
        llm_analysis=llm_analysis
    )


@app.route("/api/deploy", methods=["POST"])
def api_deploy():
    from deployers import get_deployer
    
    deployer = get_deployer()
    if not deployer:
        return jsonify({
            "success": False,
            "message": "未配置GitHub Token，请设置TOKEN_GITHUB环境变量"
        }), 400
    
    data = request.json
    repo_name = data.get("repo_name", "")
    files = data.get("files", {})
    description = data.get("description", "")
    private = data.get("private", False)
    
    if not repo_name:
        return jsonify({
            "success": False,
            "message": "仓库名称不能为空"
        }), 400
    
    if not files:
        return jsonify({
            "success": False,
            "message": "没有要部署的文件"
        }), 400
    
    success, result = deployer.deploy(
        repo_name=repo_name,
        files=files,
        description=description,
        private=private
    )
    
    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@app.route("/api/deploy/check", methods=["GET"])
def api_deploy_check():
    from deployers import get_deployer
    
    deployer = get_deployer()
    
    return jsonify({
        "configured": deployer is not None,
        "username": deployer.username if deployer else None
    })


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)
