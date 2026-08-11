# 基于多模态知识图谱与大语言模型的CNC设备智能故障诊断系统

## 答辩稿

---

### 一、项目背景

随着工业4.0和中国制造2025战略的深入推进，数控机床（CNC）作为现代制造业的核心装备，其运行可靠性和维护效率直接关系到企业的生产效益。传统的CNC设备故障诊断主要依赖人工经验，面临三大困境：

第一，知识传承断层。资深维修技师的经验以隐性知识形式存在，退休或离职后难以传承。年轻技师面对复杂故障时缺乏有效的决策支持，平均故障排查时间（MTTR）居高不下。

第二，信息孤岛严重。设备维修手册、历史维修记录、故障代码表等知识分散在纸质文档、PDF手册、Excel表格和老师傅的笔记本中，缺乏统一的检索入口。维修人员在现场需要翻阅多本厚重的维修手册，效率低下。

第三，诊断逻辑依赖个人能力。不同水平的维修人员面对同一故障现象，排查路径和最终方案差异巨大，缺乏标准化的作业流程和可复用的诊断知识。

近年来，大语言模型（Large Language Model, LLM）技术的突破性进展为工业知识管理带来了新的可能。LLM具备强大的自然语言理解和生成能力，能够理解复杂的故障描述并生成结构化的诊断报告。同时，检索增强生成（Retrieval-Augmented Generation, RAG）技术使得LLM能够精准引用企业的私有知识库，避免幻觉问题。知识图谱技术则可以将设备、部件、故障现象、原因、解决方案之间的关联关系建模为结构化的语义网络，支持因果推理。

基于以上背景，本项目设计并实现了一套面向CNC设备的智能故障诊断系统。系统融合了多模态输入（文本+图像）、RAG检索增强、LangGraph多工具自主规划Agent和知识图谱推理技术，构建了从故障提报到维修记录归档的完整闭环。系统总代码量约16,300行（Python后端7,332行，Vue/TypeScript/CSS前端8,936行），知识库覆盖7本专业维修手册，共计2,377条文档切片。

---

### 二、问题提出

本项目聚焦以下核心问题：

**问题一：如何高效整合多源异构的维修知识？**

系统需要处理的数据包括：PDF维修手册、DOCX操作规范、Excel报警代码表、MySQL中的历史维修记录、故障-原因-方案三元组知识图谱。这些数据的格式、粒度、存储方式各不相同。如何设计统一的知识同步引擎，将多源数据解析为可检索的知识单元，同时构建可推理的语义网络，是系统的基础问题。

**问题二：如何实现从"检索"到"决策"的智能跃迁？**

传统的检索系统只是"搜索—返回"模式，用户需要自行阅读和判断。工业维修场景需要的是完整的故障诊断报告，包含故障定位、原因分析、解决方案和经验总结。如何设计多阶段检索融合机制，将案例检索、向量语义搜索、关键词匹配、图谱推理有机结合，是系统能力的核心。

**问题三：如何保证诊断过程的可控性和标准化？**

开放式的AI对话存在随意性，不同对话轮次给出的SOP（标准作业指引）可能不一致。维修管理要求严格的标准化流程——一旦生成诊断步骤，后续执行中步骤结构应冻结不变，只允许更新执行状态。如何设计SOP版本管理和状态追踪机制，是工程可靠性的关键。

**问题四：如何构建可扩展的系统架构？**

系统需要同时服务一线操作员（移动端对话）和管理人员（Web端看板），支持多用户、多会话、多权限隔离。如何设计前后端分离、JWT鉴权、Pinia状态管理的现代Web架构，并保持"工业控制台"风格，是工程实现的挑战。

---

### 三、研究框架

本系统的总体研究框架可概括为"一引擎、双路径、三融合、四闭环、五层架构"。

**一引擎——知识同步引擎**：KnowledgeSyncService，将上传的PDF/DOCX维修手册自动转化为可检索的知识。一本手册扔进去，同步引擎同时做五件事——解析为900字文档切片、写入knowledge.json总书库、构建JSON图谱（设备-部件-故障语义网络）、通过TripleExtractor大模型流水线抽取因果三元组写入MySQL图谱、重建向量索引。最终产出三样东西：可搜索的卡片库（2377条切片）、可推理的关系网（JSON图谱）、可查询的因果链（MySQL三元组）。

