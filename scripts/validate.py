#!/usr/bin/env python3
"""凌零集 · 资源数据校验（流水线第③关的第一道闸门）

为什么要有它：
  条目从 25 涨到 100+ 之后，靠肉眼守着 data/resources.yaml 不现实。
  纯自动灌库最典型的翻车方式是：字段缺失 → 模板渲染出空卡片；slug 撞车 →
  详情页互相覆盖；同一厂商被收两遍 → 用户觉得这站是爬来的。

校验分三档：
  ERROR  阻断（CI / dev.py 直接失败，不允许构建）
  WARN   提示（能构建，但建议人工看一眼）
  OK     通过

用法：
  python3 scripts/validate.py              # 人类可读
  python3 scripts/validate.py --quiet      # 只报错（给 CI / dev.py 用）
  python3 scripts/validate.py --strict     # 把 WARN 也当失败

退出码：0 通过 / 1 有 ERROR（或 --strict 下有 WARN）
"""
import argparse
import os
import re
import sys
from urllib.parse import urlparse

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "resources.yaml")

# 必填字段（缺一即不可上线）
REQUIRED = [
    "name", "slug", "type", "free_type", "quota", "validity",
    "need_realname", "openai_compatible", "access_note",
    "official_url", "rule_url", "remark", "tags",
]

FREE_TYPES = {"新用户一次性", "每日重置", "每月重置", "永久免费", "学生专属", "限时免费"}
YN = {"是", "否"}

# 已知分类（新增分类会 WARN，提醒你是主动决策而不是手滑写错字）
KNOWN_TYPES = {
    "大模型API", "AI编程助手", "AI推理工具", "免费API",
    "云服务器·容器", "静态托管", "存储·CDN", "后端·数据库", "向量数据库",
}

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# 允许同一厂商一个域名下多条（腾讯云同时有混元/轻量/VDB/OCR），
# 所以域名重复只 WARN；真正判重靠 slug + 名称。
SHARED_HOST_OK = {
    "cloud.tencent.com", "www.volcengine.com", "cloud.baidu.com",
    "bailian.console.aliyun.com", "free.aliyun.com", "www.aliyun.com",
    "platform.minimax.io", "cloud.siliconflow.cn",
    # 同一厂商多个独立产品共用文档域名
    "developers.cloudflare.com", "open.bigmodel.cn",
}


class Report:
    def __init__(self, quiet=False):
        self.errors, self.warns, self.quiet = [], [], quiet

    def err(self, where, msg):
        self.errors.append((where, msg))
        print(f"  [ERROR] {where}: {msg}")

    def warn(self, where, msg):
        self.warns.append((where, msg))
        if not self.quiet:
            print(f"  [WARN ] {where}: {msg}")


def norm_url_host(u: str) -> str:
    try:
        p = urlparse(u if "://" in u else "https://" + u)
        return (p.hostname or "").lower()
    except Exception:
        return ""


def check_item(it: dict, idx: int, rep: Report) -> None:
    name = (it.get("name") or "").strip()
    where = f"#{idx + 1} {name or '<无 name>'}"

    # 1) 必填
    for k in REQUIRED:
        v = it.get(k)
        if v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, list) and not v):
            rep.err(where, f"缺少必填字段 `{k}`")
    if not name:
        return  # 没名字后面没法定位，直接返回

    # 2) slug
    slug = (it.get("slug") or "").strip()
    if slug and not SLUG_RE.match(slug):
        rep.err(where, f"slug `{slug}` 不合规（只能小写字母/数字/中划线）")

    # 3) 枚举
    ft = it.get("free_type")
    if ft and ft not in FREE_TYPES:
        rep.err(where, f"free_type `{ft}` 不在允许值 {sorted(FREE_TYPES)}")
    for k in ("need_realname", "openai_compatible"):
        v = it.get(k)
        if v and v not in YN:
            rep.err(where, f"{k} `{v}` 必须是「是」或「否」")

    # 4) 访问备注必须明确表态（首页「国内直连」筛选依赖这个字符串）
    an = it.get("access_note") or ""
    if an and ("国内可直连" not in an) and ("需要特殊网络" not in an):
        rep.err(where, "access_note 必须含「国内可直连」或「需要特殊网络」")

    # 5) URL
    for k in ("official_url", "rule_url"):
        u = (it.get(k) or "").strip()
        if not u:
            continue
        if not re.match(r"^https?://", u):
            rep.err(where, f"{k} 必须以 http(s):// 开头：{u}")
        elif not norm_url_host(u):
            rep.err(where, f"{k} 无法解析出域名：{u}")

    # 6) 额度不能是占位符
    q = (it.get("quota") or "").strip()
    if q and len(q) < 8:
        rep.err(where, f"quota 过短，疑似占位符：`{q}`")
    if q and re.search(r"(TODO|TBD|待填|xxx|XXX)", q):
        rep.err(where, "quota 含占位符文本")

    # 7) tags
    tags = it.get("tags")
    if tags is not None and not isinstance(tags, list):
        rep.err(where, "tags 必须是数组")

    # 8) 分类
    t = (it.get("type") or "").strip()
    if t and t not in KNOWN_TYPES:
        rep.warn(where, f"新分类 `{t}`（确认是有意新增，否则可能是错别字）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=DATA)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--strict", action="store_true", help="WARN 也当失败")
    args = ap.parse_args()

    with open(args.data, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if isinstance(data, dict):
        data = data.get("resources", [])
    data = data or []

    rep = Report(quiet=args.quiet)
    if not args.quiet:
        print(f"校验 {args.data}（{len(data)} 条）…")

    for i, it in enumerate(data):
        if not isinstance(it, dict):
            rep.err(f"#{i + 1}", "条目不是映射（检查缩进/短横线）")
            continue
        check_item(it, i, rep)

    # 全局查重
    seen_slug, seen_name, host_map = {}, {}, {}
    for i, it in enumerate(data):
        if not isinstance(it, dict):
            continue
        name = (it.get("name") or "").strip()
        slug = (it.get("slug") or "").strip()
        where = f"#{i + 1} {name}"
        if slug:
            if slug in seen_slug:
                rep.err(where, f"slug `{slug}` 与 #{seen_slug[slug] + 1} 重复（详情页会互相覆盖）")
            else:
                seen_slug[slug] = i
        key = re.sub(r"\s+", "", name).lower()
        if key:
            if key in seen_name:
                rep.err(where, f"名称与 #{seen_name[key] + 1} 重复")
            else:
                seen_name[key] = i
        host = norm_url_host(it.get("official_url") or "")
        if host:
            host_map.setdefault(host, []).append((i + 1, name))

    for host, items in host_map.items():
        if len(items) > 1 and host not in SHARED_HOST_OK:
            names = "、".join(n for _, n in items)
            rep.warn(f"域名 {host}", f"被 {len(items)} 条共用（{names}）——确认是同一厂商不同产品，而非重复收录")

    # 汇总
    n_err, n_warn = len(rep.errors), len(rep.warns)
    if not args.quiet:
        print("-" * 60)
    print(f"[validate] {len(data)} 条 | ERROR {n_err} | WARN {n_warn}")

    failed = n_err > 0 or (args.strict and n_warn > 0)
    if failed and args.quiet and rep.errors:
        for where, msg in rep.errors:
            print(f"  [ERROR] {where}: {msg}")
    if failed:
        print("[validate] 未通过，构建已中止。")
        sys.exit(1)
    print("[validate] 通过。")
    sys.exit(0)


if __name__ == "__main__":
    main()