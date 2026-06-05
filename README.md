# Codex 安装助手

一个小型 Windows GUI 程序，用来检查 Node.js/npm 环境，并通过 npm 安装 `@openai/codex`。

## 运行

```powershell
python .\ceshi.py
```

也可以运行包入口：

```powershell
python -m codex_installer
```

## 项目结构

```text
ceshi.py                    # 程序入口
codex_installer/
  app.py                    # GUI 界面
  api_client.py             # OpenAI 兼容 API 连接测试
  codex_config.py           # 写入 Codex 配置、认证文件和用户环境变量
  config.py                 # 应用配置和安装命令参数
  environment.py            # Node.js/npm 检测
  environment_installer.py  # 使用 winget 自动安装 Node.js LTS
  installer.py              # npm 安装执行
  __main__.py               # python -m codex_installer 入口
```
