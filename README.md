# Payroll Management System

A comprehensive, user-centric payroll tracking and management system designed for maximum precision in compensation calculations. Built from scratch to handle various employment types, shift configurations, overtime rules, bonuses, and deductions.

## Features

### Core Capabilities

- **Multi-employment Type Support**: Handles both hourly and salaried employees
- **Flexible Shift Tracking**: Regular, night, weekend, and holiday shifts with customizable rate multipliers
- **Intelligent Overtime Calculation**: Automatic overtime detection based on daily and weekly thresholds
- **Comprehensive Compensation Tracking**: Base pay, overtime, bonuses, and deductions
- **Precise Calculations**: Uses Decimal arithmetic for financial accuracy
- **Payroll Period Management**: Generate and track payroll for any date range
- **RESTful API**: Full JSON API for programmatic access
- **Web Interface**: Clean, functional web UI for data entry and reporting

### Employment Configuration

Each user can configure:
- Employment type (hourly or salaried)
- Base compensation rate
- Standard hours per week
- Overtime thresholds (daily and weekly)
- Rate multipliers for special shifts (night, weekend, holiday)
- Job title and department
- Currency

### Shift Management

Track shifts with:
- Date and time (precise to the minute)
- Shift type (regular, night, weekend, holiday)
- Automatic hours calculation
- Overtime flagging
- Rate application with multipliers
- Notes/comments

### Payroll Features

- Automatic gross pay calculation
- Multiple deduction types (tax, insurance, retirement, etc.)
- Percentage or fixed-amount deductions
- One-time and recurring bonuses
- Net pay calculation
- Payroll period finalization
- Historical payroll reports

## Technology Stack

- **Backend**: Python 3.7+
- **Web Framework**: Flask 3.0
- **Database**: SQLite (embedded, no server required)
- **Frontend**: HTML5, CSS3 (vanilla, no frameworks)
- **Testing**: pytest

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/idozaf123/Salary-Management-System.git
   cd Salary-Management-System
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python run.py
   ```

   The application will start on `http://localhost:5000`

### Command-Line Options

```bash
python run.py --help

Options:
  --host HOST      Host to bind to (default: 0.0.0.0)
  --port PORT      Port to bind to (default: 5000)
  --debug          Run in debug mode
  --db PATH        Database file path (default: payroll.db)
```

Example:
```bash
python run.py --port 8080 --debug
```

## Quick Start Guide

### 1. Create a User

**Via API:**
```bash
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "jdoe",
    "email": "jdoe@example.com",
    "full_name": "John Doe"
  }'
```

**Response:**
```json
{
  "id": 1,
  "username": "jdoe",
  "email": "jdoe@example.com",
  "full_name": "John Doe"
}
```

### 2. Create Employment Profile

```bash
curl -X POST http://localhost:5000/api/user/1/profile \
  -H "Content-Type: application/json" \
  -d '{
    "employment_type": "hourly",
    "base_rate": 25.00,
    "currency": "USD",
    "standard_hours_per_week": 40,
    "overtime_threshold_daily": 8,
    "overtime_threshold_weekly": 40,
    "overtime_multiplier": 1.5,
    "night_shift_multiplier": 1.25,
    "weekend_multiplier": 1.5,
    "job_title": "Software Engineer",
    "department": "Engineering",
    "start_date": "2025-01-01"
  }'
```

### 3. Add Work Shifts

```bash
curl -X POST http://localhost:5000/api/user/1/shifts \
  -H "Content-Type: application/json" \
  -d '{
    "shift_date": "2025-01-15",
    "start_time": "09:00",
    "end_time": "17:00",
    "shift_type": "regular",
    "notes": "Regular workday"
  }'
```

**Response:**
```json
{
  "id": 1,
  "hours_worked": 8.00,
  "hourly_rate": 25.00,
  "total_pay": 200.00
}
```

### 4. Add Deductions

```bash
curl -X POST http://localhost:5000/api/user/1/deductions \
  -H "Content-Type: application/json" \
  -d '{
    "deduction_type": "tax",
    "name": "Federal Income Tax",
    "is_percentage": true,
    "amount": 15.0,
    "applies_to_overtime": true
  }'
```

