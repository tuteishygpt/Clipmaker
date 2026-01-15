const state = {
  projectId: null,
  pollingInterval: null,
};

const formatSelect = document.getElementById('format');
const styleSelect = document.getElementById('style');
const subtitlesToggle = document.getElementById('subtitles');
const createButton = document.getElementById('create-project');
const projectInfo = document.getElementById('project-info');
const audioFile = document.getElementById('audio-file');
const uploadButton = document.getElementById('upload-audio');
const uploadStatus = document.getElementById('upload-status');
const runButton = document.getElementById('run-pipeline');
const refreshButton = document.getElementById('refresh-jobs');
const jobsStatus = document.getElementById('jobs-status');
const scenesContainer = document.getElementById('scenes');
const renderButton = document.getElementById('render-project');
const renderOutput = document.getElementById('render-output');
const audioPlayer = document.getElementById('audio-player');


const projectList = document.getElementById('project-list');
const openButton = document.getElementById('open-project');

async function setProjectInfo(project) {
  state.projectId = project.id;
  projectInfo.textContent = `Project: ${project.id} (status: ${project.status})`;
}

async function loadAudioPlayer(projectId) {
  audioPlayer.style.display = 'none';
  audioPlayer.pause();
  audioPlayer.src = '';

  if (!projectId) return;

  const audioUrl = `/projects/${projectId}/audio?t=${Date.now()}`;

  // Try to load audio and show player only if successful
  audioPlayer.src = audioUrl;

  // We need to define these handlers before setting src usually, but here fine since it's async/DOM
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
      // Format date nicely if possible, for now just use raw string
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

  try {
    const response = await fetch(`/projects/${id}`);
    if (!response.ok) {
      alert('Failed to load project details');
      return;
    }
    const project = await response.json();
    setProjectInfo(project);
    loadAudioPlayer(project.id);

    // Update UI elements based on project settings if needed (e.g. set select values)
    if (project.format) formatSelect.value = project.format;
    if (project.style) styleSelect.value = project.style;
    if (project.subtitles !== undefined) subtitlesToggle.checked = project.subtitles;

    // Refresh data
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
    }),
  });
  const data = await response.json();
  setProjectInfo(data);
  loadProjects(); // Refresh list
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
  const response = await fetch(`/projects/${state.projectId}/run`, { method: 'POST' });
  const data = await response.json();
  jobsStatus.textContent = data.message;
  startPolling();
}

function startPolling() {
  if (state.pollingInterval) return;
  state.pollingInterval = setInterval(refreshJobs, 1000);
}

function stopPolling() {
  if (state.pollingInterval) {
    clearInterval(state.pollingInterval);
    state.pollingInterval = null;
  }
}

async function refreshJobs() {
  if (!state.projectId) {
    jobsStatus.textContent = 'Create a project first.';
    return;
  }
  const response = await fetch(`/projects/${state.projectId}/jobs`);
  const data = await response.json();
  const jobs = data.jobs || {};

  // Pipeline Step & Progress
  const pipeJob = jobs.pipeline;
  const pipeContainer = document.getElementById('pipeline-progress-container');
  if (pipeJob) {
    if (pipeJob.status === 'RUNNING' || pipeJob.status === 'RETRYING') {
      pipeContainer.style.display = 'block';
      const pct = pipeJob.progress || 0;
      document.getElementById('pipeline-progress-pct').textContent = pct;
      document.getElementById('pipeline-progress-fill').style.width = `${pct}%`;
      document.getElementById('pipeline-step').textContent = `Step: ${pipeJob.step || '...'}`;
    } else if (pipeJob.status === 'DONE') {
      document.getElementById('pipeline-progress-pct').textContent = '100';
      document.getElementById('pipeline-progress-fill').style.width = '100%';
      document.getElementById('pipeline-step').textContent = 'Complete';
      setTimeout(() => {
        if (pipeJob.status === 'DONE') pipeContainer.style.display = 'none';
      }, 5000);
    } else if (pipeJob.status === 'FAILED') {
      document.getElementById('pipeline-step').textContent = `Error: ${pipeJob.error || 'Pipeline failed'}`;
      document.getElementById('pipeline-progress-fill').style.background = '#ef4444';
    }
  }

  // Render Progress
  const renderJob = jobs.render;
  const renderContainer = document.getElementById('render-progress-container');
  if (renderJob) {
    if (renderJob.status === 'RUNNING') {
      renderContainer.style.display = 'block';
      const pct = renderJob.progress || 0;
      document.getElementById('render-progress-pct').textContent = pct;
      const fill = document.getElementById('render-progress-fill');
      fill.style.width = `${pct}%`;
      fill.style.background = 'linear-gradient(90deg, #6366f1 0%, #a855f7 100%)';
    } else if (renderJob.status === 'DONE') {
      document.getElementById('render-progress-pct').textContent = '100';
      document.getElementById('render-progress-fill').style.width = '100%';
      setTimeout(() => {
        if (renderJob.status === 'DONE') renderContainer.style.display = 'none';
      }, 5000);
    } else if (renderJob.status === 'FAILED') {
      renderContainer.style.display = 'block';
      document.getElementById('render-progress-pct').textContent = 'Error';
      const fill = document.getElementById('render-progress-fill');
      fill.style.width = '100%';
      fill.style.background = '#ef4444';
    }
  }

  const anyRunning = Object.values(jobs).some((j) => j.status === 'RUNNING' || j.status === 'RETRYING');
  if (anyRunning) {
    startPolling();
  } else {
    stopPolling();
  }

  jobsStatus.textContent = JSON.stringify(data, null, 2);
  await loadScenes();
}

async function loadScenes() {
  if (!state.projectId) {
    return;
  }
  const response = await fetch(`/projects/${state.projectId}/segments`);
  if (!response.ok) {
    scenesContainer.innerHTML = '<p class="muted">Scenes not ready yet.</p>';
    return;
  }
  const data = await response.json();
  scenesContainer.innerHTML = '';
  data.segments.forEach((segment) => {
    const card = document.createElement('div');
    card.className = 'scene-card';
    card.innerHTML = `
      <img src="${segment.thumbnail}" alt="${segment.id}" />
      <div class="scene-details">
        <h3>${segment.id}</h3>
        <p class="lyric">${segment.lyric_text || segment.text || ''}</p>
        <p class="intent muted">${segment.visual_intent || segment.visual_description || ''}</p>
        <button class="regenerate-btn" data-id="${segment.id}">Regenerate</button>
      </div>
    `;
    const button = card.querySelector('.regenerate-btn');
    button.addEventListener('click', async () => {
      button.disabled = true;
      button.textContent = 'Generating...';
      try {
        await fetch(`/projects/${state.projectId}/segments/${segment.id}/regenerate`, {
          method: 'POST',
        });
      } catch (e) {
        console.error('Failed to regenerate', e);
      } finally {
        await loadScenes();
      }
    });
    scenesContainer.appendChild(card);
  });
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

createButton.addEventListener('click', createProject);
openButton.addEventListener('click', openProject);
uploadButton.addEventListener('click', uploadAudio);
runButton.addEventListener('click', runPipeline);
refreshButton.addEventListener('click', refreshJobs);
renderButton.addEventListener('click', renderVideo);

// Initialize
loadProjects();
