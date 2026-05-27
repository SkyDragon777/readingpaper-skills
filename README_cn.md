# readingpaper-skills

中文 | [English](README.md)

`readingpaper-skills` 是一组用于论文阅读、相关文献发现、合法开放获取 PDF 下载和综述综合的 Agent Skills。

## Skills

- `finalpaper`：解析用户提供的论文或 manuscript PDF，提取种子论文元数据、主张、方法、数据集、关键词和结构化摘要。
- `relevantpaper`：基于种子论文发现、排序并合法下载相关开放获取论文，生成文献索引和 BibTeX。
- `synopticpaper`：顶层综合入口。可以读取 `finalpaper` 与 `relevantpaper` 的输出，也可以在只有 PDF 的文件夹中通过文件产物编排完整流程，最终生成中英文阅读报告。

## 安装 / 开发

需要 Python 3.10+。

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

## 环境变量

| 变量 | 是否必需 | 用途 | 缺失时行为 |
|---|---:|---|---|
| `OPENALEX_API_KEY` | 推荐 / 正常检索预期提供 | OpenAlex | 警告；完整在线发现会停止，可做 dry-run 或测试 |
| `SEMANTIC_SCHOLAR_API_KEY` | 否 | Semantic Scholar | 尽可能使用公开端点；认证或限流步骤跳过 |
| `CROSSREF_MAILTO` | 否，推荐 | Crossref | 使用 public pool，并建议设置 polite pool |
| `CROSSREF_PLUS_API_TOKEN` | 否 | Crossref Metadata Plus | 不使用 plus pool |
| `RELEVANTPAPER_MAX_CANDIDATES` | 否 | relevantpaper | 默认 200 |
| `RELEVANTPAPER_MAX_DOWNLOADS` | 否 | relevantpaper | 默认 40 |
| `MINERU_API_TOKEN` | 深度报告必需 | finalpaper / relevantpaper / synopticpaper | 深度阅读指南模式会明确失败；metadata 报告仍可生成 |
| `RELEVANTPAPER_MAX_MINERU_PARSE` | 否 | relevantpaper | 默认解析 8 篇选中的相关 PDF |
| `RELEVANTPAPER_SKIP_MINERU_FOR_RELEVANT` | 否 | relevantpaper | 默认 false |
| `MINERU_PARSE_MODE` | 否 | MinerU 解析 | 默认 full；lightweight 不可用于最终深度报告 |

## 典型工作流

### Agent工作流

使用 codex 或 opencode 安装 `readingpaper-skills`：

a. 调用 `finalpaper`，通过 MinerU Precision API 解析文件夹下所有 PDF 论文，生成包含作者背景、概念解释和内嵌逐图分析的双语阅读指南。

b. 调用 `relevantpaper`，把文件夹下的 PDF 论文当作种子论文，通过 OpenAlex API 等公开论文数据源进行种子论文发现、排序并合法下载相关开放获取论文，生成文献索引和 BibTeX。

c. 调用 `synopticpaper`，一键通过文件夹下已有的 PDF 论文进行相关文献调研，并基于 MinerU full-parse 来源最终生成详细且易读的 `outputs/synopticpaper/finalpaper.md` 和 `outputs/synopticpaper/finalpaper_cn.md`。

### 一键文件夹工作流

在包含 PDF 的项目文件夹中运行：

```bash
python path\to\readingpaper-skills\skills\synopticpaper\scripts\synopticpaper.py --project-dir .
```

脚本会按文件产物衔接：

1. 从当前目录或 `input/papers/` 发现 PDF。
2. 如果缺少 `outputs/finalpaper/seed_papers.json`，先根据 PDF 文件名和可读元数据生成种子记录。
3. 调用 `relevantpaper` 脚本检索相关论文、排序、生成 BibTeX 和合法开放获取下载清单。
4. 生成 `outputs/synopticpaper/` 下的结构化综述、证据图谱、研究空白和阅读计划。
5. 在 `outputs/synopticpaper/` 下生成综合版 `finalpaper.md` 和 `finalpaper_cn.md`。

`outputs/finalpaper/finalpaper.md` 是种子论文阅读报告，可以只包含原始论文；综合相关文献后的最终文档是 `outputs/synopticpaper/finalpaper.md`。

`outputs/synopticpaper/literature_index_report.md` 是 metadata/debug 报告，不是最终阅读指南。

完整在线检索需要 `OPENALEX_API_KEY`。如果没有该变量，脚本会明确失败，而不会假装已经完成检索。

### 分步工作流

```bash
python skills/relevantpaper/scripts/relevantpaper.py --project-dir . --seeds outputs/finalpaper/seed_papers.json
python skills/synopticpaper/scripts/synopticpaper.py --project-dir . --synthesis-only
```

仅生成 metadata/debug 报告：

```bash
python skills/synopticpaper/scripts/synopticpaper.py --project-dir . --report-mode metadata_index_report
```

## 安全策略

只下载合法开放获取 PDF。

禁止使用 Sci-Hub、Library Genesis、绕过付费墙工具、共享账号、浏览器 cookies 或任何未授权抓取。
