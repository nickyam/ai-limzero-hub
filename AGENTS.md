# AGENTS.md — 凌零集（ai-limzero-hub）

AI 资源导航站 ai.limzero.com，Hugo 静态站。给 AI 协作者（和隔一段时间回来的自己）的执行说明。

## 环境
- `hugo v0.166.0+extended`（与 CI `.github/workflows/build.yml` 锁同版，别升）
- `python3` + `PyYAML`（`scripts/*.py` 依赖）

## 命令
```bash
python3 scripts/gen_resources.py   # data/resources.yaml → content/*.md + front matter（含 sitemap lastmod）
python3 scripts/validate.py        # 构建前闸门
hugo --minify                      # 本地构建
bash deploy/deploy.sh              # 部署（唯一上线路径，rsync 到 ECS，不经 GitHub）
```

## 文件边界
| 文件 / 目录 | 规则 |
| --- | --- |
| `data/resources.yaml` | **唯一内容源**，手写 |
| `data/sources.yaml` | 候选源台账（`discover.py` 输入） |
| `content/resources/*.md`、`content/categories/*.md` | `gen_resources.py` 生成，**不入库** |
| `content/{resources,categories}/_index.md` | 手写 section 首页，**必须入库** |
| `inbox/candidates.json` | `discover.py` 产物，不入库 |
| `public/` | 构建产物，不入库 |

## 铁律（违反 = 事故）
1. **部署只走 `deploy/deploy.sh`，不经 GitHub；先上线再 push**（push 到 main 才触发 CI，Actions 延迟 2~3h）。
2. **不做核验状态机制**（`verify_status` 已删，勿再提）；资源失效直接删条目。
3. **只收官方原生免费资源**，批量扩充必须人工 filter。
4. **来源标注**：remark 不引公众号/自媒体作「核实」出处；统一 `official_url` / `rule_url` + `source_id`；额度一律标「以官网为准」。
5. **元信息唯一出口 = `layouts/partials/seo.html` + `partials/schema.html`**，别在 baseof 硬写 description。
6. **sitemap lastmod 由 `gen_resources.py` 写进 front matter**；禁 `now()`，别开 `enableGitInfo`（content 在 .gitignore，反而把 `.Date` 清零）。
7. **`content/{resources,categories}/_index.md` 必须入库**（.gitignore 用 `/content/*` + `!_index.md`）；prune 的 keep 集合要含它们，否则 CI 侧这两个页标题退化成英文目录名。
8. **首页不加载 AdSense**（`homePageAds=false`）：移动 UA 会被插 12 个广告位、首卡推到 797px；详情 / 分类页照常。
9. **stats 数字构建期静态渲染**（移动端 CLS 主因）。首卡基线 369px（改前 1288px），别回退成客户端 JS 渲染。

## 扩充流程
`data/sources.yaml` → `scripts/discover.py`（产出 `inbox/candidates.json`）→ 人工写 `inbox/<批次>.yaml` → `scripts/ingest.py` 合入 `data/resources.yaml`。

## 图标
`static/icons/<slug>.png`，缺图回退首字母色块。