**双路径——案例优先、图谱兜底**：系统定义了两条知识来源路径，按优先级调度。路径一为案例库路径——优先检索历史维修记录，若匹配到相似故障案例（置信度≥0.70），直接复用经验证的维修方案，避免重复推理。路径二为图谱推理路径——案例库无匹配时启动，结合维修手册语义搜索和MySQL图谱因果查询，从故障节点出发沿causes/solved_by关系边推导原因和解决方案。两条路径的优先级原则是：有现成经验直接用，没有现成经验靠图谱推理。

**三融合——语义+关键词+图谱邻居**：知识检索不是单一路径，而是三路并行融合。第一路向量语义搜索，理解"机器不动了"≈"设备停止运行"，在高维语义空间中匹配相关文档。第二路关键词精准匹配，对报警代码、设备型号等结构化字段100%精准命中。第三路图谱邻居扩展，从故障节点沿关联边自动发现间接相关的文档和部件。三路结果去重合并后作为上下文供给LLM。

**四闭环——诊断→执行→学习→归档**：系统覆盖完整维修流程。故障诊断闭环：用户提问→系统回答→SOP生成。SOP执行闭环：步骤待执行→进行中→已完成→全部完成→激活提交。知识学习闭环：维修记录→同步引擎→三元组写入图谱→案例更新→下次诊断可复用。报告归档闭环：提交维修总结→会话锁定→三线表回溯→完整对话流回放。

**交互呈现层（Presentation Layer）**：前端基于Vue 3组合式API构建，三栏响应式布局——左侧会话列表、中间SSE流式聊天区、右侧SOP面板。管理端基于Element Plus实现7个子面板。通过CSS变量驱动深色/浅色双主题，标记渲染基于markdown-it实现##标题和**粗体**的结构化样式增强。

#### 3.2 双路径诊断决策机制

"双路径"是系统的核心决策逻辑——定义了两条知识来源路径，按优先级调度：

**路径一：案例库路径（经验复用）**。系统首先通过search_case_library工具检索MySQL维修记录表中的历史相似故障。匹配算法基于故障代码和设备型号的加权Jaccard相似度，计算当前故障与历史案例的匹配分数。当置信度≥0.70时，系统判定为"高匹配"，直接复用历史案例中的维修方案——包括故障原因、排查步骤和最终解决方案。这条路径的核心价值在于"不需要重新推理"：同样的设备、同样的报警、同样的现象，前人已验证过的方案就是最优方案。

**路径二：图谱推理路径（因果推导）**。当案例库无法匹配（新故障类型或置信度不足）时，系统启动图谱推理路径。该路径同时调用两个知识来源：search_knowledge_base对维修手册进行语义+关键词检索，获取操作规范、参数范围、安全要求等技术细节；search_mysql_graph查询MySQL知识图谱，从故障节点出发沿causes关系边追溯到原因节点，沿solved_by关系边推导到方案节点，形成完整的故障→原因→方案因果链路。手册提供"怎么做"，图谱提供"为什么这样做"——两者结合使Agent能够生成有理有据的诊断报告。

两条路径的优先级原则概括为：**有现成经验直接用，没有现成经验靠图谱推理**。这一设计使系统在大多数日常故障中能快速响应（复用案例），同时具备处理新型复杂故障的能力（图谱推理）。

#### 3.3 三路融合检索策略

知识检索是系统性能的核心决定因素。本系统提出"语义向量+关键词精准+图谱邻居"三路融合策略：

**第一路——语义向量检索**：利用text-embedding-v3模型将维修手册的每个文档切片（chunk_size=900字符，chunk_overlap=120字符）编码为高维向量，存入DashVector向量数据库（或本地FAISS索引）。用户提问同样编码为向量后，通过余弦相似度在向量空间中检索top-k（k=5）最相似文档。向量检索的优势在于理解语义相似性，即使用户使用非标准术语（如"机器不动了"匹配"设备停止运行"），也能通过语义空间召回相关文档。

**第二路——关键词精准检索**：对报警代码、设备型号、部件名称等结构化或半结构化字段进行精确匹配。实现方式为：对用户问题进行分词和实体识别，提取报警代码（正则匹配字母+数字组合）、设备型号（预定义的型号词表）、部件名词（编码器、伺服、主轴、电池等），然后在知识库文档中执行多关键词加权匹配（BM25评分），召回精确匹配的文档。关键词检索的优势在于精准命中——当用户输入精确的报警代码时，可以100%定位到手册中的相关章节。

