# Backend

Agent Town Demo 的 Python FastAPI 后端，负责小镇 NPC 对话、知识检索、长期记忆，以及狼人杀规则和对局内 NPC 状态。

## 运行

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API 文档：`http://127.0.0.1:8000/docs`

第一次知识检索会懒加载 `BAAI/bge-small-zh-v1.5`，模型约 90MB。FastEmbed 或模型不可用时，接口会自动使用关键词检索。

## LLM API

`app/llm.py` 已经实现 `mock` 和 OpenAI-compatible provider，当前用于 NPC 正式发言与私聊表达，默认关闭。

```bash
cp .env.example .env
```

以当前使用的 DeepSeek 为例：

```dotenv
ENABLE_LLM=true
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=你的_DEEPSEEK_API_KEY
LLM_MODEL=deepseek-v4-flash
```

不要使用即将弃用的 `deepseek-chat` 或 `deepseek-reasoner` 别名，本项目直接使用 `deepseek-v4-flash`。

也可以使用以下配置组合：

| Provider | `LLM_BASE_URL` | 示例 `LLM_MODEL` |
| --- | --- | --- |
| Groq | `https://api.groq.com/openai/v1` | `openai/gpt-oss-20b` |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemini-3.5-flash` |
| OpenRouter | `https://openrouter.ai/api/v1` | `openrouter/free` |

修改 `.env` 后需要重启后端。`GET /api/llm/status` 用于检查启用状态、provider、模型和配置完整性，不会返回 API Key。

当前 DeepSeek 可靠性设置：

```dotenv
LLM_MAX_RETRIES=1
LLM_RETRY_DELAY_SECONDS=0.35
```

- DeepSeek 请求使用非思考模式和 `json_object` 输出，避免思考内容占用短回答预算或返回格式漂移。
- 超时、限流、临时服务错误、空内容和坏 JSON 会自动重试一次。
- 返回文本按“声明者 → 目标 → 结果”比对验人，并校验自称身份、女巫/守卫技能行动及信息权限；引用已公开的他人验人不会被算成当前角色新增验人。
- “我验了4号”会被视为预言家起跳；“我是预言家 / 我起跳预言家”“好人 / 金水”等自然同义改写不需要与规则模板逐字一致。
- 篡改目标或结果、凭空增加查验/技能事实、断言未公开神职、泄露狼队友时，会携带全部结构化校验原因继续纠正，最多产生五份候选文本，成功即停止。
- 五轮全部失败后使用规则模板；所有被拒绝的原始返回都会写入 `data/llm_validation_failures.jsonl`，即使后续轮次成功也保留恢复记录。
- 当前调试版本会把五轮失败的 DeepSeek 原文直接返回给 Godot 对话框，不做隐藏身份脱敏；正式发布前应恢复安全显示策略。

填入 Key 后，可以先在项目根目录发送一次小请求验证连接，不需要启动后端：

```bash
backend/.venv/bin/python scripts/check_llm_connection.py
```

- Godot 开始游戏时勾选“启用 LLM”，才会为该局启用生成；全局环境变量与单局开关必须同时开启。
- 配置只从 `.env` 或环境变量读取，不提交真实 API Key。
- LLM 只接收经过权限过滤的角色状态与 RAG 上下文。
- 目标选择、夜晚行动、投票、身份、出局和胜负仍由当前规则代码处理。
- 请求失败、超时、无效 JSON、替换字符或输出越界时，自动退回当前模板逻辑，游戏仍可完整运行。

## 狼人杀状态机

```text
NIGHT → SHERIFF_SIGNUP → SHERIFF_SPEECH → SHERIFF_WITHDRAWAL（第一天）
  → SHERIFF_VOTE → SHERIFF_RUNOFF_SPEECH/VOTE（平票时至多一次）
  → 首夜结果公布 → HUNTER_SHOT（可选）→ BADGE_TRANSFER（可选）
  → MEETING_ORDER → DAY_MEETING → SHERIFF_NOMINATION（玩家警长时）
  → FREE_ACTIVITY → VOTE → HUNTER_SHOT（可选）
  → BADGE_TRANSFER（警长出局时）→ NIGHT / GAME_OVER
```

