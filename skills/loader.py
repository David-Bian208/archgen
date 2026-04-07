"""
技能加载器 (Skill Loader)

混合技能架构：
- 通用技能包 (generic/) - 所有项目共享
- 领域技能包 (domains/) - 按项目加载

使用方式：
    python3 loader.py load behavior-recorder
    python3 loader.py list
    python3 loader.py status
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import json


class SkillLoader:
    """技能加载器"""
    
    def __init__(self, skills_dir: Path = None):
        """
        初始化加载器
        
        Args:
            skills_dir: Skills 目录路径
        """
        if skills_dir is None:
            skills_dir = Path(__file__).parent
        
        self.skills_dir = skills_dir
        self.generic_dir = skills_dir / "generic"
        self.domains_dir = skills_dir / "domains"
        self.loaded_skills: List[str] = []
        self.skill_registry: Dict[str, Any] = {}
    
    def load_for_project(self, project_name: str) -> List[str]:
        """
        为项目加载技能
        
        Args:
            project_name: 项目名称（如 behavior-recorder）
            
        Returns:
            已加载的技能列表
        """
        print(f"\n🛠️  为项目 '{project_name}' 加载技能...\n")
        
        # 1. 始终加载通用技能
        print("📦 加载通用技能：")
        generic_skills = self._load_generic_skills()
        
        # 2. 加载领域技能
        print("\n🎯 加载领域技能：")
        domain_skills = self._load_domain_skills(project_name)
        
        # 3. 汇总
        all_skills = generic_skills + domain_skills
        self.loaded_skills = all_skills
        
        print(f"\n✅ 已加载 {len(all_skills)} 个技能")
        print(f"   - 通用技能：{len(generic_skills)} 个")
        print(f"   - 领域技能：{len(domain_skills)} 个")
        
        return all_skills
    
    def _load_generic_skills(self) -> List[str]:
        """加载通用技能"""
        loaded = []
        
        if not self.generic_dir.exists():
            print("  ⚠️  通用技能目录不存在")
            return loaded
        
        for skill_dir in sorted(self.generic_dir.iterdir()):
            if skill_dir.is_dir() and not skill_dir.name.startswith('_'):
                skill_name = f"generic/{skill_dir.name}"
                if self._load_skill(skill_dir, skill_name):
                    loaded.append(skill_name)
        
        return loaded
    
    def _load_domain_skills(self, project_name: str) -> List[str]:
        """加载领域技能"""
        loaded = []
        domain_path = self.domains_dir / project_name
        
        if not domain_path.exists():
            print(f"  ℹ️  领域技能目录不存在：{domain_path}")
            print(f"  💡 提示：使用项目模板创建新领域技能包")
            return loaded
        
        for skill_dir in sorted(domain_path.iterdir()):
            if skill_dir.is_dir() and not skill_dir.name.startswith('_'):
                skill_name = f"domains/{project_name}/{skill_dir.name}"
                if self._load_skill(skill_dir, skill_name):
                    loaded.append(skill_name)
        
        return loaded
    
    def _load_skill(self, skill_dir: Path, skill_name: str) -> bool:
        """
        加载单个技能
        
        Args:
            skill_dir: 技能目录
            skill_name: 技能名称
            
        Returns:
            是否加载成功
        """
        skill_md = skill_dir / "SKILL.md"
        executor_py = skill_dir / "executor.py"
        
        # 检查 SKILL.md
        if not skill_md.exists():
            print(f"  ⚠️  跳过 {skill_name}：缺少 SKILL.md")
            return False
        
        # 读取技能信息
        skill_info = self._parse_skill_md(skill_md)
        
        # 注册技能
        self.skill_registry[skill_name] = {
            "path": str(skill_dir),
            "skill_md": str(skill_md),
            "executor": str(executor_py) if executor_py.exists() else None,
            "info": skill_info,
        }
        
        print(f"  ✅ {skill_name}")
        return True
    
    def _parse_skill_md(self, skill_md_path: Path) -> Dict[str, Any]:
        """
        解析 SKILL.md 文件
        
        Args:
            skill_md_path: SKILL.md 路径
            
        Returns:
            技能信息字典
        """
        content = skill_md_path.read_text(encoding='utf-8')
        
        info = {
            "name": "",
            "description": "",
            "wake_words": [],
        }
        
        # 简单解析 Markdown
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('# ') and not info["name"]:
                info["name"] = line[2:].strip()
            elif line.startswith('**用途：**'):
                info["description"] = line.replace('**用途：**', '').strip()
            elif '唤醒词' in line and '(' in line:
                # 解析唤醒词数量
                try:
                    count_str = line.split('(')[1].split(')')[0]
                    if count_str.isdigit():
                        info["wake_word_count"] = int(count_str)
                except:
                    pass
        
        return info
    
    def list_available_skills(self) -> Dict[str, List[str]]:
        """
        列出所有可用技能
        
        Returns:
            技能分类列表
        """
        available = {
            "generic": [],
            "domains": [],
        }
        
        # 通用技能
        if self.generic_dir.exists():
            for skill_dir in self.generic_dir.iterdir():
                if skill_dir.is_dir() and not skill_dir.name.startswith('_'):
                    available["generic"].append(f"generic/{skill_dir.name}")
        
        # 领域技能
        if self.domains_dir.exists():
            for domain_dir in self.domains_dir.iterdir():
                if domain_dir.is_dir() and not domain_dir.name.startswith('_'):
                    for skill_dir in domain_dir.iterdir():
                        if skill_dir.is_dir() and not skill_dir.name.startswith('_'):
                            available["domains"].append(
                                f"domains/{domain_dir.name}/{skill_dir.name}"
                            )
        
        return available
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取加载器状态
        
        Returns:
            状态信息
        """
        available = self.list_available_skills()
        
        return {
            "skills_dir": str(self.skills_dir),
            "loaded_skills": self.loaded_skills,
            "available_generic": len(available["generic"]),
            "available_domains": len(available["domains"]),
            "total_available": len(available["generic"]) + len(available["domains"]),
        }
    
    def print_status(self):
        """打印状态"""
        status = self.get_status()
        
        print("\n🛠️  技能加载器状态\n")
        print(f"技能目录：{status['skills_dir']}")
        print(f"已加载技能：{len(status['loaded_skills'])} 个")
        print(f"可用技能：{status['total_available']} 个")
        print(f"  - 通用技能：{status['available_generic']} 个")
        print(f"  - 领域技能：{status['available_domains']} 个")
        
        if status['loaded_skills']:
            print("\n已加载列表：")
            for skill in status['loaded_skills']:
                print(f"  - {skill}")