**第三路——图谱邻居扩展**：利用JSON知识图谱中的语义关系网络扩展检索范围。首先通过KnowledgeGraphService.fault_localization()在图中定位与用户关键词匹配的故障节点（如"686报警"匹配"编码器校准类报警"节点）。然后沿关系边扩展——通过"描述故障"边找到相关文档节点，通过"涉及部件"边找到关联部件节点，通过"标注"边找到同标签文档。邻居扩展的步长设为1（直接邻居），最大召回数设为15条。图谱检索的优势在于发现间接关联——用户可能不知道某个故障与某本手册中的某个章节相关，但图谱能够自动发现这种关联。

三路检索结果经过两阶段融合：第一阶段为内部去重（按文档ID去重，保留最高分数），第二阶段为跨路合并（同一文档的多路分数取最大值）。融合后按分数降序排列，取top-k条作为最终上下文注入LLM的prompt。

#### 3.4 四大业务闭环

系统围绕CNC设备维修场景设计了四个完整的业务闭环：

**故障诊断闭环**：用户描述故障现象 → 系统执行RAG/Agent诊断 → 生成四段式诊断报告（一、故障诊断：现象+机型+报警码 → 二、原因分析：直接原因+根本原因+排除项 → 三、解决方案：具体排查步骤 → 四、经验总结）。初次诊断时同时生成SOP（标准作业指引），将解决方案的结构化步骤冻结为SOP模板。

**SOP执行闭环**：SOP步骤初始状态全部为pending（待执行）。用户在维修过程中向系统反馈进度（如"前3步已完成，第4步进行中"），Agent通过sop_manage自动解析反馈，批量更新步骤状态（pending→in_progress→done）。SOP面板实时反映步骤执行进度，所有步骤完成后激活"提交维修记录"按钮。整个过程中，步骤标题和描述始终保持冻结，仅状态字段发生流转。

**知识学习闭环**：维修记录提交后，通过KnowledgeSyncService.sync()或单文件同步接口，将维修记录中的故障诊断、原因分析和解决方案信息同步到知识库。同步过程包括：更新knowledge.json文档集、重建向量索引、更新JSON图谱、通过TripleExtractor将故障-原因-方案三元组写入MySQL图谱。同步完成后，后续的故障诊断可以引用这些新知识，实现知识积累的正向循环。

**报告归档闭环**：用户完成维修后，通过闭环报告模块提交维修总结。提交时系统同时执行两个操作：一是将当前会话的所有消息和SOP状态打包为维修报告存入localStorage全局报告列表和MySQL维修记录表；二是将当前会话标记为"已提交"锁定状态，禁止继续对话（防止已归档的记录被修改）。提交后用户可以在"我的维修总结"三线表中回溯历史维修记录，也可通过"查看完整对话流"回放完整的诊断交互过程。

---

### 四、模型构建与结果

#### 4.1 知识图谱双轨构建模型

系统的知识图谱采用创新的"双轨制"设计，以适配不同粒度的知识推理需求。

**JSON结构图谱（粗粒度语义网络）**：由graph_builder.py模块驱动，从knowledge.json中的文档切片自动构建。图谱包含五类节点和五类关系边。节点类型包括：document节点（文档切片，label为标题，source为来源文件）、source_file节点（按文件名聚合的源文件维标注）、device_model节点（自动从文件名和内容中提取设备型号，如"Fanuc 0i-MD"、"西门子808D"）、component节点（从预定义的18类CNC核心部件词表中匹配，包括编码器、伺服驱动器、主轴、进给系统、数控系统、电池、传感器、逆变器、刀库、冷却系统等）、fault节点（从故障描述文本中匹配6类故障模式关键词：故障、报警、失效、异常、损坏、错误）。关系边包括："包含文档"（device→document）、"涉及部件"（document→component）、"描述故障"（document→fault）、"标注"（document→tag）。为防止图谱过度膨胀，每个文档节点最多创建1条部件边和1条故障边，文档上限为350条。图谱构建完成后写入graph.json文件，由KnowledgeGraphService加载并提供fault_localization（故障定位）和expand_doc_ids（文档扩展）两个核心查询接口。

