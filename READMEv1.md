# 类狼人杀智能 NPC 游戏 Demo

> 历史设计稿：本文保留早期六人制方案用于追溯设计过程。当前十二人制实现、运行方式和规则以 [`README.md`](README.md) 为准。

本项目是一个基于 **Godot 4 + Python FastAPI + 标准 RAG + LLM API** 的类狼人杀游戏 demo。

当前版本目标是做出一个 **6 人局、可单机游玩、NPC 具备长期记忆与人格演化能力** 的智能狼人杀原型。

游戏规则由代码严格控制，LLM 只负责 NPC 的表达、心理活动、人格变化、复杂欺骗话术和玩家自由输入解析，不允许 LLM 直接决定死亡、身份、票数、胜负等核心游戏状态。

---

# 1. 项目定位

## 1.1 游戏类型

本项目是一个类狼人杀的单机推理游戏。

初始版本包含：

```text
1 名真实玩家
5 名 NPC
总共 6 名角色
```

基础身份池：

```text
狼人 x 2
预言家 x 1
守卫 x 1
村民 x 2
```

玩家可以自由输入发言，NPC 会根据身份、阵营、记忆、怀疑值、情绪、人格、私聊关系和动态联盟进行发言与投票。

---

## 1.2 技术目标

本项目不是普通的模板狼人杀，而是一个带有智能 NPC 系统的游戏原型。

核心技术目标包括：

```text
Godot 前端展示与交互
FastAPI 后端管理智能逻辑
标准 RAG 支撑 NPC 记忆检索
LLM API 生成 NPC 发言与心理活动
自由输入解析玩家发言
多轮人格演化
复杂长线欺骗
NPC 私聊
动态联盟
情绪系统
```

---

## 1.3 设计原则

最重要原则：

```text
游戏规则 = 代码控制
NPC 表达 = LLM 生成
```

LLM 可以负责：

```text
生成 NPC 发言
生成 NPC 心理活动
生成 NPC 私聊内容
总结 NPC 对局记忆
分析玩家自由输入
更新 NPC 主观判断
生成欺骗、辩解、带节奏、伪装等话术
```

LLM 不可以负责：

```text
直接决定谁死亡
直接决定谁胜利
直接修改角色身份
直接修改投票结果
直接伪造不存在的游戏状态
直接决定夜晚行动结果
绕过代码规则修改对局
```

所有关键状态必须由后端规则代码或 Godot 游戏逻辑确认。

---

# 2. 推荐开发环境

## 2.1 本地设备

当前目标设备：

```text
MacBook Air M2
16GB 内存
256GB 存储
macOS
```

该配置可以运行本项目的推荐架构：

```text
Godot 前端
+
本地 FastAPI 后端
+
本地向量数据库
+
云端 LLM API
```

不建议第一版在本机运行本地大模型。M2 MacBook Air 可以运行轻量后端和 RAG，但本地大模型会明显增加发热、延迟和存储压力。

---

## 2.2 推荐软件

```text
Godot 4.x
VS Code
Python 3.11+
Git
uv 或 pip
SQLite
Chroma 或 FAISS
```

推荐优先使用：

```text
Godot 4.x Apple Silicon 版本
Python 3.11
FastAPI
Uvicorn
ChromaDB
SentenceTransformers 或云端 Embedding API
```

---

# 3. 总体技术架构

## 3.1 架构总览

```text
玩家
 ↓
Godot 4 客户端
 ↓ HTTP / JSON
FastAPI 后端
 ↓
Game Rule Engine
 ↓
NPC State Manager
 ↓
RAG Memory System
 ↓
LLM Adapter
 ↓
外部 LLM API
```

---

## 3.2 模块职责

### Godot 前端

负责：

```text
游戏画面展示
玩家输入
角色卡片显示
阶段切换展示
夜晚行动选择
白天自由发言输入
投票选择
游戏日志展示
结算页展示
```

不负责复杂智能逻辑。

---

### FastAPI 后端

负责：

```text
管理游戏状态
处理规则结算
管理 NPC 记忆
处理玩家自由输入
调用 RAG 检索
调用 LLM API
生成 NPC 发言
生成 NPC 私聊
更新 NPC 情绪和人格状态
返回结构化结果给 Godot
```

---

### RAG 系统

负责：

```text
保存对局历史
保存 NPC 长期记忆
保存 NPC 私聊记忆
保存角色人设
保存规则说明
保存历史发言
保存历史投票
保存情绪变化
保存联盟关系
被欺骗与欺骗他人的记录
```

---

### LLM API

负责：

```text
根据后端提供的结构化上下文生成自然语言
分析玩家自由输入
生成 NPC 发言
生成 NPC 心理活动
生成 NPC 私聊内容
总结每轮记忆
生成复杂欺骗策略的表达文本
```

LLM API 提供商不在第一版中硬绑定。

---

# 4. LLM API 设计

## 4.1 供应商不绑定原则

项目不直接绑定具体 LLM 厂商，而是通过统一适配层调用。

支持后续接入：

```text
OpenAI compatible API
DeepSeek API
通义千问 API
智谱 API
Moonshot API
Gemini API
Claude API
本地 Ollama API
其他 OpenAI-compatible 服务
```

第一版不要求所有厂商都实现，只需要实现一个通用接口：

```text
LLMClient.generate()
LLMClient.generate_json()
LLMClient.embed()
```

---

## 4.2 费用控制原则

由于本项目有 5 个 NPC，不能每一句话都盲目调用大模型。

需要遵守：

```text
能用规则解决的不用 LLM
能批量生成的不要逐个请求
NPC 发言控制在 1 到 3 句
每轮只检索必要记忆
Prompt 不要塞完整对局日志
优先使用低价或免费额度 API
支持随时切换模型
支持 mock 模式
```

---

## 4.3 环境变量配置

后端通过 `.env` 配置模型供应商。

示例：

