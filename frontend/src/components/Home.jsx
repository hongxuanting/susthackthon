import { useState } from "react";
import { generateWorld } from "../api";
import { IDEA_PRESETS, createRandomIdea } from "../game-ui";

const STYLES = [
  {
    id: "classic",
    title: "Classic",
    label: "原版直出",
    pitch: "沉浸式叙事，严肃推进，适合认真体验世界线。",
  },
  {
    id: "meme",
    title: "Meme",
    label: "幽默风趣化",
    pitch: "轻松幽默，冷梗吐槽，适合轻松体验。",
  },
  {
    id: "chaos",
    title: "Chaos",
    label: "崩化搞笑版",
    pitch: "抽象乱入、夸张演出，随时可能串台。",
  },
];

export default function Home({ onGenerated }) {
  const [styleMode, setStyleMode] = useState("classic");
  const [worldInput, setWorldInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const currentLength = worldInput.trim().length;

  const handleGenerate = async () => {
    if (!worldInput.trim()) {
      setError("请输入世界设定。");
      return;
    }

    try {
      setLoading(true);
      setError("");
      const world = await generateWorld(worldInput.trim(), styleMode);
      await onGenerated(world, styleMode, worldInput.trim());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card hero-card home-dashboard">
      <section className="world-lab-panel">
        <div className="section-title compact">
          <h3>选择这次冒险的展开方式</h3>
        </div>

        <div className="idea-chip-row" aria-label="题材预设">
          {IDEA_PRESETS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              className={`idea-chip${worldInput === preset.prompt ? " active" : ""}`}
              onClick={() => setWorldInput(preset.prompt)}
            >
              <strong>{preset.label}</strong>
            </button>
          ))}
        </div>

        <div className="section-title compact section-divider-title">
          <h3>风格选择</h3>
        </div>

        <div className="style-row compact-style-row">
          {STYLES.map((style) => (
            <button
              key={style.id}
              type="button"
              className={`style-button compact${styleMode === style.id ? " active" : ""}`}
              onClick={() => setStyleMode(style.id)}
            >
              <span className="style-mark">{style.title}</span>
              <strong>{style.label}</strong>
              <small>{style.pitch}</small>
            </button>
          ))}
        </div>
      </section>

      <section className="world-input-panel">
        <div className="input-meta">
          <label htmlFor="world-input" className="input-label">你的世界设定</label>
          <span className="subtle">{currentLength} 字</span>
        </div>
        <textarea
          id="world-input"
          value={worldInput}
          onChange={(event) => setWorldInput(event.target.value)}
          placeholder="例如：一个赛博朋克世界，AI 控制城市秩序，底层人依靠机械义体生存，城市表面繁华而地下正在酝酿反抗。"
        />
      </section>

      <div className="action-row world-generate-row">
        <button type="button" className="primary-button compact-primary" onClick={handleGenerate} disabled={loading}>
          {loading ? "正在带着你的世界入局..." : "带着你的世界入局"}
        </button>
      </div>

      {error && <p className="error">{error}</p>}
    </section>
  );
}
