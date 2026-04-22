# InsightSync 项目现状评估

日期: 2026-04-22

## 0. 当前推进标记（2026-04-22 更新）

这部分用于标记这份 assessment 提到的关键事项目前推进到了哪一步，避免后续讨论时丢失上下文。

- 已完成：多源解析持久化中间层
  - 已新增 `insightsync/parsing/`，支持 document / html / json / text 多类型解析
  - 已新增 SQLite 持久化表：`parsed_documents`、`parsed_sections`、`parsed_tables`、`parsed_metrics`、`parsed_risk_factors`、`parsed_business_events`
  - 已打通 SQLite -> backend sync，并在 RAG document builder 中优先使用解析结果

- 已完成：基础生产级 parser backend 接入
  - 已接入 PDF: `pymupdf`
  - 已接入 HTML 正文抽取: `trafilatura`
  - 已接入 XBRL: `arelle-release`
  - 已把新依赖补入 `insightsync/data/requirements.txt` 与 `insightsync/backend/requirements.txt`

- 已完成：真实 parsing run 验证
  - 最新一次真实 run: `parse-20260422T151728Z`
  - 覆盖率：`240/240` success，`0` partial，`0` failed
  - 已验证并修复几类明显误判：
    - 指标坏值 `.` / `,` / `0,1,2`
    - HKMA 中性利率记录被误判为 risk
    - KPMG 页脚 / legal footer 被误判为 partnership event

- 已完成：报告解析质量第一轮收敛
  - 已做 CSV header 归一化、表格行标签指标抽取、PDF boilerplate 过滤、结构化抽取去噪
  - 已补 regression tests，覆盖上述真实坏样本

- 部分完成：company report parsing
  - 已具备：
    - PDF text extraction
    - HTML text extraction
    - CSV / JSON / text parsing
    - section 切分
    - table 持久化
    - metric / risk / business event 启发式抽取
    - management discussion summary 抽取框架
  - 仍待加强：
    - 长 PDF 的 layout-aware parsing
    - 更强的表格抽取与清洗
    - OCR 实战验证
    - XBRL 实战验证
    - 财务指标覆盖率与准确率

- 仍未开始闭环：fusion / scoring / recommendation
  - assessment 里提到的 company-centric fusion、prospect scoring、product recommendation、early warning workflow 目前仍未真正落地
  - 当前完成的是“可复用解析层”，还不是最终 banker-facing intelligence layer

- 对“管理层讨论摘要抽取”的当前结论
  - 代码能力已具备，并有测试样例通过
  - 但最新真实数据集中，尚未命中标准 MD&A section，因此 `parsed_documents.management_discussion_summary` 在真实 run 中还没有形成有代表性的真实样本

## 1. 结论先行

这套仓库不是一个失败的方案，相反，它已经具备了一个不错的第一阶段工程基础；但如果严格对照恒生项目 brief，它现在还不能算一个完整的“GenAI 驱动、面向业务动作的情报平台”。

更准确地说，当前仓库已经做到的是：

- 多源外部数据采集
- 统一结构化存储
- SQLite 到 PostgreSQL 的同步
- 基础 RAG 索引与检索
- 一组可调用的后端 API
- 一个强调证据约束的 AI 原型

但它还没有真正做到：

- 深度理解 company reports
- 以公司为中心融合内外部情报
- 产出可落地的 acquisition / cross-sell / risk action
- 提供完整的 banker-facing 工具体验

我的总体判断是：

- 架构方向：合理
- 当前实现：偏“数据底座 + 检索原型”
- 业务完成度：明显不足
- 作为 demo：可讲，但必须诚实定位

## 2. 仓库目前实际上做成了什么

### 已经做成的部分

- `data` 模块已经接入多类数据源：HKMA、ADB、KPMG、广东统计、InvestHK、Hong Kong Government News、HKEX、SZSE/CNINFO、company seed
- 已经建立了三层数据结构：
  - `intelligence_records`
  - `trigger_signals`
  - `client_one_view_timeline`
