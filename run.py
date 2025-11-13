#!/usr/bin/env python3
"""
Payroll Management System - Application Entry Point

Usage:
    python run.py              # Run in development mode
    python run.py --port 5001  # Run on custom port
"""

import argparse
from app import create_app


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(description="Payroll Management System")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind to (default: 5000)")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    parser.add_argument("--db", default="payroll.db", help="Database file path (default: payroll.db)")

    args = parser.parse_args()

    # Create Flask app
    app = create_app(db_path=args.db)

    print(f"""
╔══════════════════════════════════════════════════╗
║   Payroll Management System                      ║
║   Version 1.0.0                                  ║
╚══════════════════════════════════════════════════╝

Server starting...
  URL: http://{args.host}:{args.port}
  Database: {args.db}
  Debug mode: {args.debug}

Press Ctrl+C to stop
""")

    # Run application
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug
    )


if __name__ == "__main__":
    main()
