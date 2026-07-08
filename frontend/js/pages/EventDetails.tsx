import {
  Calendar,
  CheckCircle,
  Clock,
  Copy,
  FolderOpen,
  HelpCircle,
  Link2,
  MapPin,
  Navigation,
  Pencil,
  QrCode,
  RefreshCw,
  Trash2,
  UserCheck,
  UserPlus,
  Users,
} from 'lucide-react';
import { toDataURL } from 'qrcode';
import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';

import {
  AlbumListItem,
  deleteEvent,
  EventDetailResponse,
  getEventDetails,
  getMyRsvp,
  issueEventPublicInviteLink,
  listEventAlbums,
  RsvpResponse,
  updateMyRsvp,
} from '@/js/api';
import CreateAlbumModal from '@/js/components/CreateAlbumModal';
import EditEventModal from '@/js/components/EditEventModal';
import InviteGuestModal from '@/js/components/InviteGuestModal';
import ParticipantList from '@/js/components/ParticipantList';
import { Alert, Badge, Button, Card, ConfirmDialog, LoadingSpinner, PageLayout, StatCard } from '@/js/components/ui';
import { useAuth } from '@/js/context/AuthContext';
import { extractBackendErrorMessage, formatDate, formatTime } from '@/js/utils';

const DEFAULT_TTL_HOURS = 24;
const DEFAULT_MAX_USES = 10_000;

type EventDetailsResponseShape = EventDetailResponse | { data?: EventDetailResponse; event?: EventDetailResponse };

