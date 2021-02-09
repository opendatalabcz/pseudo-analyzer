from flask import (Flask, after_this_request, g, redirect, render_template,
                   request)
from flask_babel import Babel
from flask_bootstrap import Bootstrap
from flask_wtf.csrf import CSRFProtect

from psan import celery, db


def build_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    # Configs
    # Load the default configuration
    app.config.from_object("config.default")
    # Load the configuration from the instance folder
    app.config.from_pyfile('config.py', silent=True)
    # Load config according to run environment
    # Variables defined here will override those in the default configuration
    if app.debug:
        app.config.from_object("config.debug")
    else:
        app.config.from_object("config.production")

    celery.init_celery(app)
    db.init_app(app)

    # Bootstrap
    Bootstrap(app)
    init_translations(app)

    # CSRF protection
    csrf = CSRFProtect()
    csrf.init_app(app)

    @app.route("/")
    def index():
        return render_template("index.html")

    # Redirection
    app.add_url_rule("/", endpoint="index")

    # apply the blueprints to the app
    from psan import auth
    app.register_blueprint(auth.bp)
    from psan import account
    app.register_blueprint(account.bp)
    from psan import submission
    app.register_blueprint(submission.bp)
    from psan import annotate
    app.register_blueprint(annotate.bp)
    from psan import rule
    app.register_blueprint(rule.bp)

    return app


def init_translations(app: Flask) -> None:
    """
    Enable babel for `_(str)` method, language detection and sets "page" for lang switching
    """
    babel = Babel(app)

    @app.before_request
    def detect_user_language():
        # Check user language preference form cookie
        language = request.cookies.get('lang')

        if language is None:
            # Try autodetect language
            g.lang = request.accept_languages.best_match(["en", "cs"], default="en")

            # Save detected value as a cookie
            @after_this_request
            def remember_language(response):
                response.set_cookie('lang', g.lang)
                return response
        else:
            if language in ["cs", "en"]:
                g.lang = language
            else:
                raise NotImplementedError()

    @app.route("/translate")
    def switch_lang():
        """
        Switch lang from `en` to `cs` and vice versa
        """
        if g.lang == "cs":
            g.lang = "en"
        else:
            g.lang = "cs"

        # Save updated value to cookie
        response = redirect(request.referrer)
        response.set_cookie('lang', g.lang)
        return response

    @babel.localeselector
    def get_locale():
        return g.lang


app = build_app()
