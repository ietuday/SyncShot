// Browser-only planner for GitHub Pages. No upload leaves the browser.
export const demoMode = import.meta.env.VITE_DEMO_MODE === 'true';
export const samplePhotos = ['Opening.jpg', 'Journey.jpg', 'Highlights.jpg', 'Closing.jpg'];
export const sampleDuration = 60;

export function planDemoScenes({ photos, duration, sceneLength, transition }) {
  if (!Array.isArray(photos) || !photos.length || !Number.isFinite(duration) || duration <= 0) {
    throw new Error('Select photos and provide a positive narration duration.');
  }
  const desired = Number(sceneLength);
  const count = Math.min(500, desired > 0 ? Math.ceil(duration / desired) : photos.length);
  const step = duration / count;
  return Array.from({ length: count }, (_, index) => ({
    start: Number((index * step).toFixed(2)),
    end: Number(Math.min(duration, (index + 1) * step).toFixed(2)),
    image: photos[index % photos.length],
    narration: [],
  }));
}
