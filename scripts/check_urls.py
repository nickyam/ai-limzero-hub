#!/usr/bin/env python3
"""凌零集 · 链接失效检测（只读报告，不修改 YAML）

只检测 official_url / rule_url。判定规则：
  - 404 / 410                -> 失效（dead）
  - 403 / 401 / 429 / 超时 / SSL / 其他 -> 需人工确认（manual）
原因：很多官网对爬虫返回 403/WAF 拦截，误判为失效会误导维护。

用法：
  python3 scripts/check_urls.py
  python3 scripts/check_urls.py --timeout 20 --delay 0.5
"""
import argparse
import os
import sys
import time
import yaml
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

UA = "Mozilla/5.0 (compatible; LimzeroHubURLChecker/1.0)"


def check(url: str, timeout: int):
    req = Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urlopen(req, timeout=timeout) as r:
            return r.status, "ok"
    except HTTPError as e:
        code = e.code
        verdict = "dead" if code in (404, 410) else "manual"
        return code, verdict
    except (URLError, TimeoutError):
        return None, "manual"
    except Exception:
        return None, "manual"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    default_data = os.path.join(os.path.dirname(here), "data", "resources.yaml")
    p = argparse.ArgumentParser()
    p.add_argument("--data", default=default_data)
    p.add_argument("--timeout", type=int, default=15)
    p.add_argument("--delay", type=float, default=1.0)
    args = p.parse_args()

    with open(args.data, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if isinstance(data, dict):
        data = data.get("resources", [])
    data = data or []

    rows = []
    for it in data:
        for key in ("official_url", "rule_url"):
            u = it.get(key)
            if not u:
                continue
            try:
                code, verdict = check(u, args.timeout)
            except Exception:
                code, verdict = None, "manual"
            rows.append((it.get("name", ""), key, u, code, verdict))
            time.sleep(args.delay)

    dead = [r for r in rows if r[4] == "dead"]
    manual = [r for r in rows if r[4] == "manual"]

    print("=" * 72)
    print(f"检测完成：共 {len(rows)} 个链接 | 失效 {len(dead)} | 需人工确认 {len(manual)}")
    if dead:
        print("\n[失效 404/410] 建议更新或下架：")
        for n, k, u, c, _ in dead:
            print(f"  - {n} ({k}): {u} -> {c}")
    if manual:
        print("\n[需人工确认 403/429/超时/SSL] 可能是 WAF 误拦，请浏览器实测：")
        for n, k, u, c, _ in manual:
            print(f"  - {n} ({k}): {u} -> {c}")
    if not dead and not manual:
        print("全部链接正常。")
    print("=" * 72)
    sys.exit(0)


if __name__ == "__main__":
    main()
