import { AxiosError } from 'axios';
import { CheckCircle, PartyPopper, RefreshCw, XCircle } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router';

import { EventPublicInviteJoinResponse, joinEventByPublicInviteToken } from '@/js/api';
import { Button, Card, LoadingSpinner, PageLayout } from '@/js/components/ui';

type InviteJoinErrorPayload = {
  error_code?: string;
  message?: string;
};

const buildJoinErrorMessage = (error: unknown): string => {
  if (!(error instanceof AxiosError)) {
    return 'Failed to join event by invite link.';
  }

  const payload = error.response?.data as InviteJoinErrorPayload | undefined;
  if (payload?.message) {
    return payload.message;
  }

  if (payload?.error_code === 'invite_expired') {
    return 'This invitation has expired.';
  }

  if (payload?.error_code?.startsWith('invite_token_')) {
    return 'Invitation token is invalid.';
  }

  if (payload?.error_code === 'invite_limit_reached') {
    return 'Invitation usage limit has been reached.';
  }

  return 'Failed to join event by invite link.';
};

const JoinByInvite = () => {
  const [searchParams] = useSearchParams();
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [result, setResult] = useState<EventPublicInviteJoinResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [attempt, setAttempt] = useState<number>(0);

  const inviteToken = searchParams.get('token')?.trim() || '';

  useEffect(() => {
    let isMounted = true;

    const runJoinFlow = async (): Promise<void> => {
      if (!inviteToken) {
        if (!isMounted) return;
        setIsLoading(false);
        setErrorMessage('Invite token is missing in URL query.');
        return;
      }

      setIsLoading(true);
      setErrorMessage(null);
      setResult(null);

      try {
        const response = await joinEventByPublicInviteToken(inviteToken);
        if (!isMounted) return;
        setResult(response.data);
      } catch (error) {
        if (!isMounted) return;
        setErrorMessage(buildJoinErrorMessage(error));
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    runJoinFlow();

    return () => {
      isMounted = false;
    };
  }, [attempt, inviteToken]);

  const handleRetry = (): void => {
    setAttempt((currentValue) => currentValue + 1);
  };

  return (
    <PageLayout maxWidth="sm">
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="w-full animate-fade-in">
          {isLoading && <LoadingSpinner message="Joining event..." />}

          {!isLoading && errorMessage && (
            <Card padding="lg">
              <div className="text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-100">
                  <XCircle className="h-8 w-8 text-red-500" />
                </div>
                <h2 className="mb-2 text-xl font-semibold text-ink">Unable to Join</h2>
                <p className="mb-4 text-sm text-ink-muted">{errorMessage}</p>
                {inviteToken && (
                  <Button variant="secondary" onClick={handleRetry} icon={<RefreshCw className="h-4 w-4" />}>
                    Retry
                  </Button>
                )}
              </div>
            </Card>
          )}

          {!isLoading && result && (
            <Card padding="lg">
              <div className="text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100">
                  {result.already_joined ? (
                    <CheckCircle className="h-8 w-8 text-emerald-500" />
                  ) : (
                    <PartyPopper className="h-8 w-8 text-emerald-500" />
                  )}
                </div>
                <h2 className="mb-2 text-xl font-semibold text-ink">
                  {result.already_joined ? 'Already Joined' : 'You\'re In!'}
                </h2>
                <p className="mb-4 text-sm text-ink-muted">
                  {result.already_joined ? 'You are already a member of this event.' : 'You have successfully joined the event.'}
                </p>

                <div className="mb-6 rounded-xl bg-surface-2 p-4 text-left">
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="font-medium text-ink-muted">Event</span>
                      <span className="text-ink">{result.event_name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-medium text-ink-muted">Participant</span>
                      <span className="text-ink">{result.participant_name}</span>
                    </div>
                  </div>
                </div>

                <Link
                  className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-6 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-brand-700"
                  to={`/events/${result.event_uuid}`}
                >
                  Go to Event
                </Link>
              </div>
            </Card>
          )}
        </div>
      </div>
    </PageLayout>
  );
};

export default JoinByInvite;
