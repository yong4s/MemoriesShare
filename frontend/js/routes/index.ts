import { createBrowserRouter } from 'react-router';

import AlbumDetail from '@/js/pages/AlbumDetail';
import AlbumList from '@/js/pages/AlbumList';
import CreateEvent from '@/js/pages/CreateEvent';
import EventDetails from '@/js/pages/EventDetails';
import Home from '@/js/pages/Home';
import JoinByInvite from '@/js/pages/JoinByInvite';
import Login from '@/js/pages/Login';
import MyEvents from '@/js/pages/MyEvents';
import Settings from '@/js/pages/Settings';
import { GuestRoute, ProtectedRoute } from '@/js/routes/guards';
import RootLayout from '@/js/routes/RootLayout';

const router = createBrowserRouter([
  {
    Component: RootLayout,
    children: [
      { index: true, Component: Home },
      {
        Component: GuestRoute,
        children: [{ path: 'login', Component: Login }],
      },
      {
        Component: ProtectedRoute,
        children: [
          { path: 'events', Component: MyEvents },
          { path: 'events/new', Component: CreateEvent },
          { path: 'events/:eventUuid', Component: EventDetails },
          { path: 'events/:eventUuid/albums', Component: AlbumList },
          { path: 'events/:eventUuid/albums/:albumUuid', Component: AlbumDetail },
          { path: 'join', Component: JoinByInvite },
          { path: 'settings', Component: Settings },
        ],
      },
    ],
  },
]);

export default router;
