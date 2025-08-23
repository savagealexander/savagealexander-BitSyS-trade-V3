import { getStatus, startCopy, stopCopy, setLeader } from './api';

const statusEl = document.getElementById('status')!;
const leaderInput = document.getElementById('leader') as HTMLInputElement;
const saveLeaderBtn = document.getElementById('saveLeader') as HTMLButtonElement;
const startBtn = document.getElementById('startBtn') as HTMLButtonElement;
const stopBtn = document.getElementById('stopBtn') as HTMLButtonElement;

async function refresh() {
  try {
    const data = await getStatus();
    statusEl.textContent = data.running ? 'Running' : 'Stopped';
    leaderInput.value = data.leader || '';
    startBtn.disabled = data.running;
    stopBtn.disabled = !data.running;
  } catch (e) {
    statusEl.textContent = 'Error';
  }
}

startBtn.addEventListener('click', async () => {
  await startCopy();
  refresh();
});

stopBtn.addEventListener('click', async () => {
  await stopCopy();
  refresh();
});

saveLeaderBtn.addEventListener('click', async () => {
  await setLeader(leaderInput.value);
  refresh();
});

refresh();
