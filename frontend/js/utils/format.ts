export const formatDate = (dateString: string): string => {
  if (!dateString) {
    return '';
  }

  try {
    const date = new Date(`${dateString}T00:00:00`);
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateString;
  }
};

export const formatTime = (timeString: string | null | undefined): string => {
  if (!timeString) {
    return 'All day';
  }

  try {
    const [hours, minutes] = timeString.split(':').map(Number);
    const date = new Date();
    date.setHours(hours, minutes);
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  } catch {
    return timeString;
  }
};
