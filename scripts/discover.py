#!/usr/bin/env python3
"""凌零集 · 候选发现（流水线第①关）

把三层信源里「能自动读」的那部分，抽成统一格式的候选清单 inbox/candidates.json，
供后续人工/AI 结构化（第②关）与去重校验（第③关）消费。

设计取向（重要）：
  本脚本**只负责发现，不做任何判断，更不写 resources.yaml**。
  因为本站的信任资产是「只收官方原生免费资源」，而聚合池里混着大量非官方中转、
  账号池、纯试用（非免费档）、以及国内根本连不上的服务。这些只能靠人工 + AI 判定，
  纯自动灌库必然把站做烂（这一点是豆包的建议，也是对的）。

支持的信源类型：
  awesome-md   任意 Markdown 列表（free-for.dev / awesome-*），按 `* [名](url) - 描述` 解析
  md-table     Markdown 表格（public-apis 之类），按 `| [名](url) | 描述 | Auth | ... |` 解析
  html-links   普通网页里抓 <a>（适合厂商定价页 / 汇总页）

用法：
  python3 scripts/discover.py                      # 扫 sources.yaml 里 enabled 的信源
  python3 scripts/discover.py --source free-for-dev
  python3 scripts/discover.py --list               # 只看信源台账
  python3 scripts/discover.py --section "Generative AI"
"""
import argparse
import json
import os
import re
import sys
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(ROOT, "data", "sources.yaml")
RESOURCES = os.path.join(ROOT, "data", "resources.yaml")
INBOX_DIR = os.path.join(ROOT, "inbox")
OUT = os.path.join(INBOX_DIR, "candidates.json")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"

# `* [Name](https://x.com) - desc` / `- [Name](url)：desc`
MD_LINK_RE = re.compile(
    r"^\s*[-*]\s*\[(?P<name>[^\]]+)\]\((?P<url>[^)\s]+)\)\s*[-–—:：]?\s*(?P<desc>.*)$"
)
SECTION_RE = re.compile(r"^(#{2,3})\s+(?P<title>.+?)\s*$")
# Markdown 表格行：| [Name](url) | desc | Auth | HTTPS | CORS |
MD_TABLE_RE = re.compile(
    r"^\|\s*\[(?P<name>[^\]]+)\]\((?P<url>https?://[^)\s]+)\)\s*\|(?P<rest>.*)\|\s*$"
)
HTML_A_RE = re.compile(r'<a\b[^>]*href="(?P<url>https?://[^"]+)"[^>]*>(?P<text>[^<]{0,120})</a>', re.I)

# 与其他资源站点/竞争列表的域名，不算「官方资源」
NON_VENDOR_HOSTS = {
    "github.com", "gitlab.com", "twitter.com", "x.com", "youtube.com",
    "medium.com", "reddit.com", "wikipedia.org", "linkedin.com",
    "producthunt.com", "news.ycombinator.com", "discord.gg", "t.me",
}
# 明显不是「AI 开发资源」的，先粗筛（宁漏不错，人工再补）
IRRELEVANT_HINT = re.compile(
    r"\b(clinical|medical|court|legal advice|dating|casino|betting|crypto exchange|"
    r"stock trading|forex broker|insurance|loan|mortgage)\b", re.I
)