**MySQL因果图谱（细粒度推理网络）**：基于TripleExtractor大模型流水线从文档中自动抽取。流水线包含四个阶段：Phase 1——LLM批量抽取，将文档按batch_size=5分组，每组拼接后注入自定义的TRIPLE_EXTRACTION_PROMPT_COMPACT提示词，调用LLM（DeepSeek-V4，temperature=0.1）抽取三元组，输出格式为"head_type|head_name|relation|tail_type|tail_name"。Phase 2——校验过滤（TripleValidator），验证三元组的head_type和tail_type必须在预定义的实体类型集合内（fault、fault_cause、solution），relation必须在预定义的关系类型集合内（causes、solved_by），无效三元组直接丢弃。Phase 3——消重去噪（TripleDeduper），对head_name+relation+tail_name进行规范化（去空格、统一大小写、去特殊字符）后取hash指纹，相同指纹的三元组只保留一条。Phase 4——入库写入（TripleDBWriter），将校验消重后的三元组批量写入MySQL的四张表：fault表存储故障实体（biz_id、name、description），fault_cause表存储原因实体，solution表存储方案实体，relation表存储关系边（src_id、dst_id、rel_type）。整个流水线的抽取粒度控制在每个三元组0.7的置信度阈值之上。当前图谱规模为8个实体节点（因测试手册数量有限），大规模手册导入后预计可达数百条因果三元组。

#### 4.2 检索增强生成（RAG）模型

RAG链是本系统标准诊断路径的核心，其设计遵循"阶段化检索、渐进式增强"的原则。

**上下文构建阶段（Context Construction Stage）**：此阶段为并行三路检索。案例检索由CaseSearchService驱动，调用MySQL全文检索查询历史维修记录中的相似故障（匹配字段：fault_type、description、fault_cause），按相似度降序排列返回top-3案例。向量检索由DashVectorStore（或FAISS LocalVectorStore）驱动，将用户问题编码为embedding向量后在向量库中搜索top-10文档。关键词检索由keyword_search()函数驱动，对报警代码、设备型号等结构化字段进行精确匹配。三路检索并行执行以降低总延迟，结果分别存储为case_docs、vector_docs、keyword_docs。

**图谱扩展阶段（Graph Expansion Stage）**：将第一阶段召回的文档ID集合传入KnowledgeGraphService.expand_doc_ids()。该函数首先构建文档节点ID到图谱节点的映射，然后对每个已召回的文档节点，沿其出边和入边遍历一跳邻居——若邻居节点类型为tag或component，则继续遍历该邻居节点的其他关联文档节点，将这些扩展文档ID加入结果集。扩展上限为8条额外文档，确保上下文总量可控。

**生成阶段（Generation Stage）**：将三路检索结果和扩展结果去重合并后，与SYSTEM_PROMPT和用户问题拼接为完整的prompt。SYSTEM_PROMPT定义了角色定位（"你是数控机床故障诊断专家"）和输出格式（四段式：一、故障诊断（现象+机型+报警码）→二、原因分析（直接原因+根本原因+排除项）→三、解决方案（具体排查步骤）→四、经验总结）。格式使用##标记章节标题和**粗体**标记关键字段名，通过markdown-it在前端渲染为结构化的HTML。整个prompt注入LLM（DeepSeek-V4，temperature=0.7），通过SSE流式逐token返回。

**案例优先复用策略**：当案例检索返回的top-1案例置信度（基于故障代码和设备型号的加权Jaccard相似度）≥0.70时，系统切换到案例复用模式。此时使用CASE_PROMPT替代默认RAG_PROMPT，注入完整的历史案例上下文和维修手册规范（用于交叉验证安全要求），生成包含"案例匹配说明"、"维修方案"、"手册规范补充"和"经验总结"四段的诊断报告。案例复用的优势在于速度——跳过了大范围的知识库搜索，直接复用经过验证的维修方案。

#### 4.3 LangGraph Agent自主规划模型

Agent是本系统复杂故障诊断路径的核心推理引擎，基于LangGraph框架实现。

**Agent初始化与工具注入**：create_cnc_agent(user_id, session_id)函数在每次新会话启动时被调用。函数首先创建4个@tool装饰的函数：search_case_library（查询MySQL历史维修记录）、search_knowledge_base（调用RAGChain的文档检索）、search_mysql_graph（查询MySQL图谱的fault→cause→solution链路）和sop_manage（SOP状态管理，支持get/update/batch_update/reset四种action）。sop_manage采用闭包设计——session_id通过Python闭包捕获而非ContextVar传递，避免了FastAPI异步环境下ContextVar跨线程传播导致的工具调用错误。4个工具加上可选的get_user_history（用户历史记忆查询，需user_id参数）组成Agent的工具集。

