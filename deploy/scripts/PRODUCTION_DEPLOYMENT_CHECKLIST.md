# ProTech NAS — 生產環境部署檢查清單

## 腳本對照表

| 腳本 | 功能 | 部署階段 | 必要順序 |
|------|------|----------|----------|
| `install.sh` | 安裝系統依賴 (apt, docker, nodejs) | 系統初始化 | 1 |
| `setup_deps.sh` | 安裝專案 Python/Node 依賴 | 系統初始化 | 2 |
| `deploy.sh` | 完整部署流程 (frontend+backend+nginx+sudoers) | 部署 | 3 |
| `ota-update.sh` | OTA 遠端更新 (check/apply/rollback) | 運維 | 常驻 |
| `sudoers-protech-nas` | NOPASSWD 特權規則 (非 shell 腳本) | 部署階段5 |

## 支援檔案

| 檔案 | 功能 |
|------|------|
| `protech-nas.service` | systemd unit (User/Group/WorkDir/ExecStart 需置換) |
| `protech-nas-nginx.conf` | Nginx site config (proxy + SPA fallback + static cache) |

---

## 部署前檢查 (Pre-flight)

### 1. 系統環境

```bash
# 確認 OS 版本
lsb_release -a  # 支援 Debian 12 / Ubuntu Server 22.04+

# 確認磁碟數量 (RAID 1 建議)
lsblk -d -n -o NAME,TYPE | awk '$2=="disk"' | wc -l
```

### 2. 網路與憑證

```bash
# 確認主機 IP
hostname -I | awk '{print $1}'

# 確認 DNS / 閘道可達
ping -c 1 8.8.8.8

# 確認 curl / jq 可用 (OTA 更新需要)
curl --version | head -1
jq --version
```

### 3. 磁碟掛載點

```bash
# 確認 /var/www 目錄存在且可寫
ls -ld /var/www
df -h /var/www
```

---

## 階段一：系統依賴 (install.sh)

### 執行腳本

```bash
cd /path/to/protech-nas
sudo bash scripts/install.sh
```

### 驗證項目

| # | 驗證指令 | 預期結果 |
|---|----------|----------|
| 1 | `node --version` | `v20.x.x` |
| 2 | `python3 --version` | `Python 3.x.x` |
| 3 | `docker --version` | `Docker version 20.x.x` |
| 4 | `nginx -v` | `nginx version: nginx/x.x.x` |
| 5 | `systemctl is-enabled docker` | `enabled` |
| 6 | `systemctl is-enabled smbd` | `enabled` |
| 7 | `systemctl is-enabled nfs-kernel-server` | `enabled` |
| 8 | `groups $(whoami)` | 包含 `docker` 群組 |

### 注意
- 新增 docker 群組後需重新登入才能生效
- Node.js 透過 NodeSource 安裝，系統 nodejs 套件衝突需先移除

---

## 階段二：專案依賴 (setup_deps.sh)

### 執行腳本

```bash
cd /path/to/protech-nas
bash scripts/setup_deps.sh
```

### 驗證項目

| # | 驗證指令 | 預期結果 |
|---|----------|----------|
| 1 | `ls backend/.venv/bin/uvicorn` | 檔案存在 |
| 2 | `backend/.venv/bin/python --version` | `Python 3.x.x` |
| 3 | `ls frontend/node_modules/.bin/vite` | 檔案存在 |
| 4 | `ls frontend/dist/index.html` | 檔案存在 |
| 5 | `pip show fastapi` (在 venv 中) | 已安裝 |
| 6 | `npm list --depth=0` (在 frontend/) | 已安裝 |

### 注意
- `setup_deps.sh` 會 build frontend，dirty git status 需先 commit
- 生產環境建議 `npm run build` 前確認 `NODE_ENV=production`

---

## 階段三：環境變數 (.env)

### 必要設定

```bash
# 從範例建立 (僅第一次)
cp backend/.env.example backend/.env
```

`backend/.env` 需確認以下項目：

