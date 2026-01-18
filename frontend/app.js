const state = {
  projectId: null,
  pollingInterval: null,
  lastRender: null,
  videoOutput: null,
};

// Selectors
const projectList = document.getElementById('project-list');
const openButton = document.getElementById('open-project');
const formatSelect = document.getElementById('format');
const styleSelect = document.getElementById('style');
const subtitlesToggle = document.getElementById('subtitles');
const createButton = document.getElementById('create-project');
const projectInfo = document.getElementById('project-info');
const audioFile = document.getElementById('audio-file');
const uploadButton = document.getElementById('upload-audio');
const uploadStatus = document.getElementById('upload-status');
const audioPlayer = document.getElementById('audio-player');
const runButton = document.getElementById('run-pipeline');
const refreshButton = document.getElementById('refresh-jobs');
const jobsStatus = document.getElementById('jobs-status');
const scenesContainer = document.getElementById('scenes');
const renderButton = document.getElementById('render-project');
const renderOutput = document.getElementById('render-output');
const analysisContent = document.getElementById('analysis-content');
const refreshAnalysisButton = document.getElementById('refresh-analysis');

// Video preview elements
const previewPlaceholder = document.getElementById('preview-placeholder');
const previewImage = document.getElementById('preview-image');
const previewVideo = document.getElementById('preview-video');
const downloadVideo = document.getElementById('download-video');

const pipeContainer = document.getElementById('pipeline-progress-container');
const pipePct = document.getElementById('pipeline-progress-pct');
const pipeFill = document.getElementById('pipeline-progress-fill');
const pipeStep = document.getElementById('pipeline-step');

const renderContainer = document.getElementById('render-progress-container');
const renderPctValue = document.getElementById('render-progress-pct');
const renderFill = document.getElementById('render-progress-fill');

const timelineWrapper = document.querySelector('.timeline-wrapper');
const timelineMarkers = document.getElementById('timeline-markers');
const timelineProgress = document.getElementById('timeline-progress');

async function setProjectInfo(project) {
  state.projectId = project.id;
  state.videoOutput = project.video_output || null;
  state.lastRender = null;
  projectInfo.textContent = `Project: ${project.id} (status: ${project.status})`;
}

function updatePreview(type, src) {
  if (type === 'none') {
    previewPlaceholder.style.display = 'flex';
    previewImage.style.display = 'none';
    previewVideo.style.display = 'none';
    previewVideo.pause();
    downloadVideo.style.display = 'none';
  } else if (type === 'image') {
    previewPlaceholder.style.display = 'none';
    previewImage.style.display = 'block';
    previewVideo.style.display = 'none';
    previewVideo.pause();
    if (previewImage.getAttribute('src') !== src) {
      previewImage.src = src;
    }
    downloadVideo.style.display = 'none';
  } else if (type === 'video') {
    previewPlaceholder.style.display = 'none';
    previewImage.style.display = 'none';
    previewVideo.style.display = 'block';

    // Set src if missing or different
    // Use the property .src which is the full URL for more reliable comparison
    const fullSrc = new URL(src, window.location.origin).href;
    if (previewVideo.src !== fullSrc) {
      previewVideo.src = src;
      previewVideo.load();
    }

    downloadVideo.style.display = 'inline-block';

    // Use the dedicated download endpoint
    const downloadUrl = `/projects/${state.projectId}/download?t=${Date.now()}`;
    downloadVideo.onclick = null;
    downloadVideo.href = downloadUrl;
    // Force download attribute to help browser recognize it as a file save
    downloadVideo.setAttribute('download', '');
  }
}

async function loadAudioPlayer(projectId) {
  audioPlayer.style.display = 'none';
  audioPlayer.pause();
  audioPlayer.src = '';

  if (!projectId) return;

  const audioUrl = `/projects/${projectId}/audio?t=${Date.now()}`;
  audioPlayer.src = audioUrl;

  audioPlayer.onloadedmetadata = () => {
    // Only show audio player if video is NOT ready
    if (state.videoOutput) {
      audioPlayer.style.display = 'none';
    } else {
      audioPlayer.style.display = 'block';
    }
  };

  audioPlayer.onerror = () => {
    audioPlayer.style.display = 'none';
  };
}

