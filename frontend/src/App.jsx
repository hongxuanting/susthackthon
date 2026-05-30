import { useState } from "react";
import { chooseOption, initStory, restartStory } from "./api";
import Home from "./components/Home";
import WorldBuilder from "./components/WorldBuilder";
import Game from "./components/Game";
import Ending from "./components/Ending";

export default function App() {
  const [page, setPage] = useState("home");
  const [styleMode, setStyleMode] = useState("classic");
  const [world, setWorld] = useState(null);
  const [sessionId, setSessionId] = useState("");
  const [gameData, setGameData] = useState(null);
  const [ending, setEnding] = useState(null);
  const [error, setError] = useState("");

  const handleWorldGenerated = (generatedWorld, selectedStyle) => {
    setWorld(generatedWorld);
    setStyleMode(selectedStyle);
    setError("");
    setPage("world");
  };

  const handleStartGame = async (worldBackground) => {
    try {
      setError("");
      const data = await initStory(worldBackground, world.world_rules, styleMode);
      setSessionId(data.session_id);
      setGameData(data);
      setPage("game");
    } catch (err) {
      setError(err.message);
    }
  };

  const handleChoose = async (choiceId) => {
    try {
      setError("");
      const data = await chooseOption(sessionId, choiceId);
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
    setPage("home");
    setStyleMode("classic");
    setWorld(null);
    setSessionId("");
    setGameData(null);
    setEnding(null);
    setError("");
  };

  return (
    <main className="container">
      {page === "home" && <Home onGenerated={handleWorldGenerated} />}
      {page === "world" && world && (
        <WorldBuilder world={world} onStart={handleStartGame} error={error} />
      )}
      {page === "game" && gameData && !ending && (
        <Game gameData={gameData} onChoose={handleChoose} error={error} />
      )}
      {page === "game" && ending && (
        <Ending ending={ending} styleMode={styleMode} onRestart={handleRestart} />
      )}
    </main>
  );
}
