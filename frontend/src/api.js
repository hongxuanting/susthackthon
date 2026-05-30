const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8008";

async function request(path, options = {}) {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await resp.json();
  if (!resp.ok) {
    throw new Error(data.detail || "请求失败");
  }
  return data;
}

export function generateWorld(worldInput, styleMode = "classic") {
  return request("/api/world/generate", {
    method: "POST",
    body: JSON.stringify({ world_input: worldInput, style_mode: styleMode }),
  });
}

export function initStory(worldBackground, worldRules, styleMode = "classic") {
  return request("/api/story/init", {
    method: "POST",
    body: JSON.stringify({
      world_background: worldBackground,
      world_rules: worldRules || [],
      style_mode: styleMode,
    }),
  });
}

export function chooseOption(sessionId, choiceId) {
  return request("/api/story/choose", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, choice_id: choiceId }),
  });
}

export async function generateSceneImage(sceneText, styleMode) {
  const res = await fetch(`${API_BASE}/api/story/scene-image`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      scene_text: sceneText,
      style_mode: styleMode,
    }),
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data?.debug_message || "scene image generation failed");
  }

  return data;
}

export function getStory(sessionId) {
  return request(`/api/story/${sessionId}`);
}

export function restartStory(sessionId) {
  return request("/api/story/restart", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}