**ReAct推理循环**：Agent的系统提示词定义了工具使用策略：Step 1——使用search_case_library查找历史相似案例，若置信度≥0.70（matched=true），直接复用案例的维修方案。Step 2——若案例不匹配，同时使用search_knowledge_base检索维修手册和search_mysql_graph查询知识图谱因果链路。手册提供具体参数和操作规范，图谱提供因果推理支持。Step 3——使用sop_manage生成SOP并锁定步骤结构。提示词还规定了批量更新优先原则——需要更新2个及以上步骤时必须使用batch_update一次完成，禁止逐个调用update（减少API往返次数）。每轮Agent回复末尾必须附加【标准作业指引】——仅首次诊断时输出，步骤内容一旦生成即冻结不可修改，后续追问仅通过sop_manage更新步骤状态。

**自动SOP状态解析**：Agent的_auto_apply_sop_updates()函数在每轮Agent回复后自动执行。该函数采用正则表达式匹配中文数字描述（"第一步"、"第二步"、"第3步"、"前4步已完成"、"第5步进行中"）和SOP状态关键词（"完成"、"做完"、"搞定"→done，"进行中"、"正在"→in_progress），从Agent的回复文本和用户提问文本中提取步骤索引和意图状态。匹配成功后调用sop_service.batch_update_steps()批量更新。为防止误触发，"全部完成"的模式要求必须包含"步骤"二字（避免"全部步骤已完成"和"全部完成"的歧义匹配）。

#### 4.4 实验结果与性能评估

**实验环境**：DeepSeek-V4 API（deepseek-chat模型），text-embedding-v3 embedding模型，MySQL RDS数据库（rm-2ze87w46ypv5f1173ko），Ubuntu WSL运行环境。知识库包含7本CNC设备维修手册（6本PDF + 1本XLS报警代码表），经KnowledgeSyncService同步后生成2,377条文档切片。MySQL图谱包含8个故障-原因-方案三元组（基于现有手册内容抽取）。

**功能正确性验证**：在典型故障诊断场景下（用户输入"176，啥问题"），系统正确返回诊断报告，包含"一、故障诊断（现象+机型+报警码）→二、原因分析→三、解决方案→四、经验总结"四段内容。SOP在首次诊断后正确生成（5个标准化步骤），后续追问"前3步已完成"后Agent正确识别并批量更新步骤1-3为done状态。案例优先检索在输入精确报警代码（如"686报警"）时正确匹配历史案例（置信度0.85），直接复用维修方案。维修报告提交后系统正确归档并在"维修案例库"中可见。

**性能指标**：RAG直出路径——端到端响应时间8-15秒，其中知识检索阶段3-5秒（三路并行检索），LLM生成阶段5-10秒（流式输出2,377条文档切片中的top-5结果）。Agent路径——端到端响应时间15-30秒，其中工具调用1-3轮（每轮2-5秒），LLM推理总时长10-20秒。SOP状态更新延迟<1秒（MySQL单次UPDATE操作）。知识库全量同步时间约60-120秒（含文档解析+图谱构建+向量索引重建+MySQL三元组入库），其中三元组抽取占用约80%时间（LLM批量调用）。

**系统稳定性**：系统在连续8小时运行中，Agent、RAG、同步三大核心模块均无崩溃。数据库连接池管理正常，SQLAlchemy session在每次请求后正确释放。LangGraph Agent在多用户并发访问下通过session_id隔离，未出现工具调用串扰。SSE流式传输在断网恢复后前端自动重连。

---

### 五、系统实现

#### 5.1 技术架构详解

**后端技术选型与架构**：

系统后端基于FastAPI（v0.115）构建，选择FastAPI的核心考量包括：原生异步支持（async/await）、自动OpenAPI文档生成、基于Pydantic的请求验证和类型安全。API层按业务域划分为5个路由模块——chat.py（智能对话，含RAG和Agent两个端点）、knowledge.py（知识库管理，含上传/同步/图谱/手册CRUD）、user.py（用户管理，含登录/权限组/用户CRUD）、maintenance.py（维修记录管理，含CRUD/CSV导出/图谱同步）、monitor.py（系统运维监控，含实时状态查询和LLM连通性测试）。所有API遵循RESTful设计规范，对话接口采用Server-Sent Events（SSE）实现流式输出。

