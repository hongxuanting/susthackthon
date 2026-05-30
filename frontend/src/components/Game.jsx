import { useEffect, useRef, useState } from "react";
import { generateSceneImage } from "../api";

const STYLE_LABELS = {
  classic: "原版直出",
  meme: "幽默风趣化",
  chaos: "崩化搞笑版",
};

const SOURCE_LABELS = {
  generated: "AI剧情配图",
  fallback: "备用剧情图",
};

const IMAGE_REQUEST_TIMEOUT_MS = 10000;
const FALLBACK_SCENE_IMAGE = "/story-fallback.png";

export default function Game({ gameData, onChoose, error }) {
  const [loadingChoice, setLoadingChoice] = useState("");
  const [sceneImage, setSceneImage] = useState({
    imageUrl: "",
    source: "",
    sceneSummary: "",
    visualKeywords: [],
  });
  const [imageLoading, setImageLoading] = useState(false);
  const imageCache = useRef(new Map());
  const pendingImages = useRef(new Map());

  useEffect(() => {
    const scene = gameData.scene?.trim();
    if (!scene) return undefined;

    const sceneKey = `${gameData.style_mode || "classic"}::${scene}`;
    const payload = {
      scene,
      style_mode: gameData.style_mode,
      player_identity: gameData.player_profile?.identity || "",
    };
    const cachedImage = imageCache.current.get(sceneKey);
    if (cachedImage) {
      setSceneImage(cachedImage);
      setImageLoading(false);
      return undefined;
    }

    let imageRequest = pendingImages.current.get(sceneKey);
    if (!imageRequest) {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), IMAGE_REQUEST_TIMEOUT_MS);
      imageRequest = generateSceneImage(payload, { signal: controller.signal })
        .then((data) => {
          if (data.debug_message) {
            console.log("[scene-image]", data.debug_message);
          }
          const imageUrl = data.image_url;
          if (!imageUrl) throw new Error("scene image generation returned no image");
          return {
            imageUrl,
            source: data.source,
            sceneSummary: data.scene_summary || "",
            visualKeywords: data.visual_keywords || [],
          };
        })
        .catch((imageError) => {
          console.log("[scene-image] request failed, using fallback illustration", imageError);
          return {
            imageUrl: FALLBACK_SCENE_IMAGE,
            source: "fallback",
            sceneSummary: "",
            visualKeywords: [],
          };
        })
        .then((image) => {
          imageCache.current.set(sceneKey, image);
          return image;
        })
        .finally(() => {
          clearTimeout(timeoutId);
          pendingImages.current.delete(sceneKey);
        });
      pendingImages.current.set(sceneKey, imageRequest);
    }

    let ignore = false;
    setSceneImage({ imageUrl: "", source: "", sceneSummary: "", visualKeywords: [] });
    setImageLoading(true);

    imageRequest
      .then((image) => {
        if (ignore) return;
        setSceneImage(image);
      })
      .finally(() => {
        if (!ignore) setImageLoading(false);
      });

    return () => {
      ignore = true;
    };
  }, [
    gameData.scene,
    gameData.style_mode,
    gameData.player_profile?.identity,
  ]);

  const handleChoose = async (choiceId) => {
    try {
      setLoadingChoice(choiceId);
      await onChoose(choiceId);
    } finally {
      setLoadingChoice("");
    }
  };

  const handleImageError = () => {
    const scene = gameData.scene?.trim() || sceneImage.sceneSummary;
    if (sceneImage.imageUrl !== FALLBACK_SCENE_IMAGE) {
      const fallbackImage = {
        imageUrl: FALLBACK_SCENE_IMAGE,
        source: "fallback",
        sceneSummary: sceneImage.sceneSummary,
        visualKeywords: sceneImage.visualKeywords,
      };
      if (scene) {
        imageCache.current.set(`${gameData.style_mode || "classic"}::${scene}`, fallbackImage);
      }
      setSceneImage(fallbackImage);
    }
  };

  return (
    <section className="card">
      <h1>WorldForge AI</h1>
      <dl className="game-meta">
        <div><dt>当前模式</dt><dd>{STYLE_LABELS[gameData.style_mode]}</dd></div>
        <div><dt>玩家身份</dt><dd>{gameData.player_profile?.identity}</dd></div>
      </dl>
      <section className="scene-image-wrap" aria-live="polite">
        <div className="scene-image-heading">
          <h2>当前画面</h2>
          {!imageLoading && sceneImage.source && <small>{SOURCE_LABELS[sceneImage.source]}</small>}
        </div>
        <div className={`scene-image-box${imageLoading ? " is-loading" : ""}`}>
          {sceneImage.imageUrl && (
            <img
              className="scene-image"
              src={sceneImage.imageUrl}
              alt="当前剧情场景插画"
              onError={handleImageError}
            />
          )}
          {imageLoading && (
            <div className="scene-image-loading">
              <span />
              <p>AI 正在生成这一幕……</p>
            </div>
          )}
        </div>
        {sceneImage.sceneSummary && (
          <p className="scene-image-title">本幕标题：{sceneImage.sceneSummary}</p>
        )}
      </section>
      <article>
        <h2>当前剧情</h2>
        <p>{gameData.scene}</p>
      </article>
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
