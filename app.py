import os
import secrets

import click
from flask import Flask, abort, render_template, request, session
from flask_login import LoginManager

from config import Config
from models import STATUSES, User, db

login_manager = LoginManager()


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    # Local MySQL/XAMPP has no TLS. Skipping it also avoids a Windows certificate-store crash in PyMySQL.
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("mysql"):
        opts = dict(app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {}))
        opts["connect_args"] = {"ssl_disabled": os.environ.get("MYSQL_SSL", "0") != "1"}
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = opts

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "main.login"
    login_manager.login_message = "Please log in to continue."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # --- lightweight CSRF protection for every POST (form field or X-CSRF-Token header) ---
    def csrf_token():
        if "_csrf" not in session:
            session["_csrf"] = secrets.token_hex(16)
        return session["_csrf"]

    @app.before_request
    def verify_csrf():
        if request.method == "POST":
            sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
            if not sent or not secrets.compare_digest(sent, session.get("_csrf", "")):
                abort(400, "Your form expired. Go back, refresh the page and try again.")

    app.jinja_env.globals["csrf_token"] = csrf_token
    app.jinja_env.globals["STATUSES"] = STATUSES

    from routes import bp
    app.register_blueprint(bp)

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    def http_error(e):
        return render_template("error.html", error=e), e.code

    @app.cli.command("init-db")
    def init_db():
        """Create all tables."""
        db.create_all()
        click.echo("Tables created.")

    @app.cli.command("seed")
    def seed_cmd():
        """Create tables and load demo data."""
        from seed import seed
        seed()
        click.echo("Demo data loaded.")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
