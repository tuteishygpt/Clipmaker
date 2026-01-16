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

    // Set src if missing or Different
    const currentSrc = previewVideo.getAttribute('src');
    if (!currentSrc || !src.includes(currentSrc)) {
      previewVideo.src = src;
    }

    downloadVideo.style.display = 'inline-block';
    downloadVideo.href = src;
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
    audioPlayer.style.display = 'block';
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

    if (project.video_output) {
      updatePreview('video', project.video_output);
    }

    await refreshJobs();
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
      setTimeout(() => {
        if (renderJob.status === 'DONE') renderContainer.style.display = 'none';
      }, 5000);

      if (renderJob.output) {
        const parts = renderJob.output.split(/[\\/]/);
        const filename = parts[parts.length - 1];
        videoReadyUrl = `/projects/${state.projectId}/renders/${filename}`;
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

// Initialize
loadProjects();
updateTimelineProgress();
