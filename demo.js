const byId = id => document.getElementById(id);
const audio = new Audio();
const sample = [
  { name: 'A road through the hills', color: '#325647' },
  { name: 'The river crossing', color: '#214e68' },
  { name: 'A quiet evening', color: '#634137' },
];
let duration = 24;
let photos = [];
let timer;

function stopPreview() {
  cancelAnimationFrame(timer);
  audio.pause();
  byId('player').hidden = true;
}

function buildPlan() {
  const sources = photos.length ? photos : sample;
  const pacing = byId('pacing').value;
  const count = Math.min(500, pacing === 'auto' ? sources.length : Math.ceil(duration / Number(pacing)));
  return Array.from({ length: count }, (_, index) => ({
    photo: sources[index % sources.length],
    start: index * duration / count,
    end: (index + 1) * duration / count,
  }));
}

function showPlan() {
  const scenes = buildPlan();
  document.querySelector('tbody').replaceChildren(...scenes.map((scene, index) => {
    const row = document.createElement('tr');
    for (const value of [index + 1, scene.start.toFixed(2) + ' s', scene.end.toFixed(2) + ' s', scene.photo.name]) {
      row.insertCell().textContent = value;
    }
    return row;
  }));
  document.querySelector('table').hidden = false;
  byId('status').textContent = scenes.length + ' scenes across ' + duration.toFixed(1) + ' seconds.';
  return scenes;
}

byId('audio').addEventListener('change', () => {
  stopPreview();
  if (audio.src) URL.revokeObjectURL(audio.src);
  const file = byId('audio').files[0];
  byId('preview').disabled = Boolean(file);
  byId('plan').disabled = Boolean(file);
  if (file) audio.src = URL.createObjectURL(file);
  else {
    audio.removeAttribute('src');
    audio.load();
    duration = 24;
    showPlan();
  }
});

audio.addEventListener('loadedmetadata', () => {
  if (!Number.isFinite(audio.duration) || audio.duration <= 0) {
    byId('status').textContent = 'Choose an audio file with a known duration.';
    return;
  }
  duration = audio.duration;
  byId('preview').disabled = byId('plan').disabled = false;
  showPlan();
});
audio.addEventListener('error', () => {
  if (byId('audio').files.length) byId('status').textContent = 'This browser could not read the selected audio.';
});

byId('photos').addEventListener('change', () => {
  stopPreview();
  for (const photo of photos) URL.revokeObjectURL(photo.url);
  photos = Array.from(byId('photos').files, file => ({ name: file.name, url: URL.createObjectURL(file) }));
  if (!byId('plan').disabled) showPlan();
});
byId('plan').addEventListener('click', showPlan);
byId('preview').addEventListener('click', async () => {
  stopPreview();
  const scenes = showPlan();
  const frame = byId('frame');
  const limit = Math.min(duration, 10);
  if (byId('audio').files.length) {
    audio.currentTime = 0;
    try {
      await audio.play();
    } catch {
      byId('status').textContent = 'Audio playback could not start.';
      return;
    }
  }
  byId('player').hidden = false;
  const started = performance.now();
  let shown;
  function draw(now) {
    const elapsed = Math.min(limit, (now - started) / 1000);
    const scene = scenes.find(item => elapsed < item.end) ?? scenes.at(-1);
    if (scene !== shown) {
      frame.style.backgroundColor = scene.photo.color ?? '#19362d';
      frame.textContent = scene.photo.name;
      if (scene.photo.url) {
        const image = new Image();
        image.src = scene.photo.url;
        image.alt = scene.photo.name;
        frame.replaceChildren(image);
      }
      shown = scene;
    }
    byId('time').textContent = elapsed.toFixed(1) + ' / ' + limit.toFixed(1) + ' seconds';
    if (elapsed < limit) timer = requestAnimationFrame(draw);
    else audio.pause();
  }
  timer = requestAnimationFrame(draw);
});
showPlan();
