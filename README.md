# 凌零集 | Limzero AI Hub

面向国内开发者的**免费 AI 开发资源导航站**：可实测的免费大模型 API、免费 Token 额度、免费云服务器、免费托管与向量库、TTS / OCR 等配套资源。

- 纯静态：Hugo 构建 + Pagefind 静态全文搜索 + YAML 数据文件
- GitHub Actions 自动构建（仅出 `public/` 产物，不含部署）
- 无任何后端 / 数据库 / 用户系统 / 第三方统计
- 仅展示官方原生免费资源，不做 API 中转、Token 分发、账号池

> 本站仅为第三方信息导航聚合，详见页脚「免责声明」。

---

## 目录结构

```
ai-limzero-hub/
├── config.toml                 # Hugo 配置（baseURL、站点名、Slogan）
├── data/
│   └── resources.yaml          # ★ 全部资源条目（唯一来源，编辑这里）
├── content/
│   ├── _index.md               # 首页
│   ├── submit.md               # 提交指引
│   ├── disclaimer.md           # 免责声明
│   ├── about.md                # 关于
│   ├── resources/              # 由脚本生成（gitignore，勿手改）
│   └── categories/             # 由脚本生成（gitignore，勿手改）
├── layouts/                    # 模板（baseof / 首页 / 分类 / 详情 / 卡片 / 头尾）
├── assets/
│   ├── css/main.css            # 极简开发者风格、浅/深双主题
│   └── js/{theme,filters,modal}.js
├── static/                     # robots.txt、favicon.svg
├── scripts/
│   ├── dev.py                  # ★ 本地开发服务器（生成+构建+索引+自动刷新）
│   ├── gen_resources.py        # YAML → content/resources + categories（构建期）
│   └── check_urls.py           # 链接失效检测报告（只读）
├── .github/workflows/build.yml # 构建 + Pagefind 索引
├── nginx/ai.limzero.com.conf   # Nginx 参考配置
└── README.md
```

---

## 本地预览

开发阶段**只需一条命令**，改文件保存即自动重建 + 浏览器自动刷新：

```bash
pip install pyyaml            # 首次
python3 scripts/dev.py        # http://localhost:1313
```

脚本每轮自动执行：`gen_resources.py` → `hugo --minify` → `pagefind --site public` → 版本号 +1（页面轮询后自动刷新）。单次约 **3 秒**。

可选参数：

```bash
python3 scripts/dev.py --port 8080     # 换端口
python3 scripts/dev.py --no-open       # 不自动开浏览器
python3 scripts/dev.py --no-search     # 跳过 Pagefind，再快 1.5s（搜索框无结果）
```

> **为什么不用 `hugo server`？**
> Pagefind 是「对构建产物做后处理」的索引器，索引写在 `public/pagefind/`；`hugo server` 在内存渲染、不落盘，所以搜索框在 `hugo server` 下永远是空的。`dev.py` 走真实产物路径，**本地与线上的搜索、详情页、404 完全一致**。
>
> 首次运行会自动 `npm install pagefind` 到 `node_modules/`（已 gitignore）；之后每轮索引从 16 秒降到 1.5 秒。

**发布前**建议本地跑一次完整校验：

```bash
python3 scripts/gen_resources.py
hugo --minify --baseURL https://ai.limzero.com/
npx -y pagefind@1.3.0 --site public --force-language zh
python3 scripts/check_urls.py
```

---

## 新增 / 修改资源

1. 打开 `data/resources.yaml`，按下方字段追加一条；
2. 跑 `python3 scripts/check_urls.py` 确认链接有效；
3. 跑 `python3 scripts/gen_resources.py` 重新生成页面（CI 会自动跑）；
4. 提交到 `main` 分支，GitHub Actions 自动构建。

**字段规范**（每条资源）：

| 字段 | 说明 |
|---|---|
| `name` | 平台名称 |
| `type` | 分类：大模型API / 云服务器·容器 / 静态托管 / 向量数据库 / AI推理工具 |
| `slug` | URL 片段，建议英文，缺省按名称生成 |
| `model_name` | 模型名称（非大模型留空） |
| `free_type` | 新用户一次性 / 每日重置 / 每月重置 / 永久免费 / 学生专属 |
| `quota` | 额度说明（token 数量、输入/输出是否分开） |
| `validity` | 有效期 |
| `need_realname` | 是否实名（是/否） |
| `openai_compatible` | 是否兼容 OpenAI 接口（是/否） |
| `access_note` | 访问备注（**必须标注**「国内可直连」或「需要特殊网络」） |
| `official_url` | 官方领取地址 |
| `rule_url` | 官方规则说明链接 |
| `verify_status` | ✅已实测 / ⏳待复核 / ❌已失效 |
| `verify_time` | 最近核验日期 |
| `remark` | 避坑备注（到期是否自动扣费、额度不结转、地域限制等） |
| `status` | 机器字段：`verified` / `pending` / `expired`（需与 verify_status 同步） |
| `tags` | 标签数组，如 `["国内可访问","免费商用"]` |

---

## 更新核验状态

直接改 `data/resources.yaml` 中对应条目的 `verify_status` 与 `status`、`verify_time`，重新构建即可。失效条目建议把 `status` 改为 `expired`，卡片会变灰并降低排序权重。

定期巡检链接：

```bash
python3 scripts/check_urls.py --timeout 20 --delay 0.5
```

脚本只输出报告、不修改 YAML；404/410 判为失效，403/429/超时/WAF 拦截判为「需人工确认」（避免误杀）。

---

## 部署到阿里云（手动 rsync）

CI 构建完成后，到 Actions 页面下载 `public` 产物，解压后同步到 ECS：

```bash
# 在本地执行（SSH 密钥已配置）
rsync -avz --delete \
  --exclude='.git' \
  ./public/ \
  root@121.40.250.144:/opt/1panel/apps/openresty/openresty/www/sites/ai.limzero.com/index/
```

要点：
- 站点目录沿用 ECS 约定：`.../sites/ai.limzero.com/index`（不是 `html`）
- 阿里云 80 端口被合规拦截，**只走 HTTPS**；证书用 DNS-01（acme.sh）签发
- 参考配置见 `nginx/ai.limzero.com.conf`，改完 `openresty -s reload`
- 若需「push 即自动部署」，可在 Actions 增加 `appleboy/ssh-action` 步骤（需托管 SSH 私钥 secret），本仓库默认不启用

---

## 合规与边界

- 不开发 API 中转、Token 分发、账号池、充值、交易、代理转发
- 不做用户注册 / 登录 / 后台 / 站内评论
- 不收录共享账号、接码、破解、绕过厂商限制内容
- 无后端、无数据库、无广告、无弹窗、无第三方统计
- 文案统一使用【免费额度 / 免费套餐 / 试用额度】
