# 编码兼容指南

本项目在 Windows + PowerShell + Excel 环境下，统一采用以下编码约定：

## 1. CSV

- 所有 CSV 输出使用 `encoding="utf-8-sig"`
- 这样 Excel 在直接打开时更容易正确识别中文
- 适用于：
  - `reports/*.csv`
  - `data/processed/*.csv`

## 2. YAML

- 所有 YAML 读取使用 `encoding="utf-8"`
- 不使用系统默认编码
- 适用于：
  - `config/*.yaml`

## 3. Markdown

- 所有 Markdown 写入使用 `encoding="utf-8"`
- 避免在 Windows 下出现乱码或编码漂移
- 适用于：
  - `README.md`
  - `docs/*.md`

## 4. Windows / PowerShell / Excel 策略

### PowerShell

- 读取文件时显式指定编码
- 写文件时优先使用 `utf-8` 或 `utf-8-sig`
- 不依赖控制台默认代码页

### Excel

- 优先打开 `utf-8-sig` 编码的 CSV
- 如果旧版 Excel 出现乱码，可通过“数据导入”方式指定 UTF-8
- 不建议直接把纯 `utf-8` CSV 交给桌面版 Excel 双击打开

### 文件协作

- 代码、配置、说明文档统一使用 UTF-8
- 只在 CSV 导出阶段使用 `utf-8-sig`
- 新增读写入口时，必须显式写出 `encoding=...`

## 5. 本项目当前约定

- `backtest/`：CSV 导出使用 `utf-8-sig`
- `config/`：YAML 读取使用 `utf-8`
- `docs/`：Markdown 使用 `utf-8`
- `factors/`：如后续需要文件读写，默认跟随上面的三类规则
