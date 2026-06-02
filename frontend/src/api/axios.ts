import axios from "axios";
import { clearToken, getAccessToken } from "../store/auth";
import { shouldRedirectToLogin } from "./authFailure";

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || "/api"
});

http.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (shouldRedirectToLogin(error)) {
      clearToken();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default http;
