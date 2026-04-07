# Hang-Seng-InsightSync

PRD Framework
UI demo: https://v0-hang-seng.vercel.app/
1. Background
恒生在香港本地企业银行市场具备深厚基础，同时持续强化商业银行、GBA、跨境银行服务、贸易融资与数字化服务能力。
但从 RM 的实际工作流看，客户经营仍存在几类典型问题：
第一，获客前判断效率低。
 RM 需要手动或者依赖外部支持查看公司年报、公告、官网新闻、行业与政策信息，才能判断一家企业是否值得跟进、该从什么产品切入、是否具备跨境或贸易金融需求。这一过程高度依赖经验，且不同 RM 的判断口径不一致。
同时，RM在潜在客户筛选环节可能存在仍依赖个人专业经验进行主观判断的情况，缺乏基于企业画像与外部情报的量化评估体系或评估体系较为粗糙，不仅导致高价值目标易被遗漏，还使低意向客户占用过多跟进资源。而即便筛选出目标客户，在首次触达时又因缺乏“此时此地”的市场背景与行业洞察，难以快速建立专业信任。
第二，获客后客户理解碎片化。
客户信息散落在公司披露、外部新闻、政策变化和内部记录中。RM 很难快速形成统一客户画像，也难以持续追踪客户经营变化、跨境扩张、流动性压力与潜在产品缺口。
第三，风险与流失信号识别滞后。
客户经营下行、汇率暴露上升、海外扩张带来的服务复杂度提升，往往要到客户明确提出问题，或关系已经降温后才被发现。恒生年报也提到 2024 年下半年信用环境变化、减值贷款及相关信贷损失增加，说明更及时的客户级风险识别具有现实意义。
这些问题不只是效率问题，更直接影响客户覆盖深度、非利息收入增长机会和客户关系稳固程度。
2. Objective
本产品在获客前阶段聚焦解决 RM 在潜在客户发现与初步筛选中的核心问题，依托恒生银行现有数据生态与低代码 GenAI 架构，建立面向 Commercial Banking 的智能 prospecting 支持能力，具体有以下方面：
在广泛市场中识别具潜力的企业客户，扩大 lead pool，覆盖更多行业、地域及企业规模，动态关联大湾区政策热点与区域经济指标（如 GBA Index、广东省统计局数据），重点关注大湾区 SME 和中型企业；

基于企业信息与外部情报（上市公司公告、行业报告、监管动态），对潜在客户进行优先级排序与匹配推荐，帮助 RM 更精准地锁定高价值目标客户；

在首次触达前，结合客户画像与市场热点生成情境化 insight，融合客户所属行业最新政策、市场趋势与竞对动态，为 RM 提供“可直接引用”的专业话术与业务切入点，帮助其找到更合适的切入话题、产品方向与业务机会；

提升 prospecting 阶段的效率与质量，为后续客户转化、关系建立和 portfolio 增长奠定基础；

基于以上背景，本产品欲解决恒生企业客户经营中的核心问题，建立服务 RM 的客户经营决策平台，具体从以下方面做功：
在获客前，快速识别高潜力企业客户，并找到合适的首个切入场景
在获客后，利用ai汇总信息生产客户画像
在获客后，持续识别客户的 relationship deepening 机会、风险变化与服务缺口


希望达到什么业务目标
3. Target Users
Primary User： Relationship Manager


Secondary User：商业银行产品经理、客户经营团队
角色定位
RM 是恒生商业银行前线核心力量，主要负责企业客户关系维护、新客户开发、信贷审批跟进、产品交叉销售以及日常客户经营。他们每天需要服务 20-50 个中型企业/SME 客户，频繁出差至 Business Banking Center 或客户现场，时间高度碎片化。
核心痛点（2026 年真实场景）
客户会议前 10 分钟内无法快速获取“公司最新年报 + 外部市场情报”的融合洞察，导致提案不够精准。
手动收集 HKEX 年报、HKMA 监管更新、GBA 行业趋势耗时巨大，容易错过收购目标或早期风险信号。
难以批量识别组合内“增长潜力”与“风险预警”，影响绩效考核（新账户增长、交叉销售金额）。
角色定位
负责设计、迭代、定价商业银行全系列产品（贸易融资、供应链融资、现金管理、跨境财富管理、绿色信贷等），需要持续监控市场趋势、监管变化、客户需求痛点。
InsightSync 赋能点
行业趋势 & 监管情报仪表盘：实时查看 Euromoney/KPMG 报告总结 + HKMA/SFC 新规对产品的影响（例如绿色金融新指引如何影响产品设计）。
产品-客户匹配引擎：自动生成“某产品在 GBA 哪个行业/城市最有需求”的热力图，帮助产品经理快速调整营销策略。
反馈闭环：RM 使用后产生的“产品推荐点击率”数据自动回流，帮助产品经理迭代产品特性。
预期价值：产品上市周期缩短 30%，产品与市场匹配度提升，支持 2026 年“11 项 GenAI 能力”落地延伸。

4. Use Cases / Scenarios（用户会在什么场景下使用、典型使用流程是什么）
case 1：高潜客户识别（High-Growth Client Identification）
在获客前阶段，客户经理（RM）通常需要定期拓展新客户（例如按周或按月更新客户pipeline），但在实际操作中往往缺乏系统化方法来判断应优先关注哪些企业，导致客户筛选高度依赖经验且效率较低。


为解决这一问题，RM可基于目标区域或行业在系统中发起潜在客户识别任务，系统随后自动整合宏观经济数据（如GDP、PMI及行业增长指标）、行业趋势信息以及公司公告与新闻数据，构建多维度信息输入。在此基础上，生成式人工智能（GenAI）对多源数据进行统一分析，首先识别出高增长行业与重点区域，其次从公司层面提取关键“扩张信号”（如融资活动、产能扩建及市场拓展），并据此对企业进行筛选与优先级排序。


