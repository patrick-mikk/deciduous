export * from "./types";
export * from "./degreeAudit";
export { api, mockClient, httpClient, isMockApi, ensureCsrfToken, API_BASE, ApiError, isAuthError } from "./client";
export type { ApiClient, CourseSearchParams, ProgramSearchParams, PlanValidationItem, PlanValidationResult } from "./client";
export { loadGuestProfile, saveGuestProfile, clearGuestProfile } from "./guestProfile";
export type { GuestProfile, GuestCourse } from "./guestProfile";
export * as authApi from "./auth";
export type { AuthUser, Profile, ActiveSession, Passkey } from "./auth";
