"""
Comprehensive tests for Payroll Management System

Tests all core functionality with realistic scenarios.
"""

import pytest
from datetime import date, time, timedelta
from decimal import Decimal

from app.models import User, EmploymentProfile, WorkShift, Deduction, Bonus
from app.database import Database
from app.payroll_engine import PayrollEngine


@pytest.fixture
def db():
    """Create in-memory database for testing"""
    database = Database(":memory:")
    return database


@pytest.fixture
def engine(db):
    """Create payroll engine"""
    return PayrollEngine(db)


def test_user_creation(db):
    """Test creating and retrieving users"""
    user = User(
        username="jdoe",
        email="jdoe@example.com",
        full_name="John Doe"
    )

    created = db.create_user(user)
    assert created.id is not None

    retrieved = db.get_user(created.id)
    assert retrieved.username == "jdoe"
    assert retrieved.email == "jdoe@example.com"


def test_hourly_employment_profile(db):
    """Test creating hourly employment profile"""
    user = db.create_user(User(username="worker1", email="w1@test.com", full_name="Worker One"))

    profile = EmploymentProfile(
        user_id=user.id,
        employment_type="hourly",
        base_rate=Decimal("25.00"),
        overtime_threshold_daily=Decimal("8.0"),
        overtime_threshold_weekly=Decimal("40.0"),
        overtime_multiplier=Decimal("1.5"),
        job_title="Software Engineer",
        department="Engineering"
    )

    created = db.create_employment_profile(profile)
    assert created.id is not None

    retrieved = db.get_active_profile_for_user(user.id)
    assert retrieved.base_rate == Decimal("25.00")
    assert retrieved.employment_type == "hourly"


def test_shift_calculation_regular(db, engine):
    """Test regular shift pay calculation"""
    # Create user and profile
    user = db.create_user(User(username="worker2", email="w2@test.com", full_name="Worker Two"))
    profile = db.create_employment_profile(EmploymentProfile(
        user_id=user.id,
        employment_type="hourly",
        base_rate=Decimal("20.00")
    ))

    # Create 8-hour regular shift
    shift = WorkShift(
        user_id=user.id,
        employment_profile_id=profile.id,
        shift_date=date(2025, 1, 15),
        start_time=time(9, 0),
        end_time=time(17, 0),
        shift_type="regular"
    )

    processed = engine.process_shift(shift)

    assert processed.hours_worked == Decimal("8.00")
    assert processed.hourly_rate == Decimal("20.00")
    assert processed.total_pay == Decimal("160.00")


def test_shift_calculation_night_shift(db, engine):
    """Test night shift with multiplier"""
    user = db.create_user(User(username="worker3", email="w3@test.com", full_name="Worker Three"))
    profile = db.create_employment_profile(EmploymentProfile(
        user_id=user.id,
        employment_type="hourly",
        base_rate=Decimal("20.00"),
        night_shift_multiplier=Decimal("1.25")
    ))

    shift = WorkShift(
        user_id=user.id,
        employment_profile_id=profile.id,
        shift_date=date(2025, 1, 15),
        start_time=time(22, 0),
        end_time=time(6, 0),  # Next morning
        shift_type="night"
    )

    processed = engine.process_shift(shift)

    assert processed.hours_worked == Decimal("8.00")
    assert processed.hourly_rate == Decimal("25.00")  # 20 * 1.25
    assert processed.total_pay == Decimal("200.00")


def test_overtime_calculation_daily(db, engine):
    """Test daily overtime threshold"""
    user = db.create_user(User(username="worker4", email="w4@test.com", full_name="Worker Four"))
    profile = db.create_employment_profile(EmploymentProfile(
        user_id=user.id,
        employment_type="hourly",
        base_rate=Decimal("20.00"),
        overtime_threshold_daily=Decimal("8.0"),
        overtime_multiplier=Decimal("1.5")
    ))

    # Create 10-hour shift (2 hours overtime)
    shift = WorkShift(
        user_id=user.id,
        employment_profile_id=profile.id,
        shift_date=date(2025, 1, 15),
        start_time=time(9, 0),
        end_time=time(19, 0),
        shift_type="regular",
        is_overtime=True
    )

    processed = engine.process_shift(shift)

    # With OT flag, entire shift gets overtime rate
    assert processed.hours_worked == Decimal("10.00")
    assert processed.hourly_rate == Decimal("30.00")  # 20 * 1.5
    assert processed.total_pay == Decimal("300.00")


