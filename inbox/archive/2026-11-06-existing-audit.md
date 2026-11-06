# 存量资源时效复核报告（2026-11-06）

范围：`data/resources.yaml` 中除今日新增 2 条外的 **159 条存量条目**。
原则：只验证、不擅自删条目；第三方/自媒体只作线索，结论一律引用官方页。
本轮不做主库改动，改动待用户拍板后统一执行。

---

## 一、三层复核方法

| 层 | 做法 | 结果 |
|---|---|---|
| 链接健康 | `check_urls.py --timeout 15 --workers 6` 全量 322 个 official_url / rule_url | **失效 0**；21 个「需人工确认」均为 307/403/405/500/超时 WAF 误报，与 11-05 的 22 个基本重合，无新增异常 |
| 数据一致性 | Python 扫描字段完整性、free_type 分布、时效性措辞 | 161 条中 `need_credit_card`/`remark`/`validity`/`tags` 全齐；`source_id` 缺 25 条（历史条目，非致命）；`added_on` 缺 159 条（设计如此，老条目不回填） |
| 政策时效 | 剔除「以官网为准」「到期」「暂停」等正常备注噪声后，11 条真高风险 + 主定位「大模型API」41 条做官方核实 | **发现 4 处需处理**，详见下节 |

⚠️ 复核暴露 `check_urls.py` 的一个盲点：`None`（连接失败/超时）被归入「需人工确认」而非「失效」。Kluster AI 两个链接正是这类，实际已不可达。以后「需人工确认」清单应逐条看，不能一律当误报。

---

## 二、需要处理的 4 处（均有官方出处）

### ① `cerebras-cloud` Cerebras Cloud —— 字段错误最严重，必须改

官方两处一致（定价页 `https://www.cerebras.ai/pricing`、限速文档 `https://inference-docs.cerebras.ai/support/rate-limits`）：

> "Add a valid payment method to receive a one-time $5 promotional credit."
> "New accounts receive **$5 in free credits** after adding a verified payment method. **These credits expire 30 days** after they're granted... If you skip adding a payment method at sign-up, Playground and API access remain inactive until you do."
> "Cerebras doesn't currently offer a no-cost tier that renews automatically or a per-model always-free allowance."
> "API and Playground access stop on the Free Trial tier until you purchase credits."

`Free Trial` 表格里的 `TPD 1M` 是**速率上限**，不是每天重置的免费额度；官方还写明限流用 token bucket 连续补充、不按固定间隔重置。

| 主库现值 | 官方实情 |
|---|---|
| `free_type: 每日重置` | 新用户一次性（$5 赠金） |
| `need_credit_card: 否` | **需添加经验证的有效支付方式**（官方措辞 `payment method`，非明确信用卡） |
| `validity: 长期（免费档）` | 激活后 30 天过期，用完/过期即暂停 API |
| `quota: 每日约 100 万 tokens` / `remark: 无需信用卡` | 误导；100 万是 TPD 速率上限，不是免费额度 |

👉 这条正好踩中本站刚上线的「是否需要信用卡」标记，属硬错误，建议优先修正。

### ② `kluster-ai` Kluster AI —— 服务已终止，需拍板删/留

- 实测：`https://kluster.ai/` → 301 到 `www.kluster.ai`（空壳/告别页）；`docs.kluster.ai/get-started/quickstart/` → 301 也跳到主站（文档已下线）；`api.kluster.ai/v1` → **HTTP 000，连接失败**。
- 官方/一手线索：MITO AI 官方 LinkedIn 公告「MITO AI has acquired kluster.ai」；多处记录 `kluster.ai services were sunset on June 9, 2026`；free-llm.com 已标 `Discontinued`。
- 主库仍写「注册赠送约 $5 试用额度、免信用卡、赠金用完为止」，已不可能兑现。

👉 按项目原铁律「资源失效直接删条目」应删；但 2026-11-01 用户为 Mistral 拍板过「不删除、做好说明」的先例，此处交用户决定。

### ③ `huggingface-inference` Hugging Face Inference —— 免费月额度已取消，需拍板

官方定价文档 `https://huggingface.co/docs/inference-providers/pricing`：

> "PRO users and Team or Enterprise organizations receive monthly credits to use with Inference Providers. **Free users can use Inference Providers by purchasing credits, or by upgrading to PRO**"
> 表格：`| Free Users | None | - | yes (credits purchase required) |` / `| PRO Users | $2.00 | ... |`

主库写「免费账号每月约 $0.10 等值 credits / 每月重置 / 免信用卡」，与官方当前口径不符。第三方对 $0.10 ↔ None 反复改口（10-17 说 None、11-01 说改回 $0.10），**以官方当前页为准：None**。
注意：`huggingface-spaces`（Spaces / ZeroGPU）是另一条条目，不受影响。

👉 该条目的核心价值主张是「免费推理额度」，现已不成立。是删、还是保留并改写成「需购 credits / PRO $2/月」的说明，交用户决定。

### ④ `google-gemini` Google AI Studio（Gemini）—— 条目有效，但额度数字过时

官方定价页 `https://ai.google.dev/gemini-api/docs/pricing`：

