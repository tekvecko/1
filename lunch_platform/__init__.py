
from __future__ import annotations


def create_app(test_config: dict | None = None):
    from pathlib import Path
    from flask import Flask

    from .core.config import Config
    from .core.db import init_app as init_db_app
    from .core.security import init_security
    from .core.auth import init_auth
    from .auth.routes import bp as auth_bp
    from .orders.routes import bp as orders_bp
    from .admin.routes import bp as admin_bp
    from .billing.routes import bp as billing_bp
    from .delivery.routes import bp as delivery_bp
    from .imports.routes import bp as imports_bp
    from .restaurants.runtime import init_restaurants

    base_dir = Path(__file__).resolve().parent
    app = Flask(
        __name__,
        instance_path=str(base_dir.parent / "instance"),
        template_folder=str(base_dir / "templates"),
        static_folder=str(base_dir / "static"),
        instance_relative_config=False,
    )
    app.config.from_object(Config())
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["LOG_FOLDER"]).mkdir(parents=True, exist_ok=True)

    init_security(app)
    init_db_app(app)
    init_auth(app)
    init_restaurants(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(delivery_bp)
    app.register_blueprint(imports_bp)


    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "app": "final-lunch"}, 200

    @app.get("/db-healthz")
    def db_healthz():
        from .core.db import db_kind, query, table_columns

        required_tables = [
            "settings",
            "accounts",
            "users",
            "restaurants",
            "menu",
            "orders",
            "ratings",
            "audit_log",
            "notifications",
        ]

        result = {
            "status": "ok",
            "app": "final-lunch",
            "db_kind": db_kind(),
            "tables": {},
        }

        try:
            for table in required_tables:
                cols = sorted(table_columns(table))
                result["tables"][table] = {
                    "ok": True,
                    "columns": len(cols),
                }

            admin = query(
                "SELECT id, username, role, is_active FROM accounts WHERE username=?",
                ("admin",),
                one=True,
            )

            result["admin_exists"] = bool(admin)
            result["admin_role"] = admin["role"] if admin else None
            result["admin_active"] = bool(admin["is_active"]) if admin else False

            return result, 200

        except Exception as exc:
            result["status"] = "error"
            result["error_type"] = exc.__class__.__name__
            result["error"] = str(exc)
            return result, 500

    return app
