"""
Payroll Management System - Flask Application Factory
"""

import os
from flask import Flask
from app.database import Database
from app.payroll_engine import PayrollEngine


def create_app(db_path: str = "payroll.db"):
    """Create and configure Flask application"""
    # Get the base directory (project root)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    static_dir = os.path.join(base_dir, 'static')

    app = Flask(__name__,
                static_folder=static_dir,
                static_url_path='/static',
                template_folder='templates')
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
