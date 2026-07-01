import { KeyRound, Lock, Mail, ShieldCheck, UserCircle } from 'lucide-react';
import { FormEvent, useMemo, useState } from 'react';

import {
  changeAccountPassword,
  LoginMethod,
  setAccountPassword,
  updateProfile,
} from '@/js/api';
import { Alert, Button, Card, Input, PageHeader, PageLayout } from '@/js/components/ui';
import { useAuth } from '@/js/context/AuthContext';
import { extractBackendErrorMessage, setAuthTokens } from '@/js/utils';

const formatChangedAt = (iso: string | null): string => {
  if (!iso) return 'Never set';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return 'Unknown';
  const diffMs = Date.now() - then;
  const seconds = Math.round(diffMs / 1000);
  if (seconds < 60) return 'Just now';
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? '' : 's'} ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days} day${days === 1 ? '' : 's'} ago`;
  return new Date(iso).toLocaleDateString();
};

const Settings = () => {
  const { user, refetch, isLoading: authLoading } = useAuth();

  const hasPassword = Boolean(user?.has_password);
  const preferred: LoginMethod = user?.preferred_login_method ?? 'passwordless';
  const email = user?.email ?? '';
  const displayName = user?.display_name ?? '';

  const [preferenceError, setPreferenceError] = useState<string | null>(null);
  const [preferenceBusy, setPreferenceBusy] = useState(false);

  const [newPassword, setNewPassword] = useState('');
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('');
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);

  const [oldPassword, setOldPassword] = useState('');

  const lastChangedLabel = useMemo(
    () => formatChangedAt(user?.password_changed_at ?? null),
    [user?.password_changed_at],
  );

  const onChangePreference = async (next: LoginMethod) => {
    if (next === preferred || preferenceBusy) return;
    if (next === 'password' && !hasPassword) {
      setPreferenceError('Set a password first to use password sign-in.');
      return;
    }
    setPreferenceError(null);
    setPreferenceBusy(true);
    try {
      await updateProfile({ preferred_login_method: next });
      refetch();
    } catch (error) {
      setPreferenceError(extractBackendErrorMessage(error, 'Failed to update preference.'));
    } finally {
      setPreferenceBusy(false);
    }
  };

  const resetPasswordForm = () => {
    setOldPassword('');
    setNewPassword('');
    setNewPasswordConfirm('');
  };

  const onSubmitPassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(null);

    if (newPassword.length < 8) {
      setPasswordError('Password must be at least 8 characters long.');
      return;
    }
    if (newPassword !== newPasswordConfirm) {
      setPasswordError('Passwords do not match.');
      return;
    }

    setPasswordBusy(true);
    try {
      if (hasPassword) {
        await changeAccountPassword(oldPassword, newPassword, newPasswordConfirm);
        setPasswordSuccess('Password changed.');
      } else {
        const { data } = await setAccountPassword(newPassword, newPasswordConfirm);
        setAuthTokens(data.access, data.refresh);
        setPasswordSuccess('Password set. You can now sign in with either method.');
      }
      resetPasswordForm();
      refetch();
    } catch (error) {
      setPasswordError(extractBackendErrorMessage(error, 'Failed to update password.'));
    } finally {
      setPasswordBusy(false);
    }
  };

  if (authLoading) {
    return (
      <PageLayout maxWidth="md">
        <PageHeader title="Settings" />
        <Card>Loading…</Card>
      </PageLayout>
    );
  }

  return (
    <PageLayout maxWidth="md">
      <PageHeader title="Settings" subtitle="Manage how you sign in to Media Flow." />

      <div className="space-y-6">
        <Card padding="lg">
          <div className="mb-4 flex items-center gap-2 text-slate-800">
            <UserCircle className="h-5 w-5 text-brand-600" />
            <h2 className="text-lg font-semibold">Account</h2>
          </div>
          <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-zinc-500">Email</dt>
              <dd className="flex items-center gap-2 font-medium text-slate-900">
                <Mail className="h-4 w-4 text-zinc-400" />
                {email || '—'}
              </dd>
            </div>
            <div>
              <dt className="text-zinc-500">Display name</dt>
              <dd className="font-medium text-slate-900">{displayName || '—'}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Last password change</dt>
              <dd className="font-medium text-slate-900">{lastChangedLabel}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Has password</dt>
              <dd className="font-medium text-slate-900">{hasPassword ? 'Yes' : 'No'}</dd>
            </div>
          </dl>
        </Card>

        <Card padding="lg">
          <div className="mb-4 flex items-center gap-2 text-slate-800">
            <ShieldCheck className="h-5 w-5 text-brand-600" />
            <h2 className="text-lg font-semibold">Preferred sign-in method</h2>
          </div>
          <p className="mb-3 text-sm text-zinc-500">
            We remember your choice so your login screen shows the right form first.
          </p>
          <div className="flex flex-col gap-2 sm:flex-row">
            <button
              className={`flex-1 rounded-lg border px-4 py-3 text-left text-sm transition ${
                preferred === 'passwordless'
                  ? 'border-brand-500 bg-brand-50 text-brand-900'
                  : 'border-zinc-200 hover:border-zinc-300'
              }`}
              disabled={preferenceBusy}
              onClick={() => onChangePreference('passwordless')}
              type="button"
            >
              <div className="font-medium">Passwordless code</div>
              <div className="text-xs text-zinc-500">Get a 6-digit code by email each time.</div>
            </button>
            <button
              className={`flex-1 rounded-lg border px-4 py-3 text-left text-sm transition ${
                preferred === 'password'
                  ? 'border-brand-500 bg-brand-50 text-brand-900'
                  : 'border-zinc-200 hover:border-zinc-300'
              } ${!hasPassword ? 'cursor-not-allowed opacity-50' : ''}`}
              disabled={preferenceBusy || !hasPassword}
              onClick={() => onChangePreference('password')}
              title={!hasPassword ? 'Set a password first' : undefined}
              type="button"
            >
              <div className="font-medium">Password</div>
              <div className="text-xs text-zinc-500">
                {hasPassword ? 'Enter your password directly.' : 'Set a password below to enable.'}
              </div>
            </button>
          </div>
          {preferenceError && (
            <div className="mt-3">
              <Alert variant="error">{preferenceError}</Alert>
            </div>
          )}
        </Card>

        <Card padding="lg">
          <div className="mb-4 flex items-center gap-2 text-slate-800">
            <Lock className="h-5 w-5 text-brand-600" />
            <h2 className="text-lg font-semibold">{hasPassword ? 'Change password' : 'Set a password'}</h2>
          </div>
          <p className="mb-4 text-sm text-zinc-500">
            {hasPassword
              ? 'You can still sign in with a passwordless code after changing your password.'
              : 'Adding a password is optional — passwordless sign-in will keep working either way.'}
          </p>

          {passwordSuccess && (
            <div className="mb-3">
              <Alert variant="success">{passwordSuccess}</Alert>
            </div>
          )}
          {passwordError && (
            <div className="mb-3">
              <Alert variant="error">{passwordError}</Alert>
            </div>
          )}

          <form className="space-y-3" onSubmit={onSubmitPassword}>
            {hasPassword && (
              <Input
                autoComplete="current-password"
                icon={<Lock className="h-4 w-4" />}
                label="Current password"
                onChange={(e) => setOldPassword(e.target.value)}
                required
                type="password"
                value={oldPassword}
              />
            )}
            <Input
              autoComplete="new-password"
              icon={<KeyRound className="h-4 w-4" />}
              label={hasPassword ? 'New password' : 'Password'}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              type="password"
              value={newPassword}
            />
            <Input
              autoComplete="new-password"
              icon={<KeyRound className="h-4 w-4" />}
              label="Confirm password"
              onChange={(e) => setNewPasswordConfirm(e.target.value)}
              required
              type="password"
              value={newPasswordConfirm}
            />
            <Button
              disabled={passwordBusy || !newPassword || !newPasswordConfirm || (hasPassword && !oldPassword)}
              isLoading={passwordBusy}
              type="submit"
            >
              {hasPassword ? 'Change password' : 'Set password'}
            </Button>
          </form>
        </Card>
      </div>
    </PageLayout>
  );
};

export default Settings;
