#!/usr/bin/env python3
"""凌零集 · 入库（流水线第④关）

把人工/AI 结构化好的候选条目（inbox/*.yaml）合并进 data/resources.yaml。

设计取向（重要）：
  合并是**追加**而非整体覆盖 —— 主库 25 条以上的内容、注释、排序都不会被
  任何自动流程碰掉。自动流程能做的只有「校验通过后，把新条目追加到文件末尾」。
  这是本站信任资产（只收官方原生资源）的最后一道程序化闸门。

条目文件规范：
  - inbox/<slug>.yaml，单条：与 resources.yaml 里一个条目完全相同（含 source_id 字段）
  - inbox/<slug>.yaml，批量：顶层是条目列表
  - 必填字段以 scripts/validate.py 的 REQUIRED 为准；source_id 指向 sources.yaml 的 id

用法：
  python3 scripts/ingest.py                     # 处理 inbox/ 下全部 .yaml
  python3 scripts/ingest.py --dry-run           # 只校验，不写文件
  python3 scripts/ingest.py --slug supabase     # 只处理某条
"""
import argparse
import glob
import os
import re
import sys
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES = os.path.join(ROOT, "data", "resources.yaml")
INBOX_DIR = os.path.join(ROOT, "inbox")

# 与 validate.py 保持一致的最低校验（入库前再拦一次，宁严勿漏）
REQUIRED = [
    "name", "type", "free_type", "quota", "validity",
    "need_realname", "openai_compatible", "access_note",
    "official_url", "rule_url",
]

def _yaml_quote(v):
    """把单个标量转成 YAML 可安全写入的形式。"""
    if v is None:
        return "null"
    s = str(v)
    if re.search(r"[:#{}\[\],&*?|>'\"%@`]|^\s|\s$", s) or s in ("", "null", "true", "false", "yes", "no"):
        return '"' + s.replace('"', '\\"') + '"'
    return s


def dump_item(it: dict) -> str:
    """把 dict 渲染成与 resources.yaml 现有风格一致的 YAML 块（保持注释可读性）。"""
    keys = ["name", "slug", "type", "model_name", "free_type", "quota", "validity",
            "need_realname", "need_credit_card", "openai_compatible", "access_note", "official_url",
            "rule_url", "remark", "source_id", "tags"]
    lines = []
    first = True
    for k in keys:
        if k not in it:
            continue
        v = it[k]
        if v is None:
            continue
        prefix = "- " if first else "  "
        first = False
        if k == "tags":
            if not v:
                continue
            lines.append(f"{prefix}tags: [{', '.join(_yaml_quote(x) for x in v)}]")
        else:
            lines.append(f"{prefix}{k}: {_yaml_quote(v)}")
    return "\n".join(lines)


def load_existing_slugs():
    with open(RESOURCES, encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if isinstance(data, dict):
        data = data.get("resources", [])
    return {(it.get("slug") or "") for it in data if isinstance(it, dict)}


def read_item_file(path):
    """支持单条 dict 或列表两种写法。"""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if isinstance(data, dict) and "resources" in data:
        data = data["resources"]
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ValueError(f"{path}: 既不是条目也不是条目列表")
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--slug", help="只处理该 slug 的文件")
    args = ap.parse_args()

    if not os.path.isdir(INBOX_DIR):
        print(f"没有 inbox 目录：{INBOX_DIR}（先把候选结构化写成 inbox/<slug>.yaml）")
        sys.exit(1)

    files = sorted(glob.glob(os.path.join(INBOX_DIR, "*.yaml")))
    files += sorted(glob.glob(os.path.join(INBOX_DIR, "*.yml")))
    if args.slug:
        files = [f for f in files if os.path.basename(f).split(".")[0] == args.slug]
    if not files:
        print("inbox 里没有待入库的 .yaml")
        return

    existing = load_existing_slugs()
    new_blocks, errors = [], []
    stats = {"ok": 0, "dup": 0, "bad": 0}

    for path in files:
        try:
            items = read_item_file(path)
        except Exception as e:
            errors.append(f"{os.path.basename(path)}: {e}")
            stats["bad"] += 1
            continue

        for it in items:
            if not isinstance(it, dict):
                errors.append(f"{path}: 条目不是映射")
                stats["bad"] += 1
                continue
            # slug：显式给 > name 生成
            if not it.get("slug"):
                it["slug"] = re.sub(r"[^a-z0-9]+", "-", str(it.get("name", "")).lower()).strip("-") or "item"
            # 必填
            missing = [k for k in REQUIRED if not (it.get(k) and str(it.get(k)).strip())]
            if missing:
                errors.append(f"{it.get('name', '?')}（{path}）: 缺 {missing}")
                stats["bad"] += 1
                continue
            # 域查重
            slug = it["slug"]
            if slug in existing:
                errors.append(f"{it.get('name', '?')}: slug `{slug}` 已在主库，需人工确认后改名或更新旧条目")
                stats["dup"] += 1
                continue
            existing.add(slug)
            new_blocks.append(dump_item(it))
            stats["ok"] += 1

    print(f"[ingest] 校验通过 {stats['ok']} | 重复 {stats['dup']} | 不合规 {stats['bad']}")
    for e in errors:
        print(f"  [SKIP] {e}")

    if stats["bad"]:
        print("有不合规条目，全部跳过、不写文件。")
        sys.exit(1)

    if args.dry_run:
        print("[ingest] dry-run：将追加以下条目（未写文件）：")
        for b in new_blocks:
            print("\n" + b + "\n")
        return

    if not new_blocks:
        print("[ingest] 没有可追加的新条目。")
        return

    # 追加到 resources.yaml（保持注释与原有顺序不动）
    with open(RESOURCES, encoding="utf-8") as f:
        main = f.read()
    main = main.rstrip() + "\n\n# ============ 新增（脚本追加，来源见 source_id）============\n\n"
    main += "\n\n".join(new_blocks) + "\n"
    with open(RESOURCES, "w", encoding="utf-8") as f:
        f.write(main)

    print(f"[ingest] 已追加 {len(new_blocks)} 条 → data/resources.yaml")
    print("下一步：python3 scripts/validate.py && python3 scripts/check_urls.py")
    print("        人工复核后，把 inbox/ 下对应文件删掉（或移走归档）。")


if __name__ == "__main__":
    main()