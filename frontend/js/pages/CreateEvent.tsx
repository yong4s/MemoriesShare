import { addDays, format } from 'date-fns';
import { CalendarPlus } from 'lucide-react';
import React, { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router';

import { createEvent } from '@/js/api';
import {
  Alert,
  Button,
  Card,
  DatePickerField,
  FormSection,
  Input,
  PageHeader,
  PageLayout,
  Switch,
  Textarea,
  TimePickerField,
} from '@/js/components/ui';
import { useFormErrors } from '@/js/hooks/useFormErrors';
import { extractBackendErrorMessage } from '@/js/utils';

type CreateEventResponseShape = { event_uuid?: string } | { data?: { event_uuid?: string } };

type FormValues = {
  eventName: string;
  date: string;
  time: string;
};

const DATE_FMT = 'yyyy-MM-dd';
const DEFAULT_TIME = '18:00';

const validate = ({ eventName, date }: FormValues): Partial<Record<keyof FormValues, string>> => {
  const errors: Partial<Record<keyof FormValues, string>> = {};
  if (!eventName.trim()) {
    errors.eventName = 'Event name is required';
  } else if (eventName.length > 255) {
    errors.eventName = 'Event name must be 255 characters or fewer';
  }
  if (!date) {
    errors.date = 'Date is required';
  }
  return errors;
};

const CreateEvent = () => {
  const navigate = useNavigate();
  const [eventName, setEventName] = useState('');
  const [description, setDescription] = useState('');
  const [date, setDate] = useState<string>(() => format(addDays(new Date(), 1), DATE_FMT));
  const [time, setTime] = useState('');
  const [location, setLocation] = useState('');
  const [address, setAddress] = useState('');
  const [isPublic, setIsPublic] = useState(false);
  const [allDay, setAllDay] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const userTouchedTime = useRef(false);

  const minDate = useMemo(() => format(new Date(), DATE_FMT), []);
  const formValues: FormValues = { eventName, date, time };
  const { errorFor, markTouched, validateAll, validateField, focusFirstError } = useFormErrors(validate);

  // Smart default: when the user picks a date and hasn't manually entered a time,
  // prefill 18:00 (most events are evenings). Never overwrite a user-typed value.
  useEffect(() => {
    if (date && !time && !allDay && !userTouchedTime.current) {
      setTime(DEFAULT_TIME);
    }
  }, [date, time, allDay]);

  const handleTimeChange = (next: string) => {
    userTouchedTime.current = true;
    setTime(next);
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setErrorMessage(null);

    if (!validateAll(formValues)) {
      focusFirstError();
      return;
    }

    setIsLoading(true);
    try {
      const response = await createEvent({
        event_name: eventName.trim(),
        description: description.trim(),
        date,
        time: allDay || !time ? null : time,
        location: location.trim(),
        address: address.trim(),
        all_day: allDay,
        is_public: isPublic,
      });

      const payload = response.data as CreateEventResponseShape;
      const eventUuid = 'event_uuid' in payload ? payload.event_uuid : 'data' in payload ? payload.data?.event_uuid : undefined;
      if (!eventUuid) {
        throw new Error('Event UUID missing in response');
      }

      navigate(`/events/${eventUuid}`);
    } catch (error) {
      setErrorMessage(extractBackendErrorMessage(error, 'Failed to create event.'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <PageLayout maxWidth="md">
      <PageHeader title="Create Event" subtitle="Tell guests what to expect — name, when, and where." />

      {errorMessage && (
        <div className="mb-4">
          <Alert variant="error">{errorMessage}</Alert>
        </div>
      )}

      <Card padding="lg">
        <form onSubmit={onSubmit} noValidate>
          <FormSection first title="Basics" subtitle="What's this event called?">
            <Input
              label="Event name"
              maxLength={255}
              required
              type="text"
              value={eventName}
              onChange={(e) => setEventName(e.target.value)}
              onBlur={() => {
                markTouched('eventName');
                validateField(formValues, 'eventName');
              }}
              placeholder="My awesome event"
              error={errorFor('eventName')}
              id="eventName"
              name="eventName"
            />
            <Textarea
              label="Description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this event about?"
            />
          </FormSection>

          <FormSection title="Schedule" subtitle="When is it happening?">
            <div className="grid gap-3 sm:grid-cols-2">
              <DatePickerField
                label="Date"
                required
                value={date}
                min={minDate}
                onChange={(next) => {
                  setDate(next);
                  markTouched('date');
                }}
                onBlur={() => markTouched('date')}
                error={errorFor('date')}
                id="date"
              />
              <TimePickerField
                label="Time"
                value={time}
                onChange={handleTimeChange}
                hidden={allDay}
                error={errorFor('time')}
                id="time"
              />
            </div>
            <Switch
              label="All-day event"
              description="Hides the time picker; the event is shown as running all day."
              checked={allDay}
              onChange={setAllDay}
            />
          </FormSection>

          <FormSection title="Where" subtitle="Where should guests go?">
            <div className="grid gap-3 sm:grid-cols-2">
              <Input
                label="Location"
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. Conference Hall"
              />
              <Input
                label="Address"
                type="text"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="e.g. 123 Main St"
              />
            </div>
          </FormSection>

          <FormSection title="Visibility">
            <Switch
              label="Public event"
              description="Public events appear in discovery; otherwise only invitees can see it."
              checked={isPublic}
              onChange={setIsPublic}
            />
          </FormSection>

          <div className="mt-6 flex justify-end border-t border-border-subtle pt-5">
            <Button
              type="submit"
              isLoading={isLoading}
              icon={<CalendarPlus className="h-4 w-4" />}
            >
              Create Event
            </Button>
          </div>
        </form>
      </Card>
    </PageLayout>
  );
};

export default CreateEvent;
