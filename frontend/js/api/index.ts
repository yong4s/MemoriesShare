import type { AxiosResponse } from 'axios';

import { client } from '@/js/api/client.gen';

export interface HealthCheckResponse {
  message: string;
  status: string;
}

export type LoginMethod = 'password' | 'passwordless';

export interface AuthenticatedUser {
  date_joined: string;
  display_name: string;
  email: string;
  first_name: string;
  guest_name: string;
  has_password: boolean;
  id: number;
  is_active: boolean;
  is_anonymous_guest: boolean;
  is_guest: boolean;
  is_registered: boolean;
  is_staff: boolean;
  last_name: string;
  password_changed_at: string | null;
  preferred_login_method: LoginMethod;
}

export type UserProfile = AuthenticatedUser;

export interface LoginMethodsResponse {
  password: boolean;
  passwordless: boolean;
  preferred: LoginMethod;
}

export interface PasswordLoginResponse {
  access: string;
  refresh: string;
}

export interface SetPasswordResponse {
  access: string;
  message: string;
  refresh: string;
}

export interface ChangePasswordResponse {
  message: string;
}

export interface UpdateProfileRequest {
  first_name?: string;
  last_name?: string;
  preferred_login_method?: LoginMethod;
}

export interface AuthStatusResponse {
  authenticated: boolean;
  user: AuthenticatedUser;
}

export interface PasswordlessRequestResponse {
  expires_in_minutes: number;
  message: string;
  note: string;
  success: boolean;
}

export interface PasswordlessVerifyResponse {
  access: string;
  message: string;
  refresh: string;
  success: boolean;
  user: AuthenticatedUser;
}

export interface RefreshTokenResponse {
  access: string;
  refresh?: string;
}

export interface LogoutResponse {
  message: string;
}

export interface EventPublicInviteIssueRequest {
  max_uses?: number;
  ttl_hours?: number;
}

export interface EventCreateRequest {
  address?: string;
  all_day?: boolean;
  date: string;
  description?: string;
  event_name: string;
  is_public?: boolean;
  location?: string;
  time?: string | null;
}

export interface EventCreateResponse {
  created_at: string;
  date: string;
  description: string;
  event_name: string;
  event_uuid: string;
  is_public: boolean;
  location: string;
  owner_name: string;
  time: string | null;
}

export interface EventListItem {
  attending_count: number;
  created_at: string;
  date: string;
  event_name: string;
  event_uuid: string;
  is_public: boolean;
  location: string;
  owner_name: string;
  time: string | null;
  total_participants: number;
}

export interface EventListPagination {
  has_next: boolean;
  has_previous: boolean;
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
}

export interface EventListResponse {
  events: EventListItem[];
  pagination: EventListPagination;
}

export interface EventDetailResponse {
  address: string;
  all_day: boolean;
  attending_count: number;
  created_at: string;
  date: string;
  description: string;
  event_name: string;
  event_uuid: string;
  is_public: boolean;
  location: string;
  maybe_count: number;
  not_attending_count: number;
  owner_id: number;
  owner_email: string;
  owner_name: string;
  pending_count: number;
  time: string | null;
  total_participants: number;
  updated_at: string;
}

export interface EventUpdateRequest {
  address?: string;
  all_day?: boolean;
  date?: string;
  description?: string;
  event_name?: string;
  is_public?: boolean;
  location?: string;
  time?: string | null;
}

export interface EventPublicInviteIssueResponse {
  invite_url: string;
}

export interface EventPublicInviteJoinRequest {
  invite_token: string;
}

export interface EventPublicInviteJoinResponse {
  already_joined: boolean;
  event_name: string;
  event_uuid: string;
  participant_id: number;
  participant_name: string;
}

export interface EventParticipantListItem {
  id: number;
  role: string;
  rsvp_status: string;
  guest_name: string;
  user_name: string;
  is_registered_user: boolean;
  created_at: string;
}

