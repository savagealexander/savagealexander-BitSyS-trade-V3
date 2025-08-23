import {
  getStatus,
  startCopy,
  stopCopy,
  setLeader,
  listAccounts,
  createFollowerAccount,
  deleteFollowerAccount,
  verifyFollowerAccount,
  getBalance
} from './api';

const statusEl = document.getElementById('status')!;
const leaderInput = document.getElementById('leader') as HTMLInputElement;
const saveLeaderBtn = document.getElementById('saveLeader') as HTMLButtonElement;
const startBtn = document.getElementById('startBtn') as HTMLButtonElement;
const stopBtn = document.getElementById('stopBtn') as HTMLButtonElement;

const accountsList = document.getElementById('accountsList')!;
const accName = document.getElementById('accName') as HTMLInputElement;
const accExchange = document.getElementById('accExchange') as HTMLSelectElement;
const accEnv = document.getElementById('accEnv') as HTMLSelectElement;
const accApiKey = document.getElementById('accApiKey') as HTMLInputElement;
const accApiSecret = document.getElementById('accApiSecret') as HTMLInputElement;
const accPassphrase = document.getElementById('accPassphrase') as HTMLInputElement;
const passphraseContainer = document.getElementById('passphraseContainer')!;
const verifyAccBtn = document.getElementById('verifyAcc') as HTMLButtonElement;
const addAccBtn = document.getElementById('addAcc') as HTMLButtonElement;

accExchange.addEventListener('change', () => {
  passphraseContainer.style.display =
    accExchange.value === 'bitget' ? 'inline' : 'none';
});

function gatherCredentials(includeName = false) {
  const payload: any = {
    exchange: accExchange.value,
    env: accEnv.value,
    api_key: accApiKey.value.trim(),
    api_secret: accApiSecret.value.trim()
  };
  if (payload.exchange === 'bitget') {
    payload.passphrase = accPassphrase.value.trim();
  }
  if (includeName) {
    payload.name = accName.value.trim();
  }
  return payload;
}

function validatePayload(payload: any, requireName = false) {
  if (requireName && !payload.name) return false;
  if (!payload.exchange || !payload.env || !payload.api_key || !payload.api_secret)
    return false;
  if (payload.exchange === 'bitget' && !payload.passphrase) return false;
  return true;
}

async function loadAccounts() {
  try {
    const accounts = await listAccounts();
    accountsList.innerHTML = '';
    accounts.forEach((acc: any) => {
      const li = document.createElement('li');
      li.textContent = `${acc.name} (${acc.exchange}) `;

      const verifyBtn = document.createElement('button');
      verifyBtn.textContent = 'Verify';
      verifyBtn.addEventListener('click', async () => {
        const res = await verifyFollowerAccount({
          exchange: acc.exchange,
          env: acc.env,
          api_key: acc.api_key,
          api_secret: acc.api_secret,
          passphrase: acc.passphrase
        });
        alert(res.valid ? 'Valid' : `Invalid: ${res.error || ''}`);
      });

      const delBtn = document.createElement('button');
      delBtn.textContent = 'Delete';
      delBtn.addEventListener('click', async () => {
        if (confirm(`Delete ${acc.name}?`)) {
          await deleteFollowerAccount(acc.name);
          loadAccounts();
        }
      });

      li.appendChild(verifyBtn);
      li.appendChild(delBtn);
      accountsList.appendChild(li);
    });
  } catch (e) {
    accountsList.innerHTML = 'Error';
  }
}

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

verifyAccBtn.addEventListener('click', async () => {
  const payload = gatherCredentials();
  if (!validatePayload(payload)) {
    alert('Please fill in all required fields');
    return;
  }
  const res = await verifyFollowerAccount(payload);
  alert(res.valid ? 'Credentials valid' : `Invalid: ${res.error || ''}`);
});

addAccBtn.addEventListener('click', async () => {
  const payload = gatherCredentials(true);
  if (!validatePayload(payload, true)) {
    alert('Please fill in all required fields');
    return;
  }
  await createFollowerAccount(payload);
  const balance = await getBalance(payload.name);
  if (
    !balance ||
    Object.keys(balance).length === 0 ||
    Object.values(balance).every((v: any) => v === 0)
  ) {
    alert('Account added but balance not available yet. Please refresh later.');
  }
  loadAccounts();
});

refresh();
loadAccounts();