def test_payroll_period_calculation(db, engine):
    """Test complete payroll period calculation"""
    # Setup user and profile
    user = db.create_user(User(username="worker5", email="w5@test.com", full_name="Worker Five"))
    profile = db.create_employment_profile(EmploymentProfile(
        user_id=user.id,
        employment_type="hourly",
        base_rate=Decimal("25.00"),
        overtime_threshold_weekly=Decimal("40.0"),
        overtime_multiplier=Decimal("1.5")
    ))

    # Add multiple shifts
    shifts_data = [
        (date(2025, 1, 13), time(9, 0), time(17, 0)),  # Monday, 8 hours
        (date(2025, 1, 14), time(9, 0), time(17, 0)),  # Tuesday, 8 hours
        (date(2025, 1, 15), time(9, 0), time(17, 0)),  # Wednesday, 8 hours
        (date(2025, 1, 16), time(9, 0), time(17, 0)),  # Thursday, 8 hours
        (date(2025, 1, 17), time(9, 0), time(17, 0)),  # Friday, 8 hours
    ]

    for shift_date, start, end in shifts_data:
        shift = WorkShift(
            user_id=user.id,
            employment_profile_id=profile.id,
            shift_date=shift_date,
            start_time=start,
            end_time=end,
            shift_type="regular"
        )
        processed = engine.process_shift(shift)
        db.create_work_shift(processed)

    # Calculate payroll period
    period = engine.calculate_payroll_period(
        user.id,
        date(2025, 1, 13),
        date(2025, 1, 17)
    )

    assert period.shift_count == 5
    assert period.total_hours_regular == Decimal("40.00")
    assert period.gross_pay_total == Decimal("1000.00")  # 40 * 25


def test_deduction_calculation(db):
    """Test deduction calculations"""
    user = db.create_user(User(username="worker6", email="w6@test.com", full_name="Worker Six"))

    # Create percentage deduction (15% tax)
    tax = Deduction(
        user_id=user.id,
        deduction_type="tax",
        name="Federal Tax",
        is_percentage=True,
        amount=Decimal("15.0")
    )

    gross = Decimal("1000.00")
    tax_amount = tax.calculate(gross)
    assert tax_amount == Decimal("150.00")

    # Create fixed deduction
    insurance = Deduction(
        user_id=user.id,
        deduction_type="insurance",
        name="Health Insurance",
        is_percentage=False,
        amount=Decimal("50.00")
    )

    insurance_amount = insurance.calculate(gross)
    assert insurance_amount == Decimal("50.00")


def test_bonus_application(db, engine):
    """Test bonus in payroll calculation"""
    user = db.create_user(User(username="worker7", email="w7@test.com", full_name="Worker Seven"))
    profile = db.create_employment_profile(EmploymentProfile(
        user_id=user.id,
        employment_type="hourly",
        base_rate=Decimal("30.00")
    ))

    # Add shift
    shift = WorkShift(
        user_id=user.id,
        employment_profile_id=profile.id,
        shift_date=date(2025, 1, 15),
        start_time=time(9, 0),
        end_time=time(17, 0)
    )
    processed = engine.process_shift(shift)
    db.create_work_shift(processed)

    # Add bonus
    bonus = Bonus(
        user_id=user.id,
        bonus_type="performance",
        amount=Decimal("500.00"),
        description="Q1 Performance Bonus",
        bonus_date=date(2025, 1, 15)
    )
    db.create_bonus(bonus)

    # Calculate payroll
    period = engine.calculate_payroll_period(
        user.id,
        date(2025, 1, 15),
        date(2025, 1, 15)
    )

    assert period.gross_pay_total == Decimal("240.00")  # 8 * 30
    assert period.total_bonuses == Decimal("500.00")
    assert period.net_pay == Decimal("740.00")  # 240 + 500


