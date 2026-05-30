# WorldForge AI

极简 AI 互动叙事游戏。故事会根据剧情自然结束。

## 后端启动

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8008
```

## 前端启动

```powershell
cd frontend
npm install
npm run dev
```

## 环境配置

后端使用 `backend/.env`：

```dotenv
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_TEXT_MODEL=gpt-4.1-mini

OPENAI_IMAGE_API_KEY=
OPENAI_IMAGE_BASE_URL=
OPENAI_IMAGE_MODEL=gpt-image-1
IMAGE_TIMEOUT_SECONDS=60

MOCK_AI=false
```

文字 Agent 使用 `OPENAI_TEXT_MODEL`，推荐配置为 `gpt-4.1-mini`。
图片生成使用独立的 `POST /api/story/scene-image`，不会阻塞世界生成、剧情初始化或选项推进。接口直接使用当前剧情生成一张图；失败时返回 `debug_message`，前端文本流程继续可用。

前端使用 `frontend/.env.local`：

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8008
```

## 测试流程

1. 打开前端页面。
2. 选择 `classic`、`meme` 或 `chaos`。
3. 输入世界设定，点击“生成世界”。
4. 编辑 AI 生成的世界背景，点击“开始游戏”。
5. 确认开场剧情、当前问题和 A/B/C/D 选项先显示，配图区域随后异步加载。
6. 点击 A/B/C/D 推进剧情，确认新剧情和新选项先显示，新配图随后加载。
7. 确认图片失败时只显示“本幕配图生成失败”，文本流程仍可继续。
8. 确认结局页展示标题、玩家称号、结局总结、选择分析和完整故事。
9. 点击“再来一局”重新开始。
