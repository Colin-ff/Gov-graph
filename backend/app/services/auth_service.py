"""Login / credential-check service.

Sprint-1 auth is intentionally minimal (see ``app/auth.py`` for the request-time
seam). Here we verify an email/password pair against the hashed ``users.password``
value and hand back the persistent ``temp_token`` the frontend then replays as
``X-Token``.
"""

from werkzeug.security import check_password_hash

from app.db_schema import Users


def authenticate(email: str | None, password: str | None) -> dict | None:
    """Return the caller's auth profile when the credentials match, else ``None``.

    The returned dict never includes the password — only what the frontend needs
    to identify itself on later requests (``email`` + ``token``) and to drive the
    UI (``displayName`` / ``userRole``).
    """
    if not email or not password:
        return None

    # Registration stores emails lower-cased, so normalise here too — otherwise a
    # user who signs up as "A.Lee@unsw.edu.au" can never log back in.
    user = Users.query.filter_by(email=email.strip().lower()).first()
    if user is None or not user.is_active:
        return None

    if not check_password_hash(user.password, password):
        return None

    return {
        "email": user.email,
        "displayName": user.display_name,
        "userRole": user.user_role.value,
        "token": user.temp_token,
    }
