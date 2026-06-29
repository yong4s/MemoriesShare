import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router';

import Home from '@/js/pages/Home';

jest.mock('@/js/utils', () => ({
  ...jest.requireActual('@/js/utils'),
  getAccessToken: jest.fn(),
}));

import { getAccessToken } from '@/js/utils';

describe('Home', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  test('redirects to /events when authenticated', () => {
    (getAccessToken as jest.Mock).mockReturnValue('test-token');

    const { container } = render(
      <MemoryRouter initialEntries={['/']}>
        <Home />
      </MemoryRouter>,
    );

    expect(container.innerHTML).toBe('');
  });

  test('redirects to /login when not authenticated', () => {
    (getAccessToken as jest.Mock).mockReturnValue(null);

    const { container } = render(
      <MemoryRouter initialEntries={['/']}>
        <Home />
      </MemoryRouter>,
    );

    expect(container.innerHTML).toBe('');
  });
});
