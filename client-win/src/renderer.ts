import {
  getCopyStatus,
  startCopy,
  stopCopy,
  setLeader,
  listAccounts,
  createFollowerAccount,
  verifyFollowerAccount,
  getBalance,
  getCopyResults,
  updateAccountStatus
} from './api';

const statusEl = document.getElementById('status')!;
const saveLeaderBtn = document.getElementById('saveLeader') as HTMLButtonElement;
const leaderEnv = document.getElementById('leaderEnv') as HTMLSelectElement;
const leaderApiKey = document.getElementById('leaderApiKey') as HTMLInputElement;
const leaderApiSecret = document.getElementById('leaderApiSecret') as HTMLInputElement;
const startBtn = document.getElementById('startBtn') as HTMLButtonElement;
const stopBtn = document.getElementById('stopBtn') as HTMLButtonElement;

const accountsBody = document.getElementById('accountsTableBody')!;
const accName = document.getElementById('accName') as HTMLInputElement;
const accExchange = document.getElementById('accExchange') as HTMLSelectElement;
const accEnv = document.getElementById('accEnv') as HTMLSelectElement;
const accApiKey = document.getElementById('accApiKey') as HTMLInputElement;
const accApiSecret = document.getElementById('accApiSecret') as HTMLInputElement;
const accPassphrase = document.getElementById('accPassphrase') as HTMLInputElement;
const passphraseContainer = document.getElementById('passphraseContainer')!;
const verifyAccBtn = document.getElementById('verifyAcc') as HTMLButtonElement;
const addAccBtn = document.getElementById('addAcc') as HTMLButtonElement;

function updateSaveLeaderBtn() {
  saveLeaderBtn.disabled =
    !leaderEnv.value ||
    !leaderApiKey.value.trim() ||
    !leaderApiSecret.value.trim();
}

leaderEnv.addEventListener('change', updateSaveLeaderBtn);
leaderApiKey.addEventListener('input', updateSaveLeaderBtn);
leaderApiSecret.addEventListener('input', updateSaveLeaderBtn);

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

interface AccountRow {
  statusEl: HTMLElement;
  usdtEl: HTMLElement;
  btcEl: HTMLElement;
  resultEl: HTMLElement;
  errorEl: HTMLElement;
  actionBtn: HTMLButtonElement;
}

const accountRows: Record<string, AccountRow> = {};
let accounts: any[] = [];

async function loadAccounts() {
  try {
    accounts = await listAccounts();
    accountsBody.innerHTML = '';
    Object.keys(accountRows).forEach((k) => delete accountRows[k]);
    accounts.forEach((acc: any) => {
      const tr = document.createElement('tr');
      const nameTd = document.createElement('td');
      nameTd.textContent = acc.name;
      const exTd = document.createElement('td');
      exTd.textContent = acc.exchange;
      const envTd = document.createElement('td');
      envTd.textContent = acc.env;
      const statusTd = document.createElement('td');
      statusTd.textContent = acc.status;
      const usdtTd = document.createElement('td');
      usdtTd.textContent = '-';
      const btcTd = document.createElement('td');
      btcTd.textContent = '-';
      const resultTd = document.createElement('td');
      resultTd.textContent = '-';
      const errorTd = document.createElement('td');
      errorTd.textContent = '';
      const actionTd = document.createElement('td');
      const actionBtn = document.createElement('button');
      actionBtn.textContent =
        acc.status === 'active' ? 'Pause' : 'Resume';
      actionBtn.addEventListener('click', () => toggleAccount(acc.name));
      actionTd.appendChild(actionBtn);
      tr.append(
        nameTd,
        exTd,
        envTd,
        statusTd,
        usdtTd,
        btcTd,
        resultTd,
        errorTd,
        actionTd
      );
      accountsBody.appendChild(tr);
      accountRows[acc.name] = {
        statusEl: statusTd,
        usdtEl: usdtTd,
        btcEl: btcTd,
        resultEl: resultTd,
        errorEl: errorTd,
        actionBtn
      };
    });
  } catch (e) {
    accountsBody.innerHTML =
      '<tr><td colspan="9">Error loading accounts</td></tr>';
  }
}

async function toggleAccount(name: string) {
  const row = accountRows[name];
  const acc = accounts.find((a) => a.name === name);
  const target = acc.status === 'active' ? 'paused' : 'active';
  try {
    await updateAccountStatus(name, target);
    acc.status = target;
    row.statusEl.textContent = target;
    row.actionBtn.textContent = target === 'active' ? 'Pause' : 'Resume';
    row.errorEl.textContent = '';
  } catch (err: any) {
    const msg = err?.response?.data?.detail || err.message;
    row.errorEl.textContent = msg;
  }
}

async function refreshGlobal() {
  try {
    const data = await getCopyStatus();
    statusEl.textContent = data.running ? 'Running' : 'Stopped';
    leaderApiKey.value = data.leader || '';
    updateSaveLeaderBtn();
    startBtn.disabled = data.running;
    stopBtn.disabled = !data.running;
  } catch (e) {
    statusEl.textContent = 'Error';
  }
}

async function updateBalances() {
  await Promise.all(
    accounts.map(async (acc: any) => {
      try {
        const bal = await getBalance(acc.name);
        const row = accountRows[acc.name];
        row.usdtEl.textContent = (bal.USDT ?? 0).toFixed(2);
        row.btcEl.textContent = (bal.BTC ?? 0).toFixed(6);
      } catch (e) {
        const row = accountRows[acc.name];
        row.usdtEl.textContent = 'Err';
        row.btcEl.textContent = 'Err';
      }
    })
  );
}

async function updateResults() {
  try {
    const results = await getCopyResults();
    Object.keys(accountRows).forEach((name) => {
      const row = accountRows[name];
      const r = results[name];
      if (r) {
        row.resultEl.textContent = r.success ? 'Success' : 'Fail';
        row.errorEl.textContent = r.success ? '' : r.error || '';
      }
    });
  } catch (e) {
    // ignore
  }
}

setInterval(() => {
  updateBalances();
  updateResults();
}, 5000);

startBtn.addEventListener('click', async () => {
  await startCopy();
  refreshGlobal();
});

stopBtn.addEventListener('click', async () => {
  await stopCopy();
  refreshGlobal();
});

saveLeaderBtn.addEventListener('click', async () => {
  const cfg = {
    exchange: 'binance',
    env: leaderEnv.value,
    api_key: leaderApiKey.value.trim(),
    api_secret: leaderApiSecret.value.trim()
  };
  if (!cfg.env || !cfg.api_key || !cfg.api_secret) {
    alert('Please fill in all required fields');
    return;
  }
  await setLeader(cfg);
  leaderApiSecret.value = '';
  updateSaveLeaderBtn();
  refreshGlobal();
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
  await loadAccounts();
  updateBalances();
  updateResults();
});

refreshGlobal();
loadAccounts().then(() => {
  updateBalances();
  updateResults();
});
