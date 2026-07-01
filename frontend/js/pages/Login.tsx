import { AxiosError } from 'axios';
import { Camera, KeyRound, Lock, Mail } from 'lucide-react';
import { FormEvent, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';

import {
  getLoginMethods,
  LoginMethod,
  loginWithPassword,
  passwordlessRequest,
  passwordlessVerify,
} from '@/js/api';
import { Alert, Button, Card, Input } from '@/js/components/ui';
import { extractBackendErrorMessage, setAuthTokens } from '@/js/utils';

type Step = 'email' | 'password' | 'passwordless_request' | 'passwordless_verify';

const getSafeNextPath = (nextPath: string | null): string => {
  if (!nextPath || !nextPath.startsWith('/') || nextPath.startsWith('//')) {
    return '/events';
  }
  return nextPath;
};

const Login = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [step, setStep] = useState<Step>('email');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [bothAvailable, setBothAvailable] = useState(false);
  const [preferred, setPreferred] = useState<LoginMethod>('passwordless');

  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const resetFeedback = () => {
    setErrorMessage(null);
    setStatusMessage(null);
  };

  const resetToEmail = () => {
    setStep('email');
    setPassword('');
    setCode('');
    setBothAvailable(false);
    resetFeedback();
  };

  const handleRateLimit = (error: unknown): boolean => {
    if (error instanceof AxiosError && error.response?.status === 429) {
      setErrorMessage('Too many attempts. Try again in a moment.');
      return true;
    }
    return false;
  };

  const onSubmitEmail = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    resetFeedback();

    try {
      const { data } = await getLoginMethods(email);
      setPreferred(data.preferred);
      setBothAvailable(data.password && data.passwordless);

      if (data.password && data.preferred === 'password') {
        setStep('password');
      } else {
        await requestPasswordlessCode();
      }
    } catch (error) {
      if (!handleRateLimit(error)) {
        setErrorMessage(extractBackendErrorMessage(error, 'Could not start sign-in. Please try again.'));
      }
    } finally {
      setIsLoading(false);
    }
  };

  const requestPasswordlessCode = async () => {
    try {
      setIsLoading(true);
      const response = await passwordlessRequest(email);
      setStatusMessage(response.data.message);
      setStep('passwordless_verify');
    } catch (error) {
      if (!handleRateLimit(error)) {
        setErrorMessage(extractBackendErrorMessage(error, 'Failed to request verification code.'));
      }
    } finally {
      setIsLoading(false);
    }
  };

  const onSubmitPassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    resetFeedback();

    try {
      const { data } = await loginWithPassword(email, password);
      setAuthTokens(data.access, data.refresh);
      navigate(getSafeNextPath(searchParams.get('next')));
    } catch (error) {
      if (!handleRateLimit(error)) {
        setErrorMessage(extractBackendErrorMessage(error, 'Invalid email or password.'));
      }
    } finally {
      setIsLoading(false);
    }
  };

  const onSubmitCode = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    resetFeedback();

    try {
      const { data } = await passwordlessVerify(email, code);
      setAuthTokens(data.access, data.refresh);
      setStatusMessage('Login successful. Redirecting…');
      navigate(getSafeNextPath(searchParams.get('next')));
    } catch (error) {
      if (!handleRateLimit(error)) {
        setErrorMessage(extractBackendErrorMessage(error, 'Verification failed.'));
      }
    } finally {
      setIsLoading(false);
    }
  };

  const switchToPasswordless = async () => {
    resetFeedback();
    await requestPasswordlessCode();
  };

  const switchToPassword = () => {
    resetFeedback();
    setStep('password');
  };

  const renderEmailStep = () => (
    <form className="space-y-4" onSubmit={onSubmitEmail}>
      <Input
        icon={<Mail className="h-4 w-4" />}
        label="Email address"
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@example.com"
        required
        type="email"
        value={email}
      />
      <Button
        className="w-full"
        disabled={isLoading || !email}
        icon={<KeyRound className="h-4 w-4" />}
        isLoading={isLoading}
        type="submit"
      >
        Continue
      </Button>
    </form>
  );

  const renderPasswordStep = () => (
    <form className="space-y-4" onSubmit={onSubmitPassword}>
      <div className="rounded-lg bg-brand-50 px-3 py-2 text-center text-sm text-brand-800">
        Signing in as <span className="font-medium">{email}</span>
      </div>
      <Input
        autoComplete="current-password"
        icon={<Lock className="h-4 w-4" />}
        label="Password"
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Your password"
        required
        type="password"
        value={password}
      />
      <Button className="w-full" disabled={isLoading || !password} isLoading={isLoading} type="submit">
        Sign in
      </Button>
      <div className="flex flex-col gap-2">
        <button
          className="text-center text-xs text-brand-700 transition-colors hover:text-brand-900"
          onClick={switchToPasswordless}
          type="button"
        >
          Sign in with a code instead
        </button>
        <button
          className="text-center text-xs text-ink-muted transition-colors hover:text-ink"
          onClick={resetToEmail}
          type="button"
        >
          Use a different email
        </button>
      </div>
    </form>
  );

  const renderCodeStep = () => (
    <form className="space-y-4" onSubmit={onSubmitCode}>
      <div className="rounded-lg bg-brand-50 px-3 py-2 text-center text-sm text-brand-800">
        Code sent to <span className="font-medium">{email}</span>
      </div>
      <Input
        icon={<KeyRound className="h-4 w-4" />}
        inputMode="numeric"
        label="Verification code"
        maxLength={6}
        onChange={(e) => setCode(e.target.value)}
        pattern="[0-9]{6}"
        placeholder="000000"
        required
        type="text"
        value={code}
      />
      <Button className="w-full" disabled={isLoading || code.length !== 6} isLoading={isLoading} type="submit">
        Verify and Login
      </Button>
      <div className="flex flex-col gap-2">
        {bothAvailable && preferred !== 'password' && (
          <button
            className="text-center text-xs text-brand-700 transition-colors hover:text-brand-900"
            onClick={switchToPassword}
            type="button"
          >
            Use password instead
          </button>
        )}
        <button
          className="text-center text-xs text-ink-muted transition-colors hover:text-ink"
          onClick={resetToEmail}
          type="button"
        >
          Use a different email
        </button>
      </div>
    </form>
  );

  const renderCurrentStep = () => {
    if (step === 'email') return renderEmailStep();
    if (step === 'password') return renderPasswordStep();
    return renderCodeStep();
  };

  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4">
      <div className="w-full max-w-sm animate-fade-in">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600 shadow-lg shadow-brand-200">
            <Camera className="h-7 w-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">Welcome back</h1>
          <p className="mt-1 text-sm text-ink-muted">Sign in to Media Flow with your email</p>
        </div>

        {statusMessage && (
          <div className="mb-4">
            <Alert variant="success">{statusMessage}</Alert>
          </div>
        )}
        {errorMessage && (
          <div className="mb-4">
            <Alert variant="error">{errorMessage}</Alert>
          </div>
        )}

        <Card padding="lg">{renderCurrentStep()}</Card>
      </div>
    </div>
  );
};

export default Login;
