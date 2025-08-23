import conf from './config.json';

export const API_BASE_URL = process.env.API_BASE_URL || conf.apiBaseUrl;
export const API_TOKEN = process.env.API_TOKEN || conf.token;
