import * as Sentry from '@sentry/react';
import axios, { AxiosError, AxiosHeaders, InternalAxiosRequestConfig } from 'axios';
import { parse as cookieParse } from 'cookie';
import { RouterProvider } from 'react-router';

import { client } from '@/js/api/client.gen';
import router from '@/js/routes';
import { clearAuthTokens, getAccessToken, getRefreshToken, setAuthTokens } from '@/js/utils';

type RetryableRequestConfig = InternalAxiosRequestConfig & { _retry?: boolean };
type RefreshTokenResponse = { access: string; refresh?: string };

const refreshClient = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 10000,
});

let refreshRequest: Promise<string | null> | null = null;

const redirectToLogin = () => {
  const next = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  const target = next.startsWith('/login') ? '/login' : `/login?next=${encodeURIComponent(next)}`;
  window.location.replace(target);
};

const forceLogout = () => {
  clearAuthTokens();
  redirectToLogin();
};

const requestNewAccessToken = async (refreshToken: string): Promise<string | null> => {
  try {
    const { data } = await refreshClient.post<RefreshTokenResponse>('/accounts/auth/refresh/', { refresh: refreshToken });
    const nextRefreshToken = data.refresh ?? refreshToken;
    setAuthTokens(data.access, nextRefreshToken);
    return data.access;
  } catch {
    return null;
  }
};

client.instance.interceptors.request.use((request) => {
  const { csrftoken } = cookieParse(document.cookie);
  const accessToken = getAccessToken();
  if (request.headers && csrftoken) {
    request.headers['X-CSRFTOKEN'] = csrftoken;
  }
  if (request.headers && accessToken) {
    request.headers.Authorization = `Bearer ${accessToken}`;
  }
  return request;
});

client.instance.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryableRequestConfig | undefined;
    const status = error.response?.status;

    if (status !== 401 || !originalRequest) {
      throw error;
    }

    const url = originalRequest.url ?? '';
    if (url.includes('/accounts/auth/refresh/')) {
      forceLogout();
      throw error;
    }

    if (originalRequest._retry) {
      forceLogout();
      throw error;
    }

    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      forceLogout();
      throw error;
    }

    originalRequest._retry = true;

    refreshRequest ??= requestNewAccessToken(refreshToken).finally(() => {
      refreshRequest = null;
    });

    const nextAccessToken = await refreshRequest;
    if (!nextAccessToken) {
      forceLogout();
      throw error;
    }

    if (originalRequest.headers) {
      originalRequest.headers.Authorization = `Bearer ${nextAccessToken}`;
    } else {
      originalRequest.headers = AxiosHeaders.from({ Authorization: `Bearer ${nextAccessToken}` });
    }

    return client.instance(originalRequest);
  },
);

const App = () => (
  <Sentry.ErrorBoundary fallback={<p>An error has occurred</p>}>
    <RouterProvider router={router} />
  </Sentry.ErrorBoundary>
);

export default App;
