#!/usr/bin/env python3
"""凌零集 · 本地开发服务器（零第三方依赖）

为什么不用 `hugo server`？
  hugo server 在内存里渲染、不写磁盘，而且本站的搜索是「前端基于内嵌 JSON 的纯静态检索」，
  资源数据由 scripts/gen_resources.py 从 YAML 生成，hugo server 不会自动跑生成器，
  导致详情页缺失、搜索无数据。
  本脚本改为走「真实构建产物」路线：生成 → hugo --minify → 静态托管 public/，
  于是本地筛选、搜索、详情页、404 与线上完全一致。

每次保存自动执行：
  1) scripts/gen_resources.py   YAML → content/resources + content/categories
  2) hugo --minify              → public/
  3) 浏览器自动刷新（轮询 /__ver 版本号）

搜索说明：
  首页搜索框为「纯客户端静态检索」——直接对页面内嵌的 #resource-data JSON 做名称/模型/标签
  匹配并就地筛选卡片，不依赖任何后端或外部索引服务（比 Pagefind 更适合「单页卡片列表」场景）。

用法：
  python3 scripts/dev.py                 # http://localhost:1313
  python3 scripts/dev.py --port 8080
  python3 scripts/dev.py --no-open       # 不自动开浏览器
"""
import argparse
import functools
import http.server
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.path.join(ROOT, "public")

# 监听范围（content/resources、content/categories 是生成产物，必须排除，否则重建死循环）
WATCH = ["data", "content", "layouts", "assets", "static", "config.toml"]
GENERATED = {"content/resources", "content/categories"}
SKIP_DIRS = {"__pycache__", ".git", "public", "node_modules"}

STATE = {"ver": 1}

RELOAD_SNIPPET = b"""<script>
(function () {
  var v = null;
  setInterval(function () {
    fetch("/__ver", { cache: "no-store" })
      .then(function (r) { return r.text(); })
      .then(function (t) {
        if (v === null) { v = t; }
        else if (v !== t) { location.reload(); }
      })
      .catch(function () {});
  }, 700);
})();
</script>
"""


def log(msg):
    print(msg, flush=True)


def snapshot():
    """收集被监听文件的 (mtime, size)，用于判断是否真的有改动。"""
    out = {}
    for w in WATCH:
        p = os.path.join(ROOT, w)
        if os.path.isfile(p):
            try:
                out[p] = (os.path.getmtime(p), os.path.getsize(p))
            except OSError:
                pass
            continue
        if not os.path.isdir(p):
            continue
        for dirpath, dirnames, filenames in os.walk(p):
            rel = os.path.relpath(dirpath, ROOT).replace(os.sep, "/")
            if rel in GENERATED:
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                if fn.endswith((".pyc", ".swp")) or fn.startswith("."):
                    continue
                fp = os.path.join(dirpath, fn)
                try:
                    out[fp] = (os.path.getmtime(fp), os.path.getsize(fp))
                except OSError:
                    pass
    return out


def changed_files(prev, cur, limit=4):
    keys = [k for k in cur if prev.get(k) != cur[k]]
    keys += [k for k in prev if k not in cur]
    names = [os.path.relpath(k, ROOT) for k in keys]
    head = ", ".join(names[:limit])
    if len(names) > limit:
        head += f" 等 {len(names)} 个文件"
    return head


def run_step(title, cmd):
    t0 = time.time()
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    cost = time.time() - t0
    if r.returncode != 0:
        log(f"  ✗ {title} 失败 ({cost:.1f}s)")
        tail = (r.stderr or r.stdout or "").strip().splitlines()
        for line in tail[-15:]:
            log(f"    {line}")
        return False
    out = (r.stdout or "").strip().splitlines()
    msg = out[-1] if out else ""
    log(f"  ✓ {title} ({cost:.1f}s)" + (f"  {msg}" if msg and len(msg) < 90 else ""))
    return True


def build(port):
    log("── 构建 ──")
    ok = run_step("校验资源数据", [sys.executable, "scripts/validate.py", "--quiet"])
    if not ok:
        log("    （数据不合规，已跳过本轮构建；修好 data/resources.yaml 后自动重试）")
        return False
    ok = run_step("生成资源页", [sys.executable, "scripts/gen_resources.py"])
    if not ok:
        return False
    ok = run_step(
        "Hugo 构建",
        ["hugo", "--minify", "--cleanDestinationDir",
         "--baseURL", f"http://localhost:{port}/"],
    )
    if not ok:
        return False
    return True


class DevHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        clean = self.path.split("?")[0]

        # 版本号探针：供注入脚本判断是否需要刷新
        if clean == "/__ver":
            body = str(STATE["ver"]).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return

        fs = self.translate_path(self.path)
        if os.path.isdir(fs):
            fs = os.path.join(fs, "index.html")

        # HTML 注入自动刷新脚本（404 页也注入，方便调试）
        if fs.endswith(".html") and os.path.isfile(fs):
            with open(fs, "rb") as f:
                data = f.read()
            idx = data.rfind(b"</body>")
            data = data[:idx] + RELOAD_SNIPPET + data[idx:] if idx != -1 else data + RELOAD_SNIPPET
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return

        super().do_GET()

    def end_headers(self):
        # 静态资源不缓存，避免改了 CSS/JS 却看到旧版本
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass


def main():
    ap = argparse.ArgumentParser(description="凌零集本地开发服务器")
    ap.add_argument("--port", type=int, default=1313)
    ap.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    args = ap.parse_args()

    if not shutil.which("hugo"):
        log("✗ 未检测到 hugo，请先安装：brew install hugo")
        sys.exit(1)

    try:
        import yaml  # noqa: F401
    except ImportError:
        log("✗ 缺少 PyYAML，请先执行：pip install pyyaml")
        sys.exit(1)

    if not build(args.port):
        log("\n首次构建失败，已中止。修好上面的报错后重跑即可。")
        sys.exit(1)

    handler = functools.partial(DevHandler, directory=PUBLIC)
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    url = f"http://localhost:{args.port}/"
    log("")
    log(f"预览地址：{url}")
    log("监听中：data/ content/ layouts/ assets/ static/ config.toml —— 保存即自动重建并刷新")
    log("退出：Ctrl+C")
    log("")
    if not args.no_open:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()

    prev = snapshot()
    try:
        while True:
            time.sleep(0.6)
            cur = snapshot()
            if cur == prev:
                continue
            time.sleep(0.3)          # 防抖：编辑器保存常触发连续多次变更
            cur = snapshot()
            if cur == prev:
                continue
            log(f"检测到改动：{changed_files(prev, cur)}")
            prev = cur
            if build(args.port):
                STATE["ver"] += 1
                log(f"→ 已刷新 {url}\n")
    except KeyboardInterrupt:
        log("\n已退出。")
        server.shutdown()


if __name__ == "__main__":
    main()
