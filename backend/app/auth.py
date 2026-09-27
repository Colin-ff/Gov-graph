"""Authentication / authorisation seam (Sprint-1).

The whole app funnels through ``get_current_user()`` so that, once real
sessions/SSO land, only this one function needs to change.

Sprint-1 auth is intentionally minimal. A request identifies itself with two
headers:
  * ``X-User-Email`` — the account's email.
  * ``X-Token``      — the account's persistent token (``users.temp_token``).
Both must match a ``users`` row for the caller to be authenticated. The token
is persistent for now; a later sprint will swap it for a short-lived
session/SSO token without touching any callers.
"""

from functools import wraps

from flask import abort, request

from app.db_schema import Role, Users


def get_current_user() -> Users | None:
    """Return the authenticated account, or ``None`` if the request is anonymous.

    The caller supplies its email in ``X-User-Email`` and its persistent token
    in ``X-Token``. The account is returned only when both headers are present
    and match the same ``users`` row.
    """
    email = request.headers.get("X-User-Email")
    token = request.headers.get("X-Token")
    if not email or not token:
        return None
    # Emails are stored lower-cased at registration; match that when resolving.
    user = Users.query.filter_by(email=email.strip().lower()).first()
    if user is not None and user.temp_token == token:
        return user
    return None


def is_privileged_superuser(user: Users | None) -> bool:
    """True when the user may see superuser views / edit the graph directly."""
    return user is not None and user.user_role == Role.SUPER_USER


def require_role(*roles: Role):
    """Decorator guarding endpoints by role.

    Resolves the caller via ``get_current_user()`` and aborts with ``401`` when
    the request is anonymous, or ``403`` when the account's role is not in
    ``roles``.
    """

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if user is None:
                abort(401, "Authentication required")
            if user.user_role not in roles:
                abort(403, "Insufficient privileges")
            return view(*args, **kwargs)

        return wrapper

    return decorator