- 已经有 SQLite 存储与 PostgreSQL 同步链路
- 已经有 RAG document/chunk/embedding 构建流程
- 已经有可运行的 FastAPI 后端接口：
  - `/healthz`
  - `/api/signals`
  - `/api/timeline`
  - `/api/dashboard/overview`
  - `/api/rag/index/status`
  - `/api/rag/query`
  - `/api/insights/generate`
- 已经有基础安全中间件：
  - API key
  - rate limit
- 已经有一定数量的测试，尤其 backend 侧测试基础还不错

### 部分做了，但没有形成闭环的部分

- company master layer
- company ID backfill
- RAG 驱动的 insight generation
- generated insight 持久化
- frontend API guide

### 还基本没做完的部分

- prospect scoring
- prospect list / prospect detail
- acquisition ranking
- cross-sell / upsell recommendation
- early warning workflow
- 真正的前端产品
- handover 文档与 runbook
- evaluation / governance / monitoring

## 3. 关键发现

### 发现 1：项目承诺大于当前实现

从项目 brief 看，目标是“融合公司报告与市场信号，生成可执行情报和建议”。  
从代码现实看，目前更偏向：

- 把数据抓下来
- 统一存起来
- 让人能查
- 让 RAG 能基于这些记录回答问题

这和“真正帮助 RM 做获客、深耕、预警决策”的产品，之间还有一段明显距离。

最核心的问题不是代码写得差，而是“当前做成的东西”和“对外讲的业务价值”之间还有缺口。

### 发现 2：company reports 被收集了，但还没有被真正理解

这是整个项目最关键的技术差距。

当前与报告相关的实现，大致是：

- KPMG：下载 PDF，保存为文档记录
- HKEX：下载 annual report PDF，生成“年报已发布”的事件/信号
- SZSE/CNINFO：抓公告标题、类型、时间、PDF 链接

但是没有真正完成下面这些高价值步骤：

- PDF 文本抽取
- OCR 兜底
- 章节切分
- 表格抽取
- 财务指标抽取
- 管理层讨论摘要抽取
- 风险因子抽取
- 从报告正文中抽出结构化 business events

也就是说，当前系统更像是在理解“报告存在、何时发布、标题是什么”，而不是在理解“报告说了什么”。

如果后续答辩时继续强调“company reports intelligence”，这一点会是最容易被追问、也最容易暴露的问题。

### 发现 3：当前 RAG 比“没有”强很多，但比“看起来”弱

这一版 RAG 的思路其实是好的：

- 有 evidence gating
- 有 citation validation
- 没有 OpenAI key 时还有 deterministic fallback

这说明设计者有意识地避免“纯幻觉式回答”，这是优点。

但问题在于，RAG 的上游内容质量决定了它的上限。当前很多 report 类记录进入 RAG 的其实只是：

- 标题
- 摘要
- payload 里的键值对元数据
- 文件路径 / file hash / 链接
- signal_text

而不是报告正文本身。

所以目前的 RAG 更接近“基于结构化记录做证据检索”，而不是“基于公司报告内容做深度商业分析”。

### 发现 4：当前系统仍然是 source-centric，不是 company-centric

现有系统的核心对象主要还是：

- 一条记录
- 一条信号
- 一条时间线事件

这对数据工程是合理的，但对银行业务并不是最自然的抽象。

恒生真正关心的问题是：

- 哪家公司值得跟进
- 为什么现在值得跟进
- 对应什么银行产品机会
- 最近发生了什么变化
- 风险和机会的强弱如何
- RM 下一步应该做什么

这些问题都要求系统以“公司 / prospect / client”为核心对象，而不是以“source row”为核心对象。

当前仓库还没有真正建立起这个中心层。

### 发现 5：prospect scoring 仍然是空的

从 schema 看，系统已经预留了：

- `prospect_scores`
- `generated_insights`

但从当前 demo SQLite 实际内容看：

- `prospect_scores = 0`
- `generated_insights = 0`

这意味着核心业务输出层现在仍然基本没有真正落地。

换句话说，数据库结构已经在往最终产品靠，但业务逻辑本体还没补上。

### 发现 6：company universe 过小，而且过于依赖手工 seed

