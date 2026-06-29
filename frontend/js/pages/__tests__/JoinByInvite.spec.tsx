import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router';

import { joinEventByPublicInviteToken } from '@/js/api';
import JoinByInvite from '@/js/pages/JoinByInvite';

jest.mock('@/js/api', () => ({
  joinEventByPublicInviteToken: jest.fn(),
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

describe('JoinByInvite', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  test('auto-joins event when token is present', async () => {
    (joinEventByPublicInviteToken as jest.Mock).mockResolvedValue({
      data: {
        already_joined: false,
        event_name: 'Launch Party',
        event_uuid: '2f8f4c13-c8e9-4d8a-bb9f-2c93007f0ad0',
        participant_id: 42,
        participant_name: 'John Doe',
      },
    });

    render(
      <MemoryRouter initialEntries={['/join?token=signed-token-value']}>
        <Routes>
          <Route path="/join" element={<JoinByInvite />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(joinEventByPublicInviteToken).toHaveBeenCalledWith('signed-token-value');
    });

    expect(await screen.findByText('You have joined the event.')).toBeInTheDocument();
    expect(screen.getByText(/Launch Party/)).toBeInTheDocument();
    expect(screen.getByText(/John Doe/)).toBeInTheDocument();
  });

  test('shows validation error if token is missing', async () => {
    render(
      <MemoryRouter initialEntries={['/join']}>
        <Routes>
          <Route path="/join" element={<JoinByInvite />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText('Invite token is missing in URL query.')).toBeInTheDocument();
    expect(joinEventByPublicInviteToken).not.toHaveBeenCalled();
  });
});
