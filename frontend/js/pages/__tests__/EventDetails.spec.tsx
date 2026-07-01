import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { toDataURL } from 'qrcode';
import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router';

import { getEventDetails, getMyRsvp, issueEventPublicInviteLink, listEventAlbums, listEventParticipants } from '@/js/api';
import EventDetails from '@/js/pages/EventDetails';

jest.mock('@/js/api', () => ({
  getEventDetails: jest.fn(),
  getMyRsvp: jest.fn(),
  issueEventPublicInviteLink: jest.fn(),
  listEventAlbums: jest.fn(),
  listEventParticipants: jest.fn(),
  authLogout: jest.fn(),
}));

jest.mock('@/js/context/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 1,
      email: 'owner@example.com',
      display_name: 'Owner',
    },
    isAuthenticated: true,
    isLoading: false,
    refetch: jest.fn(),
  }),
}));

jest.mock('qrcode', () => ({
  toDataURL: jest.fn().mockResolvedValue('data:image/png;base64,test-qr'),
}));

describe('EventDetails', () => {
  beforeEach(() => {
    (getEventDetails as jest.Mock).mockResolvedValue({
      data: {
        address: '',
        all_day: false,
        attending_count: 1,
        created_at: '2026-03-01T10:00:00Z',
        date: '2026-03-20',
        description: 'Description',
        event_name: 'Launch Party',
        event_uuid: '2f8f4c13-c8e9-4d8a-bb9f-2c93007f0ad0',
        is_public: true,
        location: 'Kyiv',
        maybe_count: 0,
        not_attending_count: 0,
        owner_id: 1,
        owner_email: 'owner@example.com',
        owner_name: 'Owner',
        pending_count: 0,
        time: '18:00:00',
        total_participants: 1,
        updated_at: '2026-03-01T10:00:00Z',
      },
    });

    (getMyRsvp as jest.Mock).mockRejectedValue({ response: { status: 404 } });

    (listEventAlbums as jest.Mock).mockResolvedValue({ data: [] });

    (listEventParticipants as jest.Mock).mockResolvedValue({
      data: { participants: [], count: 0 },
    });

    (issueEventPublicInviteLink as jest.Mock).mockResolvedValue({
      data: {
        invite_url: 'https://frontend.example.com/join?token=signed-token-value',
      },
    });

    Object.assign(navigator, {
      clipboard: {
        writeText: jest.fn().mockResolvedValue(undefined),
      },
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test('loads event details and generates qr from backend invite link', async () => {
    render(
      <MemoryRouter initialEntries={['/events/2f8f4c13-c8e9-4d8a-bb9f-2c93007f0ad0']}>
        <Routes>
          <Route path="/events/:eventUuid" element={<EventDetails />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText('Launch Party')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Generate Invite QR' }));

    await waitFor(() => {
      expect(issueEventPublicInviteLink).toHaveBeenCalledWith('2f8f4c13-c8e9-4d8a-bb9f-2c93007f0ad0', {
        max_uses: 10_000,
        ttl_hours: 24,
      });
    });
    expect(toDataURL).toHaveBeenCalledWith('https://frontend.example.com/join?token=signed-token-value', {
      errorCorrectionLevel: 'M',
      margin: 1,
      width: 320,
    });
    expect(await screen.findByAltText('Event invitation QR code')).toBeInTheDocument();
  });

  test('supports nested event payload shape', async () => {
    (getEventDetails as jest.Mock).mockResolvedValue({
      data: {
        event: {
          address: '',
          all_day: false,
          attending_count: 1,
          created_at: '2026-03-01T10:00:00Z',
          date: '2026-03-20',
          description: 'Description',
          event_name: 'Nested Event',
          event_uuid: '2f8f4c13-c8e9-4d8a-bb9f-2c93007f0ad0',
          is_public: true,
          location: 'Kyiv',
          maybe_count: 0,
          not_attending_count: 0,
          owner_id: 1,
          owner_email: 'owner@example.com',
          owner_name: 'Owner',
          pending_count: 0,
          time: '18:00:00',
          total_participants: 1,
          updated_at: '2026-03-01T10:00:00Z',
        },
      },
    });

    render(
      <MemoryRouter initialEntries={['/events/2f8f4c13-c8e9-4d8a-bb9f-2c93007f0ad0']}>
        <Routes>
          <Route path="/events/:eventUuid" element={<EventDetails />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText('Nested Event')).toBeInTheDocument();
  });
});
