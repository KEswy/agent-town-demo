# Agent Town 常用命令

所有命令默认从项目根目录执行：

```bash
cd /Users/tonystark/game-dev-lab/agent-town-demo
```

## 首次安装后端依赖

已经存在 `backend/.venv` 时不需要重复创建虚拟环境，只需安装或更新依赖：

```bash
backend/.venv/bin/pip install -r backend/requirements.txt
```

如果 `backend/.venv` 不存在：

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
```

## 启用 DeepSeek LLM

DeepSeek 是云端 API，不需要在本机单独启动 LLM 进程。确认 `backend/.env` 包含以下配置，并把 Key 只保存在这个文件中：

```dotenv
ENABLE_LLM=true
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=你的_DEEPSEEK_API_KEY
LLM_MODEL=deepseek-v4-flash
LLM_MAX_RETRIES=1
LLM_RETRY_DELAY_SECONDS=0.35
```

修改 `.env` 后需要重启后端。

## 测试 LLM 连接

下面的命令不启动 FastAPI，但会发送一次很小的真实 DeepSeek 请求：

```bash
backend/.venv/bin/python scripts/check_llm_connection.py
```

成功时会看到：

```text
[OK] deepseek returned: ...
```

## 启动后端和 LLM

LLM 会随 FastAPI 后端一起工作：

```bash
cd backend
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

保持这个终端窗口运行。看到类似下面的输出表示后端已经启动：

```text
Uvicorn running on http://127.0.0.1:8000
```

然后在 Godot 开始新游戏时勾选“启用 LLM”。环境变量开关和单局开关必须同时启用。

## 检查服务状态

另开一个终端执行：

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/llm/status
curl http://127.0.0.1:8000/api/rag/status
```

浏览器 API 文档：

```text
http://127.0.0.1:8000/docs
```

## 启动 Godot 编辑器

```bash
godot --editor --path game
```

也可以直接用 Godot 4 打开 `game/project.godot`。

## 运行完整自检

```bash
backend/.venv/bin/python scripts/smoke_check.py
```

## 查看 LLM 校验失败日志

只要出现被结构化事实校验拒绝的 LLM 候选文本，就会生成或追加该文件；日志会列出全部原因，并区分后续恢复成功和五轮全部失败。自然同义改写不要求与规则模板逐字一致：

```bash
tail -n 5 backend/data/llm_validation_failures.jsonl
```

日志和游戏内“LLM校验失败查看”都会显示 DeepSeek 原始返回，可能带有对局隐藏信息；这是当前调试阶段的预期行为。

当前校验按“声明者 → 目标 → 结果”记录验人；例如“5号给8号金水”只会把8号识别为5号的查验目标。旧日志保留修复前的失败原因，新规则只作用于重启后生成的新回答。

## 停止后端

回到运行 Uvicorn 的终端，按：

```text
Control + C
```

确认 `8000` 端口已经关闭：

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

没有输出就表示后端已经停止。
