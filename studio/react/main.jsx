import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { readJobs, cancelJob } from '../jobs.js';
import '../studio.css';
import { downloadScenePlan } from '../scene-export.js';
import { demoMode, sampleDuration, samplePhotos, planDemoScenes } from '../demo.js';
import { reorderScenes, setSceneDuration } from '../scene-editor.js';
import { sceneAtTime, clampPreviewTime } from '../scene-preview.js';
import { recalculateScenes } from '../scene-editor.js';
import { editedTimelinePayload, downloadEditedTimeline } from '../timeline-contract.js';

function Studio() {
  const [jobs, setJobs] = useState([]);
  const [connected, setConnected] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [audio, setAudio] = useState(null);
  const [images, setImages] = useState([]);
  const [motion, setMotion] = useState('zoom_in');
  const [sceneLength, setSceneLength] = useState('auto');
  const [transition, setTransition] = useState('fade');
  const [profile, setProfile] = useState('720p');
  const [captionSource, setCaptionSource] = useState('off');
  const [language, setLanguage] = useState('auto');
  const [subtitles, setSubtitles] = useState(null);
  const [error, setError] = useState('');
  const [sampleSelected, setSampleSelected] = useState(false);
  const [demoDuration, setDemoDuration] = useState(String(sampleDuration));
  const [editedScenes, setEditedScenes] = useState(null);
  const [photoUrls, setPhotoUrls] = useState({});
  const [dragIndex, setDragIndex] = useState(null);
  const [previewTime, setPreviewTime] = useState(0);
  const [previewPlaying, setPreviewPlaying] = useState(false);
  const playbackRef = useRef(0);
  const plannedJobRef = useRef(null);

  useEffect(() => {
    if (!images.length) { setPhotoUrls({}); return; }
    const urls = Object.fromEntries(images.map(file => [file.name, URL.createObjectURL(file)]));
    setPhotoUrls(urls);
    return () => Object.values(urls).forEach(url => URL.revokeObjectURL(url));
  }, [images]);

  useEffect(() => {
    if (demoMode) { setConnected(true); return; }
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

  useEffect(() => {
    if (demoMode) return;
    const planJob = jobs.find(job => job.mode === 'plan' && job.status === 'completed' && job.scenes?.length);
    if (!planJob || plannedJobRef.current === planJob.id) return;
    plannedJobRef.current = planJob.id;
    // The renderer's automatic plan includes crossfade overlap. For editing,
    // scenes use non-overlapping visible intervals; the backend adds overlap.
    const scenes = planJob.scenes.map((scene, i, list) => ({
      ...scene,
      duration: Number(((i + 1 < list.length ? list[i + 1].start : scene.end) - scene.start).toFixed(2)),
    }));
    setEditedScenes(recalculateScenes(scenes));
    setPreviewPlaying(false);
    setPreviewTime(0);
  }, [jobs]);

  function movePhoto(index, direction) {
    setImages(current => {
      const reordered = [...current];
      const destination = index + direction;
      [reordered[index], reordered[destination]] = [reordered[destination], reordered[index]];
      return reordered;
    });
  }

  async function start(mode, useEdited = false) {
    if (demoMode) {
      if (mode !== 'plan') return;
      try {
        setError('');
        const photos = sampleSelected ? samplePhotos : images.map(file => file.name);
        const duration = Number(demoDuration);
        const scenes = planDemoScenes({ photos, duration, sceneLength, transition });
        setEditedScenes(scenes);
        setPreviewPlaying(false);
        setPreviewTime(0);
        setJobs([{ id: 'demo-' + Date.now(), mode: 'plan', status: 'completed', progress: 100,
          scenes, hasNarration: false, media: { audio: sampleSelected ? 'Demo narration (60s)' : audio?.name || 'Manual duration', durationSeconds: duration, images: photos.length } }, ...jobs]);
      } catch (err) { setError(err.message); }
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const body = new FormData();
      body.append('audio', audio);
      body.append('mode', mode);
      body.append('motion', motion);
      body.append('transition', transition);
      body.append('profile', profile);
      body.append('sceneLength', sceneLength);
      if (captionSource === 'srt') body.append('subtitles', subtitles);
      if (captionSource === 'whisper') body.append('transcribe', language);
      if (useEdited && editedScenes) body.append('timeline', JSON.stringify(editedTimelinePayload(editedScenes, motion)));
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
  const displayedScenes = editedScenes ?? latest?.scenes;
  const moveScene = (from, to) => setEditedScenes(current => reorderScenes(current, from, to));
  const totalPreviewTime = displayedScenes?.at(-1)?.end ?? 0;
  const activePreview = sceneAtTime(displayedScenes, previewTime);
  useEffect(() => {
    if (!previewPlaying || !totalPreviewTime) return;
    playbackRef.current = performance.now();
    const timer = setInterval(() => {
      const now = performance.now();
      const elapsed = (now - playbackRef.current) / 1000;
      playbackRef.current = now;
      setPreviewTime(previous => {
        const next = clampPreviewTime(previous + elapsed, displayedScenes);
        if (next >= totalPreviewTime) setPreviewPlaying(false);
        return next;
      });
    }, 80);
    return () => clearInterval(timer);
  }, [previewPlaying, totalPreviewTime, displayedScenes]);
  useEffect(() => {
    setPreviewTime(previous => clampPreviewTime(previous, displayedScenes));
  }, [displayedScenes]);
  const busy = latest && ['checking inputs', 'transcribing', 'rendering', 'cancelling'].includes(latest.status);
  const canRender = demoMode
    ? connected && (sampleSelected || images.length > 0) && Number(demoDuration) > 0
    : connected && !submitting && !busy && audio && images.length && (captionSource !== 'srt' || subtitles);
  return <main>
    <nav><strong>SyncShot</strong><a href={`${import.meta.env.BASE_URL}angular/`}>Render history</a></nav>
    <section>
      <h1>Video studio</h1>
      {demoMode && <div className="demo-notice" role="status"><strong>Browser demo mode</strong> — scene planning works here, but this site cannot render MP4s or transcribe audio. Your selected files remain in your browser.</div>}
      <p>{demoMode ? 'Try sample scenes or choose your own photos for a local timeline preview.' : 'Select a narration and the photos for your video. Uploads can total up to 512 MB.'}</p>
      {demoMode && <div className="demo-controls">
        <label><input type="checkbox" checked={sampleSelected} onChange={event => setSampleSelected(event.target.checked)} /> Use four sample photos (60-second example)</label>
        <label>Narration duration (seconds)
          <input type="number" min="1" max="7200" step="1" value={demoDuration} onChange={event => setDemoDuration(event.target.value)} />
        </label>
      </div>}
      <fieldset disabled={submitting || busy}>
        {!demoMode && <label>Narration
          <input type="file" accept=".mp3,.wav,.m4a,.aac,.flac,.ogg"
            onChange={event => setAudio(event.target.files[0] ?? null)} />
        </label>}
        {!sampleSelected && <label>Photos
          <input type="file" accept=".jpg,.jpeg,.png,.webp,.bmp" multiple
            onChange={event => setImages(Array.from(event.target.files).sort((a, b) => a.name.localeCompare(b.name)))} />
        </label>}
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
        {!demoMode && <label>Output resolution
          <select value={profile} onChange={event => setProfile(event.target.value)}>
            <option value="720p">720p — lower memory</option>
            <option value="1080p">1080p — higher quality</option>
          </select>
        </label>}
        <label>Transition
          <select value={transition} onChange={event => setTransition(event.target.value)}>
            <option value="fade">Crossfade</option>
            <option value="cut">Cut</option>
          </select>
        </label>
        {!demoMode && <label>Captions
          <select value={captionSource} onChange={event => {
            setCaptionSource(event.target.value);
            setSubtitles(null);
          }}>
            <option value="off">Off</option>
            <option value="srt">Use an SRT file</option>
            <option value="whisper">Transcribe locally with Whisper</option>
          </select>
        </label>}
        {!demoMode && captionSource === 'whisper' && <label>Narration language
          <select value={language} onChange={event => setLanguage(event.target.value)}>
            <option value="auto">Detect automatically</option>
            <option value="hi">Hindi</option>
            <option value="en">English</option>
          </select>
        </label>}
        {!demoMode && captionSource === 'srt' && <label>Subtitle file
          <input type="file" accept=".srt" onChange={event => setSubtitles(event.target.files[0] ?? null)} />
        </label>}
      </fieldset>
      <div className="actions">
        <button onClick={() => start('plan')} disabled={!canRender}>Plan scenes</button>
        {!demoMode && <button onClick={() => start('preview')} disabled={!canRender}>Preview 10 seconds</button>}
        {!demoMode && <button onClick={() => start('full')} disabled={!canRender}>Render video</button>}
        {!demoMode && editedScenes && <button type="button" onClick={() => start('full', true)} disabled={!canRender}>Render edited timeline</button>}
      </div>
      {!demoMode && busy && latest?.status !== 'cancelling' && <button type="button" onClick={() => cancelJob(latest.id).catch(err => setError(err.message))}>Cancel active job</button>}
      {submitting && <p role="status">Uploading…</p>}
      {latest && latest.mode !== 'plan' && (busy || latest.status === 'completed') && <p>
        <progress aria-label="Render progress" max="100" value={latest.progress ?? 0} /> {latest.progress ?? 0}%
      </p>}
      <div aria-live="polite">
        {!connected && !demoMode && <p>Waiting for the local job API.</p>}
        {latest && <p>{({ plan: 'Scene plan', preview: 'Preview', full: 'Full render' })[latest.mode] ?? 'Full render'}: {latest.status}</p>}
        {latest?.media && <p>{latest.media.audio} · {Math.round(latest.media.durationSeconds)} s · {latest.media.images} images</p>}
        {(error || latest?.error) && <p className="error">{error || latest.error}</p>}
        {latest?.videoUrl && (latest.mode === 'preview'
          ? <video key={latest.id} controls src={latest.videoUrl} aria-label="Video preview" />
          : <a href={latest.videoUrl}>Download MP4</a>)}
      </div>
      {displayedScenes && <div className="scene-plan">
        <div className="scene-plan-heading">
          <h2>Full video scene plan</h2>
          <button type="button" onClick={() => downloadScenePlan(displayedScenes, latest?.hasNarration)}>Download scene plan CSV</button>
          <button type="button" onClick={() => downloadEditedTimeline(displayedScenes, motion)}>Export timeline JSON</button>
        </div>
        <p>{demoMode ? 'Estimated scene timing for demonstration only.' : 'The edited timeline uses visible scene durations; the renderer adds the selected crossfade overlap. Each caption is listed where it starts.'}</p>
        {editedScenes && <div className="visual-editor">
          <h3>Visual scene editor</h3>
          <p>Drag scenes to reorder, or use arrow buttons. For real rendering, the edited total must match your narration duration within 0.06 seconds.</p>
          <div className="scene-preview-panel">
            <h3>Interactive scene preview</h3>
            <p>Timeline slideshow (not encoded video). Use Render edited timeline with the local API to create an actual MP4. Audio is not played here.</p>
            <div className="preview-stage" aria-label="Current scene preview">
              {activePreview && (photoUrls[activePreview.scene.image]
                ? <img src={photoUrls[activePreview.scene.image]} alt={activePreview.scene.image}
                    className={motion === 'static' ? 'preview-image' : 'preview-image preview-motion'}
                    key={activePreview.index} />
                : <div className="preview-placeholder">
                    <strong>Scene {activePreview.index + 1}</strong>
                    <span>{activePreview.scene.image}</span>
                  </div>)}
            </div>
            <div className="preview-controls">
              <button type="button" disabled={!totalPreviewTime} onClick={() => {
                if (previewTime >= totalPreviewTime) setPreviewTime(0);
                setPreviewPlaying(value => !value);
              }}>{previewPlaying ? 'Pause' : 'Play'}</button>
              <button type="button" disabled={!totalPreviewTime} onClick={() => {
                setPreviewPlaying(false);
                setPreviewTime(0);
              }}>Restart</button>
              <output aria-live="off">{previewTime.toFixed(1)} / {totalPreviewTime.toFixed(1)} s</output>
            </div>
            <label>Timeline playhead
              <input type="range" min="0" max={Math.max(0.1, totalPreviewTime)} step="0.1"
                value={Math.min(previewTime, totalPreviewTime)} aria-label="Seek through scenes"
                onChange={event => { setPreviewPlaying(false); setPreviewTime(Number(event.target.value)); }} />
            </label>
          </div>
          <div className="timeline-strip" aria-label="Scene timeline">
            {displayedScenes.map((scene, index) => <div className="timeline-segment" key={index}
              style={{ flexGrow: scene.duration ?? (scene.end - scene.start) }} title={scene.image}>
              {index + 1}
            </div>)}
          </div>
          <p><strong>Edited video length:</strong> {displayedScenes.at(-1)?.end.toFixed(2)} seconds</p>
          <ol className="scene-cards" aria-label="Editable scene list">
            {displayedScenes.map((scene, index) => <li key={index} className="scene-card" draggable
              onDragStart={event => { setDragIndex(index); event.dataTransfer.effectAllowed = 'move'; }}
              onDragOver={event => event.preventDefault()}
              onDrop={event => { event.preventDefault(); if (dragIndex !== null) moveScene(dragIndex, index); setDragIndex(null); }}
              onDragEnd={() => setDragIndex(null)}>
              {photoUrls[scene.image]
                ? <img className="scene-thumb" src={photoUrls[scene.image]} alt={scene.image} />
                : <div className="scene-thumb placeholder" aria-label="Sample photo placeholder">Scene {index + 1}</div>}
              <div className="scene-details">
                <strong>{index + 1}. {scene.image}</strong>
                <small>{scene.start.toFixed(2)}–{scene.end.toFixed(2)} s</small>
                <label>Duration (seconds)
                  <input type="number" min="0.5" max="3600" step="0.5"
                    value={scene.duration ?? Number((scene.end - scene.start).toFixed(2))}
                    onChange={event => setEditedScenes(current => setSceneDuration(current, index, Number(event.target.value)))} />
                </label>
              </div>
              <div className="scene-reorder">
                <button type="button" disabled={index === 0} aria-label={`Move scene ${index + 1} earlier`}
                  onClick={() => moveScene(index, index - 1)}>↑</button>
                <button type="button" disabled={index === displayedScenes.length - 1} aria-label={`Move scene ${index + 1} later`}
                  onClick={() => moveScene(index, index + 1)}>↓</button>
              </div>
            </li>)}
          </ol>
        </div>}
        <table>
          <thead><tr><th scope="col">Scene</th><th scope="col">Start</th><th scope="col">End</th><th scope="col">Photo</th>{latest.hasNarration && <th scope="col">Narration</th>}</tr></thead>
          <tbody>
            {displayedScenes.map((scene, index) => <tr key={index}>
              <td>{index + 1}</td>
              <td>{scene.start.toFixed(2)} s</td>
              <td>{scene.end.toFixed(2)} s</td>
              <td>{scene.image}</td>
              {latest.hasNarration && <td className="scene-narration">{scene.narration?.join('\n') || '—'}</td>}
            </tr>)}
          </tbody>
        </table>
      </div>}
    </section>
  </main>;
}

createRoot(document.getElementById('root')).render(<Studio />);
