"""
Payroll Calculation Engine

Core business logic for calculating compensation, overtime, bonuses, and deductions.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Tuple, Dict
import calendar

from app.models import (
    User, EmploymentProfile, WorkShift, Deduction, Bonus, PayrollPeriod
)
from app.database import Database


class PayrollEngine:
    """
    Handles all payroll calculations with precision.
    Supports hourly and salaried employees, various shift types, and complex overtime rules.
    """

    def __init__(self, db: Database):
        self.db = db

    def calculate_shift_pay(
        self,
        shift: WorkShift,
        profile: EmploymentProfile
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """
        Calculate pay for a single shift.

        Returns:
            (hours_worked, effective_hourly_rate, total_pay)
        """
        # Calculate hours worked
        hours = shift.calculate_hours()

        # Determine base hourly rate
        if profile.employment_type == "salaried":
            # Convert annual salary to hourly rate
            annual_salary = profile.base_rate
            hourly_rate = annual_salary / Decimal("2080")  # Standard 2080 hours/year
        else:
            hourly_rate = profile.base_rate

        # Apply multipliers based on shift type
        rate_multiplier = Decimal("1.0")

        if shift.shift_type == "night":
            rate_multiplier *= profile.night_shift_multiplier
        elif shift.shift_type == "weekend":
            rate_multiplier *= profile.weekend_multiplier
        elif shift.shift_type == "holiday":
            # Holiday is typically 2x
            rate_multiplier *= Decimal("2.0")

        # Apply overtime multiplier if marked as overtime
        if shift.is_overtime:
            rate_multiplier *= profile.overtime_multiplier

        effective_rate = (hourly_rate * rate_multiplier).quantize(Decimal("0.01"))
        total_pay = (hours * effective_rate).quantize(Decimal("0.01"))

        return hours, effective_rate, total_pay

    def process_shift(self, shift: WorkShift) -> WorkShift:
        """
        Process a work shift: calculate hours, rate, and pay.
        Updates the shift object with calculated values.
        """
        profile = self.db.get_employment_profile(shift.employment_profile_id)
        if not profile:
            raise ValueError(f"Employment profile {shift.employment_profile_id} not found")

        hours, rate, pay = self.calculate_shift_pay(shift, profile)

        shift.hours_worked = hours
        shift.hourly_rate = rate
        shift.total_pay = pay

        return shift

    def determine_overtime_shifts(
        self,
        user_id: int,
        shifts: List[WorkShift],
        profile: EmploymentProfile
    ) -> List[WorkShift]:
        """
        Analyze shifts and mark overtime based on daily and weekly thresholds.

        Logic:
        1. Check daily overtime (hours > threshold in single day)
        2. Check weekly overtime (total hours > threshold in week)
        """
        if not profile.overtime_threshold_daily and not profile.overtime_threshold_weekly:
            return shifts

        # Group shifts by date for daily overtime
        shifts_by_date: Dict[date, List[WorkShift]] = {}
        for shift in shifts:
            if shift.shift_date not in shifts_by_date:
                shifts_by_date[shift.shift_date] = []
            shifts_by_date[shift.shift_date].append(shift)

        # Mark daily overtime
        if profile.overtime_threshold_daily:
            for shift_date, day_shifts in shifts_by_date.items():
                daily_hours = sum(s.calculate_hours() for s in day_shifts)
                if daily_hours > profile.overtime_threshold_daily:
                    # Mark excess hours as overtime
                    # Simple approach: mark later shifts in the day as OT
                    cumulative = Decimal("0")
                    for s in sorted(day_shifts, key=lambda x: x.start_time):
                        shift_hours = s.calculate_hours()
                        cumulative += shift_hours
                        if cumulative > profile.overtime_threshold_daily:
                            s.is_overtime = True

        # Group by week for weekly overtime
        if profile.overtime_threshold_weekly:
            shifts_by_week: Dict[Tuple[int, int], List[WorkShift]] = {}
            for shift in shifts:
                # Get ISO week number
                year, week, _ = shift.shift_date.isocalendar()
                key = (year, week)
                if key not in shifts_by_week:
                    shifts_by_week[key] = []
                shifts_by_week[key].append(shift)

            for week_key, week_shifts in shifts_by_week.items():
                weekly_hours = sum(s.calculate_hours() for s in week_shifts)
                if weekly_hours > profile.overtime_threshold_weekly:
                    # Mark shifts beyond threshold as OT
                    cumulative = Decimal("0")
                    for s in sorted(week_shifts, key=lambda x: (x.shift_date, x.start_time)):
                        if not s.is_overtime:  # Don't override daily OT
                            shift_hours = s.calculate_hours()
                            cumulative += shift_hours
                            if cumulative > profile.overtime_threshold_weekly:
                                s.is_overtime = True

        return shifts

    def calculate_payroll_period(
        self,
        user_id: int,
        start_date: date,
        end_date: date
    ) -> PayrollPeriod:
        """
        Calculate complete payroll for a user over a date range.

        Steps:
        1. Fetch all shifts in period
        2. Determine overtime
        3. Calculate gross pay
        4. Apply bonuses
        5. Apply deductions
        6. Calculate net pay
        """
        # Fetch employment profile
        profile = self.db.get_active_profile_for_user(user_id)
        if not profile:
            raise ValueError(f"No active employment profile for user {user_id}")

        # Fetch shifts
        shifts = self.db.get_shifts_for_user(user_id, start_date, end_date)

        # Determine overtime
        shifts = self.determine_overtime_shifts(user_id, shifts, profile)

        # Calculate totals
        total_hours_regular = Decimal("0")
        total_hours_overtime = Decimal("0")
        gross_pay_regular = Decimal("0")
        gross_pay_overtime = Decimal("0")

        for shift in shifts:
            hours, rate, pay = self.calculate_shift_pay(shift, profile)

            if shift.is_overtime:
                total_hours_overtime += hours
                gross_pay_overtime += pay
            else:
                total_hours_regular += hours
                gross_pay_regular += pay

        gross_pay_total = gross_pay_regular + gross_pay_overtime

        # Fetch and sum bonuses
        bonuses = self.db.get_bonuses_for_period(user_id, start_date, end_date)
        total_bonuses = sum(b.amount for b in bonuses)

        # Fetch and calculate deductions
        deductions = self.db.get_active_deductions_for_user(user_id)
        total_deductions = Decimal("0")

        for deduction in deductions:
            if deduction.applies_to_overtime:
                deduction_base = gross_pay_total
            else:
                deduction_base = gross_pay_regular

            total_deductions += deduction.calculate(deduction_base)

        # Calculate net pay
        net_pay = gross_pay_total + total_bonuses - total_deductions

        # Create payroll period object
        period = PayrollPeriod(
            user_id=user_id,
            period_start=start_date,
            period_end=end_date,
            total_hours_regular=total_hours_regular.quantize(Decimal("0.01")),
            total_hours_overtime=total_hours_overtime.quantize(Decimal("0.01")),
            gross_pay_regular=gross_pay_regular.quantize(Decimal("0.01")),
            gross_pay_overtime=gross_pay_overtime.quantize(Decimal("0.01")),
            gross_pay_total=gross_pay_total.quantize(Decimal("0.01")),
            total_bonuses=total_bonuses.quantize(Decimal("0.01")),
            total_deductions=total_deductions.quantize(Decimal("0.01")),
            net_pay=net_pay.quantize(Decimal("0.01")),
            shift_count=len(shifts),
            is_finalized=False
        )

        return period

    def generate_standard_periods(
        self,
        user_id: int,
        year: int,
        period_type: str = "biweekly"
    ) -> List[Tuple[date, date]]:
        """
        Generate standard payroll period date ranges.

        Args:
            user_id: User ID
            year: Calendar year
            period_type: "weekly", "biweekly", "semimonthly", "monthly"

        Returns:
            List of (start_date, end_date) tuples
        """
        periods = []

        if period_type == "weekly":
            # Start from first Monday of year
            start = date(year, 1, 1)
            while start.weekday() != 0:  # 0 = Monday
                start += timedelta(days=1)

            current = start
            while current.year == year:
                end = current + timedelta(days=6)  # Sunday
                if end.year > year:
                    end = date(year, 12, 31)
                periods.append((current, end))
                current = end + timedelta(days=1)

        elif period_type == "biweekly":
            # Start from first Monday of year
            start = date(year, 1, 1)
            while start.weekday() != 0:
                start += timedelta(days=1)

            current = start
            while current.year == year:
                end = current + timedelta(days=13)  # 2 weeks
                if end.year > year:
                    end = date(year, 12, 31)
                periods.append((current, end))
                current = end + timedelta(days=1)

        elif period_type == "semimonthly":
            # 1st-15th and 16th-end of each month
            for month in range(1, 13):
                # First period: 1st to 15th
                start1 = date(year, month, 1)
                end1 = date(year, month, 15)
                periods.append((start1, end1))

                # Second period: 16th to last day
                start2 = date(year, month, 16)
                last_day = calendar.monthrange(year, month)[1]
                end2 = date(year, month, last_day)
                periods.append((start2, end2))

        elif period_type == "monthly":
            for month in range(1, 13):
                start = date(year, month, 1)
                last_day = calendar.monthrange(year, month)[1]
                end = date(year, month, last_day)
                periods.append((start, end))

        else:
            raise ValueError(f"Unknown period type: {period_type}")

        return periods

    def auto_calculate_and_save_period(
        self,
        user_id: int,
        start_date: date,
        end_date: date
    ) -> PayrollPeriod:
        """
        Calculate payroll period and save to database.
        """
        period = self.calculate_payroll_period(user_id, start_date, end_date)
        return self.db.create_payroll_period(period)

    def get_payroll_summary(self, user_id: int, num_periods: int = 6) -> Dict:
        """
        Get summary of recent payroll periods for user.

        Returns detailed summary including trends and totals.
        """
        periods = self.db.get_payroll_periods_for_user(user_id)[:num_periods]

        if not periods:
            return {
                "user_id": user_id,
                "total_periods": 0,
                "periods": []
            }

        total_gross = sum(p.gross_pay_total for p in periods)
        total_net = sum(p.net_pay for p in periods)
        total_hours = sum(p.total_hours_regular + p.total_hours_overtime for p in periods)

        return {
            "user_id": user_id,
            "total_periods": len(periods),
            "total_gross_pay": float(total_gross),
            "total_net_pay": float(total_net),
            "total_hours": float(total_hours),
            "average_gross_pay": float(total_gross / len(periods)) if periods else 0,
            "average_net_pay": float(total_net / len(periods)) if periods else 0,
            "periods": [
                {
                    "id": p.id,
                    "period_start": p.period_start.isoformat(),
                    "period_end": p.period_end.isoformat(),
                    "hours_regular": float(p.total_hours_regular),
                    "hours_overtime": float(p.total_hours_overtime),
                    "gross_pay": float(p.gross_pay_total),
                    "net_pay": float(p.net_pay),
                    "shift_count": p.shift_count,
                    "is_finalized": p.is_finalized
                }
                for p in periods
            ]
        }
