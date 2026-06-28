# MOD 管理（实验性）

Palworld Server Panel 2.0 提供实验性的 MOD 管理能力：上传、识别、启用、禁用、移入废纸篓，并通过“应用并重启”让变更生效。

> 重要提示：MOD 管理不是稳定保证功能。Palworld 服务端 MOD 的兼容性会受到游戏版本、服务端系统、Docker/systemd 后端、MOD 类型和 MOD 作者实现影响。请按 MOD 作者说明自行调试，安装前务必备份存档。

## 支持范围

| 类型 | 面板支持 | 说明 |
| --- | --- | --- |
| `.pak` | 实验支持 | 上传后放入 `Pal/Content/Paks/~mods`，启用/禁用通过移动文件完成。 |
| `.sig` | 实验支持 | 作为 PAK 的签名文件管理，通常应和同名 `.pak` 配套使用。 |
| `.zip` | 实验支持 | 安全解压后识别其中的 `.pak/.sig` 或官方 `Info.json` 包。 |
| 官方 `Info.json` 包 | 受控导入 | 导入到 `Pal/Content/Paks/Mods/Workshop/<mod_id>`，启用时写入 `PalModSettings.ini`。 |
| UE4SS/Lua | 暂不自动安装 | Linux/Docker 兼容性和崩服风险较高，2.0 只提示，不自动部署。 |

官方文档曾标注服务端 MOD 主要面向 Windows dedicated server。Linux/systemd 和 Docker 后端可以导入官方 `Info.json` 包，但面板会在启用前显示风险确认；是否真的生效，需要你自行测试。

## 推荐流程

1. 先在 `存档管理` 里备份当前存档。
2. 打开 `MOD 管理`。
3. 点击 `上传 MOD`，选择 `.pak`、`.sig` 或 `.zip`。
4. 填写 MOD 名称和备注，建议写上来源、版本、是否需要客户端安装。
5. 上传完成后，只启用一个 MOD 进行测试。
6. 点击 `应用并重启`，面板会尝试备份当前存档并重启 Palworld。
7. 进入 `实时日志` 和游戏客户端确认服务器是否正常启动、能否进服。
8. 如果异常，回到 `MOD 管理` 禁用最近添加的 MOD，再次应用并重启。

## 文件位置

Docker Compose 默认：

```text
data/palworld/Pal/Content/Paks/~mods
data/palworld/Pal/Content/Paks/Mods
data/panel/mod-library
```

原生 systemd 默认：

```text
/home/demo/palworld/Pal/Content/Paks/~mods
/home/demo/palworld/Pal/Content/Paks/Mods
/home/demo/palworld-panel/mod-library
```

`mod-library` 内部保存：

```text
disabled  # 禁用的 PAK/SIG
imports   # 上传导入记录
metadata  # 面板 MOD 元数据
trash     # 从面板移入废纸篓的 MOD
```

## 回滚方式

- 禁用 MOD：把启用中的 PAK/SIG 移回面板禁用目录，重启后生效。
- 删除 MOD：默认移动到 `trash`，不会立刻物理删除。
- 清理废纸篓：确认不再需要后再点，清理后无法通过面板恢复。
- 服务器启动失败：先看 `实时日志`，再禁用最近添加的 MOD；必要时从 `存档管理` 恢复备份。

## 安全策略

- 面板不会从 Nexus、Steam Workshop 或第三方网站自动下载 MOD。
- 面板不会执行 MOD 包内脚本。
- 上传 zip 会拒绝路径穿越、符号链接和 `.exe/.bat/.cmd/.ps1/.sh/.dll/.so` 等高风险文件。
- 删除操作默认移动到废纸篓，不直接物理删除。
- MOD 操作和存档切换共用互斥锁，避免同时改动关键目录。

## 客户端兼容

很多 PAK MOD 要求所有玩家客户端也安装同款 MOD，否则可能无法进服或出现行为不一致。安装前请阅读 MOD 作者说明，并确认服务端和客户端 MOD 版本一致。

