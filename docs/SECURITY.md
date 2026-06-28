# 安全说明

## 默认安全模型

本项目默认面向自用、内网和可信网络环境，不内置登录系统。

推荐部署在：

- Tailscale
- ZeroTier
- VPN
- 内网
- 带认证的反向代理后面

## 不要公开提交的文件

不要提交：

```text
.env
/etc/palworld-panel.env
data/
save-slots/
config-backups/
*.log
```

这些文件可能包含：

- RCON 密码
- 面板密钥
- 存档
- 审计日志
- 服务器路径信息

## Docker 模式风险

Docker 模式需要挂载：

```text
/var/run/docker.sock
```

Docker socket 权限很高。面板只控制 `.env` 中指定的 Palworld 容器，但如果你把面板暴露到不可信网络，仍然有风险。

## systemd 模式权限

原生安装器会创建受限 sudoers，只允许固定命令：

- 启动、停止、重启 Palworld 服务
- 查看 Palworld 服务状态
- 查看 Palworld journal 日志
- 修复 Palworld 存档和配置目录权限
- 启动固定的安装/更新 systemd oneshot

它不会给面板通用 root shell 权限。

## RCON

请使用强密码：

```env
RCON_PASSWORD=your-long-random-password
```

不要把 RCON 端口直接暴露到公网。

## 建议

- 只在可信网络访问面板
- 定期备份 `data/` 或 `/home/<user>/palworld`
- 更新前先备份存档
- 发布仓库前检查 `.env` 和日志没有被提交
