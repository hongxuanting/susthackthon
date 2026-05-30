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
IMAGE_TIMEOUT_SECONDS=10

MOCK_AI=false
MOCK_IMAGE=false
```

文字 Agent 使用 `OPENAI_TEXT_MODEL`，推荐配置为 `gpt-4.1-mini`。图片生成使用独立的
`OPENAI_IMAGE_MODEL`、`OPENAI_IMAGE_API_KEY` 和 `OPENAI_IMAGE_BASE_URL`，推荐选择服务商提供的最快图像模型。
图片 API Key 或 Base URL 留空时，会分别回退使用文字模型的对应配置。

每次生图前，后端会先把当前剧情压缩成 10 到 16 个汉字的画面描述，再提取 3 到 5 个视觉关键词。真实图片 prompt 只使用画面描述、视觉关键词和风格词，不会塞入完整剧情原文。

图片生成最多等待 `IMAGE_TIMEOUT_SECONDS` 秒，上限为 10 秒。每次请求只生成一张低质量图片，不使用历史剧情。`gpt-image-*` 使用其支持的最小尺寸 `1024x1024`，其他快速兼容模型使用 `512x512`。推荐优先使用 `gpt-image-1`，也可以按服务商支持情况选择 `flux-schnell` 或 `sdxl-turbo`。远端图片失败时会再重试一次；两次均失败后，页面才会显示静态备用剧情插图。

`POST /api/story/scene-image` 始终返回 `image_url`，并附带 `source`、`debug_message`、`scene_summary`、`visual_keywords` 和 `image_prompt`。`source` 只会是 `generated` 或 `fallback`。图片服务异常时，后端日志会记录模型名、尝试次数和失败原因。

前端使用 `frontend/.env.local`：

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8008
```

## 测试流程

1. 打开前端页面。
2. 选择 `classic`、`meme` 或 `chaos`。
3. 输入世界设定，点击“生成世界”。
4. 编辑 AI 生成的世界背景，点击“开始游戏”。
5. 确认开场剧情出现后，页面中间异步加载“当前剧情配图”。
6. 点击 A/B/C/D 推进剧情，确认新剧情先显示，配图随后更新。
7. 将 `OPENAI_IMAGE_MODEL` 临时改成不可用值，确认重试两次后页面显示“备用剧情图”。
8. 确认结局页展示标题、玩家称号、结局总结、选择分析和完整故事。
9. 点击“再来一局”重新开始。
