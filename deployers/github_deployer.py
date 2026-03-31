"""
GitHub一键部署模块

自动创建GitHub仓库并推送生成的代码
"""
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple
import requests


class GitHubDeployer:
    def __init__(self, token: str, username: str):
        self.token = token
        self.username = username
        self.api_base = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def create_repo(
        self, 
        repo_name: str, 
        description: str = "",
        private: bool = False
    ) -> Tuple[bool, Dict]:
        url = f"{self.api_base}/user/repos"
        
        payload = {
            "name": repo_name,
            "description": description,
            "private": private,
            "auto_init": False
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            
            if response.status_code == 201:
                data = response.json()
                return True, {
                    "success": True,
                    "repo_url": data.get("html_url"),
                    "clone_url": data.get("clone_url"),
                    "ssh_url": data.get("ssh_url"),
                    "message": f"仓库创建成功: {data.get('html_url')}"
                }
            elif response.status_code == 422:
                return False, {
                    "success": False,
                    "message": f"仓库已存在: {repo_name}"
                }
            else:
                return False, {
                    "success": False,
                    "message": f"创建失败: {response.text}"
                }
        except Exception as e:
            return False, {
                "success": False,
                "message": f"请求异常: {str(e)}"
            }
    
    def repo_exists(self, repo_name: str) -> bool:
        url = f"{self.api_base}/repos/{self.username}/{repo_name}"
        
        try:
            response = requests.get(url, headers=self.headers)
            return response.status_code == 200
        except:
            return False
    
    def push_code(
        self,
        repo_name: str,
        files: Dict[str, str],
        commit_message: str = "Initial commit from GitHub Radar"
    ) -> Tuple[bool, Dict]:
        temp_dir = tempfile.mkdtemp()
        
        try:
            repo_url = f"https://{self.token}@github.com/{self.username}/{repo_name}.git"
            
            repo_path = os.path.join(temp_dir, repo_name)
            os.makedirs(repo_path, exist_ok=True)
            
            for file_path, content in files.items():
                full_path = os.path.join(repo_path, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
            
            commands = [
                ["git", "init"],
                ["git", "config", "user.email", "github-radar@bot.com"],
                ["git", "config", "user.name", "GitHub Radar Bot"],
                ["git", "add", "."],
                ["git", "commit", "-m", commit_message],
                ["git", "branch", "-M", "main"],
                ["git", "remote", "add", "origin", repo_url],
                ["git", "push", "-u", "origin", "main"]
            ]
            
            for cmd in commands:
                result = subprocess.run(
                    cmd,
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0 and "push" not in cmd[0]:
                    if "nothing to commit" not in result.stdout:
                        pass
            
            return True, {
                "success": True,
                "repo_url": f"https://github.com/{self.username}/{repo_name}",
                "message": f"代码推送成功: https://github.com/{self.username}/{repo_name}"
            }
            
        except Exception as e:
            return False, {
                "success": False,
                "message": f"推送失败: {str(e)}"
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def deploy(
        self,
        repo_name: str,
        files: Dict[str, str],
        description: str = "",
        private: bool = False
    ) -> Tuple[bool, Dict]:
        if self.repo_exists(repo_name):
            exists_msg = f"仓库 {repo_name} 已存在，将直接推送代码"
        else:
            success, result = self.create_repo(repo_name, description, private)
            if not success:
                if "已存在" not in result.get("message", ""):
                    return False, result
                exists_msg = f"仓库 {repo_name} 已存在"
        
        success, result = self.push_code(repo_name, files)
        
        if success:
            result["repo_name"] = repo_name
            if exists_msg:
                result["note"] = exists_msg
        
        return success, result


def get_deployer() -> Optional[GitHubDeployer]:
    token = os.environ.get("TOKEN_GITHUB")
    username = os.environ.get("GITHUB_USERNAME", "")
    
    if not token:
        return None
    
    return GitHubDeployer(token, username)