```env
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.example.com/v1
LLM_API_KEY=your_api_key_here
LLM_MODEL=cheap-chat-model
LLM_EMBEDDING_MODEL=cheap-embedding-model

LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500
LLM_TIMEOUT_SECONDS=30

ENABLE_LLM=true
ENABLE_RAG=true
ENABLE_NPC_PRIVATE_CHAT=true
ENABLE_EMOTION_SYSTEM=true
ENABLE_PERSONALITY_EVOLUTION=true
```

注意：

```text
不要把真实 API Key 提交到 Git 仓库。
```

需要添加 `.gitignore`：

```gitignore
.env
backend/.env
*.sqlite3
*.db
/chroma_db/
/vector_store/
__pycache__/
.venv/
```

---

# 5. RAG 设计

## 5.1 RAG 目标

本项目直接使用标准 RAG，而不是简单关键词检索。

RAG 用于让 NPC 具备：

```text
短期记忆
长期记忆
局内上下文记忆
私聊记忆
人格记忆
情绪记忆
历史投票记忆
历史发言记忆
联盟关系记忆
被欺骗与欺骗他人的记录
```

---

## 5.2 RAG 技术路线

推荐第一版使用：

```text
ChromaDB
+
Embedding Model
+
SQLite 元数据存储
```

也可以后续切换：

```text
FAISS
Qdrant
Milvus
pgvector
```

第一版优先 ChromaDB，因为本地开发简单，适合 demo。

---

## 5.3 RAG 数据分类

RAG 中至少保存以下类型文档：

```text
rule_doc             游戏规则
role_doc             身份说明
npc_profile          NPC 人设
npc_memory           NPC 长期记忆
npc_private_memory   NPC 私聊记忆
public_event         公开事件
speech_record        发言记录
vote_record          投票记录
night_record         夜晚记录
emotion_record       情绪变化
alliance_record      联盟关系变化
deception_record     欺骗与伪装记录
player_input_record  玩家自由输入记录
```

---

## 5.4 RAG 文档结构

每条记忆存储为：

```json
{
  "doc_id": "memory_000001",
  "game_id": "game_001",
  "day": 2,
  "phase": "day_speech",
  "owner_character_id": 3,
  "visibility": "private",
  "memory_type": "npc_memory",
  "importance": 0.85,
  "emotion_impact": 0.4,
  "content": "3号NPC认为1号玩家上一轮发言过于强势，可能在带节奏。",
  "created_at": "2026-07-10T10:30:00",
  "metadata": {
    "source": "speech_analysis",
    "related_characters": [1, 3],
    "tags": ["suspicion", "player", "day2"]
  }
}
```

---

## 5.5 记忆可见性

记忆分为三类：

### public

所有角色可见。

例如：

```text
昨晚 4 号死亡。
2 号投票给了 5 号。
1 号玩家说怀疑 3 号。
```

### private

单个 NPC 私有。

例如：

```text
3 号 NPC 内心认为 1 号玩家很危险。
4 号 NPC 其实是狼人，正在计划伪装成村民。
```

### faction

阵营内部可见。

例如：

```text
狼人知道彼此身份。
狼人私聊决定今晚刀 5 号。
```

---

## 5.6 检索策略

每次生成 NPC 发言时，RAG 应检索：

```text
当前阶段公开事件
该 NPC 的长期记忆
该 NPC 的最近私有记忆
该 NPC 对其他角色的怀疑记录
该 NPC 的情绪变化记录
该 NPC 的联盟关系记录
与当前讨论目标相关的历史发言
```

推荐检索参数：

```text
top_k_public = 5
top_k_private = 5
top_k_emotion = 3
top_k_alliance = 3
top_k_recent = 5
```

最终 prompt 中不要塞太多内容，只保留最相关记忆。

---

# 6. 游戏规则设计

## 6.1 角色身份

身份池固定为：

```text
狼人 x 2
预言家 x 1
守卫 x 1
村民 x 2
```

每局开始随机分配身份。

玩家和 NPC 都可能成为任意身份。

---

## 6.2 阵营

```text
狼人阵营：狼人
好人阵营：预言家、守卫、村民
```

---

## 6.3 胜利条件

### 狼人胜利

第一版采用简单判断：

```text
狼人存活人数 >= 非狼人存活人数
```

### 好人胜利

```text
所有狼人死亡
```

---

## 6.4 游戏阶段

```text
INIT
ROLE_ASSIGNMENT
NIGHT
NIGHT_RESOLVE
DAY_ANNOUNCE
DAY_SPEECH
NPC_PRIVATE_CHAT
VOTE
VOTE_RESOLVE
MEMORY_SUMMARY
GAME_OVER
```

---

## 6.5 每轮流程

```text
开始游戏
 ↓
分配身份
 ↓
夜晚阶段
 ↓
夜晚结算
 ↓
白天公布死亡
 ↓
NPC 私聊阶段
 ↓
白天公开发言
 ↓
玩家自由输入发言
 ↓
后端解析玩家发言
 ↓
NPC 继续发言或回应
 ↓
投票阶段
 ↓
投票结算
 ↓
记忆总结
 ↓
胜负判断
 ↓
未结束则进入下一夜
```

---

# 7. NPC 智能系统

## 7.1 NPC 必须具备的能力

每个 NPC 至少具备：

```text
身份
阵营
记忆
怀疑值
情绪状态
人格参数
公开发言能力
私聊能力
投票能力
伪装能力
长线欺骗能力
多轮人格演化
动态联盟能力
```

---

## 7.2 NPC 数据结构

```json
{
  "character_id": 2,
  "name": "阿橙",
  "is_player": false,
  "role": "werewolf",
  "camp": "werewolf",
  "alive": true,
  "personality": {
    "aggressiveness": 0.7,
    "cautiousness": 0.4,
    "deception": 0.8,
    "logic": 0.6,
    "empathy": 0.3,
    "leadership": 0.5
  },
  "emotion": {
    "trust": 0.4,
    "fear": 0.2,
    "anger": 0.1,
    "stress": 0.5,
    "confidence": 0.7
  },
  "suspicion": {
    "1": 35,
    "3": 10,
    "4": 20,
    "5": 60,
    "6": 15
  },
  "relationships": {
    "1": {
      "trust": 0.3,
      "alliance": "none",
      "notes": "认为1号玩家发言强势"
    },
    "4": {
      "trust": 0.8,
      "alliance": "wolf_teammate",
      "notes": "狼人队友"
    }
  },
  "memory_summary": "阿橙正在伪装成谨慎好人，试图把怀疑引向5号。"
}
```