def fetch(url: str, timeout: int = 30) -> str:
    req = Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    with urlopen(req, timeout=timeout) as r:
        raw = r.read()
    for enc in ("utf-8", "gb18030", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def host_of(url: str) -> str:
    try:
        h = (urlparse(url).hostname or "").lower()
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


def parse_awesome_md(text: str, section_filter=None):
    """解析 markdown 列表，返回 [(section, name, url, desc)]"""
    out, cur = [], ""
    for line in text.splitlines():
        m = SECTION_RE.match(line)
        if m:
            cur = m.group("title").strip()
            continue
        m = MD_LINK_RE.match(line)
        if not m:
            continue
        if section_filter and section_filter.lower() not in cur.lower():
            continue
        name = re.sub(r"[*_`]", "", m.group("name")).strip()
        url = m.group("url").strip()
        desc = re.sub(r"\[#opensource\]\([^)]*\)", "", m.group("desc") or "")
        desc = re.sub(r"\s+", " ", desc).strip(" -–—:：")
        if not name or not url.startswith("http"):
            continue
        out.append((cur, name, url, desc))
    return out


def parse_md_table(text: str, section_filter=None):
    """解析 markdown 表格（public-apis 风格），返回 [(section, name, url, desc)]

    public-apis 的列是 `API | Description | Auth | HTTPS | CORS`，
    这里把 Auth 一并塞进 desc（人判断是否是「免费档」很依赖它是 No 还是 apiKey）。
    """
    out, cur = [], ""
    for line in text.splitlines():
        m = SECTION_RE.match(line)
        if m:
            cur = m.group("title").strip()
            continue
        m = MD_TABLE_RE.match(line)
        if not m:
            continue
        if section_filter and section_filter.lower() not in cur.lower():
            continue
        name = re.sub(r"[*_`]", "", m.group("name")).strip()
        url = m.group("url").strip()
        cells = [c.strip() for c in m.group("rest").split("|")]
        desc = cells[0] if cells else ""
        auth = cells[1].replace("`", "") if len(cells) > 1 else ""
        if auth:
            desc = f"{desc} (Auth: {auth})"
        desc = re.sub(r"\s+", " ", desc).strip()
        if not name or not url.startswith("http"):
            continue
        out.append((cur, name, url, desc))
    return out


def parse_html_links(text: str, section_filter=None):
    out, seen = [], set()
    for m in HTML_A_RE.finditer(text):
        url, txt = m.group("url"), re.sub(r"\s+", " ", m.group("text")).strip()
        if not txt or url in seen:
            continue
        seen.add(url)
        out.append(("", txt, url, ""))
    return out


def load_sources():
    if not os.path.isfile(SOURCES):
        return []
    with open(SOURCES, encoding="utf-8") as f:
        d = yaml.safe_load(f) or {}
    return d.get("sources", []) or []


def load_known():
    """已有资源的 slug / 名称 / 域名，用于在发现阶段就标出「疑似已收录」"""
    with open(RESOURCES, encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if isinstance(data, dict):
        data = data.get("resources", [])
    slugs = {(it.get("slug") or "") for it in data}
    names = {re.sub(r"\s+", "", (it.get("name") or "")).lower() for it in data}
    hosts = {host_of(it.get("official_url") or "") for it in data}
    return slugs, names, hosts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", help="只扫指定 id")
    ap.add_argument("--section", help="只取章节名包含该词的条目（如 Generative AI）")
    ap.add_argument("--list", action="store_true", help="只列出信源台账")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    sources = load_sources()
    if not sources:
        print(f"未找到信源台账：{SOURCES}")
        sys.exit(1)

    if args.list:
        print(f"{'id':<26}{'层':<12}{'启用':<6}名称")
        print("-" * 80)
        for s in sources:
            print(f"{s.get('id', ''):<26}{s.get('layer', ''):<12}"
                  f"{'✓' if s.get('enabled') else '·':<6}{s.get('name', '')}")
        print(f"\n共 {len(sources)} 个信源，启用 {sum(1 for s in sources if s.get('enabled'))} 个")
        return

    targets = [s for s in sources if s.get("enabled") or args.source]
    if args.source:
        targets = [s for s in targets if s.get("id") == args.source]
    if not targets:
        print("没有可扫描的信源（检查 enabled 或 --source）")
        sys.exit(1)

    known_slugs, known_names, known_hosts = load_known()
    results, errors = [], []

    for s in targets:
        sid, url = s.get("id", "?"), s.get("url", "")
        kind = s.get("kind", "awesome-md")
        print(f"[scan] {sid} ← {url}")
        try:
            text = fetch(url, args.timeout)
        except Exception as e:
            errors.append((sid, str(e)))
            print(f"       失败：{e}")
            continue
        rows = parse_awesome_md(text, args.section) if kind == "awesome-md" \
            else parse_md_table(text, args.section) if kind == "md-table" \
            else parse_html_links(text, args.section)

        added = 0
        for section, name, u, desc in rows:
            h = host_of(u)
            if h in NON_VENDOR_HOSTS:
                continue
            if IRRELEVANT_HINT.search(desc or ""):
                continue
            slug_guess = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            results.append({
                "source": sid,
                "layer": s.get("layer", ""),
                "section": section,
                "name": name,
                "url": u,
                "host": h,
                "desc": desc[:400],
                "suspect_dup": (slug_guess in known_slugs) or (h in known_hosts),
            })
            added += 1
        print(f"       解析 {added} 条")
        time.sleep(0.4)  # 对源站客气一点

    # 去掉本次扫描内的重复（同一 url 只留第一次）
    dedup, seen = [], set()
    for r in results:
        k = r["url"].rstrip("/").lower()
        if k in seen:
            continue
        seen.add(k)
        dedup.append(r)

    os.makedirs(INBOX_DIR, exist_ok=True)
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "section_filter": args.section,
        "total": len(dedup),
        "suspect_dup": sum(1 for r in dedup if r["suspect_dup"]),
        "errors": errors,
        "candidates": dedup,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("-" * 60)
    print(f"[discover] 候选 {len(dedup)} 条（其中疑似已收录 {payload['suspect_dup']} 条）")
    print(f"           输出 → {args.out}")
    if errors:
        print(f"           失败信源 {len(errors)} 个：{[e[0] for e in errors]}")
    print("\n下一步：挑出真正要收的条目，写成 inbox/<slug>.yaml（字段同 resources.yaml），")
    print("        然后运行 python3 scripts/ingest.py 校验并入主库。")


if __name__ == "__main__":
    main()