import { useState } from "react";
import { generateWorld } from "../api";

const STYLES = [
  { id: "classic", label: "短篇正剧，直接开局。" },
  { id: "meme", label: "轻松有梗，爽就完了。" },
  { id: "chaos", label: "抽象猎奇，随时可能被剧情创飞。" },
];

export default function Home({ onGenerated }) {
  const [styleMode, setStyleMode] = useState("classic");
  const [worldInput, setWorldInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleGenerate = async () => {
    if (!worldInput.trim()) {
      setError("请输入世界设定。");
      return;
    }

    try {
      setLoading(true);
      setError("");
      const world = await generateWorld(worldInput.trim(), styleMode);
      onGenerated(world, styleMode);
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
        placeholder="输入世界设定"
      />
      <button type="button" onClick={handleGenerate} disabled={loading}>
        {loading ? "生成中..." : "生成世界"}
      </button>
      {error && <p className="error">{error}</p>}
    </section>
  );
}