| 項目 | 說明 | 安全要求 |
|------|------|----------|
| `SECRET_KEY` | FastAPI session/JWT 金鑰 | **生產環境必須更換** (至少 32 字隨機) |
| `DATABASE_URL` | PostgreSQL/SQLite 連線字串 | 確認路徑/權限 |
| `ALLOWED_HOSTS` | CORS 白名單 | 不可為 `*` |
| `OTA_SERVER_URL` | OTA 更新伺服器 | 可留空 (預設 `http://localhost:8060`) |

### 驗證

```bash
grep -v '^#' backend/.env | grep -E '\w+\s*=' | cut -d= -f1 | sort
# 確認上述項目皆已設定非空白值
```

---

## 階段四：sudoers 設定 (sudoers-protech-nas)

### 執行

```bash
SERVICE_USER=你的實際使用者
sed "s/nas/$SERVICE_USER/g" scripts/sudoers-protech-nas | sudo tee /etc/sudoers.d/protech-nas > /dev/null
sudo chmod 0440 /etc/sudoers.d/protech-nas
```

### 驗證

```bash
# 語法檢查 (無輸出表示成功)
sudo visudo -c -f /etc/sudoers.d/protech-nas

# 確認檔案權限
ls -la /etc/sudoers.d/protech-nas
# 預期: -r--r----- root root (440)

# 確認內容中的使用者已置換
grep "ALL=" /etc/sudoers.d/protech-nas | head -3
# 預期: <你的使用者> ALL=(ALL) NOPASSWD: ...
```

### 安全備註

- 此 sudoers 賦予 NOPASSWD 權限給多個系統指令，適用於隔離的 NAS 內網環境
- 若暴露在公網，需重新評估最小權限原則

---

## 階段五：部署 (deploy.sh)

### 執行前確認

```bash
# 確認 SERVICE_USER 環境變數
echo $NAS_USER  # 或 echo $(whoami)

# 確認所有前置條件
ls backend/.venv/bin/uvicorn    # venv 存在
ls backend/.env                 # 環境變數已設定
command -v nginx                # nginx 已安裝
```

### 執行

```bash
sudo NAS_USER=<實際使用者> bash scripts/deploy.sh
```

### 驗證項目

| # | 驗證指令 | 預期結果 |
|---|----------|----------|
| 1 | `systemctl is-enabled protech-nas` | `enabled` |
| 2 | `systemctl status protech-nas` | `active (running)` |
| 3 | `curl -s http://localhost:8000/api/health` | 200 OK |
| 4 | `curl -s http://localhost/api/docs` | OpenAPI docs HTML |
| 5 | `ls /var/www/protech-nas/index.html` | 檔案存在 |
| 6 | `nginx -t` | `syntax is ok` |
| 7 | `systemctl is-enabled nginx` | `enabled` |
| 8 | `curl -s -o /dev/null -w '%{http_code}' http://localhost/` | `200` |
| 9 | `sudo -l -U $USER` | 列出 NOPASSWD sudo 權限 |
| 10 | `ls /etc/sudoers.d/protech-nas` | 檔案存在 |

### 常見錯誤

| 錯誤訊息 | 原因 | 解法 |
|----------|------|------|
| `Backend venv not found` | setup_deps.sh 未執行 | 先執行 scripts/setup_deps.sh |
| `Backend .env not found` | .env 未建立 | cp .env.example .env 並編輯 |
| `Nginx not installed` | nginx 未安裝 | sudo apt install nginx |
| `Nginx config test failed` | nginx.conf 語法錯誤 | `nginx -t` 查看詳細錯誤 |

### RAID 1 HA 提示

若偵測到多顆磁碟但未設定 RAID，deploy.sh 會顯示提示：
```
建議執行：sudo bash scripts/setup-raid1-ha.sh
```

---

## 階段六：OTA 更新機制 (ota-update.sh)

### 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `OTA_SERVER_URL` | `http://localhost:8060` | OTA API 伺服器 |
| `OTA_DEVICE_ID` | `1` | 設備 ID |
| `OTA_DEPLOY_MODE` | `systemd` | 部署模式 (`systemd` 或 `docker`) |
| `OTA_APP_DIR` | `/opt/protech-nas` | 應用程式目錄 |

### 操作模式

```bash
# 僅檢查更新 (不做變更)
./scripts/ota-update.sh --check-only

# 執行更新 (自動含 rollback)
sudo ./scripts/ota-update.sh
```

