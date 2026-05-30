import { useMemo, useState } from "react";
import { STYLE_META } from "../game-ui";

const TABS = [
  { id: "overview", label: "世界速览" },
  { id: "rules", label: "规则与势力" },
  { id: "stakes", label: "风险与开局感" },
];

export default function WorldBuilder({
  world,
  worldIdea,
  styleMode,
  editedBackground,
  onStart,
  onBack,
  error,
}) {
  const [background, setBackground] = useState(editedBackground || world.world_background);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");

  const worldTabContent = useMemo(() => ({
    overview: (
      <div className="tab-panel-content">
        <article className="info-panel">
          <p className="eyebrow">灵感原句</p>
          <p>{worldIdea || "本局从用户自由输入开局。"}</p>
        </article>
        <article className="info-panel">
          <p className="eyebrow">核心冲突</p>
          <h3>{world.core_conflict}</h3>
          <p className="subtle">{world.tone}</p>
        </article>
        <article className="info-panel">
          <p className="eyebrow">一句话开局感</p>
          <p>{STYLE_META[styleMode]?.guide}</p>
        </article>
      </div>
    ),
    rules: (
      <div className="tab-panel-content">
        <article className="info-panel">
          <p className="eyebrow">世界规则</p>
          <ul className="rule-list">
            {world.world_rules.map((rule, index) => <li key={`${rule}-${index}`}>{rule}</li>)}
          </ul>
        </article>
        <article className="info-panel">
          <p className="eyebrow">主要势力</p>
          <ul className="tag-list">
            {world.main_forces?.map((force, index) => <li key={`${force}-${index}`}>{force}</li>)}
          </ul>
        </article>
      </div>
    ),
    stakes: (
      <div className="tab-panel-content">
        <article className="info-panel">
          <p className="eyebrow">危险来源</p>
          <ul className="tag-list danger-list">
            {world.danger_sources?.map((danger, index) => <li key={`${danger}-${index}`}>{danger}</li>)}
          </ul>
        </article>
        <article className="info-panel">
          <p className="eyebrow">为什么值得继续玩</p>
          <p>这个世界已经具备冲突、规则和不确定代价，用户一开局就能感受到“再选一次会不会完全不同”。</p>
        </article>
      </div>
    ),
  }), [styleMode, world, worldIdea]);

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
    <section className="card flow-card">
      <div className="section-title">
        <h3>世界已经成型，先快速扫一眼重点，再让用户直接开局</h3>
        <p className="subtle">这一页不该堆长文，而是帮助用户快速确认“这个世界值得点进去玩”。</p>
      </div>

      <div className="world-overview-grid">
        <article className="info-panel spotlight-panel">
          <p className="eyebrow">核心冲突</p>
          <h2>{world.core_conflict}</h2>
          <p>{world.tone}</p>
          <div className="micro-stats">
            <span>{STYLE_META[styleMode]?.label}</span>
            <span>{world.world_rules.length} 条规则</span>
            <span>{world.danger_sources?.length || 0} 个危险源</span>
          </div>
        </article>
        <article className="tab-panel">
          <div className="tab-row">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                className={`tab-button${activeTab === tab.id ? " active" : ""}`}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>
          {worldTabContent[activeTab]}
        </article>
      </div>

      <label htmlFor="world-background" className="input-label">世界背景</label>
      <textarea
        id="world-background"
        value={background}
        onChange={(event) => setBackground(event.target.value)}
      />

      <article className="info-panel tips-panel">
        <div className="section-title compact">
          <h2>开局提示</h2>
          <p className="subtle">建议只微调背景，不要改成另一套世界，否则后续规则和结局张力会变弱。</p>
        </div>
        <div className="micro-stats">
          <span>保留核心冲突</span>
          <span>保留至少 2 条规则</span>
          <span>保持一句话就能理解</span>
        </div>
      </article>

      <div className="action-row split">
        <button type="button" className="ghost-button" onClick={onBack} disabled={loading}>
          重新设定
        </button>
        <button
          type="button"
          className="primary-button"
          onClick={handleStart}
          disabled={loading || !background.trim()}
        >
          {loading ? "正在初始化剧情..." : "带着这个世界直接开局"}
        </button>
      </div>

      {error && <p className="error">{error}</p>}
    </section>
  );
}
