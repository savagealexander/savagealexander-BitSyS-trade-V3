import axios from 'axios';
import { API_BASE_URL, API_TOKEN } from './config';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    Authorization: `Bearer ${API_TOKEN}`
  }
});

export async function getStatus() {
  const res = await client.get('/status');
  return res.data;
}

export async function setLeader(leader: string) {
  const res = await client.put('/leader', { leader });
  return res.data;
}

export async function startCopy() {
  const res = await client.post('/copy/start');
  return res.data;
}

export async function stopCopy() {
  const res = await client.post('/copy/stop');
  return res.data;
}

// ---------------------------------------------------------------------------
// Follower account management
// ---------------------------------------------------------------------------

export interface FollowerAccountPayload {
  name: string;
  exchange: string;
  env: string;
  api_key: string;
  api_secret: string;
  passphrase?: string;
}

export interface CredentialsPayload {
  exchange: string;
  env: string;
  api_key: string;
  api_secret: string;
  passphrase?: string;
}

export async function listAccounts() {
  const res = await client.get('/accounts');
  return res.data;
}

export async function createFollowerAccount(payload: FollowerAccountPayload) {
  const res = await client.post('/follower-accounts', payload);
  return res.data;
}

export async function deleteFollowerAccount(name: string) {
  const res = await client.delete(`/follower-accounts/${encodeURIComponent(name)}`);
  return res.data;
}

export async function verifyFollowerAccount(payload: CredentialsPayload) {
  const res = await client.post('/follower-accounts/verify', payload);
  return res.data;
}

export async function getBalance(account: string) {
  const res = await client.get(`/balances/${encodeURIComponent(account)}`);
  return res.data;
}
