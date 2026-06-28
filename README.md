# Palworld Panel

一个轻量、浅色毛玻璃风格的 Palworld Dedicated Server 管理面板。支持 Docker Compose 一键部署，也保留 Ubuntu/Debian 原生 systemd 安装器。

> 当前项目默认不带登录系统，适合放在内网、Tailscale、ZeroTier 或可信反代后自用。

## 功能

- 服务器状态、在线玩家、实时日志
- 启动、停止、重启 Palworld 服务
- 可视化修改 `PalWorldSettings.ini`
- RCON 控制台
- 存档备份、上传导入、切换、删除
- 操作审计记录
- 机器状态概览和趋势图
- 手动检测/触发更新
- Docker Compose 和 systemd 双部署模式

## 推荐部署：Docker Compose

适合大多数开源用户。

```bash
git clone <你的仓库地址> palworld-panel
cd palworld-panel
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

首次启动时，`palworld` 容器会自动安装 SteamCMD 和 Palworld Dedicated Server，时间取决于网络和磁盘速度。

更多说明见 [Docker 部署文档](docs/DOCKER.md)。

## 原生 Ubuntu/Debian 部署

适合直接部署在 VPS 上，使用 systemd 管理服务。

```bash
git clone <你的仓库地址> palworld-panel
cd palworld-panel
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

## License

MIT

## 状态

这是一个自用面板开源化版本。systemd 模式已在真实服务器验证；Docker 模式已完成配置和后端控制逻辑，建议发布后先标注为 beta，并在干净 Docker 主机上跑一次完整首启测试。
