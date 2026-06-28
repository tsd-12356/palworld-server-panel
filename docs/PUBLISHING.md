# 发布到 GitHub

## 发布前检查

确认不要提交敏感文件：

```bash
git status --short
```

不应出现：

```text
.env
data/
save-slots/
config-backups/
*.log
```

语法检查：

```bash
python3 -m py_compile app.py panel_install.py panel_update.py
bash -n install.sh docker/palworld-entrypoint.sh
docker compose --env-file .env.example config
```

如果当前机器没装 Docker，可以先跳过 Docker 真机验证，但 README 建议标注 Docker 部署为 beta。

## 首次发布

```bash
git init
git add .
git commit -m "Initial release"
git branch -M main
git remote add origin https://github.com/<your-name>/<repo-name>.git
git push -u origin main
```

## 推荐仓库设置

- 仓库名：`palworld-panel`
- 描述：`A lightweight Palworld dedicated server panel with Docker Compose and systemd deployment`
- Topics：
  - `palworld`
  - `palworld-server`
  - `docker-compose`
  - `flask`
  - `rcon`
  - `game-server`

## 发布说明建议

首个版本建议标记为：

```text
v0.1.0-beta
```

Release note：

```markdown
## v0.1.0-beta

Initial public beta release.

- Docker Compose deployment
- Ubuntu/Debian systemd installer
- Server status, logs, RCON and config editor
- Save slot backup/import/switch management
- Manual update check and update trigger
- Audit trail and system overview

Known note:
- Docker mode should be tested on your target host before production use.
```

## Docker 真机验收

```bash
cp .env.example .env
sed -i 's/change-me-rcon-password/your-password/' .env
sed -i 's/change-me-panel-secret-key/your-secret/' .env
docker compose up -d --build
docker compose logs -f palworld
```

接口验证：

```bash
curl http://127.0.0.1:8080/api/status
curl http://127.0.0.1:8080/api/install/status
curl http://127.0.0.1:8080/api/update/status
```