async function loadProjects() {
  try {
    const response = await fetch('/projects');
    if (!response.ok) return;
    const projects = await response.json();
    projectList.innerHTML = '<option value="">Select a project...</option>';
    projects.forEach((p) => {
      const opt = document.createElement('option');
      opt.value = p.id;
      const date = new Date(p.created_at).toLocaleString();
      opt.textContent = `${date} - ${p.status}`;
      projectList.appendChild(opt);
    });
  } catch (e) {
    console.error('Failed to load projects', e);
  }
}

async function openProject() {
  const id = projectList.value;
  if (!id) return;

  updatePreview('none');

  try {
    const response = await fetch(`/projects/${id}`);
    if (!response.ok) {
      alert('Failed to load project details');
      return;
    }
    const project = await response.json();
    setProjectInfo(project);
    loadAudioPlayer(project.id);

    if (project.format) formatSelect.value = project.format;
    if (project.style) styleSelect.value = project.style;
    if (project.subtitles !== undefined) subtitlesToggle.checked = project.subtitles;
    if (project.user_description) document.getElementById('user-description').value = project.user_description;
    else document.getElementById('user-description').value = '';

    if (project.character_description) document.getElementById('character-description').value = project.character_description;
    else document.getElementById('character-description').value = '';

    if (project.video_output) {
      updatePreview('video', project.video_output);
    }

    await refreshJobs();
    await loadAnalysis();
  } catch (e) {
    console.error('Failed to open project', e);
  }
}

async function createProject() {
  const response = await fetch('/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      format: formatSelect.value,
      style: styleSelect.value,
      subtitles: subtitlesToggle.checked,
      user_description: document.getElementById('user-description').value,
      character_description: document.getElementById('character-description').value,
    }),
  });
  const data = await response.json();
  setProjectInfo(data);
  loadProjects();
  updatePreview('none');
}

async function uploadAudio() {
  if (!state.projectId) {
    uploadStatus.textContent = 'Create a project first.';
    return;
  }
  if (!audioFile.files.length) {
    uploadStatus.textContent = 'Select an audio file.';
    return;
  }
  const formData = new FormData();
  formData.append('audio', audioFile.files[0]);
  const response = await fetch(`/projects/${state.projectId}/upload`, {
    method: 'POST',
    body: formData,
  });
  const data = await response.json();
  uploadStatus.textContent = data.message;
  loadAudioPlayer(state.projectId);
}

async function runPipeline() {
  if (!state.projectId) {
    jobsStatus.textContent = 'Create a project first.';
    return;
  }
  updatePreview('none');
  const response = await fetch(`/projects/${state.projectId}/run`, { method: 'POST' });
  const data = await response.json();
  jobsStatus.textContent = data.message;
  startPolling();
}

async function renderVideo() {
  if (!state.projectId) {
    renderOutput.textContent = 'Create a project first.';
    return;
  }
  const response = await fetch(`/projects/${state.projectId}/render`, { method: 'POST' });
  const data = await response.json();
  renderOutput.textContent = data.message;
  startPolling();
}

function startPolling() {
  if (state.pollingInterval) return;
  state.pollingInterval = setInterval(refreshJobs, 3000);
}

function stopPolling() {
  if (state.pollingInterval) {
    clearInterval(state.pollingInterval);
    state.pollingInterval = null;
  }
}

