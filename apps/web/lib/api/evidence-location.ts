import { translate as tr } from '../translations';
import type { Evidence } from './types';

export function locationLabel(e: Evidence) {
  return (
    [
      e.location.page && tr('source.pageShort', { page: e.location.page }),
      e.location.section,
      !e.location.page &&
        e.location.line_start &&
        tr('source.lines', {
          start: e.location.line_start,
          end: e.location.line_end || e.location.line_start,
        }),
    ]
      .filter(Boolean)
      .join(' · ') || tr('source.passage')
  );
}