---

## 7.3 人格参数说明

```text
aggressiveness  攻击性，越高越容易主动怀疑别人
cautiousness    谨慎性，越高越不容易跳身份或强推
deception       欺骗能力，狼人高欺骗会更擅长伪装
logic           逻辑性，越高越会引用投票和发言证据
empathy         共情性，越高越容易被情绪影响
leadership      领导力，越高越容易带节奏和组织联盟
```

---

## 7.4 情绪系统

NPC 情绪会随对局变化。

基础情绪：

```text
trust       信任感
fear        恐惧
anger       愤怒
stress      压力
confidence  自信
```

情绪变化示例：

```text
被多人怀疑：stress +0.2
被玩家攻击：anger +0.1
队友死亡：fear +0.2
成功带票：confidence +0.2
被查杀：stress +0.5
被保护：trust toward guard +0.2
```

情绪会影响发言：

```text
stress 高：发言更防御、更慌张
anger 高：发言更攻击
confidence 高：更敢带节奏
fear 高：更容易保守
trust 高：更愿意站边某人
```

---

## 7.5 怀疑值系统

每个 NPC 对其他角色有怀疑值：

```text
0 = 完全不怀疑
100 = 极度怀疑
```

怀疑值来源：

```text
投票行为
发言内容
夜晚死亡结果
预言家查验
私聊内容
阵营信息
情绪影响
LLM 对玩家自由输入的解析结果
```

怀疑值变化示例：

```text
某人强推好人出局：+25
某人被预言家查杀：+80
某人发言模糊：+10
某人攻击自己：+15
某人投票和自己一致：-5
某人救过自己：-20
狼人队友：公开怀疑可低，内部信任高
```

---

## 7.6 复杂长线欺骗

狼人 NPC 需要具备长线欺骗能力。

包括：

```text
伪装成村民
伪装成预言家
假装犹豫
故意轻微怀疑狼队友
在关键轮次带票
制造错误逻辑链
利用玩家发言漏洞
诱导好人互相怀疑
阶段性改变话术风格
```

长线欺骗不是让 LLM 直接修改规则，而是让 LLM 基于后端提供的身份和目标生成合理表达。

示例：

```text
狼人 NPC 内部目标：保护4号狼队友，转移焦点到5号村民。
LLM 输出发言：我不是说5号一定是狼，但他昨天投票跟风太明显了，我觉得今天至少应该让他解释一下。
```

---

## 7.7 多轮人格演化

NPC 人格不会每轮完全重置。

每轮结束后，根据事件微调人格状态：

```text
连续被怀疑：cautiousness +0.1, confidence -0.1
成功带票：leadership +0.1, confidence +0.1
欺骗成功：deception +0.05
误判严重：logic -0.05, stress +0.1
被玩家信任：trust toward player +0.1
```

人格演化必须有上限和下限：

```text
所有人格参数限制在 0.0 到 1.0
每轮变化不超过 0.1
```

---

## 7.8 NPC 私聊系统

NPC 私聊用于增强真实感和策略深度。

私聊类型：

```text
狼人夜间私聊
好人非正式私聊
动态联盟私聊
试探性私聊
欺骗性私聊
```

MVP 阶段建议只开放后端模拟，不一定全部展示给玩家。

### 狼人私聊

狼人知道彼此身份，可以在夜晚生成私聊内容：

```text
今晚刀谁？
白天谁来带节奏？
是否牺牲一个狼队友做身份？
是否悍跳预言家？
```

### 动态联盟私聊

NPC 可以与信任对象形成临时联盟：

```text
3号和5号互相信任，决定白天一起观察2号。
```

联盟不是绝对阵营，只是主观关系。

---

## 7.9 动态联盟系统

联盟关系包括：

```text
none
soft_trust
temporary_alliance
strong_alliance
wolf_teammate
broken_alliance
manipulated
```

联盟会影响：

```text
发言站边
投票倾向
私聊对象
怀疑值变化
被背刺后的情绪变化
```

---

# 8. 玩家自由输入系统

## 8.1 玩家输入目标

玩家白天可以自由输入发言，例如：

```text
我觉得3号很奇怪，他昨天一直在跟票，而且今天又不解释自己的逻辑。
```

后端需要解析这段文本，并提取结构化信息。

---

## 8.2 玩家输入解析结果

LLM 应输出 JSON，不直接输出自然语言。

示例：

```json
{
  "speaker_id": 1,
  "mentioned_characters": [3],
  "accusations": [
    {
      "target_id": 3,
      "reason": "昨天跟票且今天没有解释逻辑",
      "intensity": 0.7
    }
  ],
  "claims": [],
  "self_claimed_role": null,
  "tone": "suspicious",
  "strategy": "push_suspicion",
  "should_affect_suspicion": true
}
```

后端根据 JSON 更新：

```text
公开发言记录
相关 NPC 对玩家的信任或怀疑
相关目标角色的怀疑值
当前白天讨论焦点
```

---

## 8.3 玩家跳身份解析

如果玩家说：

```text
我是预言家，我昨晚查了4号，4号是狼人。
```

LLM 应解析为：

```json
{
  "speaker_id": 1,
  "mentioned_characters": [4],
  "claims": [
    {
      "claim_type": "role_claim",
      "role": "seer"
    },
    {
      "claim_type": "check_result",
      "target_id": 4,
      "result": "werewolf"
    }
  ],
  "tone": "assertive",
  "strategy": "reveal_role"
}
```

注意：

