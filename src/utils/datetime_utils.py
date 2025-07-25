"""
Date and time utility functions
"""

from datetime import datetime, date, time, timedelta, timezone
from typing import Optional, Union
import calendar


def utc_now() -> datetime:
    """Get current UTC datetime"""
    return datetime.now(timezone.utc)


def market_date() -> date:
    """Get current market date (US Eastern time)"""
    # Convert UTC to Eastern time (approximate)
    utc_time = utc_now()
    eastern_time = utc_time - timedelta(hours=5)  # EST offset (simplified)
    return eastern_time.date()


def is_market_hours(dt: Optional[datetime] = None) -> bool:
    """Check if given time is during market hours"""
    if dt is None:
        dt = utc_now()
    
    # Convert to Eastern time (simplified)
    eastern_time = dt - timedelta(hours=5)
    
    # Check if weekday (Monday=0, Sunday=6)
    if eastern_time.weekday() >= 5:  # Saturday or Sunday
        return False
    
    # Check market hours (9:30 AM to 4:00 PM Eastern)
    market_open = time(9, 30)
    market_close = time(16, 0)
    
    current_time = eastern_time.time()
    return market_open <= current_time <= market_close


def is_trading_day(dt: date) -> bool:
    """Check if given date is a trading day (weekday, non-holiday)"""
    # Check if weekday
    if dt.weekday() >= 5:  # Saturday or Sunday
        return False
    
    # Check for major US holidays (simplified)
    holidays = get_us_market_holidays(dt.year)
    return dt not in holidays


def get_us_market_holidays(year: int) -> list:
    """Get list of US market holidays for given year"""
    holidays = []
    
    # New Year's Day (or observed)
    new_years = date(year, 1, 1)
    if new_years.weekday() == 5:  # Saturday
        holidays.append(date(year, 1, 3))  # Monday
    elif new_years.weekday() == 6:  # Sunday
        holidays.append(date(year, 1, 2))  # Monday
    else:
        holidays.append(new_years)
    
    # Martin Luther King Jr. Day (3rd Monday in January)
    holidays.append(get_nth_weekday(year, 1, 0, 3))
    
    # Presidents' Day (3rd Monday in February)
    holidays.append(get_nth_weekday(year, 2, 0, 3))
    
    # Good Friday (Friday before Easter)
    easter = get_easter(year)
    good_friday = easter - timedelta(days=2)
    holidays.append(good_friday)
    
    # Memorial Day (last Monday in May)
    holidays.append(get_last_weekday(year, 5, 0))
    
    # Juneteenth (June 19)
    juneteenth = date(year, 6, 19)
    if juneteenth.weekday() == 5:  # Saturday
        holidays.append(date(year, 6, 18))  # Friday
    elif juneteenth.weekday() == 6:  # Sunday
        holidays.append(date(year, 6, 20))  # Monday
    else:
        holidays.append(juneteenth)
    
    # Independence Day (July 4)
    independence = date(year, 7, 4)
    if independence.weekday() == 5:  # Saturday
        holidays.append(date(year, 7, 3))  # Friday
    elif independence.weekday() == 6:  # Sunday
        holidays.append(date(year, 7, 5))  # Monday
    else:
        holidays.append(independence)
    
    # Labor Day (1st Monday in September)
    holidays.append(get_nth_weekday(year, 9, 0, 1))
    
    # Thanksgiving (4th Thursday in November)
    holidays.append(get_nth_weekday(year, 11, 3, 4))
    
    # Christmas Day
    christmas = date(year, 12, 25)
    if christmas.weekday() == 5:  # Saturday
        holidays.append(date(year, 12, 24))  # Friday
    elif christmas.weekday() == 6:  # Sunday
        holidays.append(date(year, 12, 26))  # Monday
    else:
        holidays.append(christmas)
    
    return holidays


