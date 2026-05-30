import { useEffect, useMemo, useRef, useState } from "react";
import { generateSceneImage } from "../api";
import {
  PHASE_META,
  getSceneViews,
} from "../game-ui";

const STORY_VIEWS = [
  { id: "full", label: "全文" },
  { id: "line", label: "一句话" },
];

export default function Game({
  gameData,
  lastChoiceLabel,
  onChoose,
  error,
}) {
  const [loadingChoice, setLoadingChoice] = useState("");
  const [storyView, setStoryView] = useState("line");
  const [sceneImage, setSceneImage] = useState("");
  const [imageLoading, setImageLoading] = useState(false);
  const [imageError, setImageError] = useState("");
  const imageCacheRef = useRef(new Map());
  const inFlightRef = useRef(new Set());
  const latestImageKeyRef = useRef("");

  const sceneViews = useMemo(() => getSceneViews(gameData.scene), [gameData.scene]);
  const currentPhase = PHASE_META[gameData.phase] || PHASE_META.opening;
  const currentScene = gameData.scene || "";
  const styleMode = gameData.style_mode || "classic";

  useEffect(() => {
    if (!currentScene) return undefined;

    const imageKey = `${styleMode}::${currentScene}`;
    latestImageKeyRef.current = imageKey;

    if (imageCacheRef.current.has(imageKey)) {
      setSceneImage(imageCacheRef.current.get(imageKey));
      setImageError("");
      setImageLoading(false);
      return undefined;
    }

    if (inFlightRef.current.has(imageKey)) return undefined;

    inFlightRef.current.add(imageKey);
    setSceneImage("");
    setImageLoading(true);
    setImageError("");

    generateSceneImage(currentScene, styleMode)
      .then((data) => {
        console.log("scene image result", {
          success: data.success,
          hasImage: !!data.image_url,
          imageType: data.image_url?.startsWith("data:image") ? "base64" : "url",
          imageLength: data.image_url?.length,
          debug_message: data.debug_message,
        });

        if (latestImageKeyRef.current !== imageKey) return;

        if (data.success === true && data.image_url) {
          imageCacheRef.current.set(imageKey, data.image_url);
          setSceneImage(data.image_url);
          setImageError("");
        } else if (!imageCacheRef.current.has(imageKey)) {
          setImageError("本幕配图生成失败，可继续游戏");
        }
      })
      .catch((err) => {
        console.warn("scene image failed:", err);

        if (latestImageKeyRef.current !== imageKey) return;

        if (!imageCacheRef.current.has(imageKey)) {
          setImageError("本幕配图生成失败，可继续游戏");
        }
      })
      .finally(() => {
        inFlightRef.current.delete(imageKey);

        if (latestImageKeyRef.current === imageKey) {
          setImageLoading(false);
        }
      });

    return undefined;
  }, [currentScene, styleMode]);

  const handleChoose = async (choiceId) => {
    try {
      setLoadingChoice(choiceId);
      await onChoose(choiceId);
    } finally {
      setLoadingChoice("");
    }
  };

  return (
    <section className="card play-card">
      <div className="game-layout">
        <div className="game-main">
          <article className="story-panel">
            <div className="story-head">
              <div>
                <h3>{currentPhase.hint}</h3>
              </div>
              <div className="tab-row compact">
                {STORY_VIEWS.map((view) => (
                  <button
                    key={view.id}
                    type="button"
                    className={`tab-button${storyView === view.id ? " active" : ""}`}
                    onClick={() => setStoryView(view.id)}
                  >
                    {view.label}
                  </button>
                ))}
              </div>
            </div>
            {storyView === "full" && <p>{sceneViews.full}</p>}
            {storyView === "line" && <p className="story-line">{sceneViews.line}</p>}
          </article>

          {(imageLoading || sceneImage || imageError) && (
            <article className="scene-image-panel" aria-live="polite">
              {sceneImage ? (
                <img src={sceneImage} alt="本幕配图" />
              ) : imageLoading ? (
                <div className="scene-image-loading">AI 正在生成本幕配图...</div>
              ) : (
                <div className="scene-image-error">本幕配图生成失败，可继续游戏</div>
              )}
            </article>
          )}

          <article className="question-panel">
            <p className="eyebrow">此刻抉择</p>
            <h2>{gameData.question}</h2>
          </article>

          {loadingChoice && (
            <div className="loading-inline" aria-live="polite">
              <span className="loading-spinner" aria-hidden="true" />
              <span>剧情生成中...</span>
            </div>
          )}

          <div className="options option-grid">
            {gameData.options?.map((option) => {
              return (
                <button
                  key={option.id}
                  type="button"
                  className={`option-card option-${option.id.toLowerCase()}`}
                  onClick={() => handleChoose(option.id)}
                  disabled={Boolean(loadingChoice)}
                >
                  <span className="option-head">
                    <strong>{option.id}</strong>
                    <small>{option.style || "即时行动"}</small>
                  </span>
                  <span className="option-text">{option.text}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
    </section>
  );
}