```text
玩家声称自己是预言家，不代表代码中的真实身份会改变。
```

后端只能记录“玩家声称”，不能改真实身份。

---

# 9. Prompt 设计

## 9.1 NPC 公开发言 Prompt

输入给 LLM 的信息应包括：

```text
当前游戏阶段
当前天数
当前 NPC 身份
当前 NPC 阵营
当前 NPC 人格
当前 NPC 情绪
当前 NPC 公开可见信息
当前 NPC 私有记忆
当前 NPC 对各角色怀疑值
当前 NPC 的策略目标
RAG 检索出的相关记忆
玩家刚刚的自由输入
输出格式要求
```

---

## 9.2 NPC 发言输出格式

LLM 必须返回 JSON：

```json
{
  "character_id": 3,
  "public_speech": "我觉得1号玩家刚才说得有一部分道理，但他推3号的速度太快了，我会先观察他的投票。",
  "inner_thought": "我不能直接反击1号，否则会显得我很心虚。",
  "target_focus": [1],
  "emotion_delta": {
    "stress": 0.1,
    "anger": 0.05,
    "confidence": -0.05
  },
  "suspicion_delta": {
    "1": 10,
    "4": -5
  },
  "memory_to_store": [
    "3号认为1号玩家正在试图掌控白天节奏。"
  ]
}
```

Godot 前端只展示：

```text
public_speech
```

后端保存：

```text
inner_thought
emotion_delta
suspicion_delta
memory_to_store
```

---

## 9.3 狼人私聊 Prompt

狼人私聊可以输出：

```json
{
  "participants": [2, 5],
  "private_chat": [
    {
      "speaker_id": 2,
      "text": "今天我们不要一起冲票，容易暴露。可以先让5号装作怀疑我一点。"
    },
    {
      "speaker_id": 5,
      "text": "我会轻轻踩你，但不会真的投你。"
    }
  ],
  "strategy_summary": "狼人决定轻微互踩，主要把焦点转移到3号村民。",
  "planned_vote_bias": {
    "2": 3,
    "5": 3
  },
  "memory_to_store": [
    "2号和5号狼人决定白天轻微互踩以降低绑定感。"
  ]
}
```

---

## 9.4 投票建议 Prompt

LLM 可以参与“解释投票倾向”，但最终投票仍由后端计算。

LLM 输出：

```json
{
  "character_id": 4,
  "preferred_vote_target": 2,
  "reason": "2号连续两轮都在转移焦点，而且他的发言和投票不一致。",
  "confidence": 0.74
}
```

后端结合怀疑值、阵营、人格、联盟关系后决定实际投票。

---

# 10. API 接口设计

后端基础地址：

```text
http://127.0.0.1:8000
```

---

## 10.1 健康检查

### GET /api/health

Response:

```json
{
  "status": "ok",
  "llm_enabled": true,
  "rag_enabled": true,
  "provider": "openai_compatible"
}
```

---

## 10.2 开始新游戏

### POST /api/game/start

Request:

```json
{
  "player_name": "玩家",
  "npc_count": 5,
  "roles": {
    "werewolf": 2,
    "seer": 1,
    "guard": 1,
    "villager": 2
  },
  "enable_llm": true,
  "enable_rag": true
}
```

Response:

```json
{
  "game_id": "game_001",
  "day": 1,
  "phase": "ROLE_ASSIGNMENT",
  "player_character_id": 1,
  "characters": [
    {
      "id": 1,
      "name": "玩家",
      "is_player": true,
      "alive": true,
      "role_visible_to_player": "seer"
    },
    {
      "id": 2,
      "name": "阿橙",
      "is_player": false,
      "alive": true,
      "role_visible_to_player": null
    }
  ],
  "message": "游戏开始，你的身份是预言家。"
}
```

---

## 10.3 获取游戏状态

### GET /api/game/{game_id}/state

Response:

```json
{
  "game_id": "game_001",
  "day": 1,
  "phase": "DAY_SPEECH",
  "characters": [],
  "public_logs": [],
  "player_private_info": {
    "role": "seer",
    "camp": "good",
    "last_check_result": {
      "target_id": 3,
      "camp": "werewolf"
    }
  }
}
```

---

## 10.4 提交玩家夜晚行动

### POST /api/night/action

Request:

```json
{
  "game_id": "game_001",
  "character_id": 1,
  "action_type": "seer_check",
  "target_id": 3
}
```

支持的 action_type：

```text
werewolf_kill
seer_check
guard_protect
none
```

Response:

```json
{
  "success": true,
  "message": "行动已记录。"
}
```

---

## 10.5 结算夜晚

### POST /api/night/resolve

Request:

```json
{
  "game_id": "game_001"
}
```

Response:

```json
{
  "game_id": "game_001",
  "day": 1,
  "dead_characters": [4],
  "is_peaceful_night": false,
  "public_message": "昨晚4号玩家死亡。",
  "player_private_result": {
    "seer_check": {
      "target_id": 3,
      "result": "werewolf"
    }
  }
}
```

---

## 10.6 生成 NPC 私聊

### POST /api/npc/private-chat

Request:

```json
{
  "game_id": "game_001",
  "day": 1,
  "phase": "NPC_PRIVATE_CHAT"
}
```

Response:

```json
{
  "private_chats": [
    {
      "chat_id": "chat_001",
      "participants": [2, 5],
      "visibility_to_player": false,
      "summary_for_debug": "狼人决定白天轻微互踩，并把焦点转移到3号。"
    }
  ]
}
```

开发模式下可以显示 debug summary，正式游戏中默认不展示给玩家。

---

## 10.7 玩家提交自由发言

### POST /api/day/player-speech

Request:

```json
{
  "game_id": "game_001",
  "character_id": 1,
  "speech": "我觉得3号很奇怪，他昨天一直在跟票，而且今天又不解释。"
}
```

Response:

