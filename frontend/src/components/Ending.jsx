const STYLE_LABELS = {
  classic: "原版直出",
  meme: "幽默风趣化",
  chaos: "崩化搞笑版",
};

export default function Ending({ ending, styleMode, onRestart }) {
  return (
    <section className="card">
      <p>当前模式：{STYLE_LABELS[styleMode]}</p>
      <h1>{ending.ending_title}</h1>
      <h2>{ending.player_title}</h2>
      <article>
        <h3>结局总结</h3>
        <p>{ending.ending_summary}</p>
      </article>
      <article>
        <h3>选择分析</h3>
        <p>{ending.choice_analysis}</p>
      </article>
      <article>
        <h3>完整故事</h3>
        <p className="full-story">{ending.full_story}</p>
      </article>
      <button type="button" onClick={onRestart}>再来一局</button>
    </section>
  );
}
