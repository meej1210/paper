type ApiErrorLike = {
  config?: {
    url?: string;
    headers?: {
      Authorization?: string;
      authorization?: string;
    };
  };
  response?: {
    status?: number;
    data?: {
      msg?: string;
      message?: string;
    };
  };
};

export function shouldRedirectToLogin(error: ApiErrorLike) {
  const status = error.response?.status;
  if (status === 401) return true;
  if (status !== 422) return false;

  const message = `${error.response?.data?.msg ?? ""} ${error.response?.data?.message ?? ""}`.toLowerCase();
  if ([
    "subject must be a string",
    "signature verification failed",
    "token has expired",
    "invalid token",
    "not enough segments",
    "bad authorization header",
    "missing authorization header",
  ].some((text) => message.includes(text))) {
    return true;
  }

  const hasAuthHeader = Boolean(error.config?.headers?.Authorization || error.config?.headers?.authorization);
  const path = normalizePath(error.config?.url ?? "");
  return hasAuthHeader && (path === "/auth/me" || path === "/tasks" || path.startsWith("/metrics/"));
}

function normalizePath(url: string) {
  try {
    const path = new URL(url, "http://localhost").pathname;
    return path.startsWith("/api/") ? path.slice(4) : path;
  } catch {
    const path = url.split("?")[0];
    return path.startsWith("/api/") ? path.slice(4) : path;
  }
}
