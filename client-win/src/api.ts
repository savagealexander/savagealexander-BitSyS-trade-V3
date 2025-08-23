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
