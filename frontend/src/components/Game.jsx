import { useState } from "react";

const STYLE_LABELS = {
  classic: "原版直出",
  meme: "幽默风趣化",
  chaos: "崩化搞笑版",
};

export default function Game({ gameData, onChoose, error }) {
  const [loadingChoice, setLoadingChoice] = useState("");

  const handleChoose = async (choiceId) => {
    try {
      setLoadingChoice(choiceId);
      await onChoose(choiceId);
    } finally {
      setLoadingChoice("");
    }
  };

  return (
    <section className="card">
      <h1>WorldForge AI</h1>
      <dl className="game-meta">
        <div><dt>当前模式</dt><dd>{STYLE_LABELS[gameData.style_mode]}</dd></div>
        <div><dt>玩家身份</dt><dd>{gameData.player_profile?.identity}</dd></div>
      </dl>
      <article>
        <h2>剧情</h2>
        <p>{gameData.scene}</p>
      </article>
      <article>
        <h2>问题</h2>
        <p>{gameData.question}</p>
      </article>
      <div className="options">
        {gameData.options?.map((option) => (
          <button
            key={option.id}
            type="button"
            onClick={() => handleChoose(option.id)}
            disabled={Boolean(loadingChoice)}
          >
            <strong>{option.id}</strong> {option.text}
          </button>
        ))}
      </div>
      {loadingChoice && <p className="loading">剧情生成中...</p>}
      {error && <p className="error">{error}</p>}
    </section>
  );
}
