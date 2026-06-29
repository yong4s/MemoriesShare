import { AxiosError } from 'axios';

export const extractBackendErrorMessage = (error: unknown, fallbackMessage: string): string => {
  if (!(error instanceof AxiosError)) {
    return fallbackMessage;
  }

  const payload = error.response?.data as
    | { detail?: string; message?: string }
    | Record<string, string[] | string>
    | undefined;

  if (!payload) {
    return fallbackMessage;
  }

  if ('message' in payload && typeof payload.message === 'string') {
    return payload.message;
  }
  if ('detail' in payload && typeof payload.detail === 'string') {
    return payload.detail;
  }

  const firstFieldError = Object.values(payload).find((value) => Array.isArray(value) || typeof value === 'string');
  if (Array.isArray(firstFieldError) && firstFieldError.length > 0) {
    return String(firstFieldError[0]);
  }
  if (typeof firstFieldError === 'string') {
    return firstFieldError;
  }

  return fallbackMessage;
};
