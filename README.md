# TokFlux 配置助手

一个小型 Windows GUI 程序，用来检查 Node.js/npm 环境，并通过 npm 安装和配置：

- Codex CLI：`@openai/codex`
- Claude Code：`@anthropic-ai/claude-code`

程序会把 TokFlux 中转地址和 API Key 写入对应工具的本地配置，方便安装后直接在终端使用。

## 运行

```powershell
python .\ceshi.py
```

也可以运行包入口：

```powershell
python -m codex_installer
```

## 功能

- 检测 TokFlux API Key 是否可用。
- 检测 Node.js 和 npm 是否可用。
- 如果缺少 Node.js，会尝试通过 `winget` 自动安装 Node.js LTS。
- 安装 Codex CLI：

```powershell
npm install -g @openai/codex --registry=https://registry.npmmirror.com
```

- 安装 Claude Code：

```powershell
npm install -g @anthropic-ai/claude-code --registry=https://registry.npmmirror.com
```

## API 地址规则

界面中的 TokFlux API 请求地址填写根地址：

```text
http://tokenflux.cloud
```

程序会按工具自动处理实际请求地址：

- Codex 使用：`http://tokenflux.cloud/v1`
- Claude Code 使用：`http://tokenflux.cloud`

环境测试时，Codex API Key 和 Claude API Key 任意一个连接成功，就会继续检测 Node.js/npm 并启用安装按钮。

## 配置写入

Codex 安装成功后会写入：

- `%USERPROFILE%\.codex\config.toml`
- `%USERPROFILE%\.codex\auth.json`
- 用户环境变量：`OPENAI_API_KEY`、`OPENAI_BASE_URL`

Claude Code 安装成功或保存 Claude API Key 后会写入：

- `%USERPROFILE%\.claude\settings.json`
- 用户环境变量：`ANTHROPIC_AUTH_TOKEN`、`ANTHROPIC_BASE_URL`、`CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY`

Claude Code 的 settings 写入结构：

```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "<Claude API Key>",
    "ANTHROPIC_BASE_URL": "http://tokenflux.cloud",
    "CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY": "1"
  },
  "includeCoAuthoredBy": false,
  "theme": "dark"
}
```

## 验证

安装完成后可以在新的终端中运行：

```powershell
codex --version
claude --version
```

## 项目结构

```text
ceshi.py                    # 程序入口
codex_installer/
  app.py                    # GUI 界面
  api_client.py             # Codex/Claude API 连接测试
  codex_config.py           # 写入 Codex 和 Claude Code 配置、认证文件和用户环境变量
  config.py                 # 应用配置和安装命令参数
  environment.py            # Node.js/npm 检测
  environment_installer.py  # 使用 winget 自动安装 Node.js LTS
  installer.py              # npm 安装执行
  __main__.py               # python -m codex_installer 入口
```