def test_complete_scenario_with_deductions(db, engine):
    """
    COMPREHENSIVE TEST SCENARIO:
    Employee works 5 days, 8 hours each, with tax deduction
    """
    # Create employee
    user = db.create_user(User(
        username="jsmith",
        email="jsmith@company.com",
        full_name="Jane Smith"
    ))

    # Create employment profile
    profile = db.create_employment_profile(EmploymentProfile(
        user_id=user.id,
        employment_type="hourly",
        base_rate=Decimal("35.00"),
        job_title="Senior Developer",
        department="Engineering",
        overtime_threshold_weekly=Decimal("40.0"),
        overtime_multiplier=Decimal("1.5")
    ))

    # Add tax deduction (20%)
    tax = db.create_deduction(Deduction(
        user_id=user.id,
        deduction_type="tax",
        name="Income Tax",
        is_percentage=True,
        amount=Decimal("20.0")
    ))

    # Add health insurance ($100)
    insurance = db.create_deduction(Deduction(
        user_id=user.id,
        deduction_type="insurance",
        name="Health Insurance",
        is_percentage=False,
        amount=Decimal("100.00")
    ))

    # Add 5 days of work (Monday-Friday)
    for day_offset in range(5):
        shift_date = date(2025, 1, 13) + timedelta(days=day_offset)
        shift = WorkShift(
            user_id=user.id,
            employment_profile_id=profile.id,
            shift_date=shift_date,
            start_time=time(9, 0),
            end_time=time(17, 0),
            shift_type="regular"
        )
        processed = engine.process_shift(shift)
        db.create_work_shift(processed)

    # Calculate payroll
    period = engine.calculate_payroll_period(
        user.id,
        date(2025, 1, 13),
        date(2025, 1, 17)
    )

    # Assertions
    assert period.shift_count == 5
    assert period.total_hours_regular == Decimal("40.00")
    assert period.gross_pay_total == Decimal("1400.00")  # 40 hours * $35/hr

    # Tax: 20% of 1400 = 280
    # Insurance: 100
    # Total deductions: 380
    assert period.total_deductions == Decimal("380.00")
    assert period.net_pay == Decimal("1020.00")  # 1400 - 380

    print("\n" + "="*60)
    print("COMPREHENSIVE PAYROLL TEST SCENARIO")
    print("="*60)
    print(f"Employee: {user.full_name}")
    print(f"Position: {profile.job_title}")
    print(f"Hourly Rate: ${profile.base_rate}")
    print(f"\nPay Period: {period.period_start} to {period.period_end}")
    print(f"Total Shifts: {period.shift_count}")
    print(f"Regular Hours: {period.total_hours_regular}")
    print(f"Overtime Hours: {period.total_hours_overtime}")
    print(f"\nGross Pay: ${period.gross_pay_total}")
    print(f"Deductions: ${period.total_deductions}")
    print(f"  - Income Tax (20%): $280.00")
    print(f"  - Health Insurance: $100.00")
    print(f"\nNET PAY: ${period.net_pay}")
    print("="*60)


def test_weekend_shift_multiplier(db, engine):
    """Test weekend shift premium"""
    user = db.create_user(User(username="worker8", email="w8@test.com", full_name="Worker Eight"))
    profile = db.create_employment_profile(EmploymentProfile(
        user_id=user.id,
        employment_type="hourly",
        base_rate=Decimal("20.00"),
        weekend_multiplier=Decimal("1.5")
    ))

    shift = WorkShift(
        user_id=user.id,
        employment_profile_id=profile.id,
        shift_date=date(2025, 1, 18),  # Saturday
        start_time=time(10, 0),
        end_time=time(18, 0),
        shift_type="weekend"
    )

    processed = engine.process_shift(shift)

    assert processed.hours_worked == Decimal("8.00")
    assert processed.hourly_rate == Decimal("30.00")  # 20 * 1.5
    assert processed.total_pay == Decimal("240.00")


def test_salaried_employee(db, engine):
    """Test salaried employee calculation"""
    user = db.create_user(User(username="manager", email="mgr@test.com", full_name="Manager"))
    profile = db.create_employment_profile(EmploymentProfile(
        user_id=user.id,
        employment_type="salaried",
        base_rate=Decimal("52000.00")  # Annual salary
    ))

    # Add one shift
    shift = WorkShift(
        user_id=user.id,
        employment_profile_id=profile.id,
        shift_date=date(2025, 1, 15),
        start_time=time(9, 0),
        end_time=time(17, 0)
    )

    processed = engine.process_shift(shift)

    # Annual salary / 2080 hours = hourly rate
    # 52000 / 2080 = 25.00
    assert processed.hourly_rate == Decimal("25.00")
    assert processed.hours_worked == Decimal("8.00")
    assert processed.total_pay == Decimal("200.00")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
