from functools import wraps

from werkzeug.security import check_password_hash, generate_password_hash
from flask import session, redirect, url_for, flash


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("signin"))
        return view(*args, **kwargs)

    return wrapped

