"""
Database layer for Payroll Management System

Uses SQLite for embedded database with full CRUD operations.
"""

import sqlite3
from datetime import datetime, date, time
from decimal import Decimal
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
import json

from app.models import (
    User, EmploymentProfile, WorkShift, Deduction, Bonus, PayrollPeriod
)


class Database:
    """SQLite database manager with connection pooling"""

    def __init__(self, db_path: str = "payroll.db"):
        self.db_path = db_path
        self._memory_conn = None  # For :memory: databases

        # For in-memory databases, keep a persistent connection
        if db_path == ":memory:":
            self._memory_conn = sqlite3.connect(db_path)
            self._memory_conn.row_factory = sqlite3.Row

        self.init_database()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        # Use persistent connection for :memory: databases
        if self._memory_conn:
            try:
                yield self._memory_conn
                self._memory_conn.commit()
            except Exception as e:
                self._memory_conn.rollback()
                raise e
        else:
            # For file-based databases, create new connection each time
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

    def init_database(self):
        """Create all tables if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # Employment profiles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS employment_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    employment_type TEXT NOT NULL,
                    base_rate REAL NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    standard_hours_per_week REAL DEFAULT 40.0,
                    overtime_threshold_daily REAL DEFAULT 8.0,
                    overtime_threshold_weekly REAL DEFAULT 40.0,
                    overtime_multiplier REAL DEFAULT 1.5,
                    night_shift_multiplier REAL DEFAULT 1.25,
                    weekend_multiplier REAL DEFAULT 1.5,
                    job_title TEXT,
                    department TEXT,
                    start_date TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Work shifts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS work_shifts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    employment_profile_id INTEGER NOT NULL,
                    shift_date TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    shift_type TEXT DEFAULT 'regular',
                    is_overtime INTEGER DEFAULT 0,
                    hours_worked REAL,
                    hourly_rate REAL,
                    total_pay REAL,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (employment_profile_id) REFERENCES employment_profiles(id)
                )
            """)

            # Deductions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS deductions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    deduction_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    is_percentage INTEGER DEFAULT 1,
                    amount REAL NOT NULL,
                    applies_to_overtime INTEGER DEFAULT 1,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Bonuses table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bonuses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    bonus_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT,
                    bonus_date TEXT NOT NULL,
                    is_taxable INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Payroll periods table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payroll_periods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    total_hours_regular REAL DEFAULT 0,
                    total_hours_overtime REAL DEFAULT 0,
                    gross_pay_regular REAL DEFAULT 0,
                    gross_pay_overtime REAL DEFAULT 0,
                    gross_pay_total REAL DEFAULT 0,
                    total_bonuses REAL DEFAULT 0,
                    total_deductions REAL DEFAULT 0,
                    net_pay REAL DEFAULT 0,
                    is_finalized INTEGER DEFAULT 0,
                    finalized_at TEXT,
                    created_at TEXT NOT NULL,
                    shift_count INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_shifts_user ON work_shifts(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_shifts_date ON work_shifts(shift_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_profiles_user ON employment_profiles(user_id)")

    # ============== USER OPERATIONS ==============

    def create_user(self, user: User) -> User:
        """Create a new user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (username, email, full_name, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user.username, user.email, user.full_name, user.created_at.isoformat())
            )
            user.id = cursor.lastrowid
            return user

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return User(
                    id=row["id"],
                    username=row["username"],
                    email=row["email"],
                    full_name=row["full_name"],
                    created_at=datetime.fromisoformat(row["created_at"])
                )
            return None

    def get_all_users(self) -> List[User]:
        """Get all users"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users ORDER BY full_name")
            return [
                User(
                    id=row["id"],
                    username=row["username"],
                    email=row["email"],
                    full_name=row["full_name"],
                    created_at=datetime.fromisoformat(row["created_at"])
                )
                for row in cursor.fetchall()
            ]

    # ============== EMPLOYMENT PROFILE OPERATIONS ==============

    def create_employment_profile(self, profile: EmploymentProfile) -> EmploymentProfile:
        """Create employment profile"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO employment_profiles (
                    user_id, employment_type, base_rate, currency,
                    standard_hours_per_week, overtime_threshold_daily,
                    overtime_threshold_weekly, overtime_multiplier,
                    night_shift_multiplier, weekend_multiplier,
                    job_title, department, start_date, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.user_id, profile.employment_type, float(profile.base_rate),
                    profile.currency, float(profile.standard_hours_per_week),
                    float(profile.overtime_threshold_daily) if profile.overtime_threshold_daily else None,
                    float(profile.overtime_threshold_weekly) if profile.overtime_threshold_weekly else None,
                    float(profile.overtime_multiplier), float(profile.night_shift_multiplier),
                    float(profile.weekend_multiplier), profile.job_title, profile.department,
                    profile.start_date.isoformat(), 1 if profile.is_active else 0
                )
            )
            profile.id = cursor.lastrowid
            return profile

    def get_employment_profile(self, profile_id: int) -> Optional[EmploymentProfile]:
        """Get employment profile by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM employment_profiles WHERE id = ?", (profile_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_employment_profile(row)
            return None

    def get_active_profile_for_user(self, user_id: int) -> Optional[EmploymentProfile]:
        """Get active employment profile for user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM employment_profiles WHERE user_id = ? AND is_active = 1 ORDER BY id DESC LIMIT 1",
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_employment_profile(row)
            return None

    def _row_to_employment_profile(self, row) -> EmploymentProfile:
        """Convert database row to EmploymentProfile"""
        return EmploymentProfile(
            id=row["id"],
            user_id=row["user_id"],
            employment_type=row["employment_type"],
            base_rate=Decimal(str(row["base_rate"])),
            currency=row["currency"],
            standard_hours_per_week=Decimal(str(row["standard_hours_per_week"])),
            overtime_threshold_daily=Decimal(str(row["overtime_threshold_daily"])) if row["overtime_threshold_daily"] else None,
            overtime_threshold_weekly=Decimal(str(row["overtime_threshold_weekly"])) if row["overtime_threshold_weekly"] else None,
            overtime_multiplier=Decimal(str(row["overtime_multiplier"])),
            night_shift_multiplier=Decimal(str(row["night_shift_multiplier"])),
            weekend_multiplier=Decimal(str(row["weekend_multiplier"])),
            job_title=row["job_title"],
            department=row["department"],
            start_date=date.fromisoformat(row["start_date"]),
            is_active=bool(row["is_active"])
        )

    # ============== WORK SHIFT OPERATIONS ==============

    def create_work_shift(self, shift: WorkShift) -> WorkShift:
        """Create work shift"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO work_shifts (
                    user_id, employment_profile_id, shift_date, start_time, end_time,
                    shift_type, is_overtime, hours_worked, hourly_rate, total_pay,
                    notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    shift.user_id, shift.employment_profile_id, shift.shift_date.isoformat(),
                    shift.start_time.isoformat(), shift.end_time.isoformat(),
                    shift.shift_type, 1 if shift.is_overtime else 0,
                    float(shift.hours_worked) if shift.hours_worked else None,
                    float(shift.hourly_rate) if shift.hourly_rate else None,
                    float(shift.total_pay) if shift.total_pay else None,
                    shift.notes, shift.created_at.isoformat()
                )
            )
            shift.id = cursor.lastrowid
            return shift

    def get_shifts_for_user(self, user_id: int, start_date: date = None, end_date: date = None) -> List[WorkShift]:
        """Get all shifts for user, optionally filtered by date range"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if start_date and end_date:
                cursor.execute(
                    """
                    SELECT * FROM work_shifts
                    WHERE user_id = ? AND shift_date BETWEEN ? AND ?
                    ORDER BY shift_date DESC, start_time DESC
                    """,
                    (user_id, start_date.isoformat(), end_date.isoformat())
                )
            else:
                cursor.execute(
                    "SELECT * FROM work_shifts WHERE user_id = ? ORDER BY shift_date DESC, start_time DESC",
                    (user_id,)
                )

            return [self._row_to_work_shift(row) for row in cursor.fetchall()]

    def _row_to_work_shift(self, row) -> WorkShift:
        """Convert database row to WorkShift"""
        return WorkShift(
            id=row["id"],
            user_id=row["user_id"],
            employment_profile_id=row["employment_profile_id"],
            shift_date=date.fromisoformat(row["shift_date"]),
            start_time=time.fromisoformat(row["start_time"]),
            end_time=time.fromisoformat(row["end_time"]),
            shift_type=row["shift_type"],
            is_overtime=bool(row["is_overtime"]),
            hours_worked=Decimal(str(row["hours_worked"])) if row["hours_worked"] else None,
            hourly_rate=Decimal(str(row["hourly_rate"])) if row["hourly_rate"] else None,
            total_pay=Decimal(str(row["total_pay"])) if row["total_pay"] else None,
            notes=row["notes"] or "",
            created_at=datetime.fromisoformat(row["created_at"])
        )

    # ============== DEDUCTION OPERATIONS ==============

    def create_deduction(self, deduction: Deduction) -> Deduction:
        """Create deduction"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO deductions (
                    user_id, deduction_type, name, is_percentage, amount,
                    applies_to_overtime, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    deduction.user_id, deduction.deduction_type, deduction.name,
                    1 if deduction.is_percentage else 0, float(deduction.amount),
                    1 if deduction.applies_to_overtime else 0, 1 if deduction.is_active else 0
                )
            )
            deduction.id = cursor.lastrowid
            return deduction

    def get_active_deductions_for_user(self, user_id: int) -> List[Deduction]:
        """Get all active deductions for user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM deductions WHERE user_id = ? AND is_active = 1",
                (user_id,)
            )
            return [self._row_to_deduction(row) for row in cursor.fetchall()]

    def _row_to_deduction(self, row) -> Deduction:
        """Convert database row to Deduction"""
        return Deduction(
            id=row["id"],
            user_id=row["user_id"],
            deduction_type=row["deduction_type"],
            name=row["name"],
            is_percentage=bool(row["is_percentage"]),
            amount=Decimal(str(row["amount"])),
            applies_to_overtime=bool(row["applies_to_overtime"]),
            is_active=bool(row["is_active"])
        )

    # ============== BONUS OPERATIONS ==============

    def create_bonus(self, bonus: Bonus) -> Bonus:
        """Create bonus"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO bonuses (
                    user_id, bonus_type, amount, description, bonus_date, is_taxable, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    bonus.user_id, bonus.bonus_type, float(bonus.amount),
                    bonus.description, bonus.bonus_date.isoformat(),
                    1 if bonus.is_taxable else 0, bonus.created_at.isoformat()
                )
            )
            bonus.id = cursor.lastrowid
            return bonus

    def get_bonuses_for_period(self, user_id: int, start_date: date, end_date: date) -> List[Bonus]:
        """Get bonuses for user within date range"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM bonuses
                WHERE user_id = ? AND bonus_date BETWEEN ? AND ?
                ORDER BY bonus_date DESC
                """,
                (user_id, start_date.isoformat(), end_date.isoformat())
            )
            return [self._row_to_bonus(row) for row in cursor.fetchall()]

    def _row_to_bonus(self, row) -> Bonus:
        """Convert database row to Bonus"""
        return Bonus(
            id=row["id"],
            user_id=row["user_id"],
            bonus_type=row["bonus_type"],
            amount=Decimal(str(row["amount"])),
            description=row["description"] or "",
            bonus_date=date.fromisoformat(row["bonus_date"]),
            is_taxable=bool(row["is_taxable"]),
            created_at=datetime.fromisoformat(row["created_at"])
        )

    # ============== PAYROLL PERIOD OPERATIONS ==============

    def create_payroll_period(self, period: PayrollPeriod) -> PayrollPeriod:
        """Create payroll period"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO payroll_periods (
                    user_id, period_start, period_end,
                    total_hours_regular, total_hours_overtime,
                    gross_pay_regular, gross_pay_overtime, gross_pay_total,
                    total_bonuses, total_deductions, net_pay,
                    is_finalized, finalized_at, created_at, shift_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    period.user_id, period.period_start.isoformat(), period.period_end.isoformat(),
                    float(period.total_hours_regular), float(period.total_hours_overtime),
                    float(period.gross_pay_regular), float(period.gross_pay_overtime),
                    float(period.gross_pay_total), float(period.total_bonuses),
                    float(period.total_deductions), float(period.net_pay),
                    1 if period.is_finalized else 0,
                    period.finalized_at.isoformat() if period.finalized_at else None,
                    period.created_at.isoformat(), period.shift_count
                )
            )
            period.id = cursor.lastrowid
            return period

    def get_payroll_periods_for_user(self, user_id: int) -> List[PayrollPeriod]:
        """Get all payroll periods for user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM payroll_periods WHERE user_id = ? ORDER BY period_end DESC",
                (user_id,)
            )
            return [self._row_to_payroll_period(row) for row in cursor.fetchall()]

    def _row_to_payroll_period(self, row) -> PayrollPeriod:
        """Convert database row to PayrollPeriod"""
        return PayrollPeriod(
            id=row["id"],
            user_id=row["user_id"],
            period_start=date.fromisoformat(row["period_start"]),
            period_end=date.fromisoformat(row["period_end"]),
            total_hours_regular=Decimal(str(row["total_hours_regular"])),
            total_hours_overtime=Decimal(str(row["total_hours_overtime"])),
            gross_pay_regular=Decimal(str(row["gross_pay_regular"])),
            gross_pay_overtime=Decimal(str(row["gross_pay_overtime"])),
            gross_pay_total=Decimal(str(row["gross_pay_total"])),
            total_bonuses=Decimal(str(row["total_bonuses"])),
            total_deductions=Decimal(str(row["total_deductions"])),
            net_pay=Decimal(str(row["net_pay"])),
            is_finalized=bool(row["is_finalized"]),
            finalized_at=datetime.fromisoformat(row["finalized_at"]) if row["finalized_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            shift_count=row["shift_count"]
        )