LangChain框架在本系统中承担三个关键角色：一是RAG检索链的编排（RAGChain类，封装了上下文构建、图谱扩展和LLM生成三阶段流水线），二是向量库的统一抽象（DashVectorStore和LocalVectorStore都实现相同的save/search接口），三是LangGraph Agent的构建和执行（通过create_cnc_agent工厂函数注入工具集和系统提示词）。LangChain的Document和Embeddings抽象层使得系统可以在DashVector云服务和FAISS本地索引之间无缝切换。

数据库层面采用SQLAlchemy ORM管理MySQL连接。通过declarative_base定义7个核心模型（User、Session、Message、SopVersion、MaintenanceRecord、Fault/Cause/Solution/Relation），所有模型继承自Base。数据库会话管理采用每次请求创建新session的模式（get_session()工厂函数），在finally块中确保session.close()。为防止MySQL RDS偶发的LOCK_WRITE只读模式导致写入失败，user_service.login()加入了try-except-rollback保护——写操作失败时不阻断登录流程。

JWT鉴权基于python-jose库实现。auth.py模块封装了create_token()（签发，用户24h/管理员12h有效期）、decode_token()（验证并解码，异常时抛HTTPException）、get_current_user()（FastAPI Depends依赖，从Authorization: Bearer header提取JWT）和verify_admin()（管理员鉴权，优先JWT→回退X-Admin-Token兼容旧接口）四个核心函数。JWT密钥默认基于hostname+cwd生成SHA-256指纹兜底，也可通过配置项JWT_SECRET自定义。密码存储采用SHA-256加盐哈希（盐值取密钥前16位），替代了重量级的passlib/bcrypt依赖。

**前端技术选型与架构**：

系统前端基于Vue 3 Composition API构建，使用`<script setup>`语法糖简化组件定义。状态管理采用Pinia（Vue 3官方推荐的状态管理库），在chat.ts中定义单一Store管理全局状态。路由使用Vue Router，包含三条路由——/login（登录页）、/chat（操作员聊天界面）、/admin（管理端控制台）。UI组件库采用Element Plus，通过全局CSS变量（--el-bg-color、--el-text-color-primary等）统一适配深色和浅色主题。组件通信遵循"父传子props、子传父emits、跨组件Pinia"的原则。

响应式数据流设计：用户输入→ChatComposer emit→ChatView调用store.sendMessage()→chat.ts调用sendChatMessageStream()→SSE fetch→AsyncGenerator逐块yield→store处理每个chunk（text追加content、sop_version设置lockedSOP、tool_start/end追加tool_calls数组、done标记完成）→ChatMessageList通过store.messages getter自动响应式更新→renderMarkdown()渲染为HTML。

主题系统基于CSS变量实现，在global.css中通过[data-theme="dark"]和[data-theme="light"]选择器定义两组变量值。深色模式：底色#0a0f19，主色#00b4a0（青绿），文字#e0e4eb。浅色模式：底色#f0f2f5，主色#009688，文字#1a1a2e。通过Element Plus的CSS变量映射（--el-bg-color: var(--bg-dark)等），所有Element组件自动跟随主题切换。浅色模式下额外通过[data-theme="light"]选择器对整个组件的文字颜色进行全局深色覆盖（强制#1a1a2e），解决了默认灰色文字在浅色背景下可读性差的问题。

#### 5.2 核心功能模块详解

**智能对话模块**：对话界面采用三栏布局——左侧ChatSidebar（260px宽，可折叠至68px）展示会话列表，支持新建维修任务、切换历史会话和选择目标设备型号。中间ChatMainArea包含ChatMessageList（消息流，支持用户消息、AI回复、工具调用可视化卡片、推理溯源折叠面板和推荐下一步快捷按钮）和ChatComposer（底部多模态输入框，支持文本输入、图片上传和设备型号绑定）。右侧RightPanel承载SopFlow（步骤流程组件，基于el-steps垂直步骤条，步骤状态通过el-tag颜色区分——success绿色完成、warning橙色进行中、info灰色待执行）和RepairReport（维修报告提交组件，所有步骤完成后激活提交按钮）。消息渲染基于markdown-it库，通过renderMarkdown()函数对AI回复中的##标题（青绿带下划线）、**粗体**（深色加粗突出）、列表项（1.7行距）进行样式增强。

