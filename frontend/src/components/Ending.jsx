import { useMemo, useState } from "react";
import {
  ROUTE_META,
  getDominantRoutes,
  getEndingSuggestion,
  getRoutePercent,
} from "../game-ui";

const ENDING_TABS = [
  { id: "summary", label: "结果总览" },
  { id: "route", label: "路线复盘" },
  { id: "story", label: "完整故事" },
];

export default function Ending({
  ending,
  routeProfile,
  storyState,
  world,
  lastChoiceLabel,
  onRestart,
}) {
  const [activeTab, setActiveTab] = useState(null);
  const dominantRoutes = useMemo(() => getDominantRoutes(routeProfile, 3), [routeProfile]);
  const recentHistory = [...(storyState?.history || [])].slice(-4).reverse();
  const endingSuggestion = getEndingSuggestion(dominantRoutes);
  const activeTabMeta = ENDING_TABS.find((tab) => tab.id === activeTab);

  return (
    <section className="card ending-card">
      <div className="ending-hero">
        <h1 className="ending-headline">
          <span className="ending-kicker">结局：</span>
          <span className="ending-title">{ending.ending_title}</span>
        </h1>
        <h2 className="ending-player-title">
          <span className="ending-player-kicker">称号：</span>
          <span className="ending-player-name">{ending.player_title}</span>
        </h2>
      </div>

      <div className="ending-stats">
        <article className="stat-pill">
          <strong>{storyState?.turn_count || 0}</strong>
          <span>推进回合</span>
        </article>
        <article className="stat-pill">
          <strong>{lastChoiceLabel || "未知"}</strong>
          <span>最后抉择</span>
        </article>
      </div>

      <div className="tab-row compact">
        {ENDING_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`tab-button${activeTab === tab.id ? " active" : ""}`}
            onClick={() => setActiveTab((currentTab) => (currentTab === tab.id ? null : tab.id))}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTabMeta && (
        <div className="ending-modal-overlay" onClick={() => setActiveTab(null)}>
          <div className="ending-modal card" onClick={(event) => event.stopPropagation()}>
            <div className="ending-modal-head">
              <h3>{activeTabMeta.label}</h3>
              <button type="button" className="ghost-button ending-modal-close" onClick={() => setActiveTab(null)}>
                关闭
              </button>
            </div>

            {activeTab === "summary" && (
              <div className="ending-grid">
                <article className="info-panel">
                  <h3>结局总结</h3>
                  <p>{ending.ending_summary}</p>
                </article>
                <article className="info-panel">
                  <h3>世界余波</h3>
                  <p>{ending.world_after_effect}</p>
                </article>
                <article className="info-panel">
                  <h3>选择分析</h3>
                  <p>{ending.choice_analysis}</p>
                </article>
                <article className="info-panel">
                  <h3>下局建议</h3>
                  <p>{endingSuggestion}</p>
                  {world?.core_conflict && <p className="subtle">这局围绕“{world.core_conflict}”收束，下次可以围绕反方向立场重打。</p>}
                </article>
              </div>
            )}

            {activeTab === "route" && (
              <div className="ending-route-grid">
                <article className="info-panel">
                  <h3>路线画像</h3>
                  <div className="route-bars">
                    {ROUTE_META.map((route) => (
                      <div key={route.id} className="route-row">
                        <div className="route-label">
                          <span>{route.label}</span>
                          <small>{routeProfile?.[route.id] || 0}</small>
                        </div>
                        <div className="route-bar">
                          <span style={{ width: getRoutePercent(routeProfile?.[route.id]) }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </article>
                <article className="info-panel">
                  <h3>最近几步怎么把你送进这个结局</h3>
                  <div className="history-list">
                    {recentHistory.length === 0 && <p className="subtle">本局缺少可回顾的历史记录。</p>}
                    {recentHistory.map((entry) => (
                      <div key={`${entry.turn}-${entry.choice?.id}`} className="history-item">
                        <strong>第 {entry.turn} 幕 · {entry.choice?.text}</strong>
                        <p>{entry.important_event}</p>
                      </div>
                    ))}
                  </div>
                </article>
              </div>
            )}

            {activeTab === "story" && (
              <article className="info-panel">
                <h3>完整故事</h3>
                <p className="full-story">{ending.full_story}</p>
              </article>
            )}
          </div>
        </div>
      )}

      <div className="action-row split">
        <button type="button" className="primary-button" onClick={onRestart}>想再来一次？</button>
      </div>
    </section>
  );
}