```json
{
  "parsed": {
    "mentioned_characters": [3],
    "accusations": [
      {
        "target_id": 3,
        "reason": "跟票且没有解释",
        "intensity": 0.7
      }
    ],
    "claims": [],
    "tone": "suspicious"
  },
  "public_log": "1号玩家：我觉得3号很奇怪，他昨天一直在跟票，而且今天又不解释。",
  "state_updates": {
    "discussion_focus": [3]
  }
}
```

---

## 10.8 生成 NPC 公开发言

### POST /api/day/npc-speeches

Request:

```json
{
  "game_id": "game_001",
  "day": 1,
  "respond_to_player": true
}
```

Response:

```json
{
  "speeches": [
    {
      "character_id": 2,
      "name": "阿橙",
      "speech": "我觉得1号说得有点道理，但3号是不是狼还不能这么快下结论。"
    },
    {
      "character_id": 3,
      "name": "小蓝",
      "speech": "我昨天投票确实有点跟票，但那是因为当时信息太少，不代表我是狼。"
    }
  ],
  "memory_updates": [
    {
      "owner_character_id": 2,
      "content": "2号认为1号玩家正在推动大家怀疑3号。"
    }
  ]
}
```

---

## 10.9 获取投票建议

### POST /api/vote/npc-decisions

Request:

```json
{
  "game_id": "game_001"
}
```

Response:

```json
{
  "npc_votes": [
    {
      "character_id": 2,
      "target_id": 3,
      "reason": "3号今天防御过多，且历史投票可疑。"
    },
    {
      "character_id": 3,
      "target_id": 2,
      "reason": "2号一直在推动大家怀疑我。"
    }
  ]
}
```

---

## 10.10 玩家提交投票

### POST /api/vote/player

Request:

```json
{
  "game_id": "game_001",
  "character_id": 1,
  "target_id": 3
}
```

Response:

```json
{
  "success": true,
  "message": "投票已记录。"
}
```

---

## 10.11 结算投票

### POST /api/vote/resolve

Request:

```json
{
  "game_id": "game_001"
}
```

Response:

```json
{
  "exiled_character_id": 3,
  "vote_result": {
    "1": 3,
    "2": 3,
    "3": 2,
    "4": 3,
    "5": 3,
    "6": 2
  },
  "public_message": "3号玩家被放逐。",
  "is_game_over": false,
  "winner": null
}
```

---

## 10.12 记忆总结

### POST /api/memory/summarize

Request:

```json
{
  "game_id": "game_001",
  "day": 1
}
```

Response:

```json
{
  "summaries": [
    {
      "character_id": 2,
      "summary": "2号今天成功把部分怀疑转移到3号，但1号玩家仍然对局势有较强影响力。"
    }
  ]
}
```

---

## 10.13 游戏结算

### GET /api/game/{game_id}/result

Response:

```json
{
  "game_id": "game_001",
  "winner": "good",
  "characters": [
    {
      "id": 1,
      "name": "玩家",
      "role": "seer",
      "camp": "good",
      "alive": true
    },
    {
      "id": 2,
      "name": "阿橙",
      "role": "werewolf",
      "camp": "werewolf",
      "alive": false
    }
  ],
  "public_logs": [],
  "summary": "好人阵营获胜。"
}
```

---

# 11. 推荐项目目录结构

```text
wolf-like-game/
├── README.md
├── .gitignore
├── godot/
│   ├── project.godot
│   ├── scenes/
│   │   ├── main/
│   │   │   └── Main.tscn
│   │   ├── game/
│   │   │   ├── GameScreen.tscn
│   │   │   ├── NightScreen.tscn
│   │   │   ├── DayScreen.tscn
│   │   │   ├── PrivateChatDebugScreen.tscn
│   │   │   ├── VoteScreen.tscn
│   │   │   └── ResultScreen.tscn
│   │   └── ui/
│   │       ├── CharacterCard.tscn
│   │       ├── DialogueBox.tscn
│   │       ├── SpeechInputBox.tscn
│   │       ├── VotePanel.tscn
│   │       └── LogPanel.tscn
│   ├── scripts/
│   │   ├── autoload/
│   │   │   ├── GameClient.gd
│   │   │   ├── EventBus.gd
│   │   │   └── Config.gd
│   │   ├── api/
│   │   │   └── ApiClient.gd
│   │   ├── ui/
│   │   │   ├── CharacterCard.gd
│   │   │   ├── SpeechInputBox.gd
│   │   │   ├── VotePanel.gd
│   │   │   └── LogPanel.gd
│   │   └── screens/
│   │       ├── Main.gd
│   │       ├── GameScreen.gd
│   │       ├── NightScreen.gd
│   │       ├── DayScreen.gd
│   │       ├── VoteScreen.gd
│   │       └── ResultScreen.gd
│   └── assets/
│       ├── portraits/
│       ├── icons/
│       └── fonts/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── game_routes.py
│   │   │   ├── night_routes.py
│   │   │   ├── day_routes.py
│   │   │   ├── vote_routes.py
│   │   │   ├── npc_routes.py
│   │   │   └── memory_routes.py
│   │   ├── core/
│   │   │   ├── game_engine.py
│   │   │   ├── rule_resolver.py
│   │   │   ├── vote_resolver.py
│   │   │   ├── win_checker.py
│   │   │   └── phase_manager.py
│   │   ├── models/
│   │   │   ├── character.py
│   │   │   ├── game_state.py
│   │   │   ├── role.py
│   │   │   ├── npc_state.py
│   │   │   ├── memory.py
│   │   │   └── api_schema.py
│   │   ├── npc/
│   │   │   ├── npc_brain.py
│   │   │   ├── suspicion_system.py
│   │   │   ├── emotion_system.py
│   │   │   ├── personality_system.py
│   │   │   ├── alliance_system.py
│   │   │   ├── deception_system.py
│   │   │   └── private_chat_system.py
│   │   ├── rag/
│   │   │   ├── vector_store.py
│   │   │   ├── embedding_client.py
│   │   │   ├── retriever.py
│   │   │   ├── memory_writer.py
│   │   │   └── memory_summarizer.py
│   │   ├── llm/
│   │   │   ├── llm_client.py
│   │   │   ├── providers/
│   │   │   │   ├── base.py
│   │   │   │   ├── openai_compatible.py
│   │   │   │   └── mock_provider.py
│   │   │   ├── prompts/
│   │   │   │   ├── npc_speech_prompt.py
│   │   │   │   ├── player_parse_prompt.py
│   │   │   │   ├── private_chat_prompt.py
│   │   │   │   ├── memory_summary_prompt.py
│   │   │   │   └── vote_reason_prompt.py
│   │   │   └── json_guard.py
│   │   ├── storage/
│   │   │   ├── database.py
│   │   │   ├── repositories.py
│   │   │   └── migrations/
│   │   └── utils/
│   │       ├── random_utils.py
│   │       ├── id_utils.py
│   │       └── time_utils.py
│   ├── data/
│   │   ├── roles.json
│   │   ├── npc_names.json
│   │   ├── npc_personalities.json
│   │   └── rule_docs.md
│   ├── tests/
│   │   ├── test_game_flow.py
│   │   ├── test_rule_resolver.py
│   │   ├── test_vote_resolver.py
│   │   ├── test_rag.py
│   │   └── test_llm_mock.py
│   ├── requirements.txt
│   ├── .env.example
│   └── run_backend.sh
```