> "Start building free of charge with generous limits..."
> "**Google AI Studio usage is free of charge in all available regions.**"

**免费层仍在、无需信用卡**，这条确认无误。但官方模型清单已迭代到 Gemini 3.8 Flash / 3.5 Flash-Lite / Gemini 4 Argon（Argon 明确 `not available on the Free tier`），而主库 `quota` 仍写死「2.5 Flash 30 RPM / 1440 RPD、2.5 Flash-Lite 10 RPM / 20 RPD、Gemini 3 Flash 5 RPM / 20 RPD」，属旧口径。
（官方 `rate-limits` 页抓取时被 Google OAuth 重定向拦截，未能逐字核对最新 RPM/RPD。）

👉 建议：保留条目，把写死的数字降级为「免费层仍在、各模型限速不同、以官网 rate-limits 页为准」，同步更新 `model_name`，不编造新数字。

---

## 三、确认无误 / 无需改动

- `gemini-code-assist`：官方 `codeassist.google` 与 `cloud.google.com/gemini/docs/quotas` 均写「6,000 requests/day、no credit card needed」，与主库「每日约 6,000 次」一致 ✔
- `mistral-platform`：11-01 已按用户拍板「保留 + ⚠️ 警示」，本轮不重复处理 ✔
- `sensenova-token-plan` / `longcat-api`：今日刚逐条官方核实并入库 ✔
- `scnet-ai`（限时免费 90 天）、`stepfun-platform`（Step Plan 限时 15 天）、`intern-tokenplan`（测试期）、`together-ai`（活动期 $25）：站内**已如实标注**「限时/活动期/随时可能」，无需改，但列入下次优先复核。
- `modelscope`「GPU 送 36 小时」、`google-gemini` 的 `beta` 字样、`tencent-ocr`「账号 1 年不用会暂停发放」、Supabase/Neon/MongoDB Atlas 的休眠暂停规则：都是正常备注，非失效信号。
- 主库**未收录**蚂蚁百灵 / Qwen Code / Gemini CLI / iFlow 心流，所以近期「蚂蚁百灵 10-31 停发每日 50 万 tokens」「Qwen Code OAuth 免费层 4-15 停」「Gemini CLI 免费层 6-18 调整」这些变动不影响本站。

---

## 四、次要发现（不阻塞）

- `source_id` 缺 25 条（多为最早手工录入的国内平台），台账溯源不完整，可择机补齐。
- `check_urls.py` 把 `None`/超时归为「需人工确认」，应单独列出，否则真正的死站会被淹没在 21 条 WAF 误报里。
- 21 条 WAF 误报中 `Scaleway Generative APIs`、`Leonardo.AI`、`Pexels API`、`Ideogram` 的 official_url + rule_url **两条同时 403**，建议下次用浏览器实点一次确认（本轮直连脚本被 WAF 拦，无法判定）。

---

核实出处均为官方页；搜索中出现的公众号 / 自媒体 / 聚合站内容仅用于发现线索，未作为任何结论依据。

---

## 五、处理结果（用户拍板后执行，2026-11-06）

用户先选「全部修正 + 两条保留加说明」，随后单独改口：**`kluster-ai` 删掉**。最终执行：

| 条目 | 最终处理 |
|---|---|
| `cerebras-cloud` | 修正 4 个字段：`free_type` → 新用户一次性、`need_credit_card` → **是**、`validity` → 激活后 30 天过期、`quota`/`remark` 按官方原文重写（TPD 1M 是速率上限而非每日免费额度）；tags 去掉「每日免费」，改「需绑卡 / 一次性额度」 |
| `google-gemini` | 条目保留；删除写死的 2.5 Flash 30RPM/1440RPD 等旧数字，改为「免费层仍在、各模型限速不同、以官网 rate-limits 页为准」；`model_name` 更新到 3.8 Flash / 3.5 Flash-Lite 等；remark 补记复核结论 |
| `huggingface-inference` | **保留 + ⚠️ 醒目说明**（沿用 Mistral 特例做法，不动 `free_type` 白名单）：`quota`/`validity`/`remark` 如实写明官方 `Free Users: None`、需购 credits 或升 PRO；tags 去掉「每月免费 / 额度很小」，改「需购额度 / 政策已变更」 |
| `kluster-ai` | **整条删除**（用户 09:23 改口，按原铁律「资源失效直接删条目」执行），主库 161 → **160 条**；`gen_resources.py` 自动清理孤儿详情页 |

校验：`validate.py` 160 条 / ERROR 0（仅 HF 同域已知 WARN）；`need_credit_card` 分布变为 否 140 / 是 3 / 以官网为准 17。
部署：`deploy/deploy.sh` 直传 ECS，线上资源页 163 → 162、首页 200；Kluster 详情页随 rsync --delete-excluded 一并清除。

**未处理（报告留存）**：`check_urls.py` 把 `None`/超时归入「需人工确认」的盲点；`source_id` 缺 25 条；Scaleway / Leonardo.AI / Pexels / Ideogram 双链 403 需浏览器实点。均不阻塞，留待后续。