### 5. Calculate Payroll

```bash
curl -X POST http://localhost:5000/api/user/1/payroll/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-01-13",
    "end_date": "2025-01-17",
    "save": true
  }'
```

**Response:**
```json
{
  "id": 1,
  "period_start": "2025-01-13",
  "period_end": "2025-01-17",
  "total_hours_regular": 40.00,
  "total_hours_overtime": 0.00,
  "gross_pay_regular": 1000.00,
  "gross_pay_overtime": 0.00,
  "gross_pay_total": 1000.00,
  "total_bonuses": 0.00,
  "total_deductions": 150.00,
  "net_pay": 850.00,
  "shift_count": 5
}
```

## API Reference

### User Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users` | List all users |
| POST | `/api/users` | Create new user |
| GET | `/api/user/{id}` | Get user by ID |

### Employment Profile Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/user/{id}/profile` | Get active employment profile |
| POST | `/api/user/{id}/profile` | Create employment profile |

### Shift Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/user/{id}/shifts` | Get all shifts (supports ?start_date=&end_date=) |
| POST | `/api/user/{id}/shifts` | Add work shift |

### Deduction Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/user/{id}/deductions` | Get active deductions |
| POST | `/api/user/{id}/deductions` | Create deduction |

### Bonus Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/user/{id}/bonuses` | Create bonus |

### Payroll Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/user/{id}/payroll/calculate` | Calculate payroll period |
| GET | `/api/user/{id}/payroll/summary` | Get payroll summary |
| GET | `/api/user/{id}/payroll/periods` | Get all payroll periods |

## Web Interface

Access the web interface at `http://localhost:5000` after starting the application.

### Available Pages

- **Dashboard** (`/`) - View all users and system overview
- **User Dashboard** (`/user/{id}`) - Individual user summary
- **Employment Profile** (`/user/{id}/profile`) - Manage employment settings
- **Work Shifts** (`/user/{id}/shifts`) - Track and view shifts
- **Payroll Reports** (`/user/{id}/payroll`) - View payroll periods and deductions

## Testing

Run the comprehensive test suite:

```bash
pytest tests/ -v
```

Run with coverage report:

```bash
pytest tests/ --cov=app --cov-report=html
```

### Test Scenarios

The test suite includes:
- User creation and retrieval
- Employment profile management
- Regular shift calculations
- Night/weekend shift premiums
- Overtime detection and calculation
- Payroll period aggregation
- Deduction calculations (percentage and fixed)
- Bonus application
- Complete end-to-end scenarios

## Architecture

### Project Structure

```
Salary-Management-System/
├── app/
│   ├── __init__.py           # Application factory
│   ├── models.py             # Data models
│   ├── database.py           # Database layer (SQLite)
│   ├── payroll_engine.py     # Calculation logic
│   ├── routes.py             # Flask routes
│   └── templates/            # HTML templates
│       ├── base.html
│       ├── index.html
│       ├── user_dashboard.html
│       ├── profile.html
│       ├── shifts.html
│       └── payroll.html
├── static/
│   └── style.css             # Stylesheet
├── tests/
│   └── test_payroll.py       # Test suite
├── config.py                 # Configuration
├── run.py                    # Application entry point
├── requirements.txt          # Dependencies
├── .gitignore
└── README.md
```

### Data Models

1. **User** - Employee/user information
2. **EmploymentProfile** - Job configuration and compensation rules
3. **WorkShift** - Individual shift records with timing and pay
4. **Deduction** - Tax and benefit deductions
5. **Bonus** - One-time or recurring bonuses
6. **PayrollPeriod** - Aggregated payroll calculations

### Database Schema

SQLite database with the following tables:
- `users` - User accounts
- `employment_profiles` - Employment configurations
- `work_shifts` - Shift records
- `deductions` - Deduction rules
- `bonuses` - Bonus payments
- `payroll_periods` - Calculated payroll periods

## Example Scenarios

### Scenario 1: Hourly Employee with Overtime

**Setup:**
- Hourly rate: $25/hour
- Overtime threshold: 40 hours/week
- Overtime multiplier: 1.5x

