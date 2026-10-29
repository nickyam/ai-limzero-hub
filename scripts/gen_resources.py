#!/usr/bin/env python3
"""凌零集 · 资源页生成器（仅构建期使用，非运行时后端）

从 data/resources.yaml 生成：
  - content/resources/<slug>.md      每资源一详情页
  - content/categories/<type>/_index.md  每分类一页

重跑幂等：会清空旧的 content/resources 与 content/categories 再重建。
注意：Hugo 保留 front matter 中的 `type` 作为内容类型，会干扰模板查找，
因此本脚本把数据字段 `type` 映射为 front matter 的 `resource_type`。
"""
import os
import re
import shutil
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "resources.yaml")
RES_DIR = os.path.join(ROOT, "content", "resources")
CAT_DIR = os.path.join(ROOT, "content", "categories")

# YAML 字段 -> front matter 键（避免与 Hugo 保留字冲突）
FIELD_MAP = {
    "name": "title",          # title 由 name 生成
    "type": "resource_type",  # 关键：避开 Hugo 保留字 type
    "model_name": "model_name",
    "free_type": "free_type",
    "quota": "quota",
    "validity": "validity",
    "need_realname": "need_realname",
    "openai_compatible": "openai_compatible",
    "access_note": "access_note",
    "official_url": "official_url",
    "rule_url": "rule_url",
    "verify_status": "verify_status",
    "verify_time": "verify_time",
    "remark": "remark",
    "status": "status",
}


def slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9一-鿿\-]", "", s)
    return s.strip("-") or "item"


def load_items():
    with open(DATA, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if isinstance(data, dict):
        data = data.get("resources", [])
    return data or []


def yaml_val(v):
    """把 Python 值格式化为 YAML front matter 片段。"""
    if v is None or v == "":
        return None
    if isinstance(v, list):
        if not v:
            return None
        inner = ", ".join(f'"{x}"' for x in v)
        return f"[{inner}]"
    s = str(v)
    if any(ch in s for ch in [":", "#", '"', "'", "\n"]) or s.strip() != s:
        s = s.replace('"', '\\"')
        return f'"{s}"'
    return s


def build_front_matter(item: dict) -> str:
    lines = ["---"]
    lines.append(f'title: "{item.get("name", "")}"')
    for src, dst in FIELD_MAP.items():
        if dst == "title":
            continue
        val = yaml_val(item.get(src))
        if val is None:
            continue
        lines.append(f"{dst}: {val}")
    lines.append("---")
    lines.append("")
    lines.append("> 本页由构建脚本自动生成，请勿直接编辑；数据维护见 data/resources.yaml。")
    return "\n".join(lines)


def clear_dir(d: str):
    if not os.path.isdir(d):
        return
    for name in os.listdir(d):
        p = os.path.join(d, name)
        if os.path.isdir(p):
            shutil.rmtree(p)
        else:
            os.remove(p)


def main():
    items = load_items()
    clear_dir(RES_DIR)
    clear_dir(CAT_DIR)
    os.makedirs(RES_DIR, exist_ok=True)
    os.makedirs(CAT_DIR, exist_ok=True)

    types = {}
    for it in items:
        slug = it.get("slug") or slugify(it.get("name", "item"))
        it["slug"] = slug
        with open(os.path.join(RES_DIR, f"{slug}.md"), "w", encoding="utf-8") as f:
            f.write(build_front_matter(it))
        t = it.get("type", "未分类")
        types[t] = slugify(t)

    for t, tslug in types.items():
        d = os.path.join(CAT_DIR, tslug)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "_index.md"), "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write(f'title: "{t}"\n')
            f.write("layout: category\n")
            f.write(f'category: "{t}"\n')
            f.write("---\n")

    print(f"[gen] 生成 {len(items)} 个资源详情页，{len(types)} 个分类页")


if __name__ == "__main__":
    main()
