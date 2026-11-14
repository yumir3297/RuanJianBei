# 数字人模型本地预览说明

## 网页

```bash
cd frontend
npm install
npm run dev
```

- 项目主站：<http://localhost:5173/tourist>
- 自带模型测试台：<http://localhost:5173/motion-tester.html>

后端未启动时，聊天 / TTS 等接口会报错，但数字人渲染不受影响。主站默认展示清岚；测试台可切换清岚、景行、宁灵。

## Blender

已生成：

- `blender/vrm/hanfu.vrm`：解压过 `EXT_meshopt_compression` 的模型（保留 VRM 1.0 全部扩展）
- `blender/hanfu.blend`：已导入并配置相机/灯光的 Blender 工程

### 添加另外两个模型

```bash
cd tools
node decompress-vrm.mjs ../frontend/public/models/male-guide.vrm ../blender/vrm/male-guide.vrm
node decompress-vrm.mjs "../frontend/public/models/林二女.vrm" "../blender/vrm/林二女.vrm"

cd ..
/Applications/Blender.app/Contents/MacOS/Blender -b --python tools/import_vrm_to_blend.py -- \
  blender/vrm/male-guide.vrm blender/male-guide.blend
/Applications/Blender.app/Contents/MacOS/Blender -b --python tools/import_vrm_to_blend.py -- \
  "blender/vrm/林二女.vrm" "blender/林二女.blend"
```

### 为什么需要解压脚本

原始 VRM 强制使用 `EXT_meshopt_compression`，Blender 的 glTF/VRM 导入器不支持该扩展，直接导入会失败。
`tools/decompress-vrm.mjs` 只解码该压缩扩展，并保留 `VRMC_vrm`、`VRMC_springBone`、`VRMC_materials_mtoon`。
同时把 `EXT_texture_webp` 的纹理索引镜像到 `textures[].source`，否则 VRM 插件在 Blender 中不会给 MToon 材质贴图。

### 导入结果

- 3 个网格（Body / Face / Hair）
- 1 个骨架，300 根骨骼
- 29 张打包贴图，28 个材质（MToon）
- VRM 1.0 元数据、62 组 SpringBone、表情数据

## 授权提醒

模型 meta 为 `avatarPermission: onlyAuthor`、`commercialUsage: personalNonProfit`、
`modification: prohibited`、`allowRedistribution: false`。仅限本地预览，不要修改后发布、商用或再分发。
