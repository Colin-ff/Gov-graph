// Canonical user roles, matching the backend Role enum (STAFF / SUPER_USER).
// AuthUser.userRole is the string form; compare against these values.
export enum UserRole {
  Staff = "STAFF",
  SuperUser = "SUPER_USER",
}
