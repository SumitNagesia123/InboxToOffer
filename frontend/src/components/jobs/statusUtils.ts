export interface ApplicationStatusConfig {
  variant: 'primary' | 'danger' | 'success' | 'warning' | 'info' | 'neutral';
  label: string;
}

/**
 * Returns distinct accessible badge styling and user-friendly label for pipeline application statuses.
 * Covers: APPLIED, INTERVIEWING, OFFER, NOT_APPLIED, REJECTED, DISCOVERED, WITHDRAWN.
 */
export const getApplicationStatusConfig = (status?: string): ApplicationStatusConfig | null => {
  if (!status) return null;
  const s = status.toUpperCase().trim();
  switch (s) {
    case 'APPLIED':
      return { variant: 'success', label: 'Applied' };
    case 'INTERVIEWING':
      return { variant: 'warning', label: 'Interviewing' };
    case 'OFFER':
      return { variant: 'primary', label: 'Offer Received' };
    case 'NOT_APPLIED':
      return { variant: 'danger', label: 'Passed' };
    case 'REJECTED':
      return { variant: 'neutral', label: 'Rejected' };
    case 'DISCOVERED':
      return { variant: 'info', label: 'Discovered' };
    case 'WITHDRAWN':
      return { variant: 'neutral', label: 'Withdrawn' };
    default:
      return {
        variant: 'neutral',
        label: s.charAt(0) + s.slice(1).toLowerCase().replace(/_/g, ' '),
      };
  }
};
