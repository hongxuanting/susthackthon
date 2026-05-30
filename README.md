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
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=your-model-name
OPENAI_BASE_URL=https://your-openai-compatible-endpoint.example/v1
MOCK_AI=false
```

前端使用 `frontend/.env.local`：

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8008
```

## 测试流程

1. 打开前端页面。
2. 选择 `classic`、`meme` 或 `chaos`。
3. 输入世界设定，点击“生成世界”。
4. 编辑 AI 生成的世界背景，点击“开始游戏”。
5. 点击 A/B/C/D 推进剧情。
6. 确认结局页展示标题、玩家称号、结局总结、选择分析和完整故事。
7. 点击“再来一局”重新开始。
