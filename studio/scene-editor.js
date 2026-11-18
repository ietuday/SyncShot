// Pure, framework-independent helpers for the browser scene editor.
export function reorderScenes(scenes, from, to) {
  if (!Number.isInteger(from) || !Number.isInteger(to) || from < 0 || to < 0 ||
      from >= scenes.length || to >= scenes.length) return scenes;
  const next = [...scenes];
  next.splice(to, 0, ...next.splice(from, 1));
  return recalculateScenes(next);
}

export function recalculateScenes(scenes) {
  let cursor = 0;
  return scenes.map(scene => {
    const duration = Math.max(0.1, Math.round((Number(scene.duration ?? (scene.end - scene.start)) || 0.1) * 100) / 100);
    const start = Math.round(cursor * 100) / 100;
    cursor += duration;
    return { ...scene, duration, start, end: Math.round(cursor * 100) / 100 };
  });
}

export function setSceneDuration(scenes, index, duration) {
  if (!Number.isFinite(duration) || duration < 0.5 || duration > 3600 ||
      index < 0 || index >= scenes.length) return scenes;
  return recalculateScenes(scenes.map((scene, i) => i === index ? { ...scene, duration } : scene));
}
