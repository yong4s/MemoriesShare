import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router';

import { listEvents } from '@/js/api';
import MyEvents from '@/js/pages/MyEvents';

jest.mock('@/js/api', () => ({
  listEvents: jest.fn(),
  authLogout: jest.fn(),
}));

jest.mock('@/js/context/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, email: 'owner@test.com', display_name: 'Owner' },
    isAuthenticated: true,
    isLoading: false,
    refetch: jest.fn(),
  }),
}));

describe('MyEvents', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  const emptyResponse = {
    data: {
      events: [],
      pagination: { has_next: false, has_previous: false, page: 1, page_size: 20, total_count: 0, total_pages: 0 },
    },
  };

  test('renders events from parallel API calls', async () => {
    (listEvents as jest.Mock)
      .mockResolvedValueOnce({
        data: {
          events: [
            {
              attending_count: 10,
              created_at: '2026-03-01T10:00:00Z',
              date: '2026-03-20',
              event_name: 'Launch Party',
              event_uuid: '2f8f4c13-c8e9-4d8a-bb9f-2c93007f0ad0',
              is_public: true,
              location: 'Kyiv',
              owner_name: 'Owner',
              time: '18:00:00',
              total_participants: 30,
            },
          ],
        },
      })
      .mockResolvedValueOnce({
        data: {
          events: [
            {
              attending_count: 10,
              created_at: '2026-03-01T10:00:00Z',
              date: '2026-03-20',
              event_name: 'Launch Party',
              event_uuid: '2f8f4c13-c8e9-4d8a-bb9f-2c93007f0ad0',
              is_public: true,
              location: 'Kyiv',
              owner_name: 'Owner',
              time: '18:00:00',
              total_participants: 30,
            },
          ],
        },
      });

    render(
      <MemoryRouter initialEntries={['/events']}>
        <MyEvents />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Launch Party')).toBeInTheDocument();
  });

  test('shows empty state when no events', async () => {
    (listEvents as jest.Mock).mockResolvedValue(emptyResponse);

    render(
      <MemoryRouter initialEntries={['/events']}>
        <MyEvents />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('No events found')).toBeInTheDocument();
    });
  });

  test('supports legacy results payload shape', async () => {
    (listEvents as jest.Mock)
      .mockResolvedValueOnce({
        data: {
          results: [
            {
              attending_count: 2,
              created_at: '2026-03-01T10:00:00Z',
              date: '2026-03-20',
              event_name: 'Legacy Event',
              event_uuid: '3f8f4c13-c8e9-4d8a-bb9f-2c93007f0ad1',
              is_public: true,
              location: 'Lviv',
              owner_name: 'Owner',
              time: '18:00:00',
              total_participants: 3,
            },
          ],
        },
      })
      .mockResolvedValueOnce(emptyResponse);

    render(
      <MemoryRouter initialEntries={['/events']}>
        <MyEvents />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Legacy Event')).toBeInTheDocument();
  });
});