async function refreshJobs() {
  if (!state.projectId) return;

  const response = await fetch(`/projects/${state.projectId}/jobs`);
  const data = await response.json();
  const jobs = data.jobs || {};

  // Pipeline Step & Progress
  const pipeJob = jobs.pipeline;
  if (pipeJob) {
    if (pipeJob.status === 'RUNNING' || pipeJob.status === 'RETRYING') {
      pipeContainer.style.display = 'block';
      const pct = pipeJob.progress || 0;
      pipePct.textContent = pct;
      pipeFill.style.width = `${pct}%`;
      pipeStep.textContent = `Step: ${pipeJob.step || '...'}`;
    } else if (pipeJob.status === 'DONE') {
      pipePct.textContent = '100';
      pipeFill.style.width = '100%';
      pipeStep.textContent = 'Complete';
      jobsStatus.textContent = 'Pipeline complete! Video is ready below.';
      setTimeout(() => {
        if (pipeJob.status === 'DONE') pipeContainer.style.display = 'none';
      }, 5000);
    } else if (pipeJob.status === 'FAILED') {
      pipeContainer.style.display = 'block';
      pipeStep.textContent = `Error: ${pipeJob.error || 'Pipeline failed'}`;
      pipeFill.style.background = '#ef4444';
    }
  }

  // Render Progress
  const renderJob = jobs.render;
  let videoReadyUrl = null;

  if (pipeJob && pipeJob.status === 'DONE' && pipeJob.output) {
    const parts = pipeJob.output.split(/[\\/]/);
    const filename = parts[parts.length - 1];
    videoReadyUrl = `/projects/${state.projectId}/renders/${filename}`;
    state.videoOutput = videoReadyUrl;
  }

  if (renderJob) {
    if (renderJob.status === 'RUNNING') {
      renderContainer.style.display = 'block';
      const pct = renderJob.progress || 0;
      renderPctValue.textContent = pct;
      renderFill.style.width = `${pct}%`;
      renderFill.style.background = 'linear-gradient(90deg, #6366f1 0%, #a855f7 100%)';
    } else if (renderJob.status === 'DONE') {
      renderPctValue.textContent = '100';
      renderFill.style.width = '100%';
      renderOutput.textContent = 'Render complete! Video is ready.';
      setTimeout(() => {
        if (renderJob.status === 'DONE') renderContainer.style.display = 'none';
      }, 5000);

      if (renderJob.output) {
        const parts = renderJob.output.split(/[\\/]/);
        const filename = parts[parts.length - 1];
        videoReadyUrl = `/projects/${state.projectId}/renders/${filename}`;
        state.videoOutput = videoReadyUrl;
      }
    } else if (renderJob.status === 'FAILED') {
      renderContainer.style.display = 'block';
      renderPctValue.textContent = 'Error';
      renderFill.style.width = '100%';
      renderFill.style.background = '#ef4444';
    }
  }

  // Fallback to project-level video output if no active render job providing one
  if (!videoReadyUrl && state.videoOutput) {
    videoReadyUrl = state.videoOutput;
  }

  const segments = await loadScenes();

  if (videoReadyUrl) {
    updatePreview('video', videoReadyUrl);
    // Hide audio player if video is ready to avoid confusion
    audioPlayer.style.display = 'none';
    audioPlayer.pause();
  } else if (segments && segments.length > 0) {
    const withImages = segments.filter(s => s.thumbnail);
    if (withImages.length > 0) {
      const last = withImages[withImages.length - 1];
      updatePreview('image', last.thumbnail);
    } else {
      updatePreview('none');
    }
  } else {
    updatePreview('none');
  }

  const anyRunning = Object.values(jobs).some((j) => j.status === 'RUNNING' || j.status === 'RETRYING');
  if (anyRunning) {
    startPolling();
  } else {
    stopPolling();
  }

  jobsStatus.textContent = JSON.stringify(data, null, 2);

  // Also refresh analysis if complete
  if (pipeJob && pipeJob.status === 'DONE') {
    loadAnalysis();
  }
}

