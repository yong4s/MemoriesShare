import { CalendarPlus, Compass, Globe, PartyPopper, Search, User, Users } from 'lucide-react';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';

import { EventListItem, listEvents } from '@/js/api';
import EventCard from '@/js/components/EventCard';
import { Alert, EmptyState, LoadingSpinner, PageHeader, PageLayout, StatCard } from '@/js/components/ui';
import { extractBackendErrorMessage } from '@/js/utils';

type FilterTab = 'all' | 'owned' | 'joined' | 'discover';

const MyEvents = () => {
  const navigate = useNavigate();
  const [eventsByTab, setEventsByTab] = useState<Record<FilterTab, EventListItem[]>>({
    all: [],
    owned: [],
    joined: [],
    discover: [],
  });
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<FilterTab>('all');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const loadEvents = async (): Promise<void> => {
      try {
        const [allResponse, ownedResponse, publicResponse] = await Promise.all([
          listEvents({ scope: 'all' }),
          listEvents({ scope: 'owned' }),
          listEvents({ scope: 'public' }),
        ]);

        const allList = allResponse.data.events ?? [];
        const ownedList = ownedResponse.data.events ?? [];
        const publicList = publicResponse.data.events ?? [];

        const ownedUuids = new Set(ownedList.map((e) => e.event_uuid));
        const joinedList = allList.filter((e) => !ownedUuids.has(e.event_uuid));

        setEventsByTab({
          all: allList,
          owned: ownedList,
          joined: joinedList,
          discover: publicList,
        });
      } catch (error) {
        setErrorMessage(extractBackendErrorMessage(error, 'Failed to load events.'));
      } finally {
        setIsLoading(false);
      }
    };

    loadEvents();
  }, []);

  const filteredEvents = useMemo(() => {
    let events = eventsByTab[activeTab];

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      events = events.filter(
        (event) =>
          event.event_name.toLowerCase().includes(query) ||
          (event.location && event.location.toLowerCase().includes(query)),
      );
    }

    return events;
  }, [eventsByTab, activeTab, searchQuery]);

  const ownedUuids = useMemo(
    () => new Set(eventsByTab.owned.map((e) => e.event_uuid)),
    [eventsByTab.owned],
  );

  const handleCreateEvent = useCallback(() => {
    navigate('/events/new');
  }, [navigate]);

  const tabs: { key: FilterTab; label: string; count: number; icon: React.ReactNode }[] = [
    { key: 'all', label: 'All', count: eventsByTab.all.length, icon: <PartyPopper className="h-3.5 w-3.5" /> },
    { key: 'owned', label: 'My Events', count: eventsByTab.owned.length, icon: <User className="h-3.5 w-3.5" /> },
    { key: 'joined', label: 'Joined', count: eventsByTab.joined.length, icon: <Users className="h-3.5 w-3.5" /> },
    { key: 'discover', label: 'Discover', count: eventsByTab.discover.length, icon: <Compass className="h-3.5 w-3.5" /> },
  ];

  const emptyMessages: Record<FilterTab, { title: string; message: string }> = {
    all: { title: 'No events yet', message: 'Create your first event to get started.' },
    owned: { title: 'No events created', message: 'You haven\'t created any events yet.' },
    joined: { title: 'No joined events', message: 'You haven\'t joined any events yet.' },
    discover: { title: 'No public events', message: 'There are no public events available right now.' },
  };

  return (
    <PageLayout>
      <PageHeader
        title="My Events"
        subtitle="View and manage your events"
        action={{ label: 'Create Event', onClick: handleCreateEvent, icon: <CalendarPlus className="h-4 w-4" /> }}
      />

      {!isLoading && !errorMessage && (
        <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard label="Total" value={eventsByTab.all.length} icon={<PartyPopper className="h-5 w-5" />} />
          <StatCard label="Owned" value={eventsByTab.owned.length} icon={<User className="h-5 w-5" />} />
          <StatCard label="Joined" value={eventsByTab.joined.length} icon={<Users className="h-5 w-5" />} />
          <StatCard label="Public" value={eventsByTab.discover.length} icon={<Globe className="h-5 w-5" />} />
        </div>
      )}

      {isLoading && <LoadingSpinner message="Loading events..." />}

      {!isLoading && errorMessage && (
        <Alert variant="error">{errorMessage}</Alert>
      )}

      {!isLoading && !errorMessage && (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <div className="flex rounded-lg border border-zinc-200 bg-zinc-50 p-1">
              {tabs.map((tab) => (
                <button
                  key={tab.key}
                  className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-all duration-150 ${
                    activeTab === tab.key
                      ? 'bg-brand-600 text-white shadow-sm'
                      : 'text-zinc-500 hover:text-zinc-700'
                  }`}
                  type="button"
                  onClick={() => setActiveTab(tab.key)}
                >
                  {tab.icon}
                  <span className="hidden sm:inline">{tab.label}</span>
                  <span>({tab.count})</span>
                </button>
              ))}
            </div>

            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
              <input
                className="rounded-lg border border-zinc-300 pl-9 pr-3 py-2 text-sm transition-colors focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
                placeholder="Search events..."
                type="text"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
              />
            </div>
          </div>

          {filteredEvents.length === 0 ? (
            <EmptyState
              title={searchQuery ? 'No events found' : emptyMessages[activeTab].title}
              message={searchQuery ? 'Try a different search term.' : emptyMessages[activeTab].message}
              action={!searchQuery && activeTab !== 'discover' ? { label: 'Create Event', onClick: handleCreateEvent } : undefined}
              icon={activeTab === 'discover' ? <Compass className="h-12 w-12" /> : <PartyPopper className="h-12 w-12" />}
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {filteredEvents.map((event) => (
                <EventCard
                  key={event.event_uuid}
                  event={event}
                  isOwner={ownedUuids.has(event.event_uuid)}
                />
              ))}
            </div>
          )}
        </>
      )}
    </PageLayout>
  );
};

export default MyEvents;
