import { format } from 'date-fns';
import { Pencil, X } from 'lucide-react';
import React, { FormEvent, useMemo, useState } from 'react';

import {
  Alert,
  Button,
  DatePickerField,
  FormSection,
  Input,
  Switch,
  Textarea,
  TimePickerField,
} from './ui';

import { EventDetailResponse, updateEvent } from '@/js/api';
import { useFormErrors } from '@/js/hooks/useFormErrors';
import { extractBackendErrorMessage } from '@/js/utils';

interface EditEventModalProps {
  event: EventDetailResponse;
  onClose: () => void;
  onUpdated: (updated: EventDetailResponse) => void;
}

type FormValues = {
  eventName: string;
  date: string;
  time: string;
};

const DATE_FMT = 'yyyy-MM-dd';

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

const EditEventModal = ({ event, onClose, onUpdated }: EditEventModalProps) => {
  const [eventName, setEventName] = useState(event.event_name);
  const [description, setDescription] = useState(event.description || '');
  const [date, setDate] = useState<string>(event.date);
  const [time, setTime] = useState(event.time || '');
  const [location, setLocation] = useState(event.location || '');
  const [address, setAddress] = useState(event.address || '');
  const [isPublic, setIsPublic] = useState(event.is_public);
  const [allDay, setAllDay] = useState(event.all_day);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Editing an existing event: never restrict the date below the event's
  // current date — server allows updates to past events for some fields.
  const minDate = useMemo(() => {
    const today = format(new Date(), DATE_FMT);
    return event.date < today ? event.date : today;
  }, [event.date]);

  const formValues: FormValues = { eventName, date, time };
  const { errorFor, markTouched, validateAll, validateField, focusFirstError } = useFormErrors(validate);

  const onSubmit = async (formEvent: FormEvent<HTMLFormElement>) => {
    formEvent.preventDefault();
    setErrorMessage(null);

    if (!validateAll(formValues)) {
      focusFirstError();
      return;
    }

    setIsLoading(true);
    try {
      const response = await updateEvent(event.event_uuid, {
        event_name: eventName.trim(),
        description: description.trim(),
        date,
        time: allDay || !time ? null : time,
        location: location.trim(),
        address: address.trim(),
        all_day: allDay,
        is_public: isPublic,
      });
      onUpdated(response.data);
      onClose();
    } catch (error) {
      setErrorMessage(extractBackendErrorMessage(error, 'Failed to update event.'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="animate-fade-in fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="animate-slide-up w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl border border-border-subtle bg-surface-1 p-6 shadow-2xl"
        onClick={(clickEvent) => clickEvent.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-100 text-brand-600">
              <Pencil className="h-5 w-5" />
            </div>
            <h2 className="text-lg font-semibold text-ink">Edit Event</h2>
          </div>
          <button
            className="rounded-lg p-1.5 text-ink-faint transition hover:bg-surface-2 hover:text-ink"
            type="button"
            onClick={onClose}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {errorMessage && (
          <div className="mb-3">
            <Alert variant="error">{errorMessage}</Alert>
          </div>
        )}

        <form onSubmit={onSubmit} noValidate>
          <FormSection first title="Basics">
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
              error={errorFor('eventName')}
              id="eventName"
              name="eventName"
            />
            <Textarea
              label="Description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe your event..."
            />
          </FormSection>

          <FormSection title="Schedule">
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
                onChange={setTime}
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

          <FormSection title="Where">
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

          <div className="mt-6 flex justify-end gap-3 border-t border-border-subtle pt-5">
            <Button variant="secondary" onClick={onClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isLoading}>
              Save Changes
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default EditEventModal;
