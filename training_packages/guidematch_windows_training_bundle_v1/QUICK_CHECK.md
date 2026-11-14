# 复制到 Windows 后的 60 秒检查

在训练包根目录打开 PowerShell：

```powershell
python --version
nvidia-smi
Get-FileHash .\data\splits\train.jsonl -Algorithm SHA256
Get-FileHash .\data\splits\dev.jsonl -Algorithm SHA256
```

预期：

- Python 推荐 3.11（可接受 3.10）；
- `nvidia-smi` 能看到 RTX 3060；
- train SHA-256：`f2cdd124a8de68a108506748c0fc9f62e70e4614d3173d49eff3ceee9dfd1578`；
- dev SHA-256：`914d5262a9f39e4b9a55f872206489ce8c9a68730a741a3d31605ae589436866`。

随后双击 `START_HERE.cmd`。首次执行需要联网安装依赖并下载底座模型；离线模型用 `start_training.ps1 -ModelSource` 指定。
