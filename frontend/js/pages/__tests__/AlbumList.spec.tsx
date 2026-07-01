import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router';

import { listEventAlbums } from '@/js/api';
import AlbumList from '@/js/pages/AlbumList';

jest.mock('@/js/api', () => ({
  listEventAlbums: jest.fn(),
  createAlbum: jest.fn(),
}));

jest.mock('@/js/context/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, email: 'owner@test.com', display_name: 'Owner' },
    isAuthenticated: true,
    isLoading: false,
    refetch: jest.fn(),
  }),
}));

jest.mock('react-router', () => {
  const actual = jest.requireActual('react-router');
  return {
    ...actual,
    useParams: () => ({ eventUuid: 'test-event-uuid' }),
  };
});

const EVENT_UUID = 'test-event-uuid';

describe('AlbumList', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  test('renders album list', async () => {
    (listEventAlbums as jest.Mock).mockResolvedValueOnce({
      data: [
        {
          album_uuid: 'album-1',
          event_name: 'Test Event',
          name: 'Wedding Photos',
          description: 'Beautiful wedding moments',
          is_public: true,
          created_at: '2026-03-01T10:00:00Z',
          mediafiles_count: 5,
        },
        {
          album_uuid: 'album-2',
          event_name: 'Test Event',
          name: 'Reception',
          description: '',
          is_public: false,
          created_at: '2026-03-02T10:00:00Z',
          mediafiles_count: 0,
        },
      ],
    });

    render(
      <MemoryRouter initialEntries={[`/events/${EVENT_UUID}/albums`]}>
        <AlbumList />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Wedding Photos')).toBeInTheDocument();
    expect(screen.getByText('Reception')).toBeInTheDocument();
    expect(screen.getByText('5 files')).toBeInTheDocument();
    expect(screen.getByText('0 files')).toBeInTheDocument();
  });

  test('shows empty state when no albums', async () => {
    (listEventAlbums as jest.Mock).mockResolvedValueOnce({ data: [] });

    render(
      <MemoryRouter initialEntries={[`/events/${EVENT_UUID}/albums`]}>
        <AlbumList />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('No albums yet')).toBeInTheDocument();
    });
  });

  test('opens create album modal', async () => {
    (listEventAlbums as jest.Mock).mockResolvedValueOnce({ data: [] });

    render(
      <MemoryRouter initialEntries={[`/events/${EVENT_UUID}/albums`]}>
        <AlbumList />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('No albums yet')).toBeInTheDocument();
    });

    const createButtons = screen.getAllByText('Create Album');
    fireEvent.click(createButtons[0]);

    expect(screen.getByText('Album name')).toBeInTheDocument();
  });
});
