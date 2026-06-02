import http from "./axios";

export async function listTasks(params?: Record<string, string | number>) {
  const { data } = await http.get("/tasks", { params });
  return data;
}

export async function getTaskSummary(params?: Record<string, string | number>) {
  const { data } = await http.get("/metrics/task-summary", { params });
  return data;
}

export async function getSastTask(taskId: number) {
  const { data } = await http.get(`/sast/tasks/${taskId}`);
  return data;
}

export async function getDastTask(taskId: number) {
  const { data } = await http.get(`/dast/tasks/${taskId}`);
  return data;
}

export async function getScaTask(taskId: number) {
  const { data } = await http.get(`/sca/tasks/${taskId}`);
  return data;
}

export async function createDastTask(payload: { target_url: string; task_name?: string; timeout?: number; description?: string; authorization_confirmed: boolean }) {
  const { data } = await http.post("/dast/tasks", payload);
  return data;
}

export async function createSastTask(formData: FormData) {
  const { data } = await http.post("/sast/tasks", formData, {
    headers: { "Content-Type": "multipart/form-data" }
  });
  return data;
}

export async function createScaTask(formData: FormData) {
  const { data } = await http.post("/sca/tasks", formData, {
    headers: { "Content-Type": "multipart/form-data" }
  });
  return data;
}

export async function cancelTask(taskId: number) {
  const { data } = await http.post(`/tasks/${taskId}/cancel`);
  return data;
}

export async function rerunTask(taskId: number) {
  const { data } = await http.post(`/tasks/${taskId}/rerun`);
  return data;
}

export async function downloadSastReport(taskId: number) {
  const response = await http.get(`/sast/tasks/${taskId}/report`, { responseType: "blob" });
  return response.data as Blob;
}

export async function downloadDastReport(taskId: number) {
  const response = await http.get(`/dast/tasks/${taskId}/report`, { responseType: "blob" });
  return response.data as Blob;
}

export async function downloadScaReport(taskId: number) {
  const response = await http.get(`/sca/tasks/${taskId}/report`, { responseType: "blob" });
  return response.data as Blob;
}
export async function generateIssueInsight(payload: { task_id: number; issue_id: number }) {
  const { data } = await http.post("/ai/issue-insight", payload);
  return data;
}

export async function exportSastReport(taskId: number, format: "html" | "pdf") {
  const response = await http.get(`/sast/tasks/${taskId}/export`, { params: { format }, responseType: "blob" });
  return response.data as Blob;
}

export async function exportDastReport(taskId: number, format: "html" | "pdf") {
  const response = await http.get(`/dast/tasks/${taskId}/export`, { params: { format }, responseType: "blob" });
  return response.data as Blob;
}

export async function exportScaReport(taskId: number, format: "html" | "pdf") {
  const response = await http.get(`/sca/tasks/${taskId}/export`, { params: { format }, responseType: "blob" });
  return response.data as Blob;
}
