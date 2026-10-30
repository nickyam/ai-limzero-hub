#!/usr/bin/env bash
# ============================================================
# deploy.sh —— 把凌零集 ai.limzero.com 的 Hugo 产物同步到阿里云 ECS
#
# 用法：
#   本地构建 + 同步：      bash deploy/deploy.sh
#   仅同步（产物已构建）：  bash deploy/deploy.sh --sync-only
#
# 【为什么用 rsync 而不是 git clone】
#   站点目录只保留网站真正需要的静态文件（HTML/CSS/JS/图片/sitemap）。
#   仓库只作为「内容源」放在 ECS 的缓存目录里，源码与部署脚本不上线，
#   避免 README.md / scripts/ / .git 等开发文件暴露在公网上。
#
# 【目录约定（1Panel 静态网站）】
#   宿主机：/opt/1panel/apps/openresty/openresty/www/sites/ai.limzero.com/index
#   容器内：/www/sites/ai.limzero.com/index
#   注意子目录名是 index（1Panel 静态站点默认约定），不是默认的 html。
#   OpenResty 容器把宿主机 .../www 挂载为容器内 /www。
#
# 【前提】
#   1. ECS 上已通过 1Panel 创建「静态网站」：主域名 + 代号均为 ai.limzero.com
#   2. DNS 已解析：ai.limzero.com A → 服务器公网 IP（阿里云万网 DNS）
#   3. 证书已签发（80 端口被合规拦截，只能 HTTPS + DNS-01）：
#      宿主机 .../sites/ai.limzero.com/ssl/{fullchain.pem,privkey.pem}
#   4. 本机已装 hugo（extended）+ python3/pyyaml
# ============================================================
set -euo pipefail

DOMAIN="ai.limzero.com"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_aliyun}"
REMOTE_HOST="${REMOTE_HOST:-root@121.40.250.144}"

# 宿主机路径：OpenResty 容器 .../www ↔ 宿主机 .../www
DEPLOY_DIR="/opt/1panel/apps/openresty/openresty/www/sites/${DOMAIN}/index"
# 仓库在 ECS 上的缓存目录（内容源，不对外提供）
REPO_TMP="/root/.ai-hub-repo-cache"

# 本地仓库根目录（本脚本所在位置的上级）
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PUBLIC_DIR="${REPO_ROOT}/public"

log() { printf '\033[36m[deploy]\033[0m %s\n' "$*"; }
die() { printf '\033[31m[deploy] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# ---------- 1. 本地构建 ----------
if [ "${1:-}" != "--sync-only" ]; then
  log "校验数据（scripts/validate.py）..."
  python3 "${REPO_ROOT}/scripts/validate.py"

  log "生成资源页（scripts/gen_resources.py）..."
  python3 "${REPO_ROOT}/scripts/gen_resources.py"

  log "Hugo 构建（--cleanDestinationDir 清空目标目录，避免旧指纹产物累积）..."
  (cd "${REPO_ROOT}" && hugo --minify --cleanDestinationDir --baseURL "https://${DOMAIN}/")

  [ -f "${PUBLIC_DIR}/index.html" ] || die "构建产物缺失：${PUBLIC_DIR}/index.html"
  log "构建完成：$(find "${PUBLIC_DIR}" -name '*.html' | wc -l | tr -d ' ') 个 HTML"
fi

[ -f "${PUBLIC_DIR}/index.html" ] || die "未找到构建产物 ${PUBLIC_DIR}/index.html，请先构建（或去掉 --sync-only）"

# ---------- 2. rsync 同步 ----------
log "同步到 ${REMOTE_HOST}:${DEPLOY_DIR}"

# --delete-excluded 必须加：否则被 --exclude 排除的旧文件不会被删除，
# 开发文件/过期产物会残留在站点目录里。
ssh -i "${SSH_KEY}" -o StrictHostKeyChecking=no "${REMOTE_HOST}" \
  "mkdir -p '${DEPLOY_DIR}'"

rsync -az --delete \
  --delete-excluded \
  -e "ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no" \
  --exclude '.git/' \
  --exclude '.github/' \
  --exclude '.workbuddy/' \
  --exclude 'scripts/' \
  --exclude 'deploy/' \
  --exclude 'data/' \
  --exclude 'inbox/' \
  --exclude 'layouts/' \
  --exclude 'content/' \
  --exclude 'assets/' \
  --exclude 'static/' \
  --exclude 'nginx/' \
  --exclude 'README.md' \
  --exclude 'config.toml' \
  --exclude '*.py' \
  --exclude '*.yaml' \
  --exclude '*.yml' \
  "${PUBLIC_DIR}/" \
  "${REMOTE_HOST}:${DEPLOY_DIR}/"

# ---------- 3. 校验线上 ----------
log "校验线上首页..."
CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 \
  --resolve "${DOMAIN}:443:$(ssh -i "${SSH_KEY}" -o StrictHostKeyChecking=no "${REMOTE_HOST}" \
  'curl -sS --max-time 5 ifconfig.me' 2>/dev/null | tr -d '[:space:]')" \
  "https://${DOMAIN}/" 2>/dev/null || echo "000")

log "资源页数量（线上）：$(ssh -i "${SSH_KEY}" -o StrictHostKeyChecking=no "${REMOTE_HOST}" \
  "ls -1 '${DEPLOY_DIR}/resources' 2>/dev/null | wc -l | tr -d ' '")"

if [ "${CODE}" = "200" ]; then
  log "✅ https://${DOMAIN}/ 返回 200"
else
  log "⚠️  https://${DOMAIN}/ 返回 ${CODE}（DNS 未生效或证书未配置时会如此）"
fi
