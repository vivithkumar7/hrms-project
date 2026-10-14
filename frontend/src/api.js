import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  withCredentials: true,
});

let accessToken = null;
let refreshPromise;
let restorePromise;

for (const key of ['hrms_access_token', 'hrms_refresh_token', 'hrms_role']) {
  localStorage.removeItem(key);
}

export function setAccessToken(token) {
  accessToken = token;
}

function clearSession() {
  const hadSession = accessToken !== null;
  accessToken = null;
  if (hadSession) window.dispatchEvent(new Event('hrms:unauthorized'));
}

export function restoreSession() {
  if (!restorePromise) {
    restorePromise = axios
      .post(`${api.defaults.baseURL}/auth/refresh`, {}, { withCredentials: true })
      .then(({ data }) => {
        if (!data.access_token || !data.role) {
          throw new Error('Refresh response did not include valid session details');
        }
        accessToken = data.access_token;
        return data;
      })
      .catch((error) => {
        if (error.response?.status === 401) return null;
        throw error;
      })
      .finally(() => {
        restorePromise = undefined;
      });
  }
  return restorePromise;
}

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const request = error.config;
    const url = request?.url || '';
    if (
      error.response?.status !== 401
      || !request
      || url.endsWith('/auth/login')
      || url.endsWith('/auth/refresh')
      || url.endsWith('/auth/logout')
    ) {
      return Promise.reject(error);
    }
    if (request._retry) {
      clearSession();
      return Promise.reject(error);
    }

    request._retry = true;
    try {
      if (!refreshPromise) {
        refreshPromise = axios
          .post(`${api.defaults.baseURL}/auth/refresh`, {}, { withCredentials: true })
          .then(({ data }) => {
            if (!data.access_token) throw new Error('Refresh response did not include an access token');
            accessToken = data.access_token;
            return data.access_token;
          })
          .finally(() => {
            refreshPromise = undefined;
          });
      }
      const refreshedAccessToken = await refreshPromise;
      request.headers.Authorization = `Bearer ${refreshedAccessToken}`;
      return api(request);
    } catch (refreshError) {
      clearSession();
      return Promise.reject(refreshError);
    }
  },
);