- `NIGHT`：狼人、预言家、女巫和守卫执行身份行动。
- `HUNTER_SHOT`：玩家猎人因狼袭或放逐出局后选择开枪目标或不开枪；被毒出局不能开枪。
- `SHERIFF_SIGNUP`：第一天玩家选择是否上警，NPC 同步形成候选人列表。
- `SHERIFF_SPEECH`：候选人按随机顺序发言；NPC 真预言家必须报出真实验人。
- `SHERIFF_WITHDRAWAL`：所有候选人明确继续或退水，阶段不会自动省略。
- `SHERIFF_VOTE`：警下角色同时投票；最高票平局时只进行一次 PK 发言和重投。
- 首夜结果公布：竞选全部结束后才执行狼刀、解药、毒药和守卫结果；后续夜晚不延迟。
- `MEETING_ORDER`：警长选择出局左/右或警左/右，没有警长时使用随机首位和方向。
- `DAY_MEETING`：存活角色逐个公开发言；有夜间出局锚点时警长按自然座次发言，并可提出暂时归票。
- `SHERIFF_NOMINATION`：全员发言后，玩家警长维持或调整最终归票，自己的正式投票随之锁定。
- `FREE_ACTIVITY`：走近存活 NPC 私密追问，每名 NPC 每天第一次追问会影响决策。
- `VOTE`：玩家提交目标和理由后，全部票同时产生并立即结算。
- `BADGE_TRANSFER`：警长出局后移交或撕毁警徽；若同时触发猎人，先完成开枪。

固定 12 人身份池为狼人 x4、预言家 x1、女巫 x1、猎人 x1、守卫 x1、村民 x4。固定座次为：玩家、梅西、C罗、周深、梅长苏、塞尔达、小骑士、大黄蜂、喜羊羊、懒羊羊、洛洛、奇异博士。`POST /api/game/start` 默认随机身份，也接受 `player_role` 指定玩家身份用于测试；服务端会从原身份池中取出该身份后再随机其余 11 人。

玩家是狼人时会在私有状态和角色卡中看到三名狼队友，NPC 狼人也会在内部关系中互认。玩家狼人提交的夜袭目标拥有最终决定权；全为 NPC 狼人时按多数目标结算。狼人公开决策会避开低压力队友，也允许在队友承受高公开压力时策略性切割。

第一天 NPC 真预言家必定上警并公布真实查验；玩家预言家可以不上警，也不强制公开真实信息。指定悍跳狼会根据玩家狼人的警上发言选择让跳、继续悍跳或退水，少数高策略局面允许双狼起跳。狼队可以发队友金水，并在高公开压力且局势允许时全局至多一次“狼查杀狼”。

参加过竞选的所有角色都不能投警长票，退水者仍保留竞选参与记录并继续禁投。首夜待公布角色在竞选期间仍视为存活，不会通过公开状态、日志或 RAG 泄露结果。

前夜有人出局时，警长选择出局左或出局右后按自身座位自然进入发言顺序；前夜无人出局时，选择警左或警右并自然最后发言。警长在自身轮次可以提出 `temporary_nomination_target_id`，后续 NPC 会把它作为公开判断因素；全员发言后再产生 `nomination_target_id`，可以维持或调整。

警长白天拥有 1.5 票。最终归票表示其正式投票目标，服务端会拒绝警长投给其他角色；其他角色只受到归票影响而不会被强制跟票。警长出局后可以移交或撕毁警徽。

