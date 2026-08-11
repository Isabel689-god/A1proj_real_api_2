/** JWT token 管理与 fetch 封装。 */

const TOKEN_KEY = 'a1proj_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * 带 JWT 鉴权的 fetch 封装。
 * 自动附加 Authorization header + 兼容旧的 X-Admin-Token。
 */
export async function authFetch(
  url: string,
  options: RequestInit = {},
): Promise<Response> {
  const token = getToken();
  const headers: Record<string, string> = {};

  // 复制已有 headers
  if (options.headers) {
    if (options.headers instanceof Headers) {
      options.headers.forEach((v, k) => { headers[k] = v; });
    } else if (Array.isArray(options.headers)) {
      options.headers.forEach(([k, v]) => { headers[k] = v; });
    } else {
      Object.assign(headers, options.headers);
    }
  }

  // 附加 JWT token
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // FormData 不设 Content-Type（浏览器自动带 boundary）
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  }

  return fetch(url, { ...options, headers });
}
