# finalpaper — AI Agent 论文阅读报告

[English](README.md)

为 AI agent 设计的可复用技能：通过 [MinerU Precision API](https://mineru.net) 解析文件夹下所有 PDF 论文，生成包含作者背景、概念解释和内嵌逐图分析的双语阅读指南。每篇 PDF 需 ≤200 页且 ≤200 MB（MinerU API 限制）。

## 安装

```bash
# 安装该 skill（触发名：finalpaper）
codex skill install --path . --name finalpaper
```

在 readingpaper-skills 仓库中，skill 根目录为 `skills/finalpaper`。触发名为 `finalpaper`。

## 本项目做什么

1. **解析 PDF** → MinerU 云端 API 提取文本、公式（LaTeX）、表格（HTML）、图示以及结构化元数据，输出至 `mineru/<paper-slug>/`。
2. **生成阅读指南** → AI agent 产出 `finalpaper.md`（英文）和 `finalpaper_cn.md`（中文），每份指南包含：
   - 附有可验证来源的作者简介
   - 文章概览与关键词定义
   - 深度概念讲解
   - 逐图描述（内嵌图片）
   - 历史背景与学术圈分析
3. **自文档化** → `SKILL.md` 作为内置指引，供任何后续 agent 无需人工指导即可继续处理更多论文。

## 目录结构

```
.
├── SKILL.md                            # Agent skill 说明
├── README.md                           # 本文件（英文）
├── README_cn.md                        # 本文件（中文）
├── references/
│   ├── mineru-api.md                   # MinerU API 工作流参考
│   ├── output-rules.md                 # finalpaper.md 生成规则
│   ├── translation-rules.md            # 双语翻译规则
│   └── examples/
│       ├── finalpaper.md               # 示例输出（英文）
│       ├── finalpaper_cn.md            # 示例输出（中文）
│       └── image/                      # 仅供示例显示的图片
└── .gitignore
```

运行时 MinerU 输出会生成在用户的论文目录中，并被本仓库忽略：

```
mineru/
├── manifest.json
└── <paper-slug>/
    ├── full.md
    ├── *_content_list.json
    ├── *_content_list_v2.json
    └── images/
```

## 快速开始

### 前置条件

- [MinerU API token](https://mineru.net/apiManage/token)。设置 `MINERU_API_TOKEN` 环境变量，或让 agent 主动询问。token 不会写入任何文件，仅在内存中用于 API 调用。
- Python 3.10+，安装 `requests` 库（或通过 `pip install mineru-open-sdk`）
- Git（用于版本控制）

### 处理新论文

1. 将 PDF 文件放入本目录。
2. 按照 `SKILL.md` 中描述的 agent 工作流运行：
   - 检查 `mineru/manifest.json`，仅当 `status: "done"`、`full_md` 和 content-list JSON 都存在时才跳过该论文
   - 将未处理的 PDF 上传至 MinerU Precision API：
     ```
     POST https://mineru.net/api/v4/file-urls/batch
     ```
   - 将每个 PDF 以 PUT 方式上传到返回的签名上传 URL
   - 轮询 `GET /api/v4/extract-results/batch/{batch_id}` 直至完成
   - 将结果 zip 解压至 `mineru/<paper-slug>/`
3. 所有 PDF 解析完成后，生成 `finalpaper.md` 和 `finalpaper_cn.md`。

完整的分步说明及 API token 设置请参见 `SKILL.md`。

### 使用 MinerU Python SDK

```python
from mineru import MinerU

client = MinerU("your-api-token")
result = client.extract("./paper.pdf", model="vlm", language="en")
result.save_all("./mineru/paper-slug/")
```

## 设计决策

- **双语输出**：英文保证精确性，中文降低阅读门槛。两份文件采用相同结构和图片引用。
- **仅正文图示**：仅收录论文正文中的图示。附录可视化会注明但不嵌入，使指南聚焦核心内容。
- **来源标签**：每条论断均标注 `[FROM CAPTION]`、`[FROM TEXT]`、`[FROM TABLE]` 或 `[INFERRED]`，方便读者追溯信息来源。
- **自包含图片**：生成的报告从 `mineru/<slug>/images/` 以相对路径引用图示；仓库内置示例的显示图片集中放在 `references/examples/image/`，因此 skill 仓库不需要提交 MinerU 运行产物。