当前 company directory 主要来自 `company_candidates.json`。  
这个 seed 文件里只有 8 家公司。

这对 PoC 是可以接受的，因为能快速演示流程；但对恒生这样的商业银行场景，这个规模远远不够。

真正能支撑业务落地的 company universe 应该来自以下一类或多类来源：

- 内部客户池 / prospect master
- 公司注册或商业目录数据
- HKEX / CNINFO issuer master
- 行业数据库
- 内部分层标签与账户画像

所以目前 company layer 更像“演示素材层”，还不是“业务底座层”。

### 发现 7：company mapping 是一个好起点，但还比较脆弱

当前 company mapping 主要是 deterministic alias match。  
它的优点是：

- 简单
- 可解释
- 易审计

但它会天然遇到这些问题：

- 同名或近似名公司
- 集团名与子公司名混淆
- 中英文别名不一致
- 股票简称与正式名差异
- 泛词误匹配

对银行应用来说，company identity resolution 需要比当前更强，否则后续所有 scoring 和 action recommendation 都会受影响。

### 发现 8：默认运行路径和文档叙事之间有落差

这是一个很现实的交付问题。

虽然代码已经支持 `hkgov`、`hkex`、`szse` 等数据源，但默认 CLI source 并不包含它们。  
同时，仓库自带的 demo SQLite 快照也没有覆盖最新 schema 方向。

当前 demo SQLite 实际情况是：

- 只有 4 个主要 source 真正出现在数据里：HKMA、Guangdong stats、ADB、KPMG
- 没有 `companies` 表
- 没有 `company_mapping_audit` 表

这意味着：

- 代码能力比 demo artifact 更新
- README 叙事比默认可复现实物更完整

如果不先修这个问题，项目在 handover 或答辩时会出现“说得比 demo 多”的可信度风险。

### 发现 9：frontend、infrastructure、handover 仍然基本是 placeholder

仓库里这几块目前还是占位状态，这是事实，也并没有被隐藏。

但如果对照项目 deliverables，这些缺口必须被正视：

- 还没有真正的 dashboard 产品
- 还没有部署与运维脚本
- 还没有 data dictionary
- 还没有 prompt/model governance 说明
- 还没有 evaluation log
- 还没有完整 handover package

所以这个仓库现在更像“核心引擎原型”，不是“可交付系统成品”。

### 发现 10：测试基础尚可，但还不到 handover-ready

这次 review 中我做了两轮验证：

- 直接 `pytest` 会因为包导入路径问题失败，需要显式设置 `PYTHONPATH=.`
- 加上 import path 后，30 个测试里有 26 个通过
- 剩余 4 个失败发生在数据侧临时目录/SQLite 写入阶段，属于当前沙箱环境的文件权限限制，失败点还没进入真正的业务断言

这说明两件事：

- backend 测试基础是有的，不是完全空白
- 但仓库还没有达到“别人拉下来就零摩擦跑通测试”的程度

如果是面向老师/评委，这不是大问题；如果是面向恒生团队 handover，这会降低成熟度印象。

### 发现 11：append-only 设计适合审计，但不适合直接当产品视图

当前 SQLite 与 PostgreSQL sync 采用按 hash 追加保留历史的方式。  
这个方向对 lineage / audit 是合理的。

但问题是，当前读 API 基本还是直接读原始表，而不是读“latest current-state view”。

长期看会有几个风险：

- 同一实体出现看起来重复的信号
- dashboard count 被历史累计抬高
- 产品层不容易区分“最新状态”和“历史记录”

RAG document builder 对这个问题做了部分处理，但 signals/timeline/dashboard 还没有真正完成 current-state serving layer。

## 4. 当前方案是否合理

### 合理的地方

- 整体技术路线清晰：采集 -> 标准化 -> 存储 -> sync -> RAG -> API
- 证据约束式 AI 设计是稳健的，不是无约束生成
- 模块划分比较清楚，后续扩展空间大
- 技术栈选择务实，适合 capstone / hackathon / early prototype

### 不合理或者说“不够”的地方

如果严格按恒生项目目标来判断，目前还不够，因为：

