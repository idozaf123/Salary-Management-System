#!/usr/bin/env python3
"""
Demo script to populate the Payroll Management System with sample data

Run this after starting the application to see it in action with realistic data.
"""

from datetime import date, time, timedelta
from decimal import Decimal

from app.database import Database
from app.payroll_engine import PayrollEngine
from app.models import User, EmploymentProfile, WorkShift, Deduction, Bonus


def create_sample_data():
    """Create sample users, profiles, shifts, and payroll data"""

    print("Creating sample data for Payroll Management System...\n")

    # Initialize database and engine
    db = Database("payroll.db")
    engine = PayrollEngine(db)

    # ========== USER 1: Hourly Employee with Regular Shifts ==========
    print("Creating User 1: Hourly Employee...")
    user1 = db.create_user(User(
        username="jsmith",
        email="jsmith@company.com",
        full_name="Jane Smith"
    ))

    profile1 = db.create_employment_profile(EmploymentProfile(
        user_id=user1.id,
        employment_type="hourly",
        base_rate=Decimal("35.00"),
        job_title="Senior Developer",
        department="Engineering",
        standard_hours_per_week=Decimal("40.0"),
        overtime_threshold_daily=Decimal("8.0"),
        overtime_threshold_weekly=Decimal("40.0"),
        overtime_multiplier=Decimal("1.5"),
        start_date=date(2024, 1, 1)
    ))

    # Add deductions
    db.create_deduction(Deduction(
        user_id=user1.id,
        deduction_type="tax",
        name="Federal Income Tax",
        is_percentage=True,
        amount=Decimal("20.0")
    ))

    db.create_deduction(Deduction(
        user_id=user1.id,
        deduction_type="insurance",
        name="Health Insurance",
        is_percentage=False,
        amount=Decimal("150.00")
    ))

    # Add 5 days of work
    start_date = date(2025, 1, 13)
    for day in range(5):
        shift_date = start_date + timedelta(days=day)
        shift = WorkShift(
            user_id=user1.id,
            employment_profile_id=profile1.id,
            shift_date=shift_date,
            start_time=time(9, 0),
            end_time=time(17, 0),
            shift_type="regular"
        )
        processed = engine.process_shift(shift)
        db.create_work_shift(processed)

    # Calculate payroll
    period1 = engine.auto_calculate_and_save_period(
        user1.id,
        date(2025, 1, 13),
        date(2025, 1, 17)
    )

    print(f"  ✓ Created {user1.full_name}")
    print(f"    Position: {profile1.job_title}")
    print(f"    Rate: ${profile1.base_rate}/hour")
    print(f"    Shifts added: 5")
    print(f"    Payroll calculated: ${period1.net_pay} net pay\n")

    # ========== USER 2: Night Shift Worker ==========
    print("Creating User 2: Night Shift Worker...")
    user2 = db.create_user(User(
        username="mjohnson",
        email="mjohnson@company.com",
        full_name="Mike Johnson"
    ))

    profile2 = db.create_employment_profile(EmploymentProfile(
        user_id=user2.id,
        employment_type="hourly",
        base_rate=Decimal("28.00"),
        job_title="Operations Specialist",
        department="Operations",
        night_shift_multiplier=Decimal("1.30"),
        overtime_threshold_weekly=Decimal("40.0"),
        overtime_multiplier=Decimal("1.5"),
        start_date=date(2024, 6, 1)
    ))

    # Add tax deduction
    db.create_deduction(Deduction(
        user_id=user2.id,
        deduction_type="tax",
        name="Federal Tax",
        is_percentage=True,
        amount=Decimal("18.0")
    ))

    # Add night shifts
    for day in range(4):
        shift_date = start_date + timedelta(days=day)
        shift = WorkShift(
            user_id=user2.id,
            employment_profile_id=profile2.id,
            shift_date=shift_date,
            start_time=time(22, 0),
            end_time=time(6, 0),
            shift_type="night"
        )
        processed = engine.process_shift(shift)
        db.create_work_shift(processed)

    # Add bonus
    db.create_bonus(Bonus(
        user_id=user2.id,
        bonus_type="performance",
        amount=Decimal("500.00"),
        description="Night shift reliability bonus",
        bonus_date=date(2025, 1, 15)
    ))

    period2 = engine.auto_calculate_and_save_period(
        user2.id,
        date(2025, 1, 13),
        date(2025, 1, 16)
    )

    print(f"  ✓ Created {user2.full_name}")
    print(f"    Position: {profile2.job_title}")
    print(f"    Rate: ${profile2.base_rate}/hour (night shift: 1.3x)")
    print(f"    Shifts added: 4 night shifts")
    print(f"    Bonus: $500.00")
    print(f"    Payroll calculated: ${period2.net_pay} net pay\n")

    # ========== USER 3: Part-time Weekend Worker ==========
    print("Creating User 3: Part-time Weekend Worker...")
    user3 = db.create_user(User(
        username="alee",
        email="alee@company.com",
        full_name="Alice Lee"
    ))

    profile3 = db.create_employment_profile(EmploymentProfile(
        user_id=user3.id,
        employment_type="hourly",
        base_rate=Decimal("22.00"),
        job_title="Weekend Support",
        department="Customer Service",
        weekend_multiplier=Decimal("1.6"),
        start_date=date(2024, 9, 1)
    ))

    # Add weekend shifts
    weekend_dates = [date(2025, 1, 18), date(2025, 1, 19)]  # Saturday, Sunday
    for shift_date in weekend_dates:
        shift = WorkShift(
            user_id=user3.id,
            employment_profile_id=profile3.id,
            shift_date=shift_date,
            start_time=time(10, 0),
            end_time=time(18, 0),
            shift_type="weekend"
        )
        processed = engine.process_shift(shift)
        db.create_work_shift(processed)

    period3 = engine.auto_calculate_and_save_period(
        user3.id,
        date(2025, 1, 18),
        date(2025, 1, 19)
    )

    print(f"  ✓ Created {user3.full_name}")
    print(f"    Position: {profile3.job_title}")
    print(f"    Rate: ${profile3.base_rate}/hour (weekend: 1.6x)")
    print(f"    Shifts added: 2 weekend shifts")
    print(f"    Payroll calculated: ${period3.net_pay} net pay\n")

    # ========== USER 4: Salaried Manager ==========
    print("Creating User 4: Salaried Manager...")
    user4 = db.create_user(User(
        username="rbrown",
        email="rbrown@company.com",
        full_name="Robert Brown"
    ))

    profile4 = db.create_employment_profile(EmploymentProfile(
        user_id=user4.id,
        employment_type="salaried",
        base_rate=Decimal("78000.00"),  # Annual salary
        job_title="Engineering Manager",
        department="Engineering",
        standard_hours_per_week=Decimal("40.0"),
        start_date=date(2023, 3, 1)
    ))

    # Add deductions
    db.create_deduction(Deduction(
        user_id=user4.id,
        deduction_type="tax",
        name="Federal Tax",
        is_percentage=True,
        amount=Decimal("25.0")
    ))

    db.create_deduction(Deduction(
        user_id=user4.id,
        deduction_type="retirement",
        name="401(k) Contribution",
        is_percentage=True,
        amount=Decimal("6.0")
    ))

    # Add regular work week
    for day in range(5):
        shift_date = start_date + timedelta(days=day)
        shift = WorkShift(
            user_id=user4.id,
            employment_profile_id=profile4.id,
            shift_date=shift_date,
            start_time=time(8, 30),
            end_time=time(17, 30),
            shift_type="regular"
        )
        processed = engine.process_shift(shift)
        db.create_work_shift(processed)

    period4 = engine.auto_calculate_and_save_period(
        user4.id,
        date(2025, 1, 13),
        date(2025, 1, 17)
    )

    print(f"  ✓ Created {user4.full_name}")
    print(f"    Position: {profile4.job_title}")
    print(f"    Salary: ${profile4.base_rate}/year")
    print(f"    Shifts added: 5")
    print(f"    Payroll calculated: ${period4.net_pay} net pay\n")

    # ========== SUMMARY ==========
    print("="*60)
    print("SAMPLE DATA CREATION COMPLETE")
    print("="*60)
    print(f"Total Users Created: 4")
    print(f"Total Shifts Created: {5 + 4 + 2 + 5}")
    print(f"Total Payroll Periods: 4")
    print("\nYou can now:")
    print("  1. Visit http://localhost:5000 to see the web interface")
    print("  2. Access the API at http://localhost:5000/api/users")
    print("  3. View individual user dashboards")
    print("  4. Add more shifts and calculate payroll")
    print("="*60)


if __name__ == "__main__":
    create_sample_data()