const EventDetails = () => {
  const { eventUuid } = useParams<{ eventUuid: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [eventDetails, setEventDetails] = useState<EventDetailResponse | null>(null);
  const [myRsvp, setMyRsvp] = useState<RsvpResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const [inviteUrl, setInviteUrl] = useState<string | null>(null);
  const [qrCodeDataUrl, setQrCodeDataUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  const [albums, setAlbums] = useState<AlbumListItem[]>([]);
  const [showCreateAlbumModal, setShowCreateAlbumModal] = useState(false);

  const [showEditModal, setShowEditModal] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isUpdatingRsvp, setIsUpdatingRsvp] = useState(false);
  const [participantRefreshKey, setParticipantRefreshKey] = useState(0);
  const [showRsvpButtons, setShowRsvpButtons] = useState(false);

  useEffect(() => {
    const loadEventDetails = async (): Promise<void> => {
      if (!eventUuid) {
        setErrorMessage('Missing event UUID in route.');
        setIsLoading(false);
        return;
      }

      try {
        const [eventResponse, rsvpResponse, albumsResponse] = await Promise.allSettled([
          getEventDetails(eventUuid),
          getMyRsvp(eventUuid),
          listEventAlbums(eventUuid),
        ]);

        if (eventResponse.status === 'fulfilled') {
          const payload = eventResponse.value.data as EventDetailsResponseShape;
          if ('event_uuid' in payload) {
            setEventDetails(payload);
          } else {
            setEventDetails(payload.event ?? payload.data ?? null);
          }
        } else {
          setErrorMessage(extractBackendErrorMessage(eventResponse.reason, 'Failed to load event details.'));
        }

        if (rsvpResponse.status === 'fulfilled') {
          setMyRsvp(rsvpResponse.value.data);
        }

        if (albumsResponse.status === 'fulfilled') {
          setAlbums(albumsResponse.value.data);
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadEventDetails();
  }, [eventUuid]);

  const isOwner = Boolean(user && eventDetails && eventDetails.owner_id === user.id);
  const userRole = myRsvp?.role?.toLowerCase() ?? '';
  const canModify = isOwner || userRole === 'moderator';

  const resetFeedback = (): void => {
    setStatusMessage(null);
    setErrorMessage(null);
  };

  const generateInviteQr = async (): Promise<void> => {
    if (!eventUuid || !canModify) return;
    resetFeedback();
    setIsGenerating(true);

    try {
      const response = await issueEventPublicInviteLink(eventUuid, {
        ttl_hours: DEFAULT_TTL_HOURS,
        max_uses: DEFAULT_MAX_USES,
      });
      const generatedQrCode = await toDataURL(response.data.invite_url, {
        errorCorrectionLevel: 'M',
        margin: 1,
        width: 320,
      });
      setInviteUrl(response.data.invite_url);
      setQrCodeDataUrl(generatedQrCode);
      setStatusMessage('Invite link generated.');
    } catch (error) {
      setErrorMessage(extractBackendErrorMessage(error, 'Failed to generate invite link.'));
      setInviteUrl(null);
      setQrCodeDataUrl(null);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopyInviteLink = async (): Promise<void> => {
    if (!inviteUrl) return;
    resetFeedback();
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setStatusMessage('Invite link copied to clipboard.');
    } catch {
      setErrorMessage('Copy failed. Please copy the link manually.');
    }
  };

  const handleDelete = async (): Promise<void> => {
    if (!eventUuid) return;
    setIsDeleting(true);

    try {
      await deleteEvent(eventUuid);
      navigate('/events');
    } catch (error) {
      setErrorMessage(extractBackendErrorMessage(error, 'Failed to delete event.'));
      setShowDeleteDialog(false);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleRsvpUpdate = async (status: string): Promise<void> => {
    if (!eventUuid) return;
    setIsUpdatingRsvp(true);
    resetFeedback();

    try {
      const response = await updateMyRsvp(eventUuid, { rsvp_status: status });
      setMyRsvp(response.data);
      setShowRsvpButtons(false);
      setStatusMessage(`RSVP updated to ${status}.`);

      // Re-fetch event details to update participant counts
      const eventResponse = await getEventDetails(eventUuid);
      const payload = eventResponse.data as EventDetailsResponseShape;
      if ('event_uuid' in payload) {
        setEventDetails(payload);
      } else {
        setEventDetails(payload.event ?? payload.data ?? null);
      }

      // Refresh participant list
      setParticipantRefreshKey((key) => key + 1);
    } catch (error) {
      setErrorMessage(extractBackendErrorMessage(error, 'Failed to update RSVP.'));
    } finally {
      setIsUpdatingRsvp(false);
    }
  };

  const handleEventUpdated = (updated: EventDetailResponse): void => {
    setEventDetails(updated);
    setStatusMessage('Event updated successfully.');
  };

  const getRsvpBadgeVariant = (status: string) => {
    const lower = status.toLowerCase();
    if (lower === 'accepted' || lower === 'attending') return 'accepted';
    if (lower === 'declined' || lower === 'not_attending') return 'declined';
    if (lower === 'maybe') return 'maybe';
    return 'pending';
  };

  return (
    <PageLayout>
      {isLoading && <LoadingSpinner message="Loading event..." />}

      {!isLoading && errorMessage && !eventDetails && (
        <Alert variant="error">{errorMessage}</Alert>
      )}

      {!isLoading && eventDetails && (
        <>
          {/* Header */}
          <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-3xl font-bold tracking-tight text-ink">{eventDetails.event_name}</h1>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <Badge variant={isOwner ? 'owner' : userRole === 'moderator' ? 'moderator' : 'guest'} />
                <Badge variant={eventDetails.is_public ? 'public' : 'private'} />
              </div>
            </div>
            <div className="flex gap-2">
              {canModify && (
                <Button variant="secondary" onClick={() => setShowEditModal(true)} icon={<Pencil className="h-4 w-4" />}>
                  Edit
                </Button>
              )}
              {isOwner && (
                <Button variant="danger" onClick={() => setShowDeleteDialog(true)} icon={<Trash2 className="h-4 w-4" />}>
                  Delete
                </Button>
              )}
            </div>
          </div>

          {/* Alerts */}
          {errorMessage && (
            <div className="mb-4">
              <Alert variant="error" onDismiss={() => setErrorMessage(null)}>{errorMessage}</Alert>
            </div>
          )}
          {statusMessage && (
            <div className="mb-4">
              <Alert variant="success" onDismiss={() => setStatusMessage(null)}>{statusMessage}</Alert>
            </div>
          )}

          {/* Stats bar */}
          <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="Total" value={eventDetails.total_participants} icon={<Users className="h-5 w-5" />} />
            <StatCard label="Attending" value={eventDetails.attending_count} icon={<CheckCircle className="h-5 w-5" />} />
            <StatCard label="Maybe" value={eventDetails.maybe_count} icon={<HelpCircle className="h-5 w-5" />} />
            <StatCard label="Pending" value={eventDetails.pending_count} icon={<Clock className="h-5 w-5" />} />
          </div>

          {/* Two-column layout */}
          <div className="grid gap-6 lg:grid-cols-3">
            {/* Left column */}
            <div className="space-y-6 lg:col-span-2">
              {/* Details card */}
              <Card padding="lg">
                <h3 className="mb-4 text-lg font-semibold text-ink">Event Details</h3>
                <div className="space-y-3">
                  <div className="flex items-start gap-3">
                    <Calendar className="mt-0.5 h-4 w-4 shrink-0 text-brand-500" />
                    <div>
                      <dt className="text-xs font-medium uppercase tracking-wider text-ink-faint">Date</dt>
                      <dd className="text-sm font-medium text-ink">{formatDate(eventDetails.date)}</dd>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <Clock className="mt-0.5 h-4 w-4 shrink-0 text-brand-500" />
                    <div>
                      <dt className="text-xs font-medium uppercase tracking-wider text-ink-faint">Time</dt>
                      <dd className="text-sm font-medium text-ink">{eventDetails.all_day ? 'All day' : formatTime(eventDetails.time)}</dd>
                    </div>
                  </div>
                  {eventDetails.location && (
                    <div className="flex items-start gap-3">
                      <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-brand-500" />
                      <div>
                        <dt className="text-xs font-medium uppercase tracking-wider text-ink-faint">Location</dt>
                        <dd className="text-sm font-medium text-ink">{eventDetails.location}</dd>
                      </div>
                    </div>
                  )}
                  {eventDetails.address && (
                    <div className="flex items-start gap-3">
                      <Navigation className="mt-0.5 h-4 w-4 shrink-0 text-brand-500" />
                      <div>
                        <dt className="text-xs font-medium uppercase tracking-wider text-ink-faint">Address</dt>
                        <dd className="text-sm font-medium text-ink">{eventDetails.address}</dd>
                      </div>
                    </div>
                  )}
                </div>
                {eventDetails.description && (
                  <div className="mt-4 border-t border-border-subtle pt-4">
                    <p className="text-sm leading-relaxed text-ink-muted whitespace-pre-wrap">{eventDetails.description}</p>
                  </div>
                )}
              </Card>

              {/* Participants */}
              <ParticipantList
                key={participantRefreshKey}
                eventUuid={eventDetails.event_uuid}
                canModify={canModify}
                showEmails={canModify}
                onInviteClick={() => setShowInviteModal(true)}
              />

              {/* Albums */}
              <Card padding="lg">
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FolderOpen className="h-5 w-5 text-brand-500" />
                    <h3 className="text-lg font-semibold text-ink">
                      Albums {albums.length > 0 && <span className="text-ink-faint">({albums.length})</span>}
                    </h3>
                  </div>
                  {canModify && (
                    <Button size="sm" onClick={() => setShowCreateAlbumModal(true)} icon={<FolderOpen className="h-3.5 w-3.5" />}>
                      Create Album
                    </Button>
                  )}
                </div>
                {albums.length === 0 ? (
                  <p className="text-sm text-ink-muted">No albums yet.</p>
                ) : (
                  <div className="space-y-2">
                    {albums.slice(0, 3).map((album) => (
                      <Link
                        key={album.album_uuid}
                        className="flex items-center justify-between rounded-xl border border-border-subtle px-4 py-3 text-sm transition-all hover:border-brand-200 hover:bg-brand-50/50"
                        to={`/events/${eventDetails.event_uuid}/albums/${album.album_uuid}`}
                      >
                        <div className="flex items-center gap-3">
                          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-100 text-brand-600">
                            <FolderOpen className="h-4 w-4" />
                          </div>
                          <span className="font-medium text-ink">{album.name}</span>
                        </div>
                        <span className="text-xs text-ink-faint">{album.mediafiles_count} files</span>
                      </Link>
                    ))}
                    {albums.length > 3 && (
                      <Link
                        className="block pt-2 text-center text-sm font-medium text-brand-600 hover:text-brand-700"
                        to={`/events/${eventDetails.event_uuid}/albums`}
                      >
                        View all {albums.length} albums &rarr;
                      </Link>
                    )}
                  </div>
                )}
                {albums.length > 0 && albums.length <= 3 && (
                  <Link
                    className="mt-4 block text-center text-sm font-medium text-brand-600 hover:text-brand-700"
                    to={`/events/${eventDetails.event_uuid}/albums`}
                  >
                    View All Albums &rarr;
                  </Link>
                )}
              </Card>
            </div>

            {/* Right column */}
            <div className="space-y-6">
              {/* RSVP card — only shown for participants (not owners, not viewers of public events) */}
              {!isOwner && myRsvp && (
                <Card padding="lg">
                  <div className="mb-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <UserCheck className="h-5 w-5 text-brand-500" />
                      <h3 className="text-lg font-semibold text-ink">Your RSVP</h3>
                    </div>
                    <Badge variant={getRsvpBadgeVariant(myRsvp.rsvp_status)}>{myRsvp.rsvp_status}</Badge>
                  </div>

                  {myRsvp.rsvp_status === 'pending' || showRsvpButtons ? (
                    <div className="flex flex-wrap gap-2">
                      <button
                        className="flex-1 rounded-lg bg-emerald-500 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-600 disabled:opacity-50"
                        disabled={isUpdatingRsvp}
                        onClick={() => handleRsvpUpdate('accepted')}
                      >
                        Accept
                      </button>
                      <button
                        className="flex-1 rounded-lg bg-amber-500 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-amber-600 disabled:opacity-50"
                        disabled={isUpdatingRsvp}
                        onClick={() => handleRsvpUpdate('maybe')}
                      >
                        Maybe
                      </button>
                      <button
                        className="flex-1 rounded-lg bg-red-500 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-red-600 disabled:opacity-50"
                        disabled={isUpdatingRsvp}
                        onClick={() => handleRsvpUpdate('declined')}
                      >
                        Decline
                      </button>
                    </div>
                  ) : (
                    <button
                      className="w-full rounded-lg border border-border-subtle px-3 py-2 text-sm font-medium text-ink-muted transition-colors hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
                      onClick={() => setShowRsvpButtons(true)}
                    >
                      Change RSVP
                    </button>
                  )}
                </Card>
              )}

              {/* Invite QR card */}
              {canModify && (
                <Card padding="lg">
                  <div className="mb-3 flex items-center gap-2">
                    <QrCode className="h-5 w-5 text-brand-500" />
                    <h3 className="text-lg font-semibold text-ink">Invite Link</h3>
                  </div>
                  {!inviteUrl ? (
                    <Button onClick={generateInviteQr} isLoading={isGenerating} icon={<Link2 className="h-4 w-4" />}>
                      Generate Invite QR
                    </Button>
                  ) : (
                    <>
                      {qrCodeDataUrl && (
                        <div className="mb-3 overflow-hidden rounded-xl border border-border-subtle bg-surface-1 p-2">
                          <img
                            alt="Event invitation QR code"
                            className="w-full"
                            src={qrCodeDataUrl}
                          />
                        </div>
                      )}
                      <div className="mb-3 rounded-lg bg-surface-2 p-2">
                        <p className="break-all text-xs text-ink-muted">{inviteUrl}</p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button size="sm" onClick={handleCopyInviteLink} icon={<Copy className="h-3.5 w-3.5" />}>
                          Copy Link
                        </Button>
                        <Button size="sm" variant="secondary" onClick={generateInviteQr} isLoading={isGenerating} icon={<RefreshCw className="h-3.5 w-3.5" />}>
                          Regenerate
                        </Button>
                      </div>
                    </>
                  )}
                </Card>
              )}

              {/* Invite guest button */}
              {canModify && (
                <Card padding="lg">
                  <div className="mb-3 flex items-center gap-2">
                    <UserPlus className="h-5 w-5 text-brand-500" />
                    <h3 className="text-lg font-semibold text-ink">Invite Guest</h3>
                  </div>
                  <p className="mb-3 text-sm text-ink-muted">Invite someone directly by name and email.</p>
                  <Button onClick={() => setShowInviteModal(true)} icon={<UserPlus className="h-4 w-4" />}>
                    Invite Guest
                  </Button>
                </Card>
              )}

              {/* Organizer card */}
              {canModify && (
                <Card padding="lg">
                  <h3 className="mb-3 text-sm font-medium uppercase tracking-wider text-ink-faint">Organizer</h3>
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-700">
                      {eventDetails.owner_name?.charAt(0)?.toUpperCase() ?? '?'}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-ink">{eventDetails.owner_name}</p>
                      <p className="text-xs text-ink-faint">{eventDetails.owner_email}</p>
                    </div>
                  </div>
                </Card>
              )}
            </div>
          </div>

          {/* Modals */}
          {showEditModal && (
            <EditEventModal
              event={eventDetails}
              onClose={() => setShowEditModal(false)}
              onUpdated={handleEventUpdated}
            />
          )}
          {showInviteModal && (
            <InviteGuestModal
              eventUuid={eventDetails.event_uuid}
              onClose={() => setShowInviteModal(false)}
              onInvited={() => setParticipantRefreshKey((key) => key + 1)}
            />
          )}
          {showCreateAlbumModal && (
            <CreateAlbumModal
              eventUuid={eventDetails.event_uuid}
              onClose={() => setShowCreateAlbumModal(false)}
              onCreated={(newAlbum) => {
                setAlbums((prev) => [
                  ...prev,
                  {
                    album_uuid: newAlbum.album_uuid,
                    event_name: newAlbum.event_name,
                    name: newAlbum.name,
                    description: newAlbum.description,
                    is_public: newAlbum.is_public,
                    created_at: newAlbum.created_at,
                    mediafiles_count: 0,
                  },
                ]);
                setStatusMessage('Album created successfully.');
              }}
            />
          )}
          {showDeleteDialog && (
            <ConfirmDialog
              title="Delete Event"
              message={`Are you sure you want to delete "${eventDetails.event_name}"? This action cannot be undone.`}
              confirmLabel="Delete"
              variant="danger"
              isLoading={isDeleting}
              onConfirm={handleDelete}
              onCancel={() => setShowDeleteDialog(false)}
            />
          )}
        </>
      )}
    </PageLayout>
  );
};

export default EventDetails;
