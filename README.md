# Palworld Server Panel

一个面向 Palworld Dedicated Server 的现代 Web 管理面板。主打浅色毛玻璃 UI、Docker Compose 一键部署、存档管理、配置编辑、RCON、日志、机器状态和手动更新，适合个人服务器、朋友服和内网运维。

> 当前项目默认不带登录系统，请放在内网、Tailscale、ZeroTier 或可信反代后使用。

## 为什么选它

- **一键部署**：推荐 Docker Compose，保留 Ubuntu/Debian 原生 systemd 安装器。
- **面板好看**：浅色玻璃拟态、星尘粒子、鼠标光斑、卡片动效，比传统黑框面板更舒服。
- **功能够完整**：状态、在线玩家、日志、配置、RCON、存档、更新、审计、机器监控都在一个页面里。
- **存档管理强**：支持备份、上传 zip 导入、创建新世界、切换存档、删除存档。
- **配置更安心**：可视化编辑 `PalWorldSettings.ini`，保存前显示差异确认，保存并重启有步骤反馈。
- **运维可追踪**：操作记录会写入审计日志，方便回看谁做了什么。
- **开源友好**：不依赖 npm/Vite/Tailwind，Flask + 原生 CSS/JS，容易二次开发。

## 界面预览

建议在发布页放 3-5 张干净截图，效果会比纯文字强很多：

- 仪表盘：展示服务器状态、机器状态、趋势图和玻璃 UI。
- 存档管理：展示上传导入、当前存档、切换按钮。
- 配置页面：展示倍率、玩法、网络等可视化配置。
- 日志 / RCON：展示浅色终端和命令反馈。
- 操作记录：展示审计列表。

截图建议放在：

```text
docs/screenshots/dashboard.png
docs/screenshots/saves.png
docs/screenshots/config.png
docs/screenshots/rcon.png
docs/screenshots/audit.png
```

有截图后，可以在这里加入：

```markdown
![Dashboard](docs/screenshots/dashboard.png)
```

## 核心功能

| 分类 | 功能 |
| --- | --- |
| 服务器控制 | 启动、停止、重启、运行状态、在线玩家 |
| 配置管理 | 可视化修改 `PalWorldSettings.ini`、差异确认、保存并重启 |
| 存档管理 | 备份、上传 zip 导入、创建新档、切换、删除 |
| 日志与 RCON | 实时日志、RCON 控制台、命令结果分层展示 |
| 机器状态 | CPU、内存、磁盘、负载、运行时间、迷你趋势图 |
| 更新管理 | 手动检测更新、手动触发后台更新 |
| 操作审计 | 记录启动/停止/重启、配置保存、RCON、存档操作 |
| 部署方式 | Docker Compose 推荐部署，systemd 原生部署保留 |

## 推荐部署：Docker Compose

适合大多数开源用户。

```bash
git clone https://github.com/tsd-12356/palworld-server-panel.git
cd palworld-server-panel
cp .env.example .env
```

编辑 `.env`，至少修改：

```env
RCON_PASSWORD=change-this-password
PANEL_SECRET_KEY=change-this-secret
```

启动：

```bash
docker compose up -d --build
```

访问：

```text
http://服务器IP:8080
```

首次启动时，`palworld` 容器会自动安装 SteamCMD 和 Palworld Dedicated Server，耗时取决于网络和磁盘速度。

更多说明见 [Docker 部署文档](docs/DOCKER.md)。

## 原生 Ubuntu/Debian 部署

适合直接部署在 VPS 上，使用 systemd 管理服务。

```bash
git clone https://github.com/tsd-12356/palworld-server-panel.git
cd palworld-server-panel
sudo bash install.sh
```

更多说明见 [systemd 部署文档](docs/SYSTEMD.md)。

## 数据目录

Docker 模式默认使用：

```text
data/palworld  # Palworld 服务端、配置、存档
data/steamcmd  # SteamCMD
data/panel     # 面板日志、审计、存档槽、状态文件
```

原生模式默认使用：

```text
/home/demo/palworld
/home/demo/steamcmd
/home/demo/palworld-panel
/etc/palworld-panel.env
```

## 常用命令

Docker：

```bash
docker compose ps
docker compose logs -f palworld
docker compose logs -f panel
docker compose restart palworld
docker compose down
```

原生 systemd：

```bash
systemctl status palworld-panel.service
systemctl status palworld.service
journalctl -u palworld-panel.service -f
journalctl -u palworld.service -f
```

## 安全说明

- 面板不自带登录，请只放在可信网络内。
- Docker 模式会挂载 `/var/run/docker.sock`，面板只控制 `.env` 中指定的 Palworld 容器。
- 原生模式使用受限 sudoers，只允许固定的 systemd、journalctl 和必要 chown 操作。
- 不要把 `.env`、`/etc/palworld-panel.env`、存档目录和审计日志提交到公开仓库。

更多见 [安全说明](docs/SECURITY.md)。

## 文档

- [Docker 部署](docs/DOCKER.md)
- [Ubuntu/Debian 原生部署](docs/SYSTEMD.md)
- [常见问题](docs/FAQ.md)
- [安全说明](docs/SECURITY.md)
- [发布到 GitHub](docs/PUBLISHING.md)

## 当前状态

- systemd 模式已在真实服务器验证。
- Docker 模式已完成配置和后端控制逻辑，建议先标注为 beta，并在干净 Docker 主机上跑一次完整首启测试。

## License

MIT
