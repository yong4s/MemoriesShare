import { AxiosError } from 'axios';
import { redirectDocument } from 'react-router';

import { accountsAuthStatusRetrieve } from '@/js/api';

export async function usersLoader({ request }: { request: Request }) {
  try {
    const response = await accountsAuthStatusRetrieve();
    return response.data;
  } catch (error) {
    const status = error instanceof AxiosError ? error.response?.status : undefined;
    if (status === 401 || status === 403) {
      const url = new URL(request.url);
      const next = url.pathname + url.search + url.hash;
      throw redirectDocument(`/admin/login/?next=${encodeURIComponent(next)}`);
    }
    throw error;
  }
}
