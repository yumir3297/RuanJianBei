# 非 WAV 时长校验实施计划

**Goal:** 真实 ASR 请求的压缩音频在转发 provider 前验证可识别时长并执行配置的最大秒数限制。

**Architecture:** 新增 `audio_duration.py`，通过受限 `ffprobe` 子进程读取私有临时文件，结束后清理；仅真实 provider 的非 WAV 路径调用，且在现有容量许可下运行。

## Tasks

1. **Probe helper** — [x] 先写测试验证有效 JSON、无音轨/损坏结果、missing executable、timeout、错误输出；实现受限 async subprocess 探测器。
2. **ASR route integration** — [x] 配置 ffprobe 路径和超时；真实 provider 非 WAV 先探测后调用 provider；区分 400、413、503，WAV/stub 保持兼容；加入 route tests。
3. **Docs and validation** — [x] 更新 F01、兼容性、架构和仓库映射；跑完整 backend suite、repo map checker、diff check。
