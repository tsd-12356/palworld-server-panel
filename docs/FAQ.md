# 常见问题

## 这个面板有登录吗？

没有。它默认用于自用场景，请放在内网、Tailscale、ZeroTier 或可信反代后面。

## Docker 和 systemd 应该选哪个？

推荐新用户使用 Docker Compose：

```bash
cp .env.example .env
docker compose up -d --build
```

如果你已经有一台 Ubuntu/Debian VPS，并且想用 systemd 管理服务，可以使用：

```bash
sudo bash install.sh
```

## Docker 首次启动很慢正常吗？

正常。首次启动会下载 SteamCMD 和 Palworld Dedicated Server，取决于网络、磁盘和 Steam 下载速度。

## 面板能发放物资吗？

面板提供 RCON 控制台。Palworld Dedicated Server 的 RCON 命令能力取决于游戏本身支持的命令。你可以在 RCON 页面执行 `Info`、`ShowPlayers`、`Broadcast 消息` 等命令。

## 修改配置后什么时候生效？

大多数 Palworld 配置需要重启服务端才会生效。面板提供“保存并重启”按钮，会显示步骤式进度。

## 存档上传支持什么格式？

上传功能支持 `.zip`。压缩包里需要包含一个 Palworld 世界存档，通常能找到 `Level.sav`。

## Docker 模式为什么需要 Docker socket？

面板需要启动、停止、重启 Palworld 容器并读取容器日志，所以需要访问：

```text
/var/run/docker.sock
```

面板代码只会控制固定容器名，不提供任意 Docker 命令接口。

## 自动更新会自己跑吗？

默认不会。项目当前以手动检测和手动触发为主，避免自用服务器在玩家在线时突然更新。

## 可以公网暴露吗？

不建议直接公网暴露。推荐：

- Tailscale
- ZeroTier
- VPN
- 内网访问
- 带认证的反向代理
