import { Navigate } from 'react-router';

import { getAccessToken } from '@/js/utils';

const Home = () => {
  if (getAccessToken()) {
    return <Navigate replace to="/events" />;
  }

  return <Navigate replace to="/login" />;
};

export default Home;
