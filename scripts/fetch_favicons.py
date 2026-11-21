#!/usr/bin/env python3
"""抓取各资源官网的 favicon，统一成 64×64 PNG 存到 static/icons/<slug>.png。

为什么自己抓、不用第三方图标服务：
  Google s2 / DuckDuckGo icons 在国内不稳定或不可达；抓成本地文件后，
  卡片图标与站点同源，国内访问零外链依赖，也不会因为对方服务挂掉而整排破图。

抓取顺序（命中即停）：
  /apple-touch-icon.png → /favicon.ico → /favicon.png → /apple-touch-icon-precomposed.png

抓不到的不生成文件。模板侧用 fileExists 判断，缺失时退回首字母色块，
所以不会出现 <img> 破图。

用法：
  python3 scripts/fetch_favicons.py              # 只抓缺失的
  python3 scripts/fetch_favicons.py --force      # 全部重抓
  python3 scripts/fetch_favicons.py --limit 10   # 只处理前 10 条（调试用）
"""
import argparse
import io
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests
import urllib3
import yaml
from PIL import Image

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "resources.yaml")
OUT_DIR = os.path.join(ROOT, "static", "icons")

SIZE = 64
TIMEOUT = 12
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
CANDIDATES = [
    "/apple-touch-icon.png",
    "/favicon.ico",
    "/favicon.png",
    "/apple-touch-icon-precomposed.png",
]


def make_session(use_proxy: bool = False) -> requests.Session:
    s = requests.Session()
    # 默认不读系统代理：本机 HTTP_PROXY 指向本地代理，对国内站点会拖慢或直接失败。
    # 境外站点直连不通时用 --use-proxy 重跑（此时才读环境变量里的代理）。
    s.trust_env = use_proxy
    s.headers.update({"User-Agent": UA, "Accept": "image/*,*/*;q=0.8"})
    return s


def _abs_url(base: str, href: str) -> str:
    from urllib.parse import urljoin
    return urljoin(base, href)


def icons_from_html(session: requests.Session, host: str):
    """先解析首页 <link rel="...icon...">，这是成功率最高的一招。

    国内大厂（DeepSeek / 智谱 / 百度）几乎都把图标挂在 CDN 子域，
    固定路径 /favicon.ico 基本拿不到，必须从 HTML 里读真实地址。
    """
    import re as _re

    for scheme in ("https", "http"):
        base = f"{scheme}://{host}/"
        try:
            r = session.get(base, timeout=TIMEOUT, allow_redirects=True, verify=False)
            if r.status_code != 200:
                continue
            html = r.text[:200000]
        except Exception:
            continue

        hrefs = []
        # rel 与 href 顺序不定，用两条正则分别覆盖
        for m in _re.finditer(r"<link\b[^>]*>", html, _re.IGNORECASE):
            tag = m.group(0)
            if "icon" not in tag.lower():
                continue
            hm = _re.search(r"""href\s*=\s*["']([^"']+)["']""", tag, _re.IGNORECASE)
            if hm:
                hrefs.append(hm.group(1).strip())

        # apple-touch-icon 通常比 16px favicon 清晰
        hrefs.sort(key=lambda u: 0 if "apple-touch" in u.lower() or "180" in u else 1)
        for href in hrefs[:6]:
            if href.startswith("data:"):
                continue
            url = _abs_url(base, href)
            if url.startswith("//"):
                url = scheme + ":" + url
            try:
                ir = session.get(url, timeout=TIMEOUT, allow_redirects=True, verify=False)
                if ir.status_code != 200 or len(ir.content) < 200:
                    continue
                img = Image.open(io.BytesIO(ir.content))
                img.load()
                return img
            except Exception:
                continue
        return None
    return None


def fetch_one(session: requests.Session, host: str):
    # 第一优先：从首页 HTML 里找真实图标地址
    img = icons_from_html(session, host)
    if img is not None:
        return img

    # 回退：常见固定路径
    for scheme in ("https", "http"):
        for path in CANDIDATES:
            url = f"{scheme}://{host}{path}"
            try:
                r = session.get(url, timeout=TIMEOUT, allow_redirects=True, verify=False)
                if r.status_code != 200 or len(r.content) < 200:
                    continue
                img = Image.open(io.BytesIO(r.content))
                img.load()
                return img
            except Exception:
                continue
    return None


def normalize(img: Image.Image) -> Image.Image:
    """统一成 64×64 RGBA，保留透明背景，四周留 1px 余量。"""
    if img.mode not in ("RGBA", "LA"):
        img = img.convert("RGBA")
    # 有些站给的是超大图，先按比例缩到 64 以内再居中贴到 64×64 画布
    w, h = img.size
    if w > SIZE or h > SIZE:
        scale = min(SIZE / w, SIZE / h)
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    canvas.paste(img, ((SIZE - img.width) // 2, (SIZE - img.height) // 2), img)
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="已存在的也重抓")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--use-proxy", action="store_true", help="走系统代理重试境外站点")
    args = ap.parse_args()

    with open(DATA, encoding="utf-8") as f:
        items = yaml.safe_load(f) or []
    os.makedirs(OUT_DIR, exist_ok=True)

    # 同一域名只抓一次，多个资源共用结果
    todo = []
    seen_host = {}
    for it in items:
        slug = it.get("slug")
        url = it.get("official_url") or ""
        host = (urlparse(url).hostname or "").lower()
        if not slug or not host:
            continue
        out = os.path.join(OUT_DIR, f"{slug}.png")
        if os.path.exists(out) and not args.force:
            continue
        todo.append((slug, host, out))
    if args.limit:
        todo = todo[: args.limit]

    print(f"待抓取 {len(todo)} 个（共 {len(items)} 条资源）")
    if not todo:
        return

    ok, fail = 0, []
    lock_host_cache = {}

    def work(task):
        slug, host, out = task
        session = make_session(args.use_proxy)
        if host in lock_host_cache:
            img = lock_host_cache[host]
        else:
            img = fetch_one(session, host)
            lock_host_cache[host] = img
        if img is None:
            return slug, host, False
        try:
            normalize(img).save(out, "PNG", optimize=True)
            return slug, host, True
        except Exception:
            return slug, host, False

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(work, t) for t in todo]
        for i, fut in enumerate(as_completed(futures), 1):
            slug, host, success = fut.result()
            if success:
                ok += 1
            else:
                fail.append(slug)
            if i % 20 == 0 or i == len(todo):
                print(f"  进度 {i}/{len(todo)}  成功 {ok}  失败 {len(fail)}", flush=True)

    print(f"[icons] 成功 {ok}，失败 {len(fail)}（失败的会退回首字母色块）")
    if fail:
        print("  未拿到图标：" + "、".join(fail[:20]) + ("…" if len(fail) > 20 else ""))


if __name__ == "__main__":
    main()
