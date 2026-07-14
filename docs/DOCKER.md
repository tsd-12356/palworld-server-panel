# Docker Compose 部署

Docker Compose 是推荐部署方式。它会启动两个容器：

- `palworld`：安装并运行 Palworld Dedicated Server
- `panel`：运行 Web 管理面板，并通过 Docker socket 控制固定 Palworld 容器

## 前置要求

- Linux 服务器
- Docker Engine
- Docker Compose v2
- 至少 8 GB 内存，建议 16 GB+
- 足够磁盘空间，建议预留 20 GB+

## 快速开始

```bash
git clone https://github.com/tsd-12356/palworld-server-panel.git
cd palworld-server-panel
cp .env.example .env
```

编辑 `.env`：

```env
RCON_PASSWORD=your-strong-rcon-password
PANEL_SECRET_KEY=your-long-random-secret
```

启动：

```bash
docker compose up -d --build
```

查看启动日志：

```bash
docker compose logs -f palworld
```

访问面板：

```text
http://服务器IP:8080
```

## 端口

默认端口：

| 用途 | 端口 |
| --- | --- |
| 面板 | `8080/tcp` |
| Palworld 游戏 | `8211/udp` |
| Query | `27015/udp` |
| RCON | `25575/tcp` |

如果服务器有防火墙，请至少放行：

```bash
8211/udp
27015/udp
8080/tcp
```

`25575/tcp` 是 RCON 端口，建议只在可信网络内开放。

## 内部 REST 玩家列表

面板可以通过 Palworld REST API 获取准确的在线玩家列表。REST 默认仅在 Docker Compose 内部网络的 `palworld:8212` 上可访问，**不会**发布到宿主机或公网。

在 `.env` 中启用：

```env
PALWORLD_REST_ENABLED=true
PALWORLD_REST_PORT=8212
PALWORLD_REST_PATH=/v1/api/players
PALWORLD_REST_USERNAME=admin
# 留空时复用 RCON_PASSWORD
PALWORLD_REST_PASSWORD=
```

更改后重启游戏容器使 Palworld 读取新设置：

```bash
docker compose restart palworld
```

不要在 `ports:` 中添加 `8212:8212`。REST 使用 HTTP Basic Auth；如确有其他工具需要跨网络访问，请通过 TLS 反向代理和严格防火墙规则保护它。

## 数据持久化

默认目录：

```text
data/palworld
data/steamcmd
data/panel
```

删除容器不会删除这些数据。迁移服务器时，备份整个 `data/` 目录即可。

MOD 管理相关路径：

```text
data/palworld/Pal/Content/Paks/~mods  # 已启用的 PAK/SIG MOD
data/palworld/Pal/Content/Paks/Mods   # 官方 Info.json / Workshop-style MOD
data/panel/mod-library                # 禁用、导入记录、元数据、废纸篓
```

面板只负责上传、识别、移动、启用状态维护和重启流程，不保证每个第三方 MOD 都能在 Linux/Docker Palworld 服务端正常运行。安装 MOD 前建议先在“存档管理”里备份当前存档。

## 更新

容器启动时会运行 SteamCMD：

```bash
app_update 2394010 validate
```

你可以通过面板“更新管理”手动触发，也可以直接执行：

```bash
docker compose restart palworld
```

## 常用命令

```bash
docker compose ps
docker compose logs -f panel
docker compose logs -f palworld
docker compose restart palworld
docker compose down
```

彻底删除容器但保留数据：

```bash
docker compose down
docker compose up -d
```

彻底删除所有数据需要手动删除 `data/`，请谨慎：

```bash
rm -rf data/
```

## 安全提醒

Docker 模式会挂载：

```text
/var/run/docker.sock
```

面板代码只控制 `.env` 里配置的 `PALWORLD_CONTAINER_NAME`，但 Docker socket 本身权限很高。请只在自用、内网、Tailscale 或可信反代后部署。