**Week's work:**
- Mon-Thu: 8 hours each (32 hours)
- Friday: 10 hours (2 hours overtime)

**Calculation:**
- Regular pay: 40 hrs × $25 = $1,000
- Overtime pay: 2 hrs × $37.50 = $75
- **Total gross: $1,075**

### Scenario 2: Night Shift Premium

**Setup:**
- Base rate: $20/hour
- Night shift multiplier: 1.25x

**Shift:**
- 10 PM to 6 AM (8 hours)

**Calculation:**
- Effective rate: $20 × 1.25 = $25/hour
- **Total pay: $200**

### Scenario 3: Salaried Employee

**Setup:**
- Annual salary: $52,000
- Converted hourly: $52,000 / 2,080 = $25/hour

**Shift:**
- 9 AM to 5 PM (8 hours)

**Calculation:**
- Pay: 8 hrs × $25 = $200

## Calculation Logic

### Overtime Determination

The system checks two thresholds:

1. **Daily Overtime**: Hours beyond threshold in a single day
2. **Weekly Overtime**: Total hours beyond threshold in a calendar week

Shifts are automatically flagged as overtime when thresholds are exceeded.

### Pay Calculation Formula

```
Effective Rate = Base Rate × Type Multiplier × Overtime Multiplier
Total Pay = Hours × Effective Rate
```

Where:
- **Type Multiplier**: night_shift (1.25), weekend (1.5), holiday (2.0), or regular (1.0)
- **Overtime Multiplier**: Applied if shift is marked as overtime

### Net Pay Calculation

```
Gross Pay = Sum of all shift pay
Total Bonuses = Sum of bonuses in period
Total Deductions = Sum of percentage and fixed deductions
Net Pay = Gross Pay + Bonuses - Deductions
```

## Security Considerations

### Current Implementation

- Uses SQLite with parameterized queries (SQL injection protection)
- Input validation on all models
- No hardcoded credentials
- Secret key configurable via environment variable

### Production Recommendations

1. Change `SECRET_KEY` in production (use environment variable)
2. Enable HTTPS/TLS
3. Implement authentication and authorization
4. Add rate limiting on API endpoints
5. Use PostgreSQL or MySQL for multi-user environments
6. Implement audit logging for payroll changes
7. Add CSRF protection for web forms
8. Implement role-based access control (admin, manager, employee)

## Limitations & Future Enhancements

### Current Limitations

- Single-user focused (no multi-tenant support)
- No user authentication
- No email notifications
- Manual shift entry (no clock-in/out)
- No integration with external payroll services

### Potential Enhancements

- [ ] User authentication and authorization
- [ ] Multi-tenant support
- [ ] Mobile application
- [ ] Clock-in/out functionality with geolocation
- [ ] Automated shift scheduling
- [ ] Integration with accounting software (QuickBooks, Xero)
- [ ] Email/SMS notifications for payroll events
- [ ] Export to PDF/Excel
- [ ] Advanced reporting and analytics
- [ ] Tax calculation by jurisdiction
- [ ] Direct deposit integration
- [ ] Time-off tracking (vacation, sick leave)

## Troubleshooting

### Database Issues

**Problem**: Database locked error
**Solution**: Ensure only one instance of the application is running

**Problem**: Database file not found
**Solution**: The database is created automatically on first run. Check file permissions.

### Installation Issues

**Problem**: `pip install` fails
**Solution**: Ensure Python 3.7+ is installed. Try upgrading pip: `pip install --upgrade pip`

### Port Already in Use

**Problem**: Port 5000 already in use
**Solution**: Use a different port: `python run.py --port 8080`

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`pytest tests/`)
6. Commit your changes (`git commit -m 'Add new feature'`)
7. Push to the branch (`git push origin feature/new-feature`)
8. Create a Pull Request

## License

This project is provided as-is for educational and commercial use.

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Submit a pull request
- Contact: jdoe@example.com

## Acknowledgments

Built with precision and attention to detail for accurate payroll management.

---

**Version**: 1.0.0
**Last Updated**: January 2025
**Python Version**: 3.7+
**Database**: SQLite 3