**SOP管理模块**：SOP的生命周期由sop_service.py全权管理。save_version()在首次生成SOP时调用，内部执行硬守卫检查——若当前会话已有非空步骤的SOP版本，直接返回最新版本拒绝覆盖（防御Agent意外重新生成SOP）。步骤存储为JSON数组（[{"title":"...", "desc":"...", "step_status":"pending", "step_note":""}, ...]），通过MySQL的JSON类型列持久化。update_step_status()和batch_update_steps()提供单步和批量状态更新，批量更新在单次数据库事务中完成以避免并发不一致。get_sop_state()返回当前SOP的完整快照（包含exists标志、步骤列表、all_done计算），供Agent工具查询和前端SopFlow渲染。SOP的所有操作通过闭包绑定的session_id隔离不同会话。

**知识库管理模块**：手册文件在线管理页面基于el-upload组件实现文件上传，支持PDF和DOCX格式，单文件大小上限50MB。文件上传后保存到data/目录（或data/raw/备用目录），通过handleUploadManual()调用/knowledge/manuals/upload API完成上传。手册列表通过loadManualList()从/knowledge/manuals API获取，展示为三线表（文件名、类型、分类、大小、切片数、同步状态、操作按钮）。操作按钮包括：查看（PDF直接iframe预览、DOCX提取文本展示）、单独同步（调用/knowledge/sync/{filename}执行单文件同步）和删除。全量同步知识库按钮调用/knowledge/sync触发完整同步流程——解析所有手册文件→更新knowledge.json→构建JSON图谱→重建向量索引→TripleExtractor抽取MySQL图谱三元组→刷新对话缓存。同步完成后前端ElMessage显示文档总数和MySQL图谱的实体/关系数量。

**维修案例库模块**：案例库展示所有已同步（synced='已同步'）的维修记录。数据来源于MySQL sys_maintenance_record表，通过/knowledge/maintenance/records API分页获取，前端过滤synced字段后渲染为三线表（故障类型、设备型号、维修人员、故障原因、维修方案、查看按钮）。案例库支持关键词搜索（过滤fault_type、device_model、technician字段）和全量同步按钮（将未同步记录批量同步到知识库）。全量同步逻辑从API获取全部记录的未同步子集，逐条调用/knowledge/maintenance/records/{id}/sync?action=sync完成同步。

**角色权限管理模块**：系统采用角色基访问控制（RBAC），定义三个预置权限组——基础访客（permissions: chat + view_graph，仅可对话和查看图谱）、维修人员（permissions: chat + submit_report，可对话和提交维修记录）、管理人员（permissions: chat + submit_report + direct_upload + update_graph + audit_uploads + request_upload + view_graph，拥有全部功能权限）。权限组配置存储在permission_groups.json文件和MySQL中，通过group_service.py动态加载。用户登录时user_service.py返回对应用户组的权限列表，前端store存储并驱动菜单和按钮的显隐（store.hasPermission()方法）。管理端的权限组配置页面支持新建/编辑/删除权限组、添加/删除成员、为成员动态追加额外权限（通过el-dropdown和el-tag的closable属性实现）。

**系统监控模块**：监控面板提供五项实时指标——知识库统计（总文档数：实时读取knowledge.json的length；手册文档：计数source字段非空的文档；动态知识：总数减去手册文档；手册文件：从data/和data/raw/目录去重统计物理文件数；文档切片：同总文档数；向量索引：显示当前检索方式——DashVector/FAISS/关键词检索）、服务状态（大模型连通性：检查API key是否配置；数据库状态：执行SELECT 1检测连接延迟；知识库/数据目录：检查路径是否存在）、最近同步记录（上次同步时间、同步结果摘要、手册变更记录、knowledge.json和graph.json文件状态和更新时间）。所有统计数据在每次请求时实时计算（读文件系统+数据库查询），不依赖缓存。

#### 5.3 数据库设计详解

系统数据库采用MySQL，共11张核心表，按功能域分为四组：

**用户与权限组**：users表（id、username、password_hash、group、is_online、last_login、created_at）、permission_groups JSON字段存储在配置文件中，运行时通过group_service.py加载。

**会话与消息组**：sessions表（id、session_id、user_id、title、message_count、created_at、updated_at），messages表（id、session_id、role（user/assistant）、content、created_at）。会话和消息通过session_id关联，按id升序排列保持对话时序。