- 没有真正理解 company report 内容
- 没有形成公司级情报融合层
- 没有 prospect ranking
- 没有 product recommendation
- 没有 early warning 闭环
- 没有 banker-facing 完整体验

所以更准确的评价不是“方向错了”，而是：

- 基础做对了
- 产品闭环还没有完成

## 5. 我建议你现在怎么定义这个项目

如果近期要对外展示，我不建议把它定义成“已经完成的银行客户经理 Copilot”。

更稳、更真实、也更有说服力的定义是：

“一个证据约束的市场与公司情报底座，已经完成多源采集、标准化、检索与基础问答，下一步聚焦于 company report parsing、company-centric scoring 和 banker action generation。”

这个说法有三个好处：

- 不会过度承诺
- 能保住当前工程成果的价值
- 能自然引出后续 roadmap

## 6. 建议的后续步骤

### 优先级 1：把系统改造成 company-centric

应该尽快在 source tables 之上建立真正的公司情报层，包括：

- canonical company profile
- alias / identifiers
- linked signals
- linked evidence
- latest status
- opportunity score
- risk score
- recommended products
- recommended next action

后端的核心对象应该逐步从“record”变成“company”。

### 优先级 2：真正做 company report parsing

这是整个项目最值钱的一步，也是最能拉开差距的一步。

建议新增一条报告处理链路：

- PDF text extraction
- OCR fallback
- section chunking
- table extraction
- bilingual extraction
- entity linking
- structured event extraction

如果这一步不做，项目很难真正支撑“从公司报告中提炼 actionable intelligence”这个核心论点。

### 优先级 3：补上 scoring 和 recommendation 逻辑

从“有 signal”升级成“有动作建议”，至少要补这几个层面：

- prospect scoring
- trigger weighting
- product mapping
- acquisition ranking
- risk early warning
- explainable reasons with citations

哪怕先用 rules + LLM hybrid，也比现在更接近业务价值。

### 优先级 4：刷新 demo 数据，修正文档与实物不一致

这是投入小、收益很高的一步。

建议在正式展示前完成：

- 重建 demo SQLite snapshot
- 把 `companies` 和 mapping 结果带进去
- 至少跑一次 `hkgov`、`hkex`、`szse`
- 让 README 与实际 demo 完全一致

这一步会显著提升项目可信度。

### 优先级 5：增加 latest-state view

建议保留原始 append-only 历史表，但新增产品层视图或物化表：

- latest company profile
- latest company signals
- latest evidence bundle
- latest dashboard metrics

这样才能把“可审计历史”和“产品可用现态”分开。

### 优先级 6：做一个最小可用前端

不需要一开始做得很大，但至少应当做出 2 到 3 个真正能演示的页面：

- priority companies
- company detail
- evidence timeline
- AI insight panel

这样项目才会从“后端原型”走向“可交互产品”。

### 优先级 7：补 governance 和 evaluation

如果目标是面向银行场景，建议至少补这些轻量能力：

- source trust level
- prompt versioning
- model config 记录
- grounding check
- evaluation set
- human review requirement

这会让项目从“能跑”升级到“更可信”。

## 7. 我建议的推进顺序

如果时间有限，我建议按下面顺序推进：

1. 刷新 demo 数据和 README，先把叙事与实物对齐
2. 做 HKEX / SZSE / KPMG 的报告解析
3. 建 company-centric aggregation layer
4. 实现第一版 scoring 与 recommendation
5. 做最小前端 demo
6. 补 evaluation、handover、runbook

## 8. 最终判断

这个项目最值得肯定的地方在于，它已经完成了很多团队最容易半路放弃的“脏活累活”：

- source integration
- normalized schema
- backend service skeleton
- RAG pipeline
- evidence-aware AI pattern

所以它不是“空心 PPT 项目”，它是有实质工程基础的。

但同样要坦诚：

它目前仍然处于“技术底座 / intelligence prototype”阶段，还没有进入“银行业务动作系统”阶段。

接下来最重要的不是再加更多 source，而是把现有 source pipeline 变成真正理解报告、以公司为中心、能输出可解释动作建议的 intelligence product。

如果这一步走通，InsightSync 会变得很强。