export interface ParticipantListResponse {
  participants: EventParticipantListItem[];
  count: number;
}

export interface EventAnalyticsResponse {
  event_uuid: string;
  event_name: string;
  statistics: Record<string, number>;
  participant_breakdown: Record<string, number>;
  total_participants: number;
}

export interface UserEventAnalyticsResponse {
  summary: Record<string, number>;
  recent_events: EventListItem[];
  upcoming_events: EventListItem[];
}

export interface GuestInviteRequest {
  guest_name: string;
  guest_email?: string;
}

export interface RsvpResponse {
  id: number;
  role: string;
  rsvp_status: string;
}

export interface RsvpUpdateRequest {
  rsvp_status: string;
}

export type EventListScope = 'all' | 'owned' | 'participating' | 'public';

export interface EventListParams {
  page?: number;
  page_size?: number;
  search?: string;
  scope?: EventListScope;
}

export const restRestCheckRetrieve = (): Promise<AxiosResponse<HealthCheckResponse>> =>
  client.instance.get<HealthCheckResponse>('/accounts/health/');

export const accountsAuthStatusRetrieve = (): Promise<AxiosResponse<AuthStatusResponse>> =>
  client.instance.get<AuthStatusResponse>('/accounts/auth/status/');

export const authRefresh = (refresh: string): Promise<AxiosResponse<RefreshTokenResponse>> =>
  client.instance.post<RefreshTokenResponse>('/accounts/auth/refresh/', { refresh });

export const authLogout = (refresh: string): Promise<AxiosResponse<LogoutResponse>> =>
  client.instance.post<LogoutResponse>('/accounts/auth/logout/', { refresh });

export const passwordlessRequest = (email: string): Promise<AxiosResponse<PasswordlessRequestResponse>> =>
  client.instance.post<PasswordlessRequestResponse>(
    '/accounts/auth/passwordless/request/',
    { email },
    {
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
    },
  );

export const passwordlessVerify = (
  email: string,
  code: string,
): Promise<AxiosResponse<PasswordlessVerifyResponse>> =>
  client.instance.post<PasswordlessVerifyResponse>('/accounts/auth/passwordless/verify/', { email, code });

export const getLoginMethods = (email: string): Promise<AxiosResponse<LoginMethodsResponse>> =>
  client.instance.post<LoginMethodsResponse>('/accounts/auth/login-methods/', { email });

export const loginWithPassword = (
  email: string,
  password: string,
): Promise<AxiosResponse<PasswordLoginResponse>> =>
  client.instance.post<PasswordLoginResponse>('/accounts/auth/login/', { email, password });

export const getProfile = (): Promise<AxiosResponse<UserProfile>> =>
  client.instance.get<UserProfile>('/accounts/profile/');

export const updateProfile = (payload: UpdateProfileRequest): Promise<AxiosResponse<UserProfile>> =>
  client.instance.put<UserProfile>('/accounts/profile/', payload);

export const setAccountPassword = (
  password: string,
  password_confirm: string,
): Promise<AxiosResponse<SetPasswordResponse>> =>
  client.instance.post<SetPasswordResponse>('/accounts/profile/set-password/', {
    password,
    password_confirm,
  });

export const changeAccountPassword = (
  old_password: string,
  new_password: string,
  new_password_confirm: string,
): Promise<AxiosResponse<ChangePasswordResponse>> =>
  client.instance.post<ChangePasswordResponse>('/accounts/profile/change-password/', {
    old_password,
    new_password,
    new_password_confirm,
  });

export const issueEventPublicInviteLink = (
  eventUuid: string,
  payload: EventPublicInviteIssueRequest,
): Promise<AxiosResponse<EventPublicInviteIssueResponse>> =>
  client.instance.post<EventPublicInviteIssueResponse>(`/events/${eventUuid}/invites/public-link/`, payload);

