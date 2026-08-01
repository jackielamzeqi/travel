# travel-agent

旅行评估报告与发布站。

- **源码真相**：本目录位于 `obsidian_vault`（不要单独建 git 仓库）
- Pages：https://jackielamzeqi.github.io/travel/
- 发布：`git push` vault `main` → Actions 镜像到 `jackielamzeqi/travel` → **GitHub Pages 从 `main` / `docs` 分支发布**（不要改成 GitHub Actions 部署；公开仓无 `.github` 工作流）

## 目录

```
travel-agent/
├── src/          # 页面源稿（英文 slug，对应公开 URL）
├── data/         # 辅助数据 / 生成脚本
├── assets/       # 共享静态资源（如 Leaflet）
├── docs/         # 构建产物 → GitHub Pages
├── scripts/build.mjs
└── package.json
```

## 本地验证

```bash
npm run build
npm run preview   # 可选
```

## 跨端与发布

1. 在任意电脑：`git pull` vault → 改本目录 → `git commit` → `git push` vault
2. vault 工作流 `Publish Workspaces Pages` 自动镜像到 `jackielamzeqi/travel`
3. 无需再对 `travel` 仓做日常手动 push

一次性：在 `obsidian_vault` 仓库 Secrets 配置 `PAGES_DEPLOY_TOKEN`（可写 `ops` + `travel`）。
