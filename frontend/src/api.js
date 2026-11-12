import axios from "axios";

const configuredUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";
const api = axios.create({
  baseURL: configuredUrl.replace(/\/$/, ""),
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

let accessToken = null;
export const setToken = (token) => {
  accessToken = token || null;
};

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});

export default api;
