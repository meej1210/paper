import http from "./axios";

export async function getAdminDashboard() {
  const { data } = await http.get("/admin/dashboard");
  return data;
}

export async function listAdminTasks(params?: Record<string, string | number>) {
  const { data } = await http.get("/admin/tasks", { params });
  return data;
}
