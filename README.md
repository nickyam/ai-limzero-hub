# 凌零集 | Limzero AI Hub

面向国内开发者的**免费 AI 开发资源导航站**：可实测的免费大模型 API、免费 Token 额度、免费云服务器、免费托管与向量库、TTS / OCR 等配套资源。

- 纯静态：Hugo 构建 + 前端内嵌 JSON 的纯静态检索（无后端、无索引服务）+ YAML 数据文件
- **部署链路：本地构建 → rsync 直传阿里云 ECS**，不经 GitHub（GitHub 只做代码备份 + 数据校验 CI）
- 无任何后端 / 数据库 / 用户系统 / 第三方统计
- 仅展示官方原生免费资源，不做 API 中转、Token 分发、账号池

> 本站仅为第三方信息导航聚合，详见页脚「免责声明」。

---

## 架构与发布链路

```
data/resources.yaml                   ← 唯一数据源（手工/流水线维护）
        ↓  scripts/gen_resources.py
content/resources/ + content/categories/   （构建期生成，不入库）
        ↓  hugo --minify
public/                               ← 构建产物（不入库）
        ↓  rsync -e "ssh -i ~/.ssh/id_aliyun"
阿里云 ECS  /opt/1panel/apps/openresty/openresty/www/sites/ai.limzero.com/index/
        ↓  OpenResty 容器
https://ai.limzero.com
```

**发布 = 一条命令**（在本地跑，3 秒）：

```bash
bash deploy/deploy.sh
```

### GitHub 在本项目里的角色

| 角色 | 说明 |
|---|---|
| **保险箱** | 版本历史与备份。150 条核实的额度数据是本站最值钱的资产，务必定期 push |
| **数据体检 CI** | `build.yml` 每次 push 跑 `validate.py`，坏数据进不了 main |
| ~~部署通道~~ | **不参与**。Actions 只出 `public/` artifact 供人工抽查，不会推送到服务器 |

为什么不走 Actions 自动部署：本地直传 3 秒完成；绕道 GitHub 海外机房再回国内，链路长、失败点多，还得把服务器凭据托管到云端。Actions 另有 2~3 小时排队延迟，**不能作为"是否已上线"的判据**。

---

## 目录结构

```
ai-limzero-hub/
├── config.toml                 # Hugo 配置（baseURL、站点名、Slogan）
├── data/
│   ├── resources.yaml          # ★ 全部资源条目（唯一来源，编辑这里）
│   └── sources.yaml            # 信源台账（扩充资源时的候选池，三层结构）
├── inbox/                      # 待入库条目暂存区（candidates.json + 人工结构化 yaml）
├── content/
│   ├── _index.md               # 首页
│   ├── submit.md               # 提交指引
│   ├── about.md                # 关于
│   ├── disclaimer.md           # 免责声明
│   ├── privacy.md              # 隐私政策
│   ├── resources/              # 由脚本生成（gitignore，勿手改）
│   └── categories/             # 由脚本生成（gitignore，勿手改）
├── layouts/                    # 模板（baseof / 首页 / 分类 / 详情 / 卡片 / 头尾）
├── assets/
│   ├── css/main.css            # 极简开发者风格、浅/深双主题
│   └── js/{theme,filters,modal}.js
├── static/                     # robots.txt、favicon.svg
├── scripts/
│   ├── dev.py                  # ★ 本地开发服务器（校验+生成+构建+自动刷新）
│   ├── validate.py             # ★ 数据校验闸门（字段/枚举/slug 查重/域名查重）
│   ├── gen_resources.py        # YAML → content/resources + categories（构建期）
│   ├── discover.py             # 候选发现：扫 sources.yaml → inbox/candidates.json
│   ├── ingest.py               # 入库：inbox/*.yaml 校验后追加进 resources.yaml
│   └── check_urls.py           # 链接失效检测报告（只读）
├── .github/workflows/build.yml # 构建并产出 public/ 产物
├── deploy/deploy.sh            # ★ 部署：本地构建 + rsync 同步到阿里云 ECS
├── nginx/ai.limzero.com.conf   # Nginx vhost 参考配置（容器内路径）
└── README.md
```

---

## 本地预览

开发阶段**只需一条命令**，改文件保存即自动重建 + 浏览器自动刷新：

```bash
pip install pyyaml            # 首次
python3 scripts/dev.py        # http://localhost:1313
```

脚本每轮自动执行：`gen_resources.py` → `hugo --minify` → 版本号 +1（页面轮询后自动刷新）。单次约 **1.5 秒**。

可选参数：

```bash
python3 scripts/dev.py --port 8080     # 换端口
python3 scripts/dev.py --no-open       # 不自动开浏览器
```