### 驗證項目

| # | 驗證指令 | 預期結果 |
|---|----------|----------|
| 1 | `cat /tmp/protech-nas-update.lock` (更新前) | 無鎖檔或 stale lock |
| 2 | `ls /var/log/protech-nas-update.log` | 日誌檔存在 |
| 3 | `./scripts/ota-update.sh --check-only` | `System is up to date.` 或顯示版本資訊 |
| 4 | `curl -s http://localhost:8000/api/health` | OTA 更新後健康檢查仍為 200 |

### Rollback 驗證 (破壞性測試，慎用)

```bash
# 人為觸發失敗並觀察 rollback
OTA_DEPLOY_MODE=systemd bash -c '
  # 模擬一個錯誤的 TARGET_HASH
  git checkout --hard HEAD~1
  ./scripts/ota-update.sh
'
```

---

## 部署後驗證 (Post-deployment)

### 完整健康檢查

```bash
# Backend API
curl -s http://localhost:8000/api/health | jq .

# Frontend
curl -s -o /dev/null -w '%{http_code}' http://localhost/

# Nginx proxy
curl -s -o /dev/null -w '%{http_code}' http://localhost/api/

# Systemd service
systemctl status protech-nas --no-pager

# 所有 services
systemctl list-units --type=service --state=running | grep -E 'protech|nginx|smbd|docker'
```

### 安全性驗證

```bash
# 確認 SECRET_KEY 已更換 (不是預設值)
grep SECRET_KEY backend/.env

# 確認預設 admin 密碼已更換 (非 admin/admin123)
# 透過 API 驗證或檢查資料庫

# 確認 /var/www/protech-nas 權限為 www-data
ls -la /var/www/protech-nas/ | head -3

# 確認 .env 權限為 600
ls -la backend/.env
```

---

## 快速重部署腳本 (已驗證流程)

```bash
#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Full Redeploy ==="
cd "$PROJECT_DIR"

# 1. Backend
cd backend
source .venv/bin/activate
pip install -r requirements.txt -q
deactivate

# 2. Frontend
cd ../frontend
npm install -q
npm run build

# 3. Restart backend
sudo systemctl restart protech-nas

# 4. Deploy frontend
sudo rm -rf /var/www/protech-nas/*
sudo cp -r dist/* /var/www/protech-nas/
sudo chown -R www-data:www-data /var/www/protech-nas

# 5. Reload nginx
sudo systemctl reload nginx

# 6. Health check
sleep 3
curl -sf http://localhost:8000/api/health && echo " OK" || echo " FAILED"
```

---

## 腳本審查摘要

### deploy.sh
- 參照 `protech-nas.service` 和 `protech-nas-nginx.conf` 部署
- sed 置換 User/Group/路徑變數
- 6 步驟：pre-flight → frontend build → frontend deploy → systemd → nginx → sudoers
- **建議**：部署前檢查 `SECRET_KEY` 是否為預設值

### install.sh
- 支援 Debian 12 / Ubuntu 22.04+
- 包含 samba, nfs, docker, nodejs, smartmontools, mdadm
- 自動啟用 docker/smb/nfs 服務
- **注意**：需重新登入才會生效 docker 群組

### setup_deps.sh
- 3 步驟：Python venv + npm install + npm build
- `pip install -r requirements.txt` 獨立執行，deploy.sh 會再次執行
- **建議**：dirty git status 時跳過 build 或 warning

### ota-update.sh
- 使用 `set -euo pipefail` 嚴格模式
- 含 lock file 防止並發執行
- 完整 rollback 機制 (git checkout + restore venv + restart)
- 支援 systemd/docker 兩種部署模式
- 前端更新含 SHA256 checksum 驗證
- **建議**：OTA 伺服器需支援 `/api/ota/nas/check` 和 `/api/ota/nas/report` 端點

### sudoers-protech-nas
- 70 行程式碼，涵蓋 storage/system/network/shares/backup/user management
- 每個指令為完整路徑，不可置換
- `nas` 使用者名稱需由 deploy.sh 動態置換
- **安全備註**：廣泛的 NOPASSWD 權限，僅適用於隔離內網

---

*最後更新：2026-08-19*
