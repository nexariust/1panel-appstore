# 自动更新脚本

## 功能说明

`check_updates.py` 脚本用于自动检查 `apps` 文件夹下所有应用的版本更新。

### 工作原理

1. 扫描 `apps` 目录下的所有应用
2. 读取每个应用的 `data.yml` 获取 GitHub 仓库地址
3. 通过 GitHub API 获取最新的 release 或 tag
4. 比较当前版本和最新版本
5. 如果有更新，自动创建新版本文件夹并更新配置文件

### 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行脚本
python check_updates.py

# 可选：设置 GitHub Token 以避免 API 限制
export GITHUB_TOKEN=your_token_here
python check_updates.py
```

### 输出

- 控制台输出：显示检查过程和结果
- `updates.json`：保存所有更新信息的 JSON 文件

## GitHub Actions 工作流

工作流配置在 `.github/workflows/auto-update.yml`，功能包括：

- **定时执行**：每天北京时间凌晨 1 点自动运行
- **手动触发**：可以在 GitHub Actions 页面手动触发
- **自动 PR**：检测到更新后自动创建 Pull Request
- **详细报告**：在 PR 中列出所有更新内容

### 工作流步骤

1. 检出代码
2. 安装 Python 和依赖
3. 运行更新检查脚本
4. 如果有更新，创建 Pull Request
5. 生成执行摘要

### 查看结果

- **Actions 页面**：查看工作流运行历史和日志
- **Pull Requests**：自动创建的 PR 包含详细的更新信息
- **Summary**：每次运行都会生成摘要报告

## 配置说明

### 时区设置

工作流使用 cron 表达式 `0 17 * * *`（UTC 时间 17:00），对应北京时间凌晨 1:00。

如需修改执行时间，可以调整 cron 表达式：

```yaml
# 北京时间凌晨 2:00（UTC 18:00）
- cron: '0 18 * * *'

# 北京时间中午 12:00（UTC 04:00）
- cron: '0 4 * * *'
```

### GitHub Token

工作流使用 `GITHUB_TOKEN` 自动认证，无需额外配置。该 Token 具有：

- 读取仓库权限
- 创建 PR 权限
- 访问 GitHub API（有更高的速率限制）

## 注意事项

1. **版本号格式**：脚本使用语义化版本号（如 `1.2.3`）进行比较
2. **Docker 镜像**：创建新版本时会自动更新 docker-compose.yml 中的镜像标签
3. **手动审查**：建议在合并 PR 前手动审查配置文件是否需要调整
4. **API 限制**：未认证的 GitHub API 请求有速率限制，建议使用 Token

## 扩展功能

可以根据需求扩展以下功能：

- [ ] 支持从 Docker Hub 直接获取版本信息
- [ ] 支持更复杂的版本号格式（alpha, beta, rc 等）
- [ ] 自动测试新版本的可用性
- [ ] 支持批量更新或选择性更新
- [ ] 添加通知功能（邮件、Slack、钉钉等）
