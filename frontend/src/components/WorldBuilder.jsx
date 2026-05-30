import { useState } from "react";

export default function WorldBuilder({ world, onStart, error }) {
  const [background, setBackground] = useState(world.world_background);
  const [loading, setLoading] = useState(false);

  const handleStart = async () => {
    if (!background.trim()) return;
    try {
      setLoading(true);
      await onStart(background.trim());
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card">
      <h1>确认世界</h1>
      <label htmlFor="world-background">世界背景</label>
      <textarea
        id="world-background"
        value={background}
        onChange={(event) => setBackground(event.target.value)}
      />
      <h2>世界规则</h2>
      <ul>
        {world.world_rules.map((rule, index) => <li key={`${rule}-${index}`}>{rule}</li>)}
      </ul>
      <button type="button" onClick={handleStart} disabled={loading || !background.trim()}>
        {loading ? "初始化中..." : "开始游戏"}
      </button>
      {error && <p className="error">{error}</p>}
    </section>
  );
}
