// Public API entry point. Transport and DTOs have separate responsibilities.
export { api, ApiError, origin } from './api/client';
export type * from './api/types';
export { originalFile } from './api/source-files';
export { locationLabel } from './api/evidence-location';