export const createEvent = (payload: EventCreateRequest): Promise<AxiosResponse<EventCreateResponse>> =>
  client.instance.post<EventCreateResponse>('/events/', payload);

export const updateEvent = (
  eventUuid: string,
  payload: EventUpdateRequest,
): Promise<AxiosResponse<EventDetailResponse>> =>
  client.instance.put<EventDetailResponse>(`/events/${eventUuid}/`, payload);

export const deleteEvent = (eventUuid: string): Promise<AxiosResponse<void>> =>
  client.instance.delete(`/events/${eventUuid}/`);

export const listEvents = (params?: EventListParams): Promise<AxiosResponse<EventListResponse>> =>
  client.instance.get<EventListResponse>('/events/', {
    params: {
      page: params?.page,
      page_size: params?.page_size,
      search: params?.search,
      scope: params?.scope,
    },
  });

export const listOwnedEvents = (): Promise<AxiosResponse<EventListResponse>> =>
  listEvents({ scope: 'owned' });

export const listUserEvents = (): Promise<AxiosResponse<EventListResponse>> =>
  listEvents({ scope: 'all' });

export const getEventDetails = (eventUuid: string): Promise<AxiosResponse<EventDetailResponse>> =>
  client.instance.get<EventDetailResponse>(`/events/${eventUuid}/`);

export const listEventParticipants = (
  eventUuid: string,
  params?: { page?: number; page_size?: number },
): Promise<AxiosResponse<ParticipantListResponse>> =>
  client.instance.get<ParticipantListResponse>(`/events/${eventUuid}/participants/`, { params });

export const inviteGuest = (
  eventUuid: string,
  payload: GuestInviteRequest,
): Promise<AxiosResponse<EventParticipantListItem>> =>
  client.instance.post<EventParticipantListItem>(`/events/${eventUuid}/participants/`, payload);

export const inviteGuestsBulk = (
  eventUuid: string,
  guests: GuestInviteRequest[],
): Promise<AxiosResponse<EventParticipantListItem[]>> =>
  client.instance.post<EventParticipantListItem[]>(`/events/${eventUuid}/participants/`, guests);

export const updateParticipantRsvp = (
  eventUuid: string,
  participantId: number,
  payload: RsvpUpdateRequest,
): Promise<AxiosResponse<EventParticipantListItem>> =>
  client.instance.patch<EventParticipantListItem>(`/events/${eventUuid}/participants/${participantId}/`, payload);

export const getMyRsvp = (eventUuid: string): Promise<AxiosResponse<RsvpResponse>> =>
  client.instance.get<RsvpResponse>(`/events/${eventUuid}/rsvp/`);

export const updateMyRsvp = (eventUuid: string, payload: RsvpUpdateRequest): Promise<AxiosResponse<RsvpResponse>> =>
  client.instance.patch<RsvpResponse>(`/events/${eventUuid}/rsvp/`, payload);

export const getEventAnalytics = (eventUuid: string): Promise<AxiosResponse<EventAnalyticsResponse>> =>
  client.instance.get<EventAnalyticsResponse>(`/events/${eventUuid}/analytics/`);

export const getUserEventAnalytics = (): Promise<AxiosResponse<UserEventAnalyticsResponse>> =>
  client.instance.get<UserEventAnalyticsResponse>('/events/analytics/user/');

export const joinEventByPublicInviteToken = (
  inviteToken: string,
): Promise<AxiosResponse<EventPublicInviteJoinResponse>> =>
  client.instance.post<EventPublicInviteJoinResponse, AxiosResponse<EventPublicInviteJoinResponse>, EventPublicInviteJoinRequest>(
    '/events/invites/public-link/join/',
    { invite_token: inviteToken },
  );

// ── Albums ──────────────────────────────────────────────────────────────────

export interface AlbumListItem {
  album_uuid: string;
  event_name: string;
  name: string;
  description: string;
  is_public: boolean;
  created_at: string;
  mediafiles_count: number;
}