---

# 12. 后端核心模块说明

## 12.1 game_engine.py

负责完整游戏流程。

核心方法：

```python
start_game()
get_game_state()
advance_phase()
submit_player_action()
resolve_night()
submit_player_speech()
generate_npc_speeches()
resolve_vote()
check_game_over()
```

---

## 12.2 rule_resolver.py

负责夜晚规则。

```python
resolve_guard_action()
resolve_werewolf_action()
resolve_seer_action()
resolve_night_deaths()
```

---

## 12.3 vote_resolver.py

负责投票。

```python
collect_votes()
resolve_vote_result()
handle_tie()
exile_character()
```

MVP 平票规则：

```text
如果最高票平票，则从最高票角色中随机放逐一名。
```

后续可改为：

```text
平票 PK
重新发言
重新投票
无人出局
```

---

## 12.4 npc_brain.py

NPC 决策入口。

负责整合：

```text
怀疑值
情绪
人格
联盟
阵营
身份
RAG 记忆
LLM 生成
```

核心方法：

```python
generate_public_speech()
generate_private_chat()
choose_vote_target()
update_after_player_speech()
update_after_vote()
update_after_night()
```

---

## 12.5 suspicion_system.py

负责怀疑值更新。

```python
update_from_speech()
update_from_vote()
update_from_seer_claim()
update_from_death()
update_from_private_chat()
```

---

## 12.6 emotion_system.py

负责情绪变化。

```python
apply_event_emotion_delta()
normalize_emotion()
get_emotion_prompt_summary()
```

---

## 12.7 personality_system.py

负责人格演化。

```python
initialize_personality()
evolve_after_day()
evolve_after_successful_deception()
evolve_after_failed_push()
```

---

## 12.8 alliance_system.py

负责动态联盟。

```python
update_trust()
form_temporary_alliance()
break_alliance()
get_alliance_bias()
```

---

## 12.9 deception_system.py

负责狼人伪装和长线欺骗。

```python
build_deception_goal()
select_fake_position()
decide_whether_to_bus_teammate()
decide_whether_to_fake_claim()
```

---

# 13. 数据库设计

## 13.1 games 表

