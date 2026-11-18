import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { readJobs } from '../jobs.js';
import '../studio.css';

function Studio() {
  const [jobs, setJobs] = useState([]);
  const [connected, setConnected] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [audio, setAudio] = useState(null);
  const [images, setImages] = useState([]);
  const [motion, setMotion] = useState('zoom_in');
  const [sceneLength, setSceneLength] = useState('auto');
  const [transition, setTransition] = useState('fade');
  const [subtitlesEnabled, setSubtitlesEnabled] = useState(false);
  const [subtitles, setSubtitles] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let mounted = true;
    async function refresh() {
      try {
        const jobs = await readJobs();
        if (!mounted) return;
        setJobs(jobs);
        setConnected(true);
      } catch {
        if (mounted) setConnected(false);
      } finally {
        if (mounted) timer = setTimeout(refresh, 1000);
      }
    }
    let timer;
    void refresh();
    return () => {
      mounted = false;
      clearTimeout(timer);
    };
  }, []);

  function movePhoto(index, direction) {
    setImages(current => {
      const reordered = [...current];
      const destination = index + direction;
      [reordered[index], reordered[destination]] = [reordered[destination], reordered[index]];
      return reordered;
    });
  }

  async function start(mode) {
    setSubmitting(true);
    setError('');
    try {
      const body = new FormData();
      body.append('audio', audio);
      body.append('mode', mode);
      body.append('motion', motion);
      body.append('transition', transition);
      body.append('sceneLength', sceneLength);
      if (mode !== 'plan' && subtitlesEnabled) body.append('subtitles', subtitles);
      for (const image of images) body.append('images', image);
      await readJobs('POST', body);
      setJobs(await readJobs());
    } catch (error) {
      setError(error.message);
    } finally {
      setSubmitting(false);
    }
  }

  const latest = jobs[0];
  const busy = latest && ['checking inputs', 'rendering'].includes(latest.status);
  const canPlan = connected && !submitting && !busy && audio && images.length;
  const canRender = canPlan && (!subtitlesEnabled || subtitles);
  return <main>
    <nav><strong>SyncShot</strong><a href="/angular/">Render history</a></nav>
    <section>
      <h1>Video studio</h1>
      <p>Select a narration and the photos for your video. Uploads can total up to 512 MB.</p>
      <fieldset disabled={submitting || busy}>
        <label>Narration
          <input type="file" accept=".mp3,.wav,.m4a,.aac,.flac,.ogg"
            onChange={event => setAudio(event.target.files[0] ?? null)} />
        </label>
        <label>Photos
          <input type="file" accept=".jpg,.jpeg,.png,.webp,.bmp" multiple
            onChange={event => setImages(Array.from(event.target.files).sort((a, b) => a.name.localeCompare(b.name)))} />
        </label>
        {!!images.length && <ol className="photo-order" aria-label="Photo order">
          {images.map((image, index) => <li key={`${image.name}-${image.lastModified}-${index}`}>
            <span>{index + 1}. {image.name}</span>
            <div>
              <button type="button" aria-label={`Move ${image.name} up`} disabled={index === 0}
                onClick={() => movePhoto(index, -1)}>↑</button>
              <button type="button" aria-label={`Move ${image.name} down`} disabled={index === images.length - 1}
                onClick={() => movePhoto(index, 1)}>↓</button>
            </div>
          </li>)}
        </ol>}
        <label>Scene pacing
          <select value={sceneLength} onChange={event => setSceneLength(event.target.value)}>
            <option value="auto">By photo count</option>
            <option value="8">About 8 seconds per scene</option>
            <option value="15">About 15 seconds per scene</option>
            <option value="30">About 30 seconds per scene</option>
          </select>
        </label>
        <label>Photo motion
          <select value={motion} onChange={event => setMotion(event.target.value)}>
            <option value="static">None</option>
            <option value="zoom_in">Zoom in</option>
            <option value="zoom_out">Zoom out</option>
            <option value="pan_left">Pan left</option>
            <option value="pan_right">Pan right</option>
          </select>
        </label>
        <label>Transition
          <select value={transition} onChange={event => setTransition(event.target.value)}>
            <option value="fade">Crossfade</option>
            <option value="cut">Cut</option>
          </select>
        </label>
        <label className="checkbox">
          <input type="checkbox" checked={subtitlesEnabled} onChange={event => {
            setSubtitlesEnabled(event.target.checked);
            setSubtitles(null);
          }} /> Add subtitles from an SRT file
        </label>
        {subtitlesEnabled && <label>Subtitle file
          <input type="file" accept=".srt" onChange={event => setSubtitles(event.target.files[0] ?? null)} />
        </label>}
      </fieldset>
      <div className="actions">
        <button onClick={() => start('plan')} disabled={!canPlan}>Plan scenes</button>
        <button onClick={() => start('preview')} disabled={!canRender}>Preview 10 seconds</button>
        <button onClick={() => start('full')} disabled={!canRender}>Render video</button>
      </div>
      {submitting && <p role="status">Uploading…</p>}
      {latest && latest.mode !== 'plan' && (busy || latest.status === 'completed') && <p>
        <progress aria-label="Render progress" max="100" value={latest.progress ?? 0} /> {latest.progress ?? 0}%
      </p>}
      <div aria-live="polite">
        {!connected && <p>Waiting for the local job API.</p>}
        {latest && <p>{({ plan: 'Scene plan', preview: 'Preview', full: 'Full render' })[latest.mode] ?? 'Full render'}: {latest.status}</p>}
        {latest?.media && <p>{latest.media.audio} · {Math.round(latest.media.durationSeconds)} s · {latest.media.images} images</p>}
        {(error || latest?.error) && <p className="error">{error || latest.error}</p>}
        {latest?.videoUrl && (latest.mode === 'preview'
          ? <video key={latest.id} controls src={latest.videoUrl} aria-label="Video preview" />
          : <a href={latest.videoUrl}>Download MP4</a>)}
      </div>
      {latest?.scenes && <div className="scene-plan">
        <h2>Full video scene plan</h2>
        <p>Timings use the files and settings from the last plan. Crossfade scenes overlap.</p>
        <table>
          <thead><tr><th scope="col">Scene</th><th scope="col">Start</th><th scope="col">End</th><th scope="col">Photo</th></tr></thead>
          <tbody>
            {latest.scenes.map((scene, index) => <tr key={index}>
              <td>{index + 1}</td>
              <td>{scene.start.toFixed(2)} s</td>
              <td>{scene.end.toFixed(2)} s</td>
              <td>{scene.image}</td>
            </tr>)}
          </tbody>
        </table>
      </div>}
    </section>
  </main>;
}

createRoot(document.getElementById('root')).render(<Studio />);
