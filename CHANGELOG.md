# 更新日志

本文件记录 SD 提示词工具集的所有重要变更。
格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2026-10-21

首个稳定版本：由仓库原始上传历史重排整理，代码内容与重排前完全一致。

### 新增

- NAI 与 SD 提示词的**双向格式转换**，支持 `{}` / `[]` 嵌套层级与 0.05 步长换算。
- 权重按 half-up 规则保留三位小数，避免浮点边界误差。
- 标签内部括号自动转义，`artist:` 前缀依据 danbooru 艺术家标签表自动补全。
- 图片元数据探测：PNG 的 tEXt/iTXt 文本块、JPEG/WEBP 的 Exif UserComment。
- Gradio 双标签页界面，附带复制与重置按钮。

### 已知限制

- 项目暂无自动化测试，验证方式为模块导入与针对性输入对照。
- `image_processor.py` 为图片处理链路预留，尚未接入界面。
- `danbooru_art.csv` 带 BOM，在 LF 行尾的检出下 `csv.Sniffer` 会误判表头，导致 `artist:` 前缀不生效（Windows 默认 CRLF 检出正常）。计划在 2.0.0 修复。