```sql
CREATE TABLE games (
    id TEXT PRIMARY KEY,
    day INTEGER NOT NULL,
    phase TEXT NOT NULL,
    winner TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

---

## 13.2 characters 表

```sql
CREATE TABLE characters (
    id INTEGER,
    game_id TEXT,
    name TEXT,
    is_player BOOLEAN,
    role TEXT,
    camp TEXT,
    alive BOOLEAN,
    personality_json TEXT,
    emotion_json TEXT,
    suspicion_json TEXT,
    relationships_json TEXT,
    memory_summary TEXT,
    PRIMARY KEY (game_id, id)
);
```

---

## 13.3 public_logs 表

```sql
CREATE TABLE public_logs (
    id TEXT PRIMARY KEY,
    game_id TEXT,
    day INTEGER,
    phase TEXT,
    content TEXT,
    created_at TEXT
);
```

---

## 13.4 votes 表

```sql
CREATE TABLE votes (
    id TEXT PRIMARY KEY,
    game_id TEXT,
    day INTEGER,
    voter_id INTEGER,
    target_id INTEGER,
    reason TEXT,
    created_at TEXT
);
```

---

## 13.5 night_actions 表

```sql
CREATE TABLE night_actions (
    id TEXT PRIMARY KEY,
    game_id TEXT,
    day INTEGER,
    actor_id INTEGER,
    action_type TEXT,
    target_id INTEGER,
    created_at TEXT
);
```

---

## 13.6 memories 表

```sql
CREATE TABLE memories (
    id TEXT PRIMARY KEY,
    game_id TEXT,
    owner_character_id INTEGER,
    day INTEGER,
    phase TEXT,
    memory_type TEXT,
    visibility TEXT,
    content TEXT,
    importance REAL,
    vector_doc_id TEXT,
    metadata_json TEXT,
    created_at TEXT
);
```

---

# 14. Godot 前端设计

## 14.1 前端职责

Godot 只负责：

```text
显示当前游戏状态
接收玩家操作
调用后端 API
展示后端返回结果
维护少量 UI 状态
```

不要在 Godot 中重复实现复杂 NPC 智能逻辑。

---

## 14.2 ApiClient.gd

统一封装 HTTP 请求。

建议方法：

```gdscript
func health_check()
func start_game(player_name: String)
func get_game_state(game_id: String)
func submit_night_action(game_id: String, action_type: String, target_id: int)
func resolve_night(game_id: String)
func submit_player_speech(game_id: String, speech: String)
func generate_npc_speeches(game_id: String)
func submit_player_vote(game_id: String, target_id: int)
func resolve_vote(game_id: String)
func get_result(game_id: String)
```

---

## 14.3 GameClient.gd

Godot 全局游戏客户端状态。

保存：

```gdscript
var game_id: String
var player_character_id: int
var current_phase: String
var day: int
var characters: Array
var public_logs: Array
```

---

## 14.4 UI 页面

### Main.tscn

功能：

```text
输入玩家名
开始游戏
检查后端连接
显示连接状态
```

### GameScreen.tscn

功能：

```text
总游戏容器
角色区
日志区
阶段区
操作区
```

### NightScreen.tscn

功能：

```text
根据玩家身份显示夜晚操作
提交行动
等待后端结算
```

### DayScreen.tscn

功能：

```text
显示死亡信息
显示 NPC 发言
玩家自由输入发言
继续生成 NPC 回应
进入投票
```

### VoteScreen.tscn

功能：

```text
显示存活角色
玩家选择投票目标
提交投票
显示投票结果
```

### ResultScreen.tscn

功能：

```text
显示胜利阵营
展示全部身份
展示关键日志
重新开始
```

---

# 15. 开发里程碑

## Milestone 1：项目骨架

目标：

```text
创建 Godot 项目
创建 FastAPI 项目
建立前后端目录
后端提供 /api/health
Godot 可以请求 /api/health
```

验收标准：

```text
运行 Godot 后可以看到后端连接成功。
```

---

## Milestone 2：游戏基础状态

目标：

```text
实现 /api/game/start
创建 6 名角色
随机分配身份
玩家可见自己的身份
NPC 身份隐藏
Godot 显示 6 张角色卡
```

验收标准：

```text
点击开始游戏后，前端能展示 6 名角色，玩家能看到自己的身份。
```

---

## Milestone 3：规则闭环

目标：

```text
实现夜晚行动
实现夜晚结算
实现白天公布
实现投票
实现胜负判断
暂时不接 LLM
NPC 行动使用规则随机
```

验收标准：

```text
不依赖 LLM，也可以完整跑完一局。
```

---

## Milestone 4：标准 RAG 接入

目标：

```text
接入 ChromaDB
接入 Embedding
实现记忆写入
实现记忆检索
保存公开事件
保存发言记录
保存投票记录
保存 NPC 私有记忆
```

验收标准：

```text
每轮发言和投票后，后端可以写入并检索相关记忆。
```

---

## Milestone 5：LLM Adapter 接入

目标：

```text
实现 LLMClient
实现 OpenAI-compatible provider
实现 mock provider
支持 .env 切换
实现 JSON 输出校验
```

验收标准：

```text
在 mock 模式下不需要 API Key 也能跑；
在真实 API 模式下可以生成 NPC 发言。
```

---

## Milestone 6：玩家自由输入解析

目标：

```text
玩家可以输入自然语言发言
后端调用 LLM 解析为 JSON
解析 accusation、claim、tone、target 等信息
更新公开日志和怀疑值
```

验收标准：

```text
玩家输入“我怀疑3号”，后端能识别目标为3号并影响 NPC 判断。
```

---

## Milestone 7：NPC LLM 公开发言

目标：

```text
每个 NPC 根据身份、人格、情绪、RAG 记忆生成公开发言
狼人能伪装
预言家能选择是否跳身份
村民能基于信息怀疑别人
```

验收标准：

```text
NPC 发言不再是模板，而是结合当前局势生成。
```

---

## Milestone 8：情绪与人格系统

目标：

```text
实现 NPC 情绪变化
实现 NPC 人格初始化
实现每轮人格微调
发言受情绪和人格影响
```

验收标准：

```text
被攻击的 NPC 会更紧张或愤怒；
高攻击性的 NPC 更容易主动推人。
```

---

## Milestone 9：私聊与动态联盟

目标：

```text
实现狼人私聊
实现 NPC 临时联盟
实现信任关系变化
实现私聊记忆写入 RAG
```

验收标准：

```text
狼人会在夜晚形成策略；
部分 NPC 会因为信任关系而互相站边。
```

---

## Milestone 10：复杂欺骗与长线策略

目标：

```text
狼人 NPC 具备长期伪装目标
可以轻踩队友
可以悍跳
可以转移焦点
可以利用玩家发言漏洞
```

验收标准：

```text
狼人 NPC 的行为在多轮中具有连续策略，而不是每轮随机发言。
```

---

## Milestone 11：完整体验优化

目标：

```text
优化 UI
增加日志展示
增加 debug 面板
增加结算分析
增加重开功能
优化 prompt 成本
减少 API 调用次数
```

验收标准：

```text
游戏可以稳定运行多局，且每局 NPC 表现有差异。
```

---

# 16. Codex 开发要求

## 16.1 总原则

Codex 开发时必须遵守：

```text
每次只做一个 milestone
每次修改后保证项目可运行
不要一次性重构全部代码
先保证规则闭环，再增强智能
不要让 LLM 控制规则结果
所有 API 都要有 mock 模式
所有 LLM JSON 输出都要校验
```

---

## 16.2 第一阶段任务

请 Codex 优先完成 Milestone 1：

```text
1. 创建 godot/ 目录和 backend/ 目录
2. 创建 FastAPI 基础项目
3. 实现 GET /api/health
4. 创建 Godot Main.tscn
5. 创建 ApiClient.gd
6. Godot 启动后请求 /api/health
7. UI 显示后端连接状态
8. 编写运行说明
```

完成后输出：

```text
本次新增文件
本次修改文件
如何启动后端
如何启动 Godot
当前已完成的功能
下一步建议
```

---

## 16.3 第二阶段任务

完成 Milestone 2：

```text
1. 实现角色模型
2. 实现身份模型
3. 实现 /api/game/start
4. 随机分配 6 人身份
5. 玩家只看到自己的身份
6. NPC 身份隐藏
7. Godot 展示角色卡
```

---

## 16.4 不允许提前做的事情

在 Milestone 3 之前，不要做：

```text
LLM 接入
RAG 接入
复杂 NPC 私聊
复杂人格系统
美术资源扩展
联网多人
账号系统
数据库复杂迁移
```

原因：

```text
必须先保证游戏基础流程能跑通。
```

---

# 17. 测试要求

## 17.1 后端测试

至少包含：

```text
test_game_start
test_role_assignment
test_night_resolve
test_vote_resolve
test_win_checker
test_player_speech_parse_mock
test_rag_memory_write
test_rag_retrieve
test_llm_mock_response
```

---

## 17.2 前端测试

Godot 手动测试流程：

```text
启动后端
打开 Godot
点击连接测试
点击开始游戏
查看角色卡
提交夜晚行动
进入白天
输入玩家发言
查看 NPC 发言
进入投票
查看放逐结果
重复直到游戏结束
```

---

## 17.3 LLM 安全测试

需要验证：

```text
LLM 不会改变角色真实身份
LLM 不会直接决定胜负
LLM 不会伪造不存在的查验结果
LLM 输出 JSON 不合法时后端能 fallback
API 失败时游戏仍可继续
```

---

# 18. Fallback 机制

任何 LLM API 失败时，系统不能崩溃。

需要 fallback 到：

```text
模板发言
规则投票
默认情绪变化
默认记忆总结
```

例如：

```python
if llm_failed:
    return template_speech(character, game_state)