女巫每局各有一瓶解药和毒药，每晚最多使用一瓶，仅第一夜可以自救；同一刀口被守卫和解药同时保护仍会出局。守卫不能连续两晚守同一目标。全部狼人出局则好人获胜；全部村民、全部神职出局，或存活狼人数不少于存活好人数形成控场时，狼人获胜。可开枪猎人因狼袭或放逐出局时先结算猎人技能，再检查控场。

正式出局记录包含 `source_action`、`source_actor_ids` 和 `source_target_id`。规则引擎会验证来源与本轮狼刀、毒药、猎人开枪或投票是否匹配，拒绝无来源、过期目标或目标不一致的出局。

## 狼人杀接口

- `GET /api/health`
- `GET /api/llm/status`
- `GET /api/rag/status`
- `POST /api/game/start`
- `GET /api/game/{game_id}/state`
- `GET /api/game/{game_id}/summary`
- `POST /api/night/action`
- `POST /api/night/resolve`
- `POST /api/hunter/shot`
- `POST /api/sheriff/signup`
- `POST /api/sheriff/player-speech`
- `POST /api/sheriff/npc-speech`
- `POST /api/sheriff/withdraw`
- `POST /api/sheriff/vote`
- `POST /api/sheriff/meeting-order`
- `POST /api/sheriff/nominate`
- `POST /api/sheriff/transfer`
- `POST /api/day/player-speech`
- `POST /api/day/npc-speech`
- `POST /api/day/private-chat`
- `POST /api/day/end-free-activity`
- `POST /api/vote/submit-and-resolve`

旧的 `POST /api/vote/npc-decisions`、`POST /api/vote/player` 与 `POST /api/vote/resolve` 仍保留兼容，但 Godot 主流程只调用同步结算接口。

`GET /api/game/{game_id}/state` 的 `meeting` 字段包含：

- `direction`：`clockwise` 或 `counterclockwise`。
- `order`：当天所有存活角色的发言顺序。
- `current_speaker_id`：当前允许发言的角色。
- `current_position` 与 `total_speakers`：会议进度。
- `completed`：会议是否完成。

同一响应的 `sheriff` 字段包含完整候选人、活跃候选人、退水名单、当前竞选发言者、轮次、投票资格及原因、可投目标、警长、发言锚点、暂时归票和最终归票目标。角色视图的 `sheriff_campaign_status` 为 `candidate`、`withdrawn`、`pk` 或空字符串，供 Godot 显示头顶标记。

同一响应的 `player_private_info.action_history` 是只对玩家可见的本局累计记录，包含夜间技能与结算结果、猎人开枪、警上操作、完整公开发言、私聊问题及放逐投票；新游戏使用新的状态数组，因此记录自动清空。

服务端会验证发言者。玩家和 NPC 都不能跳过顺序，也不能在同一天重复正式发言。

NPC 正式发言会检索知识库和当前已经发生的公开发言。返回的 `speech` 包含 `evidence_titles` 和 `retrieval_mode`，正文会引用最相关的一条公开安全证据。

公开发言会解析并记录身份与验人声明。真预言家可以公布实际查验；每局指定一名 NPC 狼人作为悍跳候选，可以起跳预言家并维护跨轮假验人记录；女巫、守卫和猎人也会根据已知信息、公开压力与性格决定是否公开技能信息。公共状态只返回中立的 `public_claims` 标签，不标记真假。

`config/npc_profiles.json` 中的 `speech_style`、`catchphrases` 和 `easter_eggs` 控制角色化表达。规则文本和 LLM 润色都必须保留公开声明中的身份、目标、结果与技能行动；校验器按事实而非模板字面判断，姓名、座位号、“好人/金水”等同义词和合法私聊代词会归一到同一事实。五轮均失败时响应返回 `llm_validation_failure`，当前调试版 Godot 会展示每轮完整原文与全部原因。

`POST /api/day/private-chat` 只允许在 `FREE_ACTIVITY` 使用。私聊不会写入 `public_logs`；同一 NPC 当天只有第一次提问会修改怀疑、信任和内部记忆，后续追问只返回回答。

