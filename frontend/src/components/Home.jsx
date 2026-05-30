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
    <section className="card">
      <h1>WorldForge AI</h1>
      <div className="style-row">
        {STYLES.map((style) => (
          <button
            key={style.id}
            type="button"
            className={`style-button${styleMode === style.id ? " active" : ""}`}
            onClick={() => setStyleMode(style.id)}
          >
            <strong>{style.id}</strong>
            <span>{style.label}</span>
          </button>
        ))}
      </div>
      <textarea
        value={worldInput}
        onChange={(event) => setWorldInput(event.target.value)}
        aria-label="输入世界设定"
      />
      <button type="button" onClick={handleGenerate} disabled={loading}>
        {loading ? "生成中..." : "生成世界"}
      </button>
      {error && <p className="error">{error}</p>}
    </section>
  );
}
