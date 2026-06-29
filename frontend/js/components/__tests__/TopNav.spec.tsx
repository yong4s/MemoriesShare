import { render, screen } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router';

import TopNav from '@/js/components/TopNav';

jest.mock('@/js/api', () => ({
  authLogout: jest.fn(),
}));

jest.mock('@/js/context/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, email: 'test@test.com', display_name: 'Test User' },
    isAuthenticated: true,
    isLoading: false,
    refetch: jest.fn(),
  }),
}));

describe('TopNav', () => {
  test('renders brand and navigation links when authenticated', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <TopNav />
      </MemoryRouter>,
    );

    expect(screen.getByText('Media Flow')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'My Events' })).toHaveAttribute('href', '/events');
    expect(screen.getByRole('link', { name: 'Create Event' })).toHaveAttribute('href', '/events/new');
    expect(screen.getByText('Test User')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Login' })).not.toBeInTheDocument();
  });
});
