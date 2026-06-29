import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router';

import { createEvent } from '@/js/api';
import CreateEvent from '@/js/pages/CreateEvent';

jest.mock('@/js/api', () => ({
  createEvent: jest.fn(),
  authLogout: jest.fn(),
}));

jest.mock('@/js/context/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, email: 'test@test.com', display_name: 'Test' },
    isAuthenticated: true,
    isLoading: false,
    refetch: jest.fn(),
  }),
}));

describe('CreateEvent', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  test('creates event and navigates to event details', async () => {
    (createEvent as jest.Mock).mockResolvedValue({
      data: {
        created_at: '2026-03-07T11:00:00Z',
        date: '2026-03-20',
        description: 'Team event',
        event_name: 'Corporate Team Building',
        event_uuid: 'cda85cdd-6d86-48e0-bd52-eff4232ecd41',
        is_public: false,
        location: 'Office',
        owner_name: 'Owner',
        time: '18:00:00',
      },
    });

    render(
      <MemoryRouter initialEntries={['/events/new']}>
        <Routes>
          <Route path="/events/new" element={<CreateEvent />} />
          <Route path="/events/:eventUuid" element={<div data-testid="event-details-page">Event details page</div>} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText('Event name'), { target: { value: 'Corporate Team Building' } });
    fireEvent.change(screen.getByLabelText('Date'), { target: { value: '2026-03-20' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create Event' }));

    await waitFor(() => {
      expect(createEvent).toHaveBeenCalledWith({
        address: '',
        all_day: false,
        date: '2026-03-20',
        description: '',
        event_name: 'Corporate Team Building',
        is_public: false,
        location: '',
        time: null,
      });
    });
    expect(await screen.findByTestId('event-details-page')).toBeInTheDocument();
  });
});