最终，系统输出一份结构化的高潜客户清单（Top acquisition targets），并为每个客户生成一页式摘要，概括其增长逻辑及潜在产品匹配。RM可基于该结果直接制定外展策略（如优先联系重点客户或安排拜访顺序），从而将传统经验驱动的客户筛选转变为数据驱动决策，显著提升获客效率与客户转化率。
case 2：融资需求识别（Financing Need Detection）
在获客及客户跟进过程中，客户经理（RM）通常希望能够提前识别企业即将产生融资需求的时间窗口，以便在需求形成初期介入。然而，这类信号往往分散于公司公告、财务变化及行业动态中，难以及时捕捉，导致银行在竞争中处于被动位置。


在该场景下，RM可基于目标客户池或重点行业发起融资需求监测任务，系统将自动整合公司公告（如发债、再融资及资本开支计划）、财务数据（如收入增长与负债变化）以及行业趋势信息。在此基础上，生成式人工智能（GenAI）从结构化与非结构化数据中提取与融资相关的关键信号（如fundraising与expansion），并结合行业发展趋势对融资行为的合理性与可持续性进行判断，从而识别出具有潜在融资需求的企业。


系统最终输出融资需求客户清单，并为每个客户匹配相应的产品建议（如贷款、贸易融资及现金管理服务）。RM可据此提前开展客户触达与方案准备，在融资需求显现前抢占业务机会，从而提升客户获取成功率及整体市场竞争力。
case 3：跨境业务机会识别（Cross-border Opportunity Detection）
在粤港澳大湾区（GBA）一体化持续推进的背景下，企业跨境扩张活动显著增加，银行需要更高效地识别相关业务机会。然而，跨境相关信息通常分散于贸易数据、政策文件及企业披露中，缺乏系统整合，导致机会识别存在滞后。


在该场景下，RM可围绕特定区域或行业发起跨境机会分析任务，系统将自动整合贸易数据（如出口增长）、跨境及区域政策（如GBA发展政策）以及公司层面的信息（如海外布局与扩张计划）。随后，生成式人工智能（GenAI）对多源数据进行分析，识别跨境业务增长较快的区域与行业，并匹配具有实际跨境经营行为的企业，同时进一步评估其在外汇及贸易融资方面的潜在需求。


最终，系统输出跨境业务潜在客户清单，并针对不同客户生成相应的产品建议（如贸易融资、外汇服务及跨境资金管理方案）。RM可基于该结果制定针对性业务策略，从而在GBA背景下更高效地获取跨境业务客户并提升业务转化能力。
case 4：客户触达前情报准备（Contextual Client Briefing）
在实际客户触达前，客户经理（RM）往往缺乏对目标企业的系统性了解，导致沟通停留在产品推介层面，难以建立有效互动与信任。


在该场景下，RM可在系统中选定目标客户并发起情报生成请求，系统将自动整合宏观经济数据、行业报告、公司信息以及实时新闻等多维度数据源，构建全面的信息输入。在此基础上，生成式人工智能（GenAI）对多源信息进行融合与分析，为该客户生成个性化的一页式情报简报。


该简报不仅涵盖企业基本情况、所处行业趋势及当前市场热点（talking points），还能够识别潜在业务切入点，并结合银行产品提供初步建议。RM可直接基于该简报开展客户沟通，例如围绕行业趋势展开讨论或提出针对性解决方案，从而将传统“产品导向”的沟通转变为“价值导向”的对话。同时，该功能有效打通了从数据洞察到实际客户互动之间的“最后一公里”，实现从insight到action的转化，显著提升沟通质量、客户体验及后续转化效率。






5. Functional Requirements
Module
Purpose
What it should show
Market Opportunity Overview
Help RMs understand where the biggest prospecting opportunities are in the market
Lead pool size, opportunity hotspots by industry/region/company size, GBA market trends, macro/policy/sector signals
Priority Prospect List
Help RMs identify and rank the most promising target companies
Ranked prospect list, prospect score, priority tier, industry, region, product fit, recommended entry angle
Prospect Intelligence
Provide a deeper understanding of each target company before outreach
Company profile, business model, expansion signals, cross-border footprint, external news, likely needs, and possible banking opportunities
Trigger Signals
Surface important events or changes that make a prospect more actionable
Growth signals, funding/expansion news, hiring trends, policy relevance, trade/cross-border signals, financing clues





获客后：
模块
功能
说明
Dashboard Overview
Summary Cards
展示当前客户经营相关的核心指标：
deepening opportunities
client at risk
retention alerts
支持点击相应指标切换Priority Client List
Recommended Action
展示AI自动生成的洞察与建议
Priority Client List
deepening opportunities
默认展示，展示需要deepen的客户名单


client at risk
展示风控客户名单


retention alerts
展示retention alerts名单
Client Intelligence
Client Search
支持 RM 按客户名称或客户 ID 搜索并进入具体客户页面
Client Profile Page


展示客户固定字段，包括行业、注册地、主要市场、集团结构、跨境布局和近期动态
形态：One View 时间线：
把“跟这家客户有关的关键事实”按时间顺序放在一条线上，形成全行共享的一页式客户脉络，让 RM看到的是同一套证据与结论（One Bank, One View）
Key Signals Display
提醒客户近期特殊经营变化、跨境扩张、流动性压力、FX 暴露和风险事件
AI Assistance
ai Copilot
以悬浮入口形式存在，RM 可随时唤起并通过自然语言提问，快速获取客户变化、推荐原因和跟进建议。

