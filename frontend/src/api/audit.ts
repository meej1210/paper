import http from "./axios";

export type AuditLogParams = {
  page?: number;
  page_size?: number;
  keyword?: string;
  action?: string;
  result?: string;
  resource_id?: string;
  start_time?: string;
  end_time?: string;
};

export async function listAuditLogs(params?: AuditLogParams) {
  const { data } = await http.get("/audit-logs", { params });
  return data;
}
