import '@angular/compiler';
import { Component, provideZonelessChangeDetection, signal } from '@angular/core';
import { bootstrapApplication } from '@angular/platform-browser';
import { readJobs } from '../jobs.js';
import { demoMode } from '../demo.js';
import '../studio.css';

class Jobs {
  jobs = signal([]);
  demoMode = demoMode;
  connected = signal(false);
  stopped = false;

  async refresh() {
    if (demoMode) { this.connected.set(true); return; }
    try {
      this.jobs.set(await readJobs());
      this.connected.set(true);
    } catch {
      this.connected.set(false);
    } finally {
      if (!this.stopped) this.timer = setTimeout(() => this.refresh(), 1000);
    }
  }

  ngOnInit() {
    void this.refresh();
  }

  ngOnDestroy() {
    this.stopped = true;
    clearTimeout(this.timer);
  }
}

Component({
  selector: 'syncshot-jobs',
  standalone: true,
  template: `
    <main>
      <nav><strong>SyncShot</strong><a href="../">Video studio</a></nav>
      <section>
        <h1>Render history</h1>
        @if (demoMode) { <p>Browser demo: job history is available only when running the local API. Create a sample scene plan in Video studio.</p> }
        @else if (!connected()) {
          <p role="status">Waiting for the local job API.</p>
        } @else {
          <ul aria-label="Render jobs">
            @for (job of jobs(); track job.id) {
              <li>
                <strong>{{job.media?.audio ?? 'Render job'}}</strong>
                <p>
                  {{job.mode === 'plan' ? 'Scene plan' : job.mode === 'preview' ? 'Preview' : 'Full render'}}
                  · {{job.status}}
                  @if (job.mode !== 'plan') { · {{job.progress ?? 0}}% }
                </p>
                @if (job.error) { <p class="error">{{job.error}}</p> }
                @if (job.videoUrl) { <a [href]="job.videoUrl">{{job.mode === 'preview' ? 'Open preview' : 'Download MP4'}}</a> }
              </li>
            } @empty {
              <li>No render jobs this session.</li>
            }
          </ul>
        }
      </section>
    </main>
  `,
})(Jobs);

bootstrapApplication(Jobs, { providers: [provideZonelessChangeDetection()] })
  .catch(console.error);