```

---

# 19. 成本优化策略

为了控制 API 成本：

```text
玩家输入解析使用低价模型
NPC 发言尽量批量生成
记忆总结每轮只做一次
私聊可以只生成 summary
Embedding 使用低价或本地轻量 embedding
限制每个 prompt 的记忆条数
限制每个 NPC 发言长度
支持关闭私聊系统
支持关闭人格演化
支持 mock 模式
```

---

# 20. Debug 模式

开发阶段需要 debug 面板。

Debug 面板可以显示：

```text
所有角色真实身份
NPC 怀疑值
NPC 情绪
NPC 人格
NPC 联盟关系
狼人私聊 summary
RAG 检索结果
LLM 原始 JSON
API 调用耗时
Token 粗略消耗
```

正式游玩模式默认隐藏这些信息。

---

# 21. 当前版本不做的功能

第一大版本暂时不做：

```text
多人联机
语音聊天
账号系统
排行榜
商业化付费系统
复杂皮肤系统
3D 场景
本地大模型推理
移动端适配
完整美术包装
```

---

# 22. 后续扩展方向

## 22.1 多人联机

后续可以改为：

```text
1 名玩家 + 多名真人玩家 + NPC 混合局
```

但这需要加入：

```text
WebSocket
房间系统
玩家同步
断线重连
权限校验
```

---

## 22.2 更多身份

可加入：

```text
女巫
猎人
白痴
骑士
狼王
隐狼
丘比特
守墓人
摄梦人
```

每次只加入一个身份，并写单独测试。

---

## 22.3 更强 NPC 智能

后续可加入：

```text
NPC 复盘能力
NPC 反思机制
NPC 识别玩家话术风格
NPC 长期跨局记忆
NPC 对玩家形成长期印象
NPC 自适应难度
```

---

# 23. 最小成功标准

本项目第一阶段最终成功标准：

```text
1. Godot 可以启动游戏
2. FastAPI 可以运行后端
3. 玩家可以开始 6 人局
4. 玩家可以自由输入发言
5. 后端可以解析玩家发言
6. NPC 可以基于 RAG 和 LLM 生成发言
7. NPC 有怀疑值
8. NPC 有情绪
9. NPC 有人格
10. NPC 可以私聊
11. 狼人可以伪装和长线欺骗
12. 预言家可以选择是否跳身份
13. NPC 可以形成动态联盟
14. 游戏规则不被 LLM 控制
15. 游戏可以完整走到胜负结算
```

---

# 24. 启动方式

## 24.1 启动后端

进入后端目录：

```bash
cd backend
```

创建虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

复制环境变量：

```bash
cp .env.example .env
```

启动服务：

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

访问：

```text
http://127.0.0.1:8000/api/health
```

---

## 24.2 启动 Godot

```text
1. 打开 Godot
2. Import godot/project.godot
3. 打开 Main.tscn
4. 点击运行
5. 确认后端连接状态为 connected
6. 点击开始游戏
```

---

# 25. requirements.txt 建议

```txt
fastapi
uvicorn
pydantic
pydantic-settings
python-dotenv
httpx
sqlalchemy
chromadb
sentence-transformers
numpy
pytest
```

如果使用云端 embedding，可以暂时不安装 sentence-transformers。

---

# 26. .env.example

```env
APP_ENV=development
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000

DATABASE_URL=sqlite:///./wolf_game.sqlite3

ENABLE_LLM=false
ENABLE_RAG=true
ENABLE_NPC_PRIVATE_CHAT=true
ENABLE_EMOTION_SYSTEM=true
ENABLE_PERSONALITY_EVOLUTION=true
ENABLE_DEBUG_MODE=true

LLM_PROVIDER=mock
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=mock-model
LLM_EMBEDDING_MODEL=mock-embedding
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500
LLM_TIMEOUT_SECONDS=30

VECTOR_STORE_TYPE=chroma
VECTOR_STORE_PATH=./chroma_db
RAG_TOP_K=8
```

开发早期建议：

```text
ENABLE_LLM=false
LLM_PROVIDER=mock
```

等规则流程跑通后再打开真实 API。

---

# 27. 重要提醒

本项目的最大风险不是设备性能，而是系统复杂度。

因此开发顺序必须是：

```text
先规则闭环
再 RAG
再 LLM
再自由输入
再情绪人格
再私聊联盟
再复杂欺骗
```

不要一开始就同时开发全部智能系统。

最终目标是做出一个：

```text
能玩
能讲逻辑
NPC 有记忆
NPC 会骗人
玩家能自由发言
规则稳定不乱
成本可控
可逐步扩展
```

的智能类狼人杀 demo。