async function loadAnalysis() {
  if (!state.projectId) {
    console.warn('loadAnalysis called without projectId');
    return;
  }

  try {
    const response = await fetch(`/projects/${state.projectId}/analysis?t=${Date.now()}`);
    if (!response.ok) {
      analysisContent.innerHTML = '<p class="muted">Analysis not available yet (start generation first).</p>';
      return;
    }
    const data = await response.json();

    if (!data || Object.keys(data).length === 0) {
      analysisContent.innerHTML = '<p class="muted">Analysis file is empty.</p>';
      return;
    }

    let html = '<div class="analysis-dump">';

    // Global Fields
    const globals = [
      { key: 'summary', label: 'Summary' },
      { key: 'global_visual_narrative', label: 'Narrative' },
      { key: 'visual_style_anchor', label: 'Visual Style' },
      { key: 'total_duration', label: 'Duration' }
    ];

    let hasGlobals = false;
    globals.forEach(item => {
      if (data[item.key]) {
        hasGlobals = true;
        html += `<div style="margin-bottom: 16px; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">
                <strong style="color: #4f46e5; text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.05em;">${item.label}</strong>
                <div style="margin-top: 6px; font-size: 0.9rem; color: #334155;">${data[item.key]}</div>
            </div>`;
      }
    });

    // Technical Stats
    if (data.technical_stats) {
      hasGlobals = true;
      html += `<div style="margin-bottom: 16px; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">
            <strong style="color: #4f46e5; text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.05em;">Technical Stats</strong>
            <div style="font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.75rem; margin-top: 8px; background: #f1f5f9; padding: 8px; border-radius: 6px;">
                BPM: <span style="color: #059669; font-weight: 600;">${data.technical_stats.bpm ? Math.round(data.technical_stats.bpm) : 'N/A'}</span><br>
                Beats: ${data.technical_stats.beat_times ? data.technical_stats.beat_times.length : 0}<br>
                Energy: ${data.technical_stats.energy_stats ? data.technical_stats.energy_stats.avg.toFixed(4) : 'N/A'}
            </div>
        </div>`;
    }

    // Segments Table
    if (data.segments && data.segments.length > 0) {
      hasGlobals = true;
      html += `<strong style="color: #4f46e5; text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.05em; display: block; margin-bottom: 8px;">LLM Segments</strong>`;
      html += `<div style="overflow-x: auto;"><table style="width: 100%; border-collapse: collapse; font-size: 0.7rem;">
            <thead>
                <tr style="text-align: left; background: #f8fafc; border-bottom: 2px solid #e2e8f0;">
                    <th style="padding: 8px 4px; border: 1px solid #e2e8f0;">Time</th>
                    <th style="padding: 8px 4px; border: 1px solid #e2e8f0;">Section</th>
                    <th style="padding: 8px 4px; border: 1px solid #e2e8f0;">Text / Lyrics</th>
                </tr>
            </thead>
            <tbody>`;

      data.segments.forEach(seg => {
        html += `<tr style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 6px 4px; border: 1px solid #e2e8f0; white-space: nowrap; font-weight: 500;">${seg.start_time}-${seg.end_time}</td>
                <td style="padding: 6px 4px; border: 1px solid #e2e8f0; color: #6366f1;">${seg.section_type || ''}</td>
                <td style="padding: 6px 4px; border: 1px solid #e2e8f0;">${seg.text || seg.lyric_text || ''}</td>
            </tr>`;
      });
      html += `</tbody></table></div>`;
    }

    // Fallback if no specific keys found but data exists
    if (!hasGlobals) {
      html += `<strong style="color: #4f46e5; text-transform: uppercase; font-size: 0.7rem;">Raw Analysis</strong>
                 <pre style="font-size: 0.7rem; background: #f1f5f9; padding: 10px; border-radius: 6px; overflow: auto;">${JSON.stringify(data, null, 2)}</pre>`;
    }

    html += '</div>';
    analysisContent.innerHTML = html;
  } catch (e) {
    console.error('Failed to load analysis', e);
    analysisContent.innerHTML = `<p class="error">Failed to load analysis: ${e.message}</p>`;
  }
}

