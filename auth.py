"""
Google sign-in restricted to one company domain.

Every page requires a signed-in @trexorobotics.com account. Config comes from
environment variables (set them in Vercel -> Settings -> Environment Variables):

    SECRET_KEY            long random string used to sign the login cookie
    GOOGLE_CLIENT_ID      OAuth client ID from Google Cloud Console
    GOOGLE_CLIENT_SECRET  OAuth client secret

Locally (not on Vercel) with no Google credentials set, sign-in is skipped so
the prototype still runs for development. On Vercel, missing config fails
closed - the app refuses to serve pages rather than running open.
"""

import datetime
import os

from authlib.integrations.flask_client import OAuth
from flask import redirect, render_template, request, session, url_for

ALLOWED_DOMAIN = "trexorobotics.com"
_PUBLIC_ENDPOINTS = {"login", "login_google", "auth_callback", "static"}

oauth = OAuth()


def _on_vercel():
    return bool(os.environ.get("VERCEL"))


def _configured():
    return bool(os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET"))


def _safe_next(target):
    # Only allow same-site relative paths, so /login?next= can't bounce users elsewhere.
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("clinic_directory")


def current_user():
    return session.get("user")


def init_auth(app):
    secret = os.environ.get("SECRET_KEY")
    if secret:
        app.secret_key = secret
    elif not _on_vercel():
        app.secret_key = "dev-only-not-for-production"

    app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(hours=12)
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SECURE"] = _on_vercel()

    if _on_vercel():
        # Vercel terminates TLS in front of the app; trust its forwarded headers
        # so the OAuth redirect URL is built with the real https host.
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=os.environ.get("GOOGLE_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    @app.context_processor
    def inject_user():
        return {"current_user": current_user()}

    @app.before_request
    def require_login():
        if request.endpoint in _PUBLIC_ENDPOINTS:
            if _on_vercel() and not (secret and _configured()):
                return _config_error()
            return None
        if _on_vercel() and not (secret and _configured()):
            return _config_error()
        if not _configured():
            return None  # local development without Google credentials
        if not current_user():
            return redirect(url_for("login", next=request.full_path.rstrip("?")))
        return None

    @app.route("/login")
    def login():
        if current_user():
            return redirect(_safe_next(request.args.get("next")))
        return render_template(
            "login.html",
            next=_safe_next(request.args.get("next")),
            domain=ALLOWED_DOMAIN,
            error=request.args.get("error"),
        )

    @app.route("/login/google")
    def login_google():
        session["login_next"] = _safe_next(request.args.get("next"))
        redirect_uri = url_for("auth_callback", _external=True)
        # hd narrows Google's account picker to the company domain; it's only a
        # hint, so the callback re-checks the domain itself.
        return oauth.google.authorize_redirect(redirect_uri, hd=ALLOWED_DOMAIN, prompt="select_account")

    @app.route("/auth/callback")
    def auth_callback():
        try:
            token = oauth.google.authorize_access_token()
        except Exception:
            return redirect(url_for("login", error="Sign-in failed. Please try again."))

        info = token.get("userinfo") or {}
        email = (info.get("email") or "").lower()
        if (
            not info.get("email_verified")
            or not email.endswith("@" + ALLOWED_DOMAIN)
            or info.get("hd") != ALLOWED_DOMAIN
        ):
            session.clear()
            return redirect(url_for("login", error=f"Please sign in with your @{ALLOWED_DOMAIN} account."))

        next_url = session.pop("login_next", None)
        session.clear()
        session.permanent = True
        session["user"] = {"email": email, "name": info.get("name") or email}
        return redirect(_safe_next(next_url))

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))


def _config_error():
    return (
        "Sign-in isn't configured for this deployment yet "
        "(SECRET_KEY, GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required).",
        503,
    )
