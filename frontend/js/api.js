/** API 请求封装：统一处理认证、错误、JSON 解析。 */

const API_BASE = 'http://localhost:8000/api';

function getToken() {
    return localStorage.getItem('access_token');
}

async function request(method, path, body = null, options = {}) {
    const url = API_BASE + path;
    const headers = {};

    const token = getToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    if (body && !(body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
    }

    const config = { method, headers, ...options };
    if (body) {
        config.body = body instanceof FormData ? body : JSON.stringify(body);
    }

    const response = await fetch(url, config);

    // 204 No Content
    if (response.status === 204) {
        return null;
    }

    const data = await response.json();

    if (!response.ok) {
        const detail = data.detail || '请求失败';
        if (response.status === 401) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
            if (window.location.pathname !== '/login.html' && window.location.pathname !== '/register.html') {
                window.location.href = '/login.html';
            }
        }
        throw new Error(detail);
    }

    return data;
}

const api = {
    get: (path, opts) => request('GET', path, null, opts),
    post: (path, body, opts) => request('POST', path, body, opts),
    delete: (path, opts) => request('DELETE', path, null, opts),
};
