import { CalendarPlus, Camera, LogOut, Menu, PartyPopper, Settings, X } from 'lucide-react';
import React, { useState } from 'react';
import { NavLink } from 'react-router';

import { authLogout } from '@/js/api';
import ThemeToggle from '@/js/components/ui/ThemeToggle';
import { useAuth } from '@/js/context/AuthContext';
import { clearAuthTokens, getRefreshToken } from '@/js/utils';

const navLinkClass = ({ isActive }: { isActive: boolean }): string =>
  [
    'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150',
    'hover:text-ink hover:bg-surface-2',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 focus-visible:ring-offset-surface',
    isActive ? 'text-ink bg-surface-2 shadow-soft-sm' : 'text-ink-muted',
  ].join(' ');

const TopNav = () => {
  const { user, isAuthenticated } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const onLogout = async () => {
    const refreshToken = getRefreshToken();
    try {
      if (refreshToken) await authLogout(refreshToken);
    } catch {
      // Backend logout can fail for expired/invalid refresh token.
    } finally {
      clearAuthTokens();
      window.location.href = '/login';
    }
  };

  const userInitial = (user?.display_name || user?.email || '?')[0].toUpperCase();

  return (
    <header className="sticky top-0 z-50 px-4">
      <nav
        aria-label="Primary"
        className="glass-strong mx-auto mt-4 mb-6 max-w-6xl rounded-2xl shadow-soft-md"
      >
        <div className="flex items-center justify-between px-4 py-2.5">
          <div className="flex items-center gap-4">
            <NavLink className="group flex items-center gap-2 font-semibold tracking-tight text-ink" to="/">
              <span className="relative inline-flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-brand-400 via-blush-300 to-peach-300 shadow-soft-sm transition-transform duration-300 group-hover:rotate-6 group-hover:scale-105">
                <Camera className="h-4 w-4 text-white" strokeWidth={2.2} />
              </span>
              <span className="bg-gradient-to-r from-brand-600 via-brand-500 to-blush-500 bg-clip-text text-transparent">
                Media Flow
              </span>
            </NavLink>

            {isAuthenticated && (
              <div className="hidden items-center gap-1 sm:flex">
                <NavLink className={navLinkClass} to="/events">
                  <PartyPopper className="h-4 w-4" />
                  My Events
                </NavLink>
                <NavLink className={navLinkClass} to="/events/new">
                  <CalendarPlus className="h-4 w-4" />
                  Create
                </NavLink>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            <ThemeToggle />

            {isAuthenticated ? (
              <>
                <div className="hidden items-center gap-3 sm:flex">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-brand-400 to-blush-300 text-sm font-semibold text-white shadow-soft-sm">
                    {userInitial}
                  </div>
                  <span className="max-w-[10rem] truncate text-sm text-ink-muted">
                    {user?.display_name || user?.email}
                  </span>
                  <NavLink className={navLinkClass} to="/settings">
                    <Settings className="h-4 w-4" />
                    Settings
                  </NavLink>
                  <button
                    className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-ink-muted transition-all duration-150 hover:bg-blush-100 hover:text-blush-700"
                    type="button"
                    onClick={onLogout}
                  >
                    <LogOut className="h-4 w-4" />
                    Logout
                  </button>
                </div>
                <button
                  aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
                  className="rounded-lg p-2 text-ink-muted transition hover:bg-surface-2 hover:text-ink sm:hidden"
                  type="button"
                  onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                >
                  {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
                </button>
              </>
            ) : (
              <NavLink className={navLinkClass} to="/login">
                Login
              </NavLink>
            )}
          </div>
        </div>

        {mobileMenuOpen && isAuthenticated && (
          <div className="animate-fade-in border-t border-border-subtle px-4 pb-3 pt-2 sm:hidden">
            <div className="mb-2 flex items-center gap-3 border-b border-border-subtle pb-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-brand-400 to-blush-300 text-sm font-semibold text-white shadow-soft-sm">
                {userInitial}
              </div>
              <span className="truncate text-sm text-ink">{user?.display_name || user?.email}</span>
            </div>
            <NavLink
              className={navLinkClass}
              to="/events"
              onClick={() => setMobileMenuOpen(false)}
            >
              <PartyPopper className="h-4 w-4" />
              My Events
            </NavLink>
            <NavLink
              className={navLinkClass}
              to="/events/new"
              onClick={() => setMobileMenuOpen(false)}
            >
              <CalendarPlus className="h-4 w-4" />
              Create Event
            </NavLink>
            <NavLink
              className={navLinkClass}
              to="/settings"
              onClick={() => setMobileMenuOpen(false)}
            >
              <Settings className="h-4 w-4" />
              Settings
            </NavLink>
            <button
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-ink-muted transition hover:bg-blush-100 hover:text-blush-700"
              type="button"
              onClick={onLogout}
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        )}
      </nav>
    </header>
  );
};

export default TopNav;
