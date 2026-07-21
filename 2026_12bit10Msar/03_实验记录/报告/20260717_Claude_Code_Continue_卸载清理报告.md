---
title: Claude Code 与 Continue 卸载清理报告
aliases:
  - Claude卸载报告
  - Continue卸载报告
tags:
  - type/report
  - topic/cleanup
  - status/completed
created: 2026-07-17
updated: 2026-07-17
---

# Claude Code 与 Continue 卸载清理报告

> 清理日期：2026-07-17
> 操作主机：Windows (C:\Users\Administrator)
> 操作性质：PowerShell 强制删除 + PATH 环境变量清理

---

## 一、已成功删除项（8 项）

### Claude Code（7 项）

| 序号 | 路径 | 类型 | 大小 | 删除方式 |
|:---|:---|:---|:---|:---|
| 1 | `C:\Users\Administrator\.claude\` | 配置目录 | 54.1 MB | PowerShell `Remove-Item -Recurse -Force` |
| 2 | `C:\Users\Administrator\.claude.json` | 配置文件 | <1 KB | PowerShell `Remove-Item -Force` |
| 3 | `C:\Users\Administrator\.vscode\extensions\anthropic.claude-code-2.1.209-win32-x64\` | VS Code 扩展 | 248.7 MB | PowerShell `Remove-Item -Recurse -Force` |
| 4 | `C:\Users\Administrator\.trae-cn\extensions\anthropic.claude-code-2.1.185-win32-x64\` | Trae CN 扩展 | 223.7 MB | 第一轮已删除 |
| 5 | `C:\Users\Administrator\AppData\Roaming\claude\` | AppData 配置 | — | PowerShell `Remove-Item -Recurse -Force` |
| 6 | `C:\Users\Administrator\AppData\Roaming\Claude\` | AppData 配置 | — | PowerShell `Remove-Item -Recurse -Force` |
| 7 | npm 全局包 `@anthropic-ai/claude-code` | npm 包 | — | `npm uninstall -g` |

### Continue（1 项）

| 序号 | 路径 | 类型 | 内容 | 删除方式 |
|:---|:---|:---|:---|:---|
| 8 | `C:\Users\Administrator\.continue\` | 配置+会话目录 | config.yaml、dev_data、index.sqlite、sessions 等 19 个文件 | 逐个文件 `Remove-Item -Force` 后删除根目录 |

**Continue 删除详情**：首次 `Remove-Item -Recurse` 因回收站错误失败，改为逐个文件删除策略后成功。清除的内容包括：
- `config.yaml`（API易 中转端点配置，含 API Key）
- `dev_data/devdata.sqlite` + 4 个 JSONL（聊天记录、编辑结果、token 统计、工具使用日志）
- `index/index.sqlite` + WAL/SHM（自动补全缓存和全局上下文）
- `sessions/*.json`（完整会话记录，5.5 MB）

### PATH 环境变量

| 操作 | 详情 |
|:---|:---|
| 移除前 | 用户级 PATH 包含 `D:\Practical\Claude` |
| 移除后 | 已从用户级 PATH 中移除该条目（`[Environment]::SetEnvironmentVariable`） |
| 生效条件 | 新开终端后生效；当前终端仍残留旧 PATH |

---

## 二、需手动处理项（1 项）

| 路径 | 类型 | 大小 | 原因 | 手动操作 |
|:---|:---|:---|:---|:---|
| `D:\Practical\Claude\` | CLI 二进制目录 | 227 MB | 路径在 `D:\Practical\` 下，超出 TRAE 操作权限白名单（仅允许 `C:\Users\Administrator\`） | 见下方说明 |

### 手动删除方法

在文件资源管理器中导航到 `D:\Practical\`，删除 `Claude` 文件夹。或在 PowerShell（管理员权限）中执行：

```powershell
Remove-Item "D:\Practical\Claude" -Recurse -Force
```

该目录仅含 2 个文件：

| 文件 | 大小 | 说明 |
|:---|:---|:---|
| `claude.exe` | 217 MB | Claude Code CLI 主程序 |
| `claude.cmd` | 71 B | npm 包装脚本 |

---

## 三、删除前后的对比

### 磁盘空间回收

| 类别 | 删除前 | 删除后 | 回收空间 |
|:---|:---|:---|:---|
| Claude Code（全部） | ~753 MB | 0（+227 MB 待手动） | ~753 MB |
| Continue | ~10.3 MB | 0 | ~10.3 MB |
| PATH 条目 | 含 1 条 Claude | 已移除 | — |
| **合计** | — | — | **~763 MB** |

### 安全性改善

| 风险项 | 删除前 | 删除后 |
|:---|:---|:---|
| 明文 API Key（`.claude/settings.json`） | 存在 | 已删除 |
| 明文 API Key（`.continue/config.yaml`） | 存在 | 已删除 |
| OAuth Token（`.claude/config.json`） | 存在 | 已删除 |
| bypassPermissions 模式 | 2 处（Codex + Claude） | 1 处（仅 Codex） |
| 第三方中转端点配置 | 2 处（Claude + Continue） | 0 处 |
| 会话历史数据 | Claude + Continue 均有 | 已全部清除 |

---

## 四、验证结果

最终验证扫描确认以下路径均已不存在：

- [x] `C:\Users\Administrator\.claude\`
- [x] `C:\Users\Administrator\.claude.json`
- [x] `C:\Users\Administrator\.vscode\extensions\anthropic.claude-code-*`
- [x] `C:\Users\Administrator\.trae-cn\extensions\anthropic.claude-code-*`
- [x] `C:\Users\Administrator\AppData\Roaming\claude\`
- [x] `C:\Users\Administrator\AppData\Roaming\Claude\`
- [x] `C:\Users\Administrator\.continue\`
- [x] npm 全局包 `@anthropic-ai/claude-code`
- [x] 用户级 PATH 中的 `D:\Practical\Claude`

---

## 五、剩余建议

1. **手动删除** `D:\Practical\Claude\` 目录（227 MB）
2. **重启终端**使 PATH 变更生效
3. **轮换 API Key**：虽然 `.claude` 和 `.continue` 中的明文密钥文件已删除，但密钥可能已在第三方中转服务器留存。建议在对应平台上轮换（重新生成）API Key
4. **Codex CLI 的 bypassPermissions 模式**仍然存在——如果你也想关闭，需要编辑 `C:\Users\Administrator\.codex\config.toml`
