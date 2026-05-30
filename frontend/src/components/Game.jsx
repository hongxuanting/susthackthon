import { useEffect, useRef, useState } from "react";
import { generateSceneImage } from "../api";

const STYLE_LABELS = {
  classic: "原版直出",
  meme: "幽默风趣化",
  chaos: "崩化搞笑版",
};

export default function Game({ gameData, onChoose, error }) {
  const [loadingChoice, setLoadingChoice] = useState("");
  const [sceneImage, setSceneImage] = useState("");
  const [imageLoading, setImageLoading] = useState(false);
  const [imageError, setImageError] = useState("");
  const imageCacheRef = useRef(new Map());
  const inFlightRef = useRef(new Set());
  const latestImageKeyRef = useRef("");

  useEffect(() => {
    const currentScene = gameData.scene?.trim();
    const styleMode = gameData.style_mode || "classic";
    if (!currentScene) return undefined;

    const imageKey = `${styleMode}::${currentScene}`;
    latestImageKeyRef.current = imageKey;

    if (imageCacheRef.current.has(imageKey)) {
      setSceneImage(imageCacheRef.current.get(imageKey));
      setImageError("");
      setImageLoading(false);
      return undefined;
    }

    if (inFlightRef.current.has(imageKey)) {
      return undefined;
    }

    inFlightRef.current.add(imageKey);
    setSceneImage("");
    setImageError("");
    setImageLoading(true);
    console.log("request scene image:", imageKey);

    generateSceneImage(currentScene, styleMode)
      .then((data) => {
        if (latestImageKeyRef.current !== imageKey) return;
        console.log("scene image result", {
          success: data.success,
          hasImage: !!data.image_url,
          imageType: data.image_url?.startsWith("data:image") ? "base64" : "url",
          imageLength: data.image_url?.length,
          debug_message: data.debug_message,
        });
        if (data.success === true && data.image_url) {
          imageCacheRef.current.set(imageKey, data.image_url);
          setSceneImage(data.image_url);
          setImageError("");
        } else {
          console.warn("scene image failed:", {
            success: data.success,
            hasImage: !!data.image_url,
            imageType: data.image_url?.startsWith("data:image") ? "base64" : "url",
            imageLength: data.image_url?.length,
            debug_message: data.debug_message,
          });
          if (!imageCacheRef.current.has(imageKey)) {
            setImageError("本幕配图生成失败");
          }
        }
      })
      .catch((err) => {
        if (latestImageKeyRef.current !== imageKey) return;
        console.warn("scene image failed:", err);
        if (!imageCacheRef.current.has(imageKey)) {
          setImageError("本幕配图生成失败");
        }
      })
      .finally(() => {
        inFlightRef.current.delete(imageKey);
        if (latestImageKeyRef.current === imageKey) {
          setImageLoading(false);
        }
      });

    return undefined;
  }, [
    gameData.scene,
    gameData.style_mode,
  ]);

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
        <h2>当前剧情</h2>
        <p>{gameData.scene}</p>
      </article>
      <section className="scene-image-panel" aria-live="polite">
        {imageLoading && !sceneImage && (
          <p className="scene-image-status">AI 正在生成本幕配图...</p>
        )}
        {sceneImage && (
          <img
            className="scene-image"
            src={sceneImage}
            alt="本幕配图"
            onError={() => {
              console.error("image load failed:", {
                imageType: sceneImage?.startsWith("data:image") ? "base64" : "url",
                imageLength: sceneImage?.length,
              });
              setImageError("图片加载失败");
            }}
          />
        )}
        {!sceneImage && imageError && (
          <p className="scene-image-status">{imageError}</p>
        )}
      </section>
      <article>
        <h2>当前问题</h2>
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