私聊回复使用当前会话视角：NPC 以“我”自称、称玩家为“你”，其他角色显示“号码 + 名字”。玩家消息里的“我/自己”映射到玩家，“你”映射到当前 NPC；无法从本句或同一 NPC 最近私聊中解析的“他/她/TA”会触发澄清，并且不消耗当天的有效追问次数。

`GET /api/game/{game_id}/summary` 只允许在 `GAME_OVER` 后调用，返回：

- 获胜阵营和总天数。
- 每名角色的真实身份、阵营、胜负、生存结果和关联行动。
- 按阶段排序的全局时间线，包括夜间技能、查验、实际挡刀、公开身份声明、发言、完整私聊、投票理由和出局结果。
- 本局全部 LLM 校验失败记录；赛后响应包含未脱敏的原始返回。

## 小镇 NPC 接口

- `GET /health`
- `GET /npcs`
- `GET /knowledge`
- `GET /knowledge/search`
- `POST /chat`
- `GET /memory/{player_id}/{npc_name}`
- `DELETE /memory/{player_id}/{npc_name}`
- `DELETE /memory/{player_id}`
- `DELETE /memory`
- `POST /admin/reload-config`

普通聊天记忆保存在 `data/memory.json`。狼人杀的身份、关系、私有记忆和 `private_conversations` 只存在当前 `GAME_STORE`，两类记忆不会混用。

## 配置

- `config/npc_profiles.json`：NPC 人设、说话风格、口头禅、彩蛋与基础知识。
- `config/knowledge_base.json`：107 条静态知识，包括开发资料、十二人狼人杀规则、完整警长规则、身份声明规则和 11 名 NPC 的判断风格。
- `data/memory.json`：运行时普通对话记忆。

## 混合 RAG

- `app/rag.py` 使用 FastEmbed `0.7.4` 和 `BAAI/bge-small-zh-v1.5`。
- 静态知识在首次查询时生成向量并保存在内存中。
- 综合关键词分数与余弦相似度返回 Top-K 结果。
- `/chat` 使用静态知识；狼人杀私聊还会检索公开日志和当前 NPC 的私有记忆。
- 私有记忆来源不会通过响应标题泄露。
- NPC 正式发言和投票理由使用独立的公开决策检索器，只读取静态知识和正式公开发言。
- 私聊、查验结果和 NPC 内部记忆不会进入公开决策证据；私聊造成的怀疑值变化仍可间接影响目标选择。
- `NpcSpeechItem` 与 `NpcVoteDecision` 会返回 `evidence_titles` 和 `retrieval_mode`，便于 Godot 展示来源。
- `GET /api/rag/status` 返回 `hybrid` 或 `keyword`、模型名、索引状态和错误信息。
- 设置 `AGENT_TOWN_DISABLE_VECTOR_RAG=1` 可以强制测试关键词降级。

## 自检

在项目根目录运行：

```bash
backend/.venv/bin/python scripts/smoke_check.py
```

自检会覆盖配置、编译、DeepSeek 非思考 JSON 模式、五轮结构化事实校验、验人声明归属与隐式起跳、真实自然改写与篡改反例、调试原文展示与日志审计、玩家累计行动历史、LLM 回退、语义召回、关键词降级、公开决策证据、私密来源隔离、私聊指代、十二人会议顺序、指定玩家女巫与双药、首夜延迟公布与合法出局来源、警上报名、真预言家强制起跳、狼人让跳、退水持续禁投、一次 PK、警长自然座次、暂时归票与最终改票、1.5 票、首夜警长猎人开枪后的警徽移交、狼队互认、狼查杀狼、神职公开信息、角色化表达、屠边与控场胜负、同步投票、结束复盘、候选头顶标记、控制面板焦点清理、输入移动锁、全局中文字体和 Godot 错误日志。