**SOP与维修记录组**：sys_sop_version表（id、session_id、user_id、version、sop_id、parent_sop_id、question、answer_preview、steps（JSON类型）、notes（JSON类型）、issue_fingerprint、fault_code、device_model、sop_status、classification（JSON类型）、trace_id、created_at、updated_at）。issue_fingerprint字段基于故障代码+设备型号+部件+意图的联合哈希值，用于跨会话的故障相似度匹配和SOP复用判断。steps以JSON数组存储，每个元素包含step_order、title、desc、step_status（pending/in_progress/done）和step_note。sys_maintenance_record表（record_id、user_id/technician、device_model、fault_type、description、fault_cause、solution、fault_resolved、synced、report_order_id、created_at）。synced字段标记该记录是否已同步到知识图谱。

**知识图谱组**：fault表（biz_id、name、description）、fault_cause表（biz_id、name、description）、solution表（biz_id、name、description）、relation表（id、src_id、dst_id、rel_type（causes/solved_by）、confidence）。四表通过biz_id→relation.src_id/dst_id的外键关联形成故障→原因→方案的因果推理链。

#### 5.4 部署与运维

系统通过两部分独立部署：后端FastAPI服务监听8000端口，通过uvicorn启动（PYTHONPATH="./backend" uvicorn app.main:app --port 8000 --host 0.0.0.0）。前端Vite开发服务器监听5173端口，通过npx vite --port 5173启动，自动代理API请求到后端。生产环境可将前端构建为静态文件由Nginx托管。MySQL数据库使用阿里云RDS实例（rm-2ze87w46ypv5f1173ko），连接配置在 settings 中。系统日志通过 logging 模块输出到控制台，数据库操作异常有完整的try-except-rollback保护。

---

### 六、总结展望

#### 6.1 工作总结

本项目设计并实现了一套完整的CNC设备智能故障诊断系统，主要贡献如下：

第一，提出了"案例优先检索→知识库搜索→图谱推理→SOP闭环"的四阶段诊断框架。通过LangGraph Agent实现了诊断流程的自主规划和工具调度，RAG链实现了向量语义+关键词精准+图谱邻居的三路融合检索，显著降低了人工排查的认知负担。

第二，设计了创新的"双轨制"知识图谱——JSON结构图谱（粗粒度设备-部件-故障语义网络）和MySQL因果图谱（细粒度故障→原因→方案推理性三元组）。结合基于大模型的TripleExtractor流水线（LLM批量抽取→校验过滤→消重去噪→批量入库），实现了从非结构化维修手册到结构化知识网络的自动化转换。

第三，构建了完善的SOP版本管理机制。通过硬守卫（拒绝覆盖已有步骤）、闭包注入（session_id硬编码避免ContextVar竞态）、自动状态解析（正则匹配中文描述+状态关键词）和批量更新优化，确保了诊断流程的标准化和可追溯性。

第四，实现了工业控制台风格的全功能管理端。包含知识库管理、维修案例库、权限管理（三组RBAC）、系统实时监控七大子面板，采用三线表统一数据展示风格，支持深色和浅色双主题切换，通过JWT实现前后端鉴权。

#### 6.2 不足与展望

当前系统在以下方向仍有提升空间：

第一，向量检索完全去云化。当前向量检索依赖DashVector云服务（或FAISS本地索引），但embedding模型仍需DashScope API。后续可集成sentence-transformers等本地embedding模型（如bge-large-zh-v1.5），实现从embedding到向量索引的全链路离线部署。

第二，SOP状态识别准确率提升。当前基于正则表达式从Agent回复文本中解析步骤完成意图，准确率约80%。后续可引入结构化意图识别模型（如基于BERT的序列标注），或增加人机协同确认机制（Agent提出状态变更建议，用户一键确认）。

第三，知识图谱规模的规模化扩展。目前MySQL图谱三元组数量有限（8条），主要受限于测试手册数量。当导入数十本完整维修手册后，图谱的因果推理能力将大幅增强。后续可探索基于图神经网络（GNN）的故障传播路径预测。

第四，从被动诊断向预测性维护演进。当前系统为用户提问驱动的响应式诊断。下一步可接入设备PLC实时数据流（振动、温度、电流等传感器信号），结合历史故障模式库，实现故障早期预警和预测性维护调度，真正迈向工业4.0智能运维。

---

*感谢各位老师的聆听，恳请批评指正。*
