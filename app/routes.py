"""
Flask routes for Payroll Management System

Provides both web UI and JSON API endpoints.
"""

from flask import render_template, request, jsonify, redirect, url_for, current_app
from datetime import datetime, date, time
from decimal import Decimal
import json

from app.models import (
    User, EmploymentProfile, WorkShift, Deduction, Bonus, PayrollPeriod
)


def register_routes(app):
    """Register all application routes"""

    # ============== WEB UI ROUTES ==============

    @app.route("/")
    def index():
        """Main dashboard"""
        users = app.db.get_all_users()
        return render_template("index.html", users=users)

    @app.route("/user/<int:user_id>")
    def user_dashboard(user_id):
        """User-specific dashboard"""
        user = app.db.get_user(user_id)
        if not user:
            return "User not found", 404

        profile = app.db.get_active_profile_for_user(user_id)
        recent_shifts = app.db.get_shifts_for_user(user_id)[:10]
        payroll_summary = app.engine.get_payroll_summary(user_id, num_periods=6)

        return render_template(
            "user_dashboard.html",
            user=user,
            profile=profile,
            recent_shifts=recent_shifts,
            payroll_summary=payroll_summary
        )

    @app.route("/user/<int:user_id>/profile", methods=["GET", "POST"])
    def employment_profile(user_id):
        """Manage employment profile"""
        user = app.db.get_user(user_id)
        if not user:
            return "User not found", 404

        if request.method == "POST":
            # Create or update employment profile
            profile = EmploymentProfile(
                user_id=user_id,
                employment_type=request.form["employment_type"],
                base_rate=Decimal(request.form["base_rate"]),
                currency=request.form.get("currency", "USD"),
                standard_hours_per_week=Decimal(request.form.get("standard_hours_per_week", "40")),
                overtime_threshold_daily=Decimal(request.form.get("overtime_threshold_daily", "8")),
                overtime_threshold_weekly=Decimal(request.form.get("overtime_threshold_weekly", "40")),
                overtime_multiplier=Decimal(request.form.get("overtime_multiplier", "1.5")),
                night_shift_multiplier=Decimal(request.form.get("night_shift_multiplier", "1.25")),
                weekend_multiplier=Decimal(request.form.get("weekend_multiplier", "1.5")),
                job_title=request.form.get("job_title", ""),
                department=request.form.get("department", ""),
                start_date=datetime.strptime(request.form["start_date"], "%Y-%m-%d").date(),
                is_active=True
            )
            app.db.create_employment_profile(profile)
            return redirect(url_for("user_dashboard", user_id=user_id))

        profile = app.db.get_active_profile_for_user(user_id)
        return render_template("profile.html", user=user, profile=profile)

    @app.route("/user/<int:user_id>/shifts", methods=["GET", "POST"])
    def shifts(user_id):
        """Manage work shifts"""
        user = app.db.get_user(user_id)
        if not user:
            return "User not found", 404

        profile = app.db.get_active_profile_for_user(user_id)
        if not profile:
            return "No active employment profile. Please create one first.", 400

        if request.method == "POST":
            # Create new shift
            shift = WorkShift(
                user_id=user_id,
                employment_profile_id=profile.id,
                shift_date=datetime.strptime(request.form["shift_date"], "%Y-%m-%d").date(),
                start_time=datetime.strptime(request.form["start_time"], "%H:%M").time(),
                end_time=datetime.strptime(request.form["end_time"], "%H:%M").time(),
                shift_type=request.form.get("shift_type", "regular"),
                notes=request.form.get("notes", "")
            )

            # Process shift to calculate pay
            shift = app.engine.process_shift(shift)

            # Save to database
            app.db.create_work_shift(shift)

            return redirect(url_for("shifts", user_id=user_id))

        # Get shifts
        all_shifts = app.db.get_shifts_for_user(user_id)
        return render_template("shifts.html", user=user, shifts=all_shifts, profile=profile)

    @app.route("/user/<int:user_id>/payroll")
    def payroll_reports(user_id):
        """View payroll reports"""
        user = app.db.get_user(user_id)
        if not user:
            return "User not found", 404

        periods = app.db.get_payroll_periods_for_user(user_id)
        deductions = app.db.get_active_deductions_for_user(user_id)

        return render_template(
            "payroll.html",
            user=user,
            periods=periods,
            deductions=deductions
        )

    # ============== JSON API ROUTES ==============

    @app.route("/api/users", methods=["GET", "POST"])
    def api_users():
        """Get all users or create new user"""
        if request.method == "POST":
            data = request.json
            user = User(
                username=data["username"],
                email=data["email"],
                full_name=data["full_name"]
            )
            user = app.db.create_user(user)
            return jsonify({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name
            }), 201

        users = app.db.get_all_users()
        return jsonify([
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "full_name": u.full_name
            }
            for u in users
        ])

    @app.route("/api/user/<int:user_id>", methods=["GET"])
    def api_user(user_id):
        """Get user by ID"""
        user = app.db.get_user(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name
        })

    @app.route("/api/user/<int:user_id>/profile", methods=["GET", "POST"])
    def api_employment_profile(user_id):
        """Get or create employment profile"""
        if request.method == "POST":
            data = request.json
            profile = EmploymentProfile(
                user_id=user_id,
                employment_type=data["employment_type"],
                base_rate=Decimal(str(data["base_rate"])),
                currency=data.get("currency", "USD"),
                standard_hours_per_week=Decimal(str(data.get("standard_hours_per_week", 40))),
                overtime_threshold_daily=Decimal(str(data.get("overtime_threshold_daily", 8))),
                overtime_threshold_weekly=Decimal(str(data.get("overtime_threshold_weekly", 40))),
                overtime_multiplier=Decimal(str(data.get("overtime_multiplier", 1.5))),
                night_shift_multiplier=Decimal(str(data.get("night_shift_multiplier", 1.25))),
                weekend_multiplier=Decimal(str(data.get("weekend_multiplier", 1.5))),
                job_title=data.get("job_title", ""),
                department=data.get("department", ""),
                start_date=datetime.strptime(data["start_date"], "%Y-%m-%d").date(),
                is_active=True
            )
            profile = app.db.create_employment_profile(profile)
            return jsonify({"id": profile.id, "message": "Profile created"}), 201

        profile = app.db.get_active_profile_for_user(user_id)
        if not profile:
            return jsonify({"error": "No active profile found"}), 404

        return jsonify({
            "id": profile.id,
            "user_id": profile.user_id,
            "employment_type": profile.employment_type,
            "base_rate": float(profile.base_rate),
            "currency": profile.currency,
            "standard_hours_per_week": float(profile.standard_hours_per_week),
            "overtime_threshold_daily": float(profile.overtime_threshold_daily) if profile.overtime_threshold_daily else None,
            "overtime_threshold_weekly": float(profile.overtime_threshold_weekly) if profile.overtime_threshold_weekly else None,
            "overtime_multiplier": float(profile.overtime_multiplier),
            "night_shift_multiplier": float(profile.night_shift_multiplier),
            "weekend_multiplier": float(profile.weekend_multiplier),
            "job_title": profile.job_title,
            "department": profile.department,
            "is_active": profile.is_active
        })

    @app.route("/api/user/<int:user_id>/shifts", methods=["GET", "POST"])
    def api_shifts(user_id):
        """Get all shifts or create new shift"""
        if request.method == "POST":
            data = request.json
            profile = app.db.get_active_profile_for_user(user_id)
            if not profile:
                return jsonify({"error": "No active employment profile"}), 400

            shift = WorkShift(
                user_id=user_id,
                employment_profile_id=profile.id,
                shift_date=datetime.strptime(data["shift_date"], "%Y-%m-%d").date(),
                start_time=datetime.strptime(data["start_time"], "%H:%M").time(),
                end_time=datetime.strptime(data["end_time"], "%H:%M").time(),
                shift_type=data.get("shift_type", "regular"),
                notes=data.get("notes", "")
            )

            # Process and save
            shift = app.engine.process_shift(shift)
            shift = app.db.create_work_shift(shift)

            return jsonify({
                "id": shift.id,
                "hours_worked": float(shift.hours_worked),
                "hourly_rate": float(shift.hourly_rate),
                "total_pay": float(shift.total_pay)
            }), 201

        # Get shifts with optional date filtering
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        if start_date and end_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            shifts = app.db.get_shifts_for_user(user_id, start, end)
        else:
            shifts = app.db.get_shifts_for_user(user_id)

        return jsonify([
            {
                "id": s.id,
                "shift_date": s.shift_date.isoformat(),
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat(),
                "shift_type": s.shift_type,
                "is_overtime": s.is_overtime,
                "hours_worked": float(s.hours_worked) if s.hours_worked else None,
                "hourly_rate": float(s.hourly_rate) if s.hourly_rate else None,
                "total_pay": float(s.total_pay) if s.total_pay else None,
                "notes": s.notes
            }
            for s in shifts
        ])

    @app.route("/api/user/<int:user_id>/deductions", methods=["GET", "POST"])
    def api_deductions(user_id):
        """Get deductions or create new deduction"""
        if request.method == "POST":
            data = request.json
            deduction = Deduction(
                user_id=user_id,
                deduction_type=data["deduction_type"],
                name=data["name"],
                is_percentage=data.get("is_percentage", True),
                amount=Decimal(str(data["amount"])),
                applies_to_overtime=data.get("applies_to_overtime", True),
                is_active=True
            )
            deduction = app.db.create_deduction(deduction)
            return jsonify({"id": deduction.id, "message": "Deduction created"}), 201

        deductions = app.db.get_active_deductions_for_user(user_id)
        return jsonify([
            {
                "id": d.id,
                "deduction_type": d.deduction_type,
                "name": d.name,
                "is_percentage": d.is_percentage,
                "amount": float(d.amount),
                "applies_to_overtime": d.applies_to_overtime
            }
            for d in deductions
        ])

    @app.route("/api/user/<int:user_id>/bonuses", methods=["POST"])
    def api_create_bonus(user_id):
        """Create bonus"""
        data = request.json
        bonus = Bonus(
            user_id=user_id,
            bonus_type=data["bonus_type"],
            amount=Decimal(str(data["amount"])),
            description=data.get("description", ""),
            bonus_date=datetime.strptime(data["bonus_date"], "%Y-%m-%d").date(),
            is_taxable=data.get("is_taxable", True)
        )
        bonus = app.db.create_bonus(bonus)
        return jsonify({"id": bonus.id, "message": "Bonus created"}), 201

    @app.route("/api/user/<int:user_id>/payroll/calculate", methods=["POST"])
    def api_calculate_payroll(user_id):
        """Calculate payroll for a period"""
        data = request.json
        start_date = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
        end_date = datetime.strptime(data["end_date"], "%Y-%m-%d").date()

        save = data.get("save", False)

        if save:
            period = app.engine.auto_calculate_and_save_period(user_id, start_date, end_date)
        else:
            period = app.engine.calculate_payroll_period(user_id, start_date, end_date)

        return jsonify({
            "id": period.id if save else None,
            "period_start": period.period_start.isoformat(),
            "period_end": period.period_end.isoformat(),
            "total_hours_regular": float(period.total_hours_regular),
            "total_hours_overtime": float(period.total_hours_overtime),
            "gross_pay_regular": float(period.gross_pay_regular),
            "gross_pay_overtime": float(period.gross_pay_overtime),
            "gross_pay_total": float(period.gross_pay_total),
            "total_bonuses": float(period.total_bonuses),
            "total_deductions": float(period.total_deductions),
            "net_pay": float(period.net_pay),
            "shift_count": period.shift_count
        })

    @app.route("/api/user/<int:user_id>/payroll/summary")
    def api_payroll_summary(user_id):
        """Get payroll summary"""
        num_periods = int(request.args.get("num_periods", 6))
        summary = app.engine.get_payroll_summary(user_id, num_periods)
        return jsonify(summary)

    @app.route("/api/user/<int:user_id>/payroll/periods")
    def api_payroll_periods(user_id):
        """Get all payroll periods"""
        periods = app.db.get_payroll_periods_for_user(user_id)
        return jsonify([
            {
                "id": p.id,
                "period_start": p.period_start.isoformat(),
                "period_end": p.period_end.isoformat(),
                "gross_pay_total": float(p.gross_pay_total),
                "net_pay": float(p.net_pay),
                "shift_count": p.shift_count,
                "is_finalized": p.is_finalized
            }
            for p in periods
        ])

    # ============== HEALTH CHECK ==============

    @app.route("/health")
    def health():
        """Health check endpoint"""
        return jsonify({"status": "healthy", "message": "Payroll Management System is running"})
