# travel-agent

旅行评估报告与发布站（GitHub 仓库：`jackielamzeqi/travel`）。

- Pages：https://jackielamzeqi.github.io/travel/
- Pages 源：`main` 分支 `/docs`

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

## 发布

```bash
npm run build
git add docs src data assets
git commit -m "Update travel site"
git push
```

本目录即唯一本地工程，**不要**再维护 `GitHub/travel` 或 `GitHub/travel.github.io`。
