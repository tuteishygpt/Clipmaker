const state = {
  projectId: null,
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

function setProjectInfo(project) {
  state.projectId = project.id;
  projectInfo.textContent = `Project: ${project.id} (status: ${project.status})`;
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
}

async function runPipeline() {
  if (!state.projectId) {
    jobsStatus.textContent = 'Create a project first.';
    return;
  }
  const response = await fetch(`/projects/${state.projectId}/run`, { method: 'POST' });
  const data = await response.json();
  jobsStatus.textContent = data.message;
}

async function refreshJobs() {
  if (!state.projectId) {
    jobsStatus.textContent = 'Create a project first.';
    return;
  }
  const response = await fetch(`/projects/${state.projectId}/jobs`);
  const data = await response.json();
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
      <div>
        <h3>${segment.id}</h3>
        <p>${segment.lyric_text}</p>
        <p class="muted">${segment.visual_intent}</p>
        <button data-id="${segment.id}">Regenerate</button>
      </div>
    `;
    const button = card.querySelector('button');
    button.addEventListener('click', async () => {
      await fetch(`/projects/${state.projectId}/segments/${segment.id}/regenerate`, {
        method: 'POST',
      });
      await loadScenes();
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
}

createButton.addEventListener('click', createProject);
uploadButton.addEventListener('click', uploadAudio);
runButton.addEventListener('click', runPipeline);
refreshButton.addEventListener('click', refreshJobs);
renderButton.addEventListener('click', renderVideo);
