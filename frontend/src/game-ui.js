export const STORAGE_KEY = "worldforge-ui-snapshot-v1";

export const STYLE_META = {
  classic: {
    label: "短篇正剧",
    mood: "稳扎稳打，沉浸推进",
    guide: "更适合铺出人物动机和代价感，越谨慎越容易走出厚重结局。",
  },
  meme: {
    label: "轻松爽局",
    mood: "节奏快，梗感强",
    guide: "更适合反复重开试错，离谱一点往往能更快看到有趣结果。",
  },
  chaos: {
    label: "抽象失控",
    mood: "高波动，高反转",
    guide: "越往危险和混乱方向推，越容易提早进入意外结局。",
  },
};

export const PHASE_META = {
  opening: { label: "开局", hint: "先建立局势和第一轮判断" },
  rising: { label: "升温", hint: "风险开始累积，角色立场逐渐成型" },
  crisis: { label: "危机", hint: "局势加速失控，代价感开始兑现" },
  climax: { label: "高潮", hint: "故事正在逼近决定性的结果" },
  ending: { label: "收束", hint: "任何一次选择都可能把结局锁死" },
};

export const ROUTE_META = [
  { id: "bravery", label: "勇气", tone: "正面硬推" },
  { id: "wisdom", label: "谋略", tone: "观察与算计" },
  { id: "kindness", label: "善意", tone: "救人与共情" },
  { id: "ambition", label: "野心", tone: "争取更大回报" },
  { id: "chaos", label: "混乱", tone: "失控与突变" },
  { id: "danger", label: "危险", tone: "高风险高代价" },
  { id: "truth", label: "真相", tone: "追索隐藏信息" },
];

export const IDEA_PRESETS = [
  {
    label: "校园怪谈",
    prompt: "期末考试结束后，学校广播每晚都会点名一个第二天会消失的人。",
  },
  {
    label: "赛博悬疑",
    prompt: "城市停电 3 分钟后，所有监控都出现了一个与你一模一样的人。",
  },
  {
    label: "古风异闻",
    prompt: "边陲小城昨夜坠下一条黑龙，只有你听懂了它临死前说的话。",
  },
  {
    label: "末日生存",
    prompt: "海水一夜退去后，海底露出了一座会说人话的旧神遗迹。",
  },
];

const RANDOM_ROLES = ["实习记者", "县城少年", "失眠程序员", "被贬祭司", "见习猎魔人"];
const RANDOM_EVENTS = ["收到未来自己的录音", "看见所有人头顶的结局标签", "被一场停电卷进时间断层", "发现城市边缘出现会说话的门", "目睹一位神明在街头坠落"];
const RANDOM_TWISTS = ["而且只有你记得上一轮世界发生过什么", "并且每做一个选择都会删去一段真实记忆", "但所有人都坚称灾难根本不存在", "同时有人在暗中直播你的每一次决定", "而你的名字已经被写进了终局公告"];

export function createRandomIdea() {
  const role = RANDOM_ROLES[Math.floor(Math.random() * RANDOM_ROLES.length)];
  const event = RANDOM_EVENTS[Math.floor(Math.random() * RANDOM_EVENTS.length)];
  const twist = RANDOM_TWISTS[Math.floor(Math.random() * RANDOM_TWISTS.length)];
  return `${role}${event}，${twist}。`;
}

export function createEmptyFlags() {
  return {
    bravery: 0,
    wisdom: 0,
    kindness: 0,
    ambition: 0,
    chaos: 0,
    danger: 0,
    truth: 0,
  };
}

export function mergeFlagDelta(currentFlags = createEmptyFlags(), delta = {}) {
  const merged = { ...createEmptyFlags(), ...currentFlags };
  Object.entries(delta || {}).forEach(([key, value]) => {
    if (Object.prototype.hasOwnProperty.call(merged, key)) {
      merged[key] += Number(value || 0);
    }
  });
  return merged;
}

