import { execFile } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { mkdir, rm, stat, writeFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createInterface } from 'node:readline';
import { maxUploadBytes, receiveMedia } from './uploads.mjs';
import { validateEditedTimeline } from './timeline-contract.js';
import { trimManualTimeline } from './manual-preview.js';
import { promisify } from 'node:util';

const run = promisify(execFile);
const studio = fileURLToPath(new URL('.', import.meta.url));
const root = resolve(studio, '..');
const inputs = resolve(process.env.SYNCSHOT_INPUTS ?? join(root, 'inputs'));
const runs = resolve(process.env.SYNCSHOT_RUNS ?? join(root, 'output', 'studio'));
const renderer = resolve(process.env.SYNCSHOT_BIN ?? join(root, 'output', 'syncshot-studio-renderer'));
const python = process.env.SYNCSHOT_PYTHON ?? 'python3';
const jobs = new Map();
const controllers = new Map();
const allowedOrigins = request => !request.headers.origin || [
  'http://localhost:5173', 'http://localhost:4200', 'http://127.0.0.1:5173',
  'http://127.0.0.1:4200', 'http://' + request.headers.host,
].includes(request.headers.origin);
let active = false;

async function render(job, upload) {
  const directory = join(runs, job.id);
  const controller = controllers.get(job.id);
  const signal = controller?.signal;
  try {
    const { audio, images } = upload ?? { audio: join(inputs, 'audio'), images: join(inputs, 'images') };
    const preflight = await run(python, [join(studio, 'preflight.py'), audio, images], {
      timeout: 20000, signal,
    });
    job.media = JSON.parse(preflight.stdout);
    if (upload) job.media.audio = upload.audioName;
    const filename = job.mode === 'preview' ? 'preview.mp4' : 'final.mp4';
    await mkdir(directory, { recursive: true });
    let subtitles = upload?.subtitles;
    if (upload?.language) {
      job.status = 'transcribing';
      subtitles = join(directory, 'uploads', 'generated.srt');
      await run(python, [
        join(root, 'scripts', 'transcribe-audio.py'), '--audio', upload.audioPath,
        '--output', subtitles, '--format', 'srt', '--language', upload.language,
      ], { timeout: 2 * 60 * 60 * 1000, maxBuffer: 1024 * 1024, signal });
    }
    let timelinePath;
    let renderAudioDir = audio;
    if (upload?.timeline) {
      const timeline = validateEditedTimeline(upload.timeline, upload.imageNames,
        job.media.durationSeconds, { crossfade: upload.crossfade, width: upload.profile === '1080p' ? 1920 : 1280, height: upload.profile === '1080p' ? 1080 : 720 });
      if (job.mode === 'preview') {
        const previewSeconds = Math.min(10, job.media.durationSeconds);
        const previewDir = join(directory, 'preview-audio');
        await mkdir(previewDir, { recursive: true });
        await run('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y',
          '-i', upload.audioPath, '-t', String(previewSeconds),
          '-vn', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le',
          join(previewDir, 'narration.wav')], { timeout: 120000, signal });
        renderAudioDir = previewDir;
        Object.assign(timeline, trimManualTimeline(timeline, previewSeconds));
      }
      timeline.scenes = timeline.scenes.map(scene => ({
        ...scene, image: join(images, scene.image),
      }));
      timelinePath = join(directory, 'edited-timeline.json');
      await writeFile(timelinePath, JSON.stringify(timeline));
    }
    const configPath = join(directory, 'config.json');
    await writeFile(configPath, JSON.stringify({
      WorkDir: join(directory, 'work'),
      OutShortsDir: join(directory, 'shorts'),
      ...(upload ? {
        ClipSeconds: 0,
        ...(upload.profile ? { RenderProfile: upload.profile } : {}),
        ...(timelinePath ? { CinematicTimelinePath: timelinePath, CinematicChunkScenes: 0, RenderProfile: '' } : {}),
        PreviewSeconds: job.mode === 'preview' && !timelinePath ? 10 : 0,
        CinematicMotion: upload.motion,
        CinematicCrossfade: upload.crossfade,
        CinematicAutoSceneSeconds: upload.sceneLength || job.media.durationSeconds / job.media.images,
        ...(subtitles ? { SubtitleSRTPath: subtitles } : {}),
      } : {}),
    }));
    const args = [
      '--config', configPath, '--audio-dir', renderAudioDir, '--images-dir', images,
      '--output', join(directory, timelinePath ? filename : 'final.mp4'), '--memory-mode', 'low',
    ];
    if (job.mode === 'plan') {
      const result = await run(renderer, [...args, '--plan-scenes', '--timeout', '20s'], { cwd: directory, maxBuffer: 8 * 1024 * 1024 });
      job.scenes = JSON.parse(result.stdout).map(scene => ({
        ...scene, image: upload.imageNames.get(scene.image),
      }));
      job.hasNarration = Boolean(subtitles);
      job.status = 'completed';
      return;
    }

    job.status = 'rendering';
    const process = run(renderer, [...args, '--json-progress', '--timeout', '2h'],
      { cwd: directory, maxBuffer: 16 * 1024 * 1024, signal });
    const lines = createInterface({ input: process.child.stdout });
    lines.on('line', line => {
      const match = /^\{"renderProgress":(\d+\.\d+)\}$/.exec(line);
      if (match) job.progress = Math.max(job.progress, Math.min(99, Math.floor(Number(match[1]) * 100)));
    });
    try {
      await process;
    } finally {
      lines.close();
    }
    const video = await stat(join(directory, filename));
    if (!video.isFile() || video.size === 0) throw new Error('Renderer produced no video.');
    job.progress = 100;
    job.status = 'completed';
    job.videoUrl = '/api/jobs/' + job.id + '/video';
  } catch (error) {
    job.status = signal?.aborted ? 'cancelled' : 'failed';
    if (!signal?.aborted) job.error = (error.stderr?.trim() || error.message).slice(-2000);
  } finally {
    if (upload) {
      const temporary = job.mode === 'plan' ? directory : join(directory, 'uploads');
      await rm(temporary, { recursive: true, force: true }).catch(console.error);
    }
    controllers.delete(job.id);
    active = false;
  }
}

