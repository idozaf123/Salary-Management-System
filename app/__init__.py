"""
Payroll Management System - Flask Application Factory
"""

from flask import Flask
from app.database import Database
from app.payroll_engine import PayrollEngine


def create_app(db_path: str = "payroll.db"):
    """Create and configure Flask application"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-key-change-in-production"
    app.config["DATABASE_PATH"] = db_path

    # Initialize database and payroll engine
    db = Database(db_path)
    engine = PayrollEngine(db)

    # Store in app context
    app.db = db
    app.engine = engine

    # Register routes
    from app.routes import register_routes
    register_routes(app)

    return app
