#!/usr/bin/env python3
"""凌零集 · 资源页生成器（仅构建期使用，非运行时后端）

从 data/resources.yaml 生成：
  - content/resources/<slug>.md            每资源一详情页
  - content/categories/<type>/_index.md    每分类一页

幂等且**增量**：
  - 内容未变的文件不重写（保留 mtime，避免无意义的删除/重建）
  - 只删除数据里已不存在的孤儿页（资源下架时自动清理）

注意：Hugo 保留 front matter 中的 `type` 作为内容类型，会干扰模板查找，
因此本脚本把数据字段 `type` 映射为 front matter 的 `resource_type`。
"""
import os
import re
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
    "slug": "slug",
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


def write_if_changed(path: str, content: str) -> bool:
    """内容相同则跳过写入，返回是否真的写了。"""
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                if f.read() == content:
                    return False
        except OSError:
            pass
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def prune(dir_path: str, keep: set) -> int:
    """删除目录下不在 keep 里的文件 / 子目录。返回删除数量。"""
    if not os.path.isdir(dir_path):
        return 0
    removed = 0
    for name in os.listdir(dir_path):
        if name in keep:
            continue
        p = os.path.join(dir_path, name)
        if os.path.isdir(p):
            for root, _dirs, files in os.walk(p, topdown=False):
                for fn in files:
                    os.remove(os.path.join(root, fn))
                    removed += 1
                os.rmdir(root)
        else:
            os.remove(p)
            removed += 1
    return removed


def main():
    items = load_items()
    os.makedirs(RES_DIR, exist_ok=True)
    os.makedirs(CAT_DIR, exist_ok=True)

    types = {}
    written = 0
    keep_res = set()
    for it in items:
        slug = it.get("slug") or slugify(it.get("name", "item"))
        it["slug"] = slug
        fname = f"{slug}.md"
        keep_res.add(fname)
        if write_if_changed(os.path.join(RES_DIR, fname), build_front_matter(it)):
            written += 1
        t = it.get("type", "未分类")
        types[t] = slugify(t)

    keep_cat = set()
    for t, tslug in types.items():
        keep_cat.add(tslug)
        body = (
            "---\n"
            f'title: "{t}"\n'
            "layout: category\n"
            f'category: "{t}"\n'
            "---\n"
        )
        write_if_changed(os.path.join(CAT_DIR, tslug, "_index.md"), body)

    # 清理数据里已移除的孤儿页（增量：只有下架时才删）
    pruned = prune(RES_DIR, keep_res) + prune(CAT_DIR, keep_cat)

    if written or pruned:
        print(
            f"[gen] {len(items)} 个资源、{len(types)} 个分类"
            f"（更新 {written} 个，清理 {pruned} 个孤儿文件）"
        )
    else:
        print(f"[gen] {len(items)} 个资源、{len(types)} 个分类（无变化）")


if __name__ == "__main__":
    main()