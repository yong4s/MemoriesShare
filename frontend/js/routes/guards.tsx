import { Navigate, Outlet, useLocation } from 'react-router';

import { getAccessToken } from '@/js/utils';

const isAuthenticated = (): boolean => Boolean(getAccessToken());

export const GuestRoute = () => {
  if (isAuthenticated()) {
    return <Navigate replace to="/events" />;
  }

  return <Outlet />;
};

export const ProtectedRoute = () => {
  const location = useLocation();

  if (!isAuthenticated()) {
    const next = encodeURIComponent(`${location.pathname}${location.search}${location.hash}`);
    return <Navigate replace to={`/login?next=${next}`} />;
  }

  return <Outlet />;
};