export interface AlbumDetail {
  album_uuid: string;
  event_uuid: string;
  event_name: string;
  name: string;
  description: string;
  is_public: boolean;
  file_count: number;
  total_file_size: number;
  has_cover_image: boolean;
  created_at: string;
  updated_at: string;
}

export interface AlbumCreateRequest {
  name: string;
  description?: string;
  is_public?: boolean;
}

export interface AlbumUpdateRequest {
  name?: string;
  description?: string;
  is_public?: boolean;
}

export const listEventAlbums = (eventUuid: string): Promise<AxiosResponse<AlbumListItem[]>> =>
  client.instance.get<AlbumListItem[]>(`/albums/event/${eventUuid}/`);

export const getAlbumDetail = (albumUuid: string): Promise<AxiosResponse<AlbumDetail>> =>
  client.instance.get<AlbumDetail>(`/albums/${albumUuid}/`);

export const createAlbum = (eventUuid: string, payload: AlbumCreateRequest): Promise<AxiosResponse<AlbumDetail>> =>
  client.instance.post<AlbumDetail>(`/albums/event/${eventUuid}/`, payload);

export const updateAlbum = (albumUuid: string, payload: AlbumUpdateRequest): Promise<AxiosResponse<AlbumDetail>> =>
  client.instance.put<AlbumDetail>(`/albums/${albumUuid}/`, payload);

export const deleteAlbum = (albumUuid: string): Promise<AxiosResponse<void>> =>
  client.instance.delete(`/albums/${albumUuid}/`);

// ── Media Files ─────────────────────────────────────────────────────────────

export interface MediaFileItem {
  file_uuid: string;
  file_name: string;
  file_type: string;
  /** Size in bytes; 0 for legacy files awaiting backfill_media_file_sizes. */
  file_size: number;
  s3_key: string;
  album_uuid: string;
  created_at: string;
  thumbnail_url: string | null;
}

export interface MediaFileListResponse {
  files: MediaFileItem[];
}

export interface PresignedUploadResponse {
  /** Presigned S3 POST endpoint. */
  url: string;
  /** Form fields that must accompany the multipart POST (policy, signature, key, …). */
  fields: Record<string, string>;
  s3_key: string;
  file_uuid: string;
  event_uuid: string;
  album_uuid: string;
  expires_in: number;
}

export interface PresignedDownloadResponse {
  download_url: string;
  expires_in: number;
}

export interface MediaUploadRequest {
  event_uuid: string;
  album_uuid: string;
  file_name: string;
  content_type: string;
}

export interface MediaUploadConfirmRequest {
  event_uuid: string;
  album_uuid: string;
  s3_key: string;
  file_type: string;
  file_name: string;
  user_id: number;
  file_uuid: string;
}

export const listMediaFiles = (params: { event_uuid?: string; album_uuid?: string }): Promise<AxiosResponse<MediaFileListResponse>> =>
  client.instance.get<MediaFileListResponse>('/mediafiles/', { params });

export const getMediaFileDownloadUrl = (fileUuid: string): Promise<AxiosResponse<PresignedDownloadResponse>> =>
  client.instance.get<PresignedDownloadResponse>(`/mediafiles/${fileUuid}/`, { params: { download: 'true' } });

export const requestMediaUploadUrl = (payload: MediaUploadRequest): Promise<AxiosResponse<PresignedUploadResponse>> =>
  client.instance.post<PresignedUploadResponse>('/mediafiles/', payload);

export const deleteMediaFile = (fileUuid: string): Promise<AxiosResponse<void>> =>
  client.instance.delete(`/mediafiles/${fileUuid}/`);

export const confirmMediaUpload = (payload: MediaUploadConfirmRequest): Promise<AxiosResponse<void>> =>
  client.instance.post<void>('/mediafiles/files/uploaded/', payload);
