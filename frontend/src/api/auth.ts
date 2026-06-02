import http from "./axios";

export async function register(payload: { username: string; email: string; password: string }) {
  const { data } = await http.post("/auth/register", payload);
  return data;
}

export async function login(payload: { username: string; password: string }) {
  const { data } = await http.post("/auth/login", payload);
  return data;
}

export async function getCurrentUser() {
  const { data } = await http.get("/auth/me");
  return data;
}

export async function listAuditLogs(params?: Record<string, string | number>) {
  const { data } = await http.get("/audit-logs", { params });
  return data;
}
