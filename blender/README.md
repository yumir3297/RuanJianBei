# 数字人模型本地预览说明

## 网页

```bash
cd frontend
npm ci
npm run dev:tourist
```

- 游客主站：<http://localhost:5173/>

## 动作制作

游客端使用 `frontend/public/` 中的模型与动作。Blender 工程与制作脚本用于编辑源素材。复作宁灵拱手动作时，从历史版本导出制作脚本所需的源场景，在运行脚本前设置环境变量（从仓库根目录执行）：

```sh
export NINGLING_GREETING_SOURCE="$(mktemp -d)/greeting-source.blend"
git show cbe74bf:blender/ningling-cupped-greeting-before-lift-fix.blend > "$NINGLING_GREETING_SOURCE"
```

### 历史导入结果

- 3 个网格（Body / Face / Hair）
- 1 个骨架，300 根骨骼
- 29 张打包贴图，28 个材质（MToon）
- VRM 1.0 元数据、62 组 SpringBone、表情数据

## 授权提醒

历史记录中所检查模型的 meta 为 `avatarPermission: onlyAuthor`、`commercialUsage: personalNonProfit`、
`modification: prohibited`、`allowRedistribution: false`。仅限本地预览，不要修改后发布、商用或再分发。
