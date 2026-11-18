// End-to-end smoke: Node upload -> Go manual timeline -> FFmpeg MP4 -> ffprobe.
// Run with: npm ci (studio), go build -o output/syncshot-studio-renderer ./cmd/syncshot,
// then node studio/test/real-media-smoke.mjs from the repository root.
import { spawn, execFile } from 'node:child_process';
import { mkdtemp, mkdir, readFile, rm, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

const exec = promisify(execFile);
const studio = resolve(fileURLToPath(new URL('..', import.meta.url)));
const root = resolve(studio, '..');
const temp = await mkdtemp(join(tmpdir(), 'syncshot-phase4-'));
let api;
try {
  const audioPath = join(temp, 'narration.wav');
  const photoPath = join(temp, 'one.jpg');
  const secondPhotoPath = join(temp, 'two.jpg');
  await exec('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi',
    '-i', 'sine=frequency=440:duration=1.5', '-ac', '1', '-ar', '48000', audioPath]);
  await exec('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y',
    '-f', 'lavfi', '-i', 'color=c=blue:s=640x360', '-frames:v', '1', '-update', '1', photoPath]);
  await exec('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y',
    '-f', 'lavfi', '-i', 'color=c=red:s=640x360', '-frames:v', '1', '-update', '1', secondPhotoPath]);
  const { stdout: probe } = await exec('ffprobe', ['-v', 'error', '-show_entries',
    'format=duration', '-of', 'default=nw=1:nk=1', audioPath]);
  const seconds = Number(probe.trim());
  if (!(seconds > 0)) throw new Error('Synthetic audio duration missing.');
  api = spawn('node', [join(studio, 'server.mjs')], {
    cwd: root, env: { ...process.env, SYNCSHOT_RUNS: join(temp, 'runs'),
      SYNCSHOT_BIN: join(root, 'output', 'syncshot-studio-renderer') },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let stderr = '';
  api.stderr.on('data', chunk => { stderr += chunk.toString(); });

  async function request(method, path, body) {
    const res = await fetch('http://127.0.0.1:4310' + path, { method, body });
    const payload = await res.json();
    if (!res.ok) throw new Error(JSON.stringify(payload));
    return payload;
  }
  for (let i = 0; i < 100; i++) {
    try { await request('GET', '/api/jobs'); break; }
    catch (error) {
      if (api.exitCode !== null) throw new Error('API exited: ' + stderr);
      if (i === 99) throw error;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }
  for (const variant of [
    { mode: 'preview', transition: 'cut', scenes: [{ image:'one.jpg', duration:seconds, motion:'static' }] },
    { mode: 'full', transition: 'cut', scenes: [{ image:'one.jpg', duration:seconds, motion:'static' }] },
    { mode: 'full', transition: 'fade', scenes: [
      { image:'two.jpg', duration:seconds / 2, motion:'static' },
      { image:'one.jpg', duration:seconds / 2, motion:'static' },
    ] },
  ]) {
    const { mode, transition, scenes } = variant;
    const form = new FormData();
    form.append('audio', new Blob([await readFile(audioPath)], { type: 'audio/wav' }), 'narration.wav');
    form.append('images', new Blob([await readFile(photoPath)], { type: 'image/jpeg' }), 'one.jpg');
    if (scenes.length > 1) form.append('images', new Blob([await readFile(secondPhotoPath)], { type: 'image/jpeg' }), 'two.jpg');
    for (const [key, value] of Object.entries({ mode, motion:'static', transition,
      sceneLength:'auto', profile:'720p' })) form.append(key, value);
    form.append('timeline', JSON.stringify({ version:1, scenes }));
    const job = await request('POST', '/api/jobs', form);
    let final;
    for (let i = 0; i < 240; i++) {
      const history = await request('GET', '/api/jobs');
      final = history.find(item => item.id === job.id);
      if (final?.status === 'completed' || final?.status === 'failed') break;
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    if (final?.status !== 'completed') {
      throw new Error(mode + ' job did not complete: ' + JSON.stringify(final) + '\n' + stderr);
    }
    const file = join(temp, 'runs', job.id, mode === 'preview' ? 'preview.mp4' : 'final.mp4');
    const info = await stat(file);
    if (info.size < 1024) throw new Error('Empty ' + mode + ' MP4');
    const { stdout } = await exec('ffprobe', ['-v', 'error', '-show_entries',
      'format=duration', '-of', 'default=nw=1:nk=1', file]);
    if (Math.abs(Number(stdout.trim()) - seconds) > 0.20) {
      throw new Error(mode + ' duration mismatch: ' + stdout);
    }
    console.log(mode + ' (' + scenes.length + ' scenes, ' + transition + ') MP4 smoke passed (' + info.size + ' bytes)');
  }
} finally {
  if (api && api.exitCode === null) {
    api.kill('SIGTERM');
    await new Promise(resolve => api.once('exit', resolve));
  }
  await rm(temp, { recursive: true, force: true });
}
