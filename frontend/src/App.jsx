import { useEffect, useState } from "react";
import { chooseOption, getStory, initStory, restartStory } from "./api";
import Home from "./components/Home";
import Game from "./components/Game";
import Ending from "./components/Ending";
import {
  STORAGE_KEY,
  createEmptyFlags,
} from "./game-ui";

export default function App() {
  const [page, setPage] = useState("intro");
  const [introStep, setIntroStep] = useState("cover");
  const [styleMode, setStyleMode] = useState("classic");
  const [world, setWorld] = useState(null);
  const [worldIdea, setWorldIdea] = useState("");
  const [editedWorldBackground, setEditedWorldBackground] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [gameData, setGameData] = useState(null);
  const [storyState, setStoryState] = useState(null);
  const [ending, setEnding] = useState(null);
  const [lastChoiceLabel, setLastChoiceLabel] = useState("");
  const [error, setError] = useState("");
  const [isRestoring, setIsRestoring] = useState(true);

  const clearLocalState = () => {
    setPage("intro");
    setIntroStep("cover");
    setStyleMode("classic");
    setWorld(null);
    setWorldIdea("");
    setEditedWorldBackground("");
    setSessionId("");
    setGameData(null);
    setStoryState(null);
    setEnding(null);
    setLastChoiceLabel("");
    setError("");
  };

  const syncStoryState = (state, options = {}) => {
    if (!state) return;
    const { preservePage = false } = options;
    setStoryState(state);
    setSessionId(state.session_id || "");
    setGameData({
      session_id: state.session_id,
      player_profile: state.player_profile,
      scene: state.current_scene,
      question: state.current_question,
      options: state.current_options,
      turn_count: state.turn_count,
      max_turns: state.max_turns,
      phase: state.phase,
      style_mode: state.style_mode,
    });
    setStyleMode(state.style_mode || "classic");
    if (state.world_background) {
      setEditedWorldBackground(state.world_background);
    }
    if (state.history?.length) {
      const latestChoice = state.history[state.history.length - 1]?.choice?.text || "";
      setLastChoiceLabel(latestChoice);
    }
    if (state.ending) {
      setEnding(state.ending);
      if (!preservePage) {
        setPage("game");
      }
    }
  };

  useEffect(() => {
    let cancelled = false;

    async function restoreSnapshot() {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        setIsRestoring(false);
        return;
      }

      try {
        const snapshot = JSON.parse(raw);
        setStyleMode(snapshot.styleMode || "classic");
        setWorld(snapshot.world || null);
        setWorldIdea(snapshot.worldIdea || "");
        setEditedWorldBackground(snapshot.editedWorldBackground || "");
        setSessionId(snapshot.sessionId || "");
        setPage("intro");
        setIntroStep("cover");
        setLastChoiceLabel(snapshot.lastChoiceLabel || "");
        setEnding(snapshot.ending || null);
        setGameData(snapshot.gameData || null);
        setStoryState(snapshot.storyState || null);

        if (snapshot.sessionId) {
          try {
            const freshState = await getStory(snapshot.sessionId);
            if (!cancelled) {
              syncStoryState(freshState, { preservePage: true });
            }
          } catch {
            window.localStorage.removeItem(STORAGE_KEY);
            if (!cancelled) {
              clearLocalState();
            }
          }
        }
      } catch {
        window.localStorage.removeItem(STORAGE_KEY);
        clearLocalState();
      } finally {
        if (!cancelled) {
          setIsRestoring(false);
        }
      }
    }

    restoreSnapshot();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (isRestoring) return;

    if (page === "intro" && !sessionId && !world) {
      window.localStorage.removeItem(STORAGE_KEY);
      return;
    }

    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        page,
        introStep,
        styleMode,
        world,
        worldIdea,
        editedWorldBackground,
        sessionId,
        gameData,
        storyState,
        ending,
        lastChoiceLabel,
      }),
    );
  }, [page, introStep, styleMode, world, worldIdea, editedWorldBackground, sessionId, gameData, storyState, ending, lastChoiceLabel, isRestoring]);

  useEffect(() => {
    if (isRestoring || page !== "intro" || introStep !== "cover") return undefined;

    const timer = window.setTimeout(() => {
      setIntroStep("detail");
    }, 1400);

    return () => {
      window.clearTimeout(timer);
    };
  }, [page, introStep, isRestoring]);

  const handleWorldGenerated = async (generatedWorld, selectedStyle, sourceIdea) => {
    setWorld(generatedWorld);
    setStyleMode(selectedStyle);
    setWorldIdea(sourceIdea);
    setEditedWorldBackground(generatedWorld.world_background);
    setSessionId("");
    setGameData(null);
    setStoryState(null);
    setEnding(null);
    setLastChoiceLabel("");
    setError("");

    try {
      const data = await initStory(generatedWorld.world_background, generatedWorld.world_rules, selectedStyle);
      setSessionId(data.session_id);
      setGameData(data);
      try {
        const state = await getStory(data.session_id);
        syncStoryState(state);
      } catch {
        setStoryState(null);
        setPage("game");
      }
      setPage("game");
    } catch (err) {
      setError(err.message);
      setPage("home");
    }
  };

  const handleStartGame = async (worldBackground) => {
    try {
      setError("");
      setEditedWorldBackground(worldBackground);
      const data = await initStory(worldBackground, world.world_rules, styleMode);
      setSessionId(data.session_id);
      setGameData(data);
      try {
        const state = await getStory(data.session_id);
        syncStoryState(state);
      } catch {
        setStoryState(null);
      }
      setPage("game");
    } catch (err) {
      setError(err.message);
    }
  };

  const handleChoose = async (choiceId) => {
    try {
      setError("");
      const selectedChoice = gameData?.options?.find((option) => option.id === choiceId);
      if (selectedChoice?.text) {
        setLastChoiceLabel(selectedChoice.text);
      }
      const data = await chooseOption(sessionId, choiceId);
      try {
        const state = await getStory(sessionId);
        syncStoryState(state);
      } catch {
        // The current turn still succeeds even if the follow-up sync request fails.
      }
      if (data.is_finished) {
        setEnding(data.ending);
      } else {
        setGameData((current) => ({ ...current, ...data }));
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const handleRestart = async () => {
    if (sessionId) {
      try {
        await restartStory(sessionId);
      } catch {
        // Local state still resets if the previous session is already unavailable.
      }
    }
    clearLocalState();
    window.localStorage.removeItem(STORAGE_KEY);
  };

  const routeProfile = storyState?.flags || createEmptyFlags();
  if (isRestoring) {
    return (
      <div className="app-shell">
        <main className="container">
          <section className="card restore-card">
            <p className="eyebrow">恢复进度</p>
            <h2>正在检查你上一次的冒险记录</h2>
            <p className="subtle">如果服务端 session 还在，前端会自动恢复到上一次游玩位置。</p>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <div className="bg-glow bg-glow-1" aria-hidden="true" />
      <div className="bg-glow bg-glow-2" aria-hidden="true" />
      <main className="container">
        {page === "intro" ? (
          <section className="landing-page">
            <div className={`landing-book${introStep === "detail" ? " is-turned" : ""}`}>
              <div className="landing-sheet landing-sheet-front">
                <div className="landing-cover">
                  <div className="landing-cover-copy">
                    <p className="landing-cover-en">WORLD ENCODER</p>
                    <h1>
                      <span>世界</span>
                      <span>编码器</span>
                    </h1>
                  </div>
                </div>
              </div>
              <div className="landing-sheet landing-sheet-back">
                <div className="landing-detail">
                  <span className="detail-glow detail-glow-left" aria-hidden="true" />
                  <span className="detail-glow detail-glow-right" aria-hidden="true" />
                  <span className="detail-ring" aria-hidden="true" />
                  <div className="landing-copy">
                    <p className="landing-detail-en">CREATE AND ENTER YOUR WORLD</p>
                    <p className="landing-subtitle">
                      从一个灵感开始，创造你的世界，进入你的故事，走向一场无法预知的结局
                    </p>
                    <button
                      type="button"
                      className="primary-button landing-button"
                      onClick={() => setPage("home")}
                    >
                      立即体验
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </section>
        ) : (
          <section className="stage-panel">
            {page === "home" && <Home onGenerated={handleWorldGenerated} />}
            {page === "game" && gameData && !ending && (
              <Game
                gameData={gameData}
                lastChoiceLabel={lastChoiceLabel}
                onChoose={handleChoose}
                error={error}
              />
            )}
            {page === "game" && ending && (
              <Ending
                ending={ending}
                routeProfile={routeProfile}
                storyState={storyState}
                world={world}
                lastChoiceLabel={lastChoiceLabel}
                onRestart={handleRestart}
              />
            )}
          </section>
        )}
      </main>
    </div>
  );
}