> **为什么不用 `hugo server`？**
> 本站搜索是「前端基于内嵌 JSON 的纯静态检索」，资源数据由 `gen_resources.py` 从 YAML 生成；`hugo server` 不会自动跑生成器，导致详情页缺失、搜索无数据。`dev.py` 走真实产物路径，**本地搜索、筛选、详情页、404 与线上完全一致**。

**发布前**建议本地跑一次完整校验：

```bash
python3 scripts/gen_resources.py
hugo --minify --baseURL https://ai.limzero.com/
python3 scripts/check_urls.py
```

---

## 部署到阿里云 ECS（ai.limzero.com）

站点为纯静态，服务器端只做「文件托管 + HTTPS」，**不需要任何后端运行时**。

### 一次性准备

| 项 | 说明 |
|---|---|
| 1Panel 建站 | 「网站 → 创建 → 静态网站」，主域名与**代号**都填 `ai.limzero.com`（代号决定目录落到 `.../sites/ai.limzero.com/index`，注意是 `index` 不是 `html`） |
| DNS 解析 | 阿里云万网（dns17/18.hichina.com）添加 A 记录 `ai.limzero.com` → ECS 公网 IP |
| 证书 | **只能 DNS-01**。备案 ECS 的 80 端口明文被透明劫持，HTTP-01 签发必然失败 |

### 日常发布

```bash
bash deploy/deploy.sh              # 校验 → 生成 → Hugo 构建 → rsync 同步 → 线上校验
bash deploy/deploy.sh --sync-only  # 产物已构建，只同步
```

脚本用 `rsync --delete-excluded` 把 `public/` 同步到服务器站点目录，**并排除** `.git/` `.github/` `scripts/` `deploy/` `data/` `layouts/` 等开发文件——源码与部署脚本不上公网。

### vhost 路径陷阱

`nginx/ai.limzero.com.conf` 由**容器内**的 OpenResty 读取，`root` 必须写容器内路径：

```
容器内：/www/sites/ai.limzero.com/index
宿主机：/opt/1panel/apps/openresty/openresty/www/sites/ai.limzero.com/index
```

宿主机 `.../www` 挂载为容器内 `/www`。写成宿主机路径会导致**全站 404**。

改完 vhost 后 reload OpenResty 容器使其生效。

### 手动 rsync 等价写法

日常用 `deploy/deploy.sh` 即可，下列是等价的裸命令（**要点在参数，漏一个就报错**）：

```bash
# 在本地执行，产物已由 hugo --minify 构建到 public/
rsync -az --delete --delete-excluded \
  -e "ssh -i ~/.ssh/id_aliyun -o StrictHostKeyChecking=no" \
  --exclude '.git/' --exclude '.github/' --exclude 'scripts/' \
  --exclude 'deploy/' --exclude 'data/' --exclude 'layouts/' \
  --exclude 'content/' --exclude 'assets/' --exclude 'README.md' \
  ./public/ \
  root@121.40.250.144:/opt/1panel/apps/openresty/openresty/www/sites/ai.limzero.com/index/
```

- **rsync 必须显式带 `-e "ssh -i ~/.ssh/id_aliyun"`** —— `ssh` 命令带 `-i` 不代表 rsync 会带上，漏了直接 `Permission denied (publickey)`
- **必须 `--delete-excluded`** —— 否则被 `--exclude` 的旧文件不会被清理，开发文件会残留在站点目录
- ⚠️ **不需要**在 Actions 里加 `appleboy/ssh-action` 做自动部署 —— 本仓库默认不走那条路，理由见「架构与发布链路」

---

## 新增 / 修改资源

1. 打开 `data/resources.yaml`，按下方字段追加一条（或走上面的流水线，批量入库）；
2. 跑 `python3 scripts/validate.py` 确认字段与 slug 合规；
3. 跑 `python3 scripts/check_urls.py` 确认链接有效；
4. 跑 `python3 scripts/gen_resources.py` 重新生成页面；
5. 跑 `bash deploy/deploy.sh` 发布到线上（本地构建 + rsync 直传 ECS）；
6. 提交到 `main` 分支做版本备份（CI 会再跑一次校验，不过则红——但**不影响线上**，线上产物来自第 5 步）。

**字段规范**（每条资源）：