def get_nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Get nth occurrence of weekday in month"""
    first_day = date(year, month, 1)
    first_weekday = first_day.weekday()
    
    # Calculate days to first occurrence
    days_to_first = (weekday - first_weekday) % 7
    
    # Calculate target date
    target_day = 1 + days_to_first + (n - 1) * 7
    
    return date(year, month, target_day)


def get_last_weekday(year: int, month: int, weekday: int) -> date:
    """Get last occurrence of weekday in month"""
    # Get last day of month
    last_day = calendar.monthrange(year, month)[1]
    last_date = date(year, month, last_day)
    
    # Calculate days back to last occurrence
    days_back = (last_date.weekday() - weekday) % 7
    
    return last_date - timedelta(days=days_back)


def get_easter(year: int) -> date:
    """Calculate Easter date for given year"""
    # Using the anonymous Gregorian algorithm
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    
    return date(year, month, day)


def next_trading_day(dt: date) -> date:
    """Get next trading day after given date"""
    next_day = dt + timedelta(days=1)
    
    while not is_trading_day(next_day):
        next_day += timedelta(days=1)
    
    return next_day


def previous_trading_day(dt: date) -> date:
    """Get previous trading day before given date"""
    prev_day = dt - timedelta(days=1)
    
    while not is_trading_day(prev_day):
        prev_day -= timedelta(days=1)
    
    return prev_day


def days_to_expiry(expiry_date: date, from_date: Optional[date] = None) -> int:
    """Calculate days to expiry from given date"""
    if from_date is None:
        from_date = market_date()
    
    return (expiry_date - from_date).days


def trading_days_to_expiry(expiry_date: date, from_date: Optional[date] = None) -> int:
    """Calculate trading days to expiry"""
    if from_date is None:
        from_date = market_date()
    
    if expiry_date <= from_date:
        return 0
    
    trading_days = 0
    current_date = from_date
    
    while current_date < expiry_date:
        current_date += timedelta(days=1)
        if is_trading_day(current_date):
            trading_days += 1
    
    return trading_days


def format_market_time(dt: datetime) -> str:
    """Format datetime for market display (Eastern time)"""
    # Convert to Eastern time (simplified)
    eastern_time = dt - timedelta(hours=5)
    return eastern_time.strftime("%Y-%m-%d %H:%M:%S ET")


def parse_expiry_date(expiry_str: str) -> date:
    """Parse expiry date string in various formats"""
    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%Y%m%d",
        "%m/%d/%y",
        "%y%m%d"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(expiry_str, fmt).date()
        except ValueError:
            continue
    
    raise ValueError(f"Could not parse expiry date: {expiry_str}")


def is_third_friday(dt: date) -> bool:
    """Check if date is third Friday of month (standard options expiry)"""
    if dt.weekday() != 4:  # Not Friday
        return False
    
    # Check if it's the third Friday
    third_friday = get_nth_weekday(dt.year, dt.month, 4, 3)
    return dt == third_friday


def get_monthly_expiry(year: int, month: int) -> date:
    """Get monthly options expiry date (3rd Friday)"""
    return get_nth_weekday(year, month, 4, 3)


def get_weekly_expiries(year: int, month: int) -> list:
    """Get all weekly expiry dates for a month (Fridays except monthly)"""
    expiries = []
    monthly_expiry = get_monthly_expiry(year, month)
    
    # Find all Fridays in the month
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    
    current_date = first_day
    while current_date <= last_day:
        if current_date.weekday() == 4 and current_date != monthly_expiry:  # Friday, not monthly
            expiries.append(current_date)
        current_date += timedelta(days=1)
    
    return expiries


def time_until_expiry(expiry_date: date, reference_time: Optional[datetime] = None) -> timedelta:
    """Calculate time until expiry"""
    if reference_time is None:
        reference_time = utc_now()
    
    # Assume expiry at 4:00 PM Eastern on expiry date
    expiry_datetime = datetime.combine(expiry_date, time(21, 0))  # 4 PM ET = 9 PM UTC
    expiry_datetime = expiry_datetime.replace(tzinfo=timezone.utc)
    
    return expiry_datetime - reference_time


def is_expiry_today(expiry_date: date) -> bool:
    """Check if expiry is today"""
    return expiry_date == market_date()


def get_time_to_market_open() -> Optional[timedelta]:
    """Get time until market opens"""
    now = utc_now()
    
    if is_market_hours(now):
        return None  # Market is already open
    
    # Calculate next market open
    market_date_today = market_date()
    
    if is_trading_day(market_date_today):
        # Market opens today
        market_open = datetime.combine(market_date_today, time(14, 30))  # 9:30 AM ET = 2:30 PM UTC
        market_open = market_open.replace(tzinfo=timezone.utc)
        
        if now < market_open:
            return market_open - now
    
    # Market opens next trading day
    next_trading = next_trading_day(market_date_today)
    market_open = datetime.combine(next_trading, time(14, 30))
    market_open = market_open.replace(tzinfo=timezone.utc)
    
    return market_open - now


def get_time_to_market_close() -> Optional[timedelta]:
    """Get time until market closes"""
    now = utc_now()
    
    if not is_market_hours(now):
        return None  # Market is already closed
    
    # Calculate market close today
    market_date_today = market_date()
    market_close = datetime.combine(market_date_today, time(21, 0))  # 4:00 PM ET = 9:00 PM UTC
    market_close = market_close.replace(tzinfo=timezone.utc)
    
    return market_close - now