function json(response, status, body) {
  response.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
  response.end(JSON.stringify(body));
}

createServer(async (request, response) => {
  const { method, url } = request;
  if (url === '/api/jobs' && method === 'GET') {
    return json(response, 200, Array.from(jobs.values()).reverse());
  }
  if (url === '/api/jobs' && method === 'POST') {
    if (!allowedOrigins(request)) {
      return json(response, 403, { error: 'Origin is not allowed.' });
    }
    if (active) return json(response, 409, { error: 'A render is already running.' });
    const job = { id: randomUUID(), status: 'checking inputs', progress: 0 };
    const contentType = request.headers['content-type'] ?? '';
    if (Number(request.headers['content-length']) > maxUploadBytes) {
      return json(response, 413, { error: 'Upload exceeds 512 MB.' });
    }
    active = true;
    let upload;
    if (contentType.startsWith('multipart/form-data')) {
      const directory = join(runs, job.id);
      try {
        upload = await receiveMedia(request, join(directory, 'uploads'));
      } catch (error) {
        await rm(directory, { recursive: true, force: true }).catch(console.error);
        active = false;
        return json(response, 400, { error: error.message });
      }
    } else if (contentType || request.headers['transfer-encoding'] || Number(request.headers['content-length']) > 0) {
      active = false;
      return json(response, 415, { error: 'Send media as multipart form data.' });
    }
    job.mode = upload?.mode ?? 'full';
    jobs.set(job.id, job);
    controllers.set(job.id, new AbortController());
    json(response, 202, job);
    void render(job, upload);
    return;
  }
  const cancelMatch = url.match(/^\/api\/jobs\/([a-f0-9-]+)\/cancel$/);
  if (method === 'POST' && cancelMatch) {
    if (!allowedOrigins(request)) return json(response, 403, { error: 'Origin is not allowed.' });
    const job = jobs.get(cancelMatch[1]);
    const controller = controllers.get(cancelMatch[1]);
    if (!job || !controller || !['checking inputs', 'transcribing', 'rendering'].includes(job.status)) {
      return json(response, 409, { error: 'Job is not currently running.' });
    }
    controller.abort();
    job.status = 'cancelling';
    return json(response, 202, { id: job.id, status: job.status });
  }
  const match = url.match(/^\/api\/jobs\/([a-f0-9-]+)\/video$/);
  const job = match && jobs.get(match[1]);
  if (method === 'GET' && job?.status === 'completed' && job.videoUrl) {
    const preview = job.mode === 'preview';
    const filename = preview ? 'preview.mp4' : 'final.mp4';
    const stream = createReadStream(join(runs, job.id, filename));
    stream.once('error', () => {
      if (response.headersSent) response.destroy();
      else json(response, 404, { error: 'Video is unavailable.' });
    });
    stream.once('open', () => {
      response.writeHead(200, { 'Content-Type': 'video/mp4',
        'Content-Disposition': preview ? 'inline; filename="preview.mp4"' : 'attachment; filename="syncshot.mp4"' });
      stream.pipe(response);
    });
    response.once('close', () => stream.destroy());
    return;
  }
  json(response, 404, { error: 'Route not found.' });
}).listen(4310, '127.0.0.1', () => console.log('SyncShot API listening on http://127.0.0.1:4310'));