| 字段 | 说明 |
|---|---|
| `name` | 平台名称 |
| `type` | 分类：大模型API / AI编程助手 / AI推理工具 / 云服务器·容器 / 静态托管 / 存储·CDN / 后端·数据库 / 向量数据库 |
| `slug` | URL 片段，英文小写+中划线，全局唯一（重复会让详情页互相覆盖） |
| `model_name` | 模型名称（非大模型留空） |
| `free_type` | 新用户一次性 / 每日重置 / 每月重置 / 永久免费 / 学生专属 / 限时免费 |
| `quota` | 额度说明（token 数量、输入/输出是否分开） |
| `validity` | 有效期 |
| `need_realname` | 是否实名（是/否） |
| `openai_compatible` | 是否兼容 OpenAI 接口（是/否） |
| `access_note` | 访问备注（**必须标注**「国内可直连」或「需要特殊网络」，首页筛选依赖此字段） |
| `official_url` | 官方领取地址 |
| `rule_url` | 官方规则说明链接 |
| `remark` | 避坑备注（到期是否自动扣费、额度不结转、休眠/回收规则、地域限制等） |
| `source_id` | 可选：来源信源 id（对应 `data/sources.yaml`），便于溯源 |
| `tags` | 标签数组，如 `["国内可访问","免费商用"]` |

---

## 扩充资源：四段流水线

条目从几十条涨到上百条后，手工维护会崩。所以扩充走固定四段，每段一个脚本，**任何一段都能单独跑**：

```
① 发现            ② 结构化            ③ 校验              ④ 入库
discover.py  →   人工/AI 写 yaml  →  validate.py   →   ingest.py
候选清单          inbox/*.yaml        闸门（失败即停）    追加进主库
```

### ① 候选发现

信源登记在 `data/sources.yaml`，分三层：**开源聚合池**（量大但混杂）、**厂商官方**（权威但需逐个找）、**中文内容源**（贴合国内但需核验）。

```bash
python3 scripts/discover.py --list                  # 看信源台账
python3 scripts/discover.py                         # 扫所有 enabled 的信源
python3 scripts/discover.py --source free-for-dev --section "Generative AI"
```

输出 `inbox/candidates.json`，每条带 `section / name / url / host / desc / suspect_dup`（是否疑似已收录）。

> ⚠️ 发现**只负责找**，不做判断、不写主库。聚合池里混着大量非官方中转、账号池、纯试用，必须人工过滤——这是本站「只收官方原生资源」的底线。

### ② 结构化

从候选里挑出真正要收的，写成 `inbox/<批次>.yaml`。格式与 `resources.yaml` 单个条目完全一致，额外多一个 `source_id`（指向 `sources.yaml` 的 id，用于溯源）。

一个文件可放多条（顶层是列表），也可以只放一条。

### ③ 校验（闸门）

`scripts/validate.py` 是整条流水线的守门人，同时挂在 **CI 构建前** 和 **dev.py 每轮重建前**，不通过就中止：

| 检查项 | 级别 |
|---|---|
| 必填字段缺失（13 个字段） | ERROR |
| `slug` 格式不合规 / 重复（详情页会互相覆盖） | ERROR |
| `free_type` / `need_realname` / `openai_compatible` 枚举非法 | ERROR |
| `access_note` 未声明「国内可直连 / 需要特殊网络」 | ERROR |
| URL 非 http(s) 或解析不出域名 | ERROR |
| `quota` 过短或含 TODO 占位符 | ERROR |
| 名称重复、同域名多条目（可能是重复收录） | WARN |
| 未知分类（可能是错别字） | WARN |

```bash
python3 scripts/validate.py              # 人类可读
python3 scripts/validate.py --quiet      # 只报错（CI / dev.py 用）
python3 scripts/validate.py --strict     # WARN 也算失败
```

### ④ 入库

```bash
python3 scripts/ingest.py --dry-run      # 先看会追加什么
python3 scripts/ingest.py                # 追加进 data/resources.yaml
python3 scripts/validate.py && hugo --minify --baseURL https://ai.limzero.com/
python3 scripts/check_urls.py            # 新链接有效性
```

`ingest.py` 只做**追加**，不重排、不改动已有条目和注释。校验不过的条目整体跳过、不写文件。

入库并确认无误后，把 `inbox/` 里对应的 yaml 删掉（或移走归档）——它是暂存区，不是历史库。

---

## 下架失效资源

免费层政策随时会变，厂商砍掉额度时需要把对应条目从 `data/resources.yaml` 中删除，重新构建即可下线。

定期巡检链接：

```bash
python3 scripts/check_urls.py --timeout 20 --delay 0.5
```

脚本只输出报告、不修改 YAML；404/410 判为失效，403/429/超时/WAF 拦截判为「需人工确认」（避免误杀）。

---

## 合规与边界

- 不开发 API 中转、Token 分发、账号池、充值、交易、代理转发
- 不做用户注册 / 登录 / 后台 / 站内评论
- 不收录共享账号、接码、破解、绕过厂商限制内容
- 无后端、无数据库、无广告、无弹窗、无第三方统计
- 文案统一使用【免费额度 / 免费套餐 / 试用额度】
