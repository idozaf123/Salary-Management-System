"""
Data models for Payroll Management System

Supports various employment types, shift tracking, and compensation calculations.
"""

from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional, List
from dataclasses import dataclass, field


@dataclass
class User:
    """Represents a system user/employee"""
    id: Optional[int] = None
    username: str = ""
    email: str = ""
    full_name: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.username:
            raise ValueError("Username is required")


@dataclass
class EmploymentProfile:
    """
    Employment configuration for a user.
    Supports both hourly and salaried employees with flexible shift rules.
    """
    id: Optional[int] = None
    user_id: int = 0
    employment_type: str = "hourly"  # "hourly" or "salaried"

    # Base compensation
    base_rate: Decimal = Decimal("0.00")  # Hourly rate or annual salary
    currency: str = "USD"

    # Shift configuration
    standard_hours_per_week: Decimal = Decimal("40.00")
    overtime_threshold_daily: Optional[Decimal] = Decimal("8.00")  # Hours per day
    overtime_threshold_weekly: Optional[Decimal] = Decimal("40.00")  # Hours per week
    overtime_multiplier: Decimal = Decimal("1.5")  # 1.5x for overtime

    # Additional rules
    night_shift_multiplier: Decimal = Decimal("1.25")  # 25% extra for night shifts
    weekend_multiplier: Decimal = Decimal("1.5")  # 50% extra for weekends

    # Metadata
    job_title: str = ""
    department: str = ""
    start_date: date = field(default_factory=date.today)
    is_active: bool = True

    def __post_init__(self):
        if self.employment_type not in ["hourly", "salaried"]:
            raise ValueError("employment_type must be 'hourly' or 'salaried'")
        if self.base_rate <= 0:
            raise ValueError("base_rate must be positive")


@dataclass
class WorkShift:
    """
    Individual work shift record with precise timing and rate calculation.
    """
    id: Optional[int] = None
    user_id: int = 0
    employment_profile_id: int = 0

    # Shift timing
    shift_date: date = field(default_factory=date.today)
    start_time: time = field(default_factory=lambda: time(9, 0))
    end_time: time = field(default_factory=lambda: time(17, 0))

    # Shift classification
    shift_type: str = "regular"  # "regular", "night", "weekend", "holiday"
    is_overtime: bool = False

    # Calculated fields
    hours_worked: Optional[Decimal] = None
    hourly_rate: Optional[Decimal] = None  # Effective rate for this shift
    total_pay: Optional[Decimal] = None

    # Notes
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def calculate_hours(self) -> Decimal:
        """Calculate hours worked from start and end times"""
        start_datetime = datetime.combine(self.shift_date, self.start_time)
        end_datetime = datetime.combine(self.shift_date, self.end_time)

        # Handle overnight shifts
        if end_datetime < start_datetime:
            end_datetime = datetime.combine(
                date.fromordinal(self.shift_date.toordinal() + 1),
                self.end_time
            )

        duration = end_datetime - start_datetime
        hours = Decimal(str(duration.total_seconds() / 3600))
        return hours.quantize(Decimal("0.01"))


@dataclass
class Deduction:
    """
    Payroll deduction (tax, insurance, retirement, etc.)
    """
    id: Optional[int] = None
    user_id: int = 0

    deduction_type: str = "tax"  # "tax", "insurance", "retirement", "other"
    name: str = ""

    # Amount calculation
    is_percentage: bool = True
    amount: Decimal = Decimal("0.00")  # Percentage (e.g., 15.0 for 15%) or fixed amount

    # Application rules
    applies_to_overtime: bool = True
    is_active: bool = True

    def calculate(self, gross_pay: Decimal) -> Decimal:
        """Calculate deduction amount from gross pay"""
        if self.is_percentage:
            return (gross_pay * self.amount / Decimal("100")).quantize(Decimal("0.01"))
        else:
            return self.amount


@dataclass
class Bonus:
    """
    One-time or recurring bonus payment
    """
    id: Optional[int] = None
    user_id: int = 0

    bonus_type: str = "performance"  # "performance", "commission", "retention", "other"
    amount: Decimal = Decimal("0.00")
    description: str = ""

    bonus_date: date = field(default_factory=date.today)
    is_taxable: bool = True

    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PayrollPeriod:
    """
    Aggregated payroll calculation for a specific time period
    """
    id: Optional[int] = None
    user_id: int = 0

    # Period definition
    period_start: date = field(default_factory=date.today)
    period_end: date = field(default_factory=date.today)

    # Calculated totals
    total_hours_regular: Decimal = Decimal("0.00")
    total_hours_overtime: Decimal = Decimal("0.00")

    gross_pay_regular: Decimal = Decimal("0.00")
    gross_pay_overtime: Decimal = Decimal("0.00")
    gross_pay_total: Decimal = Decimal("0.00")

    total_bonuses: Decimal = Decimal("0.00")
    total_deductions: Decimal = Decimal("0.00")

    net_pay: Decimal = Decimal("0.00")

    # Metadata
    is_finalized: bool = False
    finalized_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

    shift_count: int = 0

    def finalize(self):
        """Mark payroll period as finalized (locked)"""
        if not self.is_finalized:
            self.is_finalized = True
            self.finalized_at = datetime.now()
            self.net_pay = (
                self.gross_pay_total + self.total_bonuses - self.total_deductions
            ).quantize(Decimal("0.01"))