def main():
    """CLI 入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='技能加载器')
    parser.add_argument('action', choices=['load', 'list', 'status'], 
                       help='操作类型')
    parser.add_argument('-p', '--project', dest='project', help='项目名称（load 操作需要）')
    parser.add_argument('-d', '--skills-dir', dest='skills_dir', help='Skills 目录路径')
    
    args = parser.parse_args()
    
    loader = SkillLoader(
        skills_dir=Path(args.skills_dir) if args.skills_dir else None
    )
    
    if args.action == 'load':
        if not args.project:
            print("❌ load 操作需要 --project 参数")
            sys.exit(1)
        loader.load_for_project(args.project)
        
        # 保存加载状态
        status_file = Path(__file__).parent / ".loaded_skills.json"
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump({
                "project": args.project,
                "loaded_skills": loader.loaded_skills,
                "registry": loader.skill_registry,
            }, f, indent=2, ensure_ascii=False)
        print(f"\n💾 加载状态已保存到：{status_file}")
        
    elif args.action == 'list':
        available = loader.list_available_skills()
        
        print("\n📚 可用技能列表\n")
        print("通用技能：")
        for skill in available["generic"]:
            print(f"  - {skill}")
        
        print("\n领域技能：")
        for skill in available["domains"]:
            print(f"  - {skill}")
        
    elif args.action == 'status':
        loader.print_status()


if __name__ == "__main__":
    main()
