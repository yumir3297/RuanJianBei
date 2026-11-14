# 数字人模型本地预览说明

## 网页

```bash
cd frontend
npm ci
npm run dev:tourist
```

- 游客主站：<http://localhost:5173/>
- 自带模型测试台：<http://localhost:5173/motion-tester.html>

后端未启动时，聊天 / TTS 等接口不可用；数字人预览仍受模型资源、浏览器 WebGL 和配置影响。具体形象与实际接入以当前代码、资源许可和 [代码地图](../docs/REPO_MAP.md) 为准。

## Blender

历史工程包含：

- `blender/vrm/hanfu.vrm`：解压过 `EXT_meshopt_compression` 的模型（保留 VRM 1.0 全部扩展）
- `blender/hanfu.blend`：已导入并配置相机/灯光的 Blender 工程

### 模型转换和导入

本目录包含历史导出的 VRM、Blender 工程和动作试验；部分名称带 `trial`、`draft` 或 `candidate`，不表示已经接入游客端。早期记录中的 `tools/decompress-vrm.mjs` 和 `tools/import_vrm_to_blend.py` 不在当前跟踪仓库中，不能直接照旧命令运行；需要重新转换时应先准备并核实相应工具及其许可。原始模型的 `EXT_meshopt_compression` 与 `EXT_texture_webp` 兼容性、VRM 扩展及材质导入需在实际 Blender/插件版本中验证。

### 历史导入结果

- 3 个网格（Body / Face / Hair）
- 1 个骨架，300 根骨骼
- 29 张打包贴图，28 个材质（MToon）
- VRM 1.0 元数据、62 组 SpringBone、表情数据

## 授权提醒

历史记录中所检查模型的 meta 为 `avatarPermission: onlyAuthor`、`commercialUsage: personalNonProfit`、
`modification: prohibited`、`allowRedistribution: false`。仅限本地预览，不要修改后发布、商用或再分发。