async function loadScenes() {
  if (!state.projectId) return [];

  const response = await fetch(`/projects/${state.projectId}/segments`);
  if (!response.ok) {
    scenesContainer.innerHTML = '<p class="muted">Scenes not ready yet.</p>';
    timelineMarkers.innerHTML = '';
    return [];
  }
  const data = await response.json();
  const segments = data.segments || [];

  scenesContainer.innerHTML = '';
  timelineMarkers.innerHTML = '';

  // Get total duration from any source (audio or video or last segment)
  let totalDuration = audioPlayer.duration || previewVideo.duration || 0;
  if (!totalDuration && segments.length > 0) {
    totalDuration = parseTimeToSeconds(segments[segments.length - 1].end_time);
  }

  segments.forEach((segment) => {
    // Scene Card
    const card = document.createElement('div');
    card.className = 'scene-card';
    card.style.cursor = 'pointer';
    card.innerHTML = `
      <img src="${segment.thumbnail}" alt="${segment.id}" loading="lazy" />
      <div class="scene-details">
        <h3>${segment.id} (${segment.start_time} - ${segment.end_time})</h3>
        <p class="lyric">${segment.lyric_text || segment.text || ''}</p>
        <p class="intent muted">${segment.visual_intent || segment.visual_description || ''}</p>
        <button class="regenerate-btn">Regenerate</button>
      </div>
    `;

    card.onclick = (e) => {
      if (e.target.tagName === 'BUTTON') return;
      jumpToTime(parseTimeToSeconds(segment.start_time));
    };

    const button = card.querySelector('.regenerate-btn');
    button.onclick = async (e) => {
      e.stopPropagation();
      button.disabled = true;
      button.textContent = '...';
      try {
        await fetch(`/projects/${state.projectId}/segments/${segment.id}/regenerate`, { method: 'POST' });
        startPolling();
      } catch (e) {
        console.error(e);
      } finally {
        await refreshJobs();
      }
    };
    scenesContainer.appendChild(card);

    // Timeline Marker (Point)
    if (totalDuration > 0) {
      const start = parseTimeToSeconds(segment.start_time);
      const pct = (start / totalDuration) * 100;
      const marker = document.createElement('div');
      marker.className = 'playback-point';
      marker.style.left = `${pct}%`;
      marker.title = `${segment.id}: ${segment.start_time}`;
      timelineMarkers.appendChild(marker);
    }
  });

  return segments;
}

function parseTimeToSeconds(t) {
  if (typeof t === 'number') return t;
  if (!t) return 0;
  const parts = t.split(':').map(parseFloat);
  if (parts.length === 1) return parts[0];
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  return 0;
}

function jumpToTime(time) {
  if (audioPlayer.style.display !== 'none') {
    audioPlayer.currentTime = time;
    audioPlayer.play();
  }
  if (previewVideo.style.display !== 'none') {
    previewVideo.currentTime = time;
    previewVideo.play();
  }
}

// Sync timeline progress with active player
function updateTimelineProgress() {
  const activePlayer = previewVideo.style.display !== 'none' ? previewVideo : audioPlayer;
  if (activePlayer && activePlayer.duration) {
    const pct = (activePlayer.currentTime / activePlayer.duration) * 100;
    timelineProgress.style.width = `${pct}%`;
  }
  requestAnimationFrame(updateTimelineProgress);
}

// Allow clicking timeline to seek
timelineWrapper.onclick = (e) => {
  const rect = timelineWrapper.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const pct = x / rect.width;
  const activePlayer = previewVideo.style.display !== 'none' ? previewVideo : audioPlayer;
  if (activePlayer && activePlayer.duration) {
    activePlayer.currentTime = pct * activePlayer.duration;
    activePlayer.play();
  }
};

// Event Listeners
createButton.addEventListener('click', createProject);
openButton.addEventListener('click', openProject);
uploadButton.addEventListener('click', uploadAudio);
runButton.addEventListener('click', runPipeline);
refreshButton.addEventListener('click', refreshJobs);
renderButton.addEventListener('click', renderVideo);
refreshAnalysisButton.addEventListener('click', loadAnalysis);

// Initialize
loadProjects();
updateTimelineProgress();
