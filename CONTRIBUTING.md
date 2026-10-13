# 贡献指南

感谢你想改进这个项目。该项目定位是**学习 / 演示**，请据此把握改动的尺度。

## 1. 先跑起来

```bash
cd backend
uv sync                              # 或 pip install -r requirements.txt
cp .env.example .env                  # 必填 JWT_SECRET
uv run python -m seed.runner base     # 自动建库 + 建表 + 管理员
uv run python -m seed.runner demo     # 演示数据
uv run python run.py                  # 8001
cd ../front && python -m http.server 8000
```

测试前置：MySQL 可达且已执行 `base` + `demo`；基线 `uv run pytest -q tests` 为 `84 passed`。

## 2. 改代码前

- **需求与实现冲突时以 `specs/` 为准；要改行为先改 spec，再改代码，最后回写 spec 的变更记录。**
- 二次开发的架构约定、目录约定与坑位清单见 **[docs/开发指南.md](./docs/开发指南.md)**，动代码前请先读它的「不能踩的坑」。
- 文档口径（页数、端口、命令、账号）要与 `README.md` / `README.en.md` / `操作手册.md` 保持一致。

## 3. 提交规范

- 分支：`feat/xxx`、`fix/xxx`、`docs/xxx`
- commit 前缀：`feat:` `fix:` `docs:` `refactor:` `test:` `chore:`
- 一个 PR 只做一件事，描述里写清「改了什么 / 为什么 / 怎么验证」

## 4. PR 检查清单

- [ ] `uv run pytest -q tests` 通过（不低于 84 passed）
- [ ] 新增/变更的接口已同步 spec 与 `seed/base.py` 权限树（若涉及权限码）
- [ ] 新增表已进 `seed/schema.py`，且 seed 幂等（重跑不翻倍、不报错）
- [ ] 前端新增页面已同步菜单（`manager/js/common.js` 的 `menuData` 与 `MENU_PERM`）
- [ ] 未引入真实品牌、真实个人信息、第三方版权素材
- [ ] README / 操作手册 的口径已同步

## 5. 不接受的改动

- 引入 GPL/AGPL 等强传染性依赖
- 引入需要联网、需要商业授权的资源（字体、图片、SDK）
- 提交 `.env`、真实口令、密钥、个人信息
- 把演示项目改造成生产级系统的大规模重写（欢迎开 issue 讨论，但请单独分支）

## 6. 报告问题

请附上：复现步骤、期望与实际结果、`.env` 相关配置（**脱敏**）、`seed` 执行过的命令、报错原文。