export function getDominantRoutes(flags = {}, limit = 3) {
  return ROUTE_META
    .map((item) => ({ ...item, value: Number(flags?.[item.id] || 0) }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .filter((item) => item.value !== 0)
    .slice(0, limit);
}

export function getRoutePercent(value) {
  return `${Math.min(100, Math.max(8, Math.abs(Number(value || 0)) * 18 + 10))}%`;
}

export function getSceneViews(scene = "") {
  const clean = scene.trim();
  const chunks = clean
    .split(/(?<=[。！？!?])/)
    .map((item) => item.trim())
    .filter(Boolean);

  return {
    line: chunks[0] || clean,
    storyboard: chunks.length ? chunks : [clean],
    full: clean,
  };
}

export function getOptionRisk(option = {}, flags = {}) {
  const effects = option.effects || {};
  const dangerScore = Number(effects.danger || 0) + Math.max(0, Number(flags.danger || 0));
  const chaosScore = Number(effects.chaos || 0) + Math.max(0, Number(flags.chaos || 0));
  const ambitionScore = Number(effects.ambition || 0);
  const truthSafety = Number(effects.truth || 0) + Number(effects.wisdom || 0);
  const rawScore = dangerScore * 2 + chaosScore + ambitionScore - truthSafety;

  if (rawScore >= 4) {
    return { label: "高风险", tone: "hot" };
  }
  if (rawScore >= 2) {
    return { label: "有波动", tone: "warn" };
  }
  return { label: "相对稳", tone: "safe" };
}

export function getFateForecast(option = {}, flags = {}, phase = "opening") {
  const effects = option.effects || {};
  const risk = getOptionRisk(option, flags);

  if (Number(effects.truth || 0) > 0) {
    return "这一步更像在撬开隐藏信息，后续大概率会换来更清晰的局势。";
  }
  if (Number(effects.kindness || 0) > 0 && Number(effects.danger || 0) > 0) {
    return "你在拿自己去换别人的命运，适合打出更有代价感的走向。";
  }
  if (Number(effects.chaos || 0) > 0 || Number(effects.ambition || 0) > 0) {
    return phase === "ending"
      ? "这一步很可能直接把故事推入不可逆的结局。"
      : "这一步会明显抬高戏剧张力，回报高，但翻车也更快。";
  }
  if (risk.tone === "safe") {
    return "这一步更偏稳，适合继续观察世界规则和隐藏动机。";
  }
  return "这一步会让局势继续升温，适合已经做好承担后果的时候再按下。";
}

export function getGuideLine({ stage, styleMode, phase, dominantRoutes = [], selectedOption }) {
  const style = STYLE_META[styleMode] || STYLE_META.classic;
  const topRoute = dominantRoutes[0];

  if (stage === "home") {
    return `先给我一个足够具体的世界钩子，我会帮你把它压成可立即开局的互动叙事。`;
  }
  if (stage === "world") {
    return `这个世界现在已经能玩了。再确认一次核心冲突是否够尖锐，然后直接开局。`;
  }
  if (stage === "ending") {
    return `这局的轨迹已经回收完成。如果你想看另一种命运，换模式或换第一轮判断最有效。`;
  }
  if (selectedOption) {
    return `你正在考虑“${selectedOption.text}”。${getFateForecast(selectedOption, {}, phase)}`;
  }
  if (topRoute) {
    return `当前剧情更偏“${topRoute.label}”路线。${style.guide}`;
  }
  return `${style.label}模式下，${PHASE_META[phase]?.hint || "故事正在推进"}。`;
}

export function getEffectTags(option = {}) {
  return Object.entries(option.effects || {})
    .filter(([, value]) => Number(value) !== 0)
    .map(([key, value]) => {
      const meta = ROUTE_META.find((item) => item.id === key);
      return `${meta?.label || key}${Number(value) > 0 ? "+" : ""}${value}`;
    });
}

export function getEndingSuggestion(dominantRoutes = []) {
  const top = dominantRoutes[0];
  if (!top) {
    return "换一个风格模式，通常比微调单个选项更容易得到完全不同的结局。";
  }
  if (top.id === "danger" || top.id === "chaos") {
    return "下次把前两轮改成更稳的判断，通常能拖出更完整的主线与不同收束。";
  }
  if (top.id === "truth") {
    return "下次少追真相，多做立场选择，结局通常会从“揭露”变成“代价”或“掌控”。";
  }
  if (top.id === "kindness") {
    return "下次放弃一次救人冲动，故事很可能会转向更锋利的个人命运。";
  }
  return "下次试着连续两轮选择反方向气质的选项，最容易拉开新的结局分支。";
}
