"""
SPXW options instrument models and utilities
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from enum import Enum


class SPXWType(Enum):
    """SPXW option types"""
    STANDARD = "STANDARD"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"


class ExpirationStyle(Enum):
    """Option expiration styles"""
    AMERICAN = "AMERICAN"
    EUROPEAN = "EUROPEAN"


@dataclass_json
@dataclass
class SPXWInstrument:
    """SPXW options instrument definition"""
    symbol: str                    # e.g., "SPXW"
    underlying_symbol: str         # "SPX"
    strike_price: Decimal
    expiry_date: date
    option_type: str              # "CALL" or "PUT"
    
    # Contract specifications
    contract_size: int = 100
    currency: str = "USD"
    exchange: str = "CBOE"
    security_type: str = "OPT"
    
    # SPXW-specific
    spxw_type: SPXWType = SPXWType.WEEKLY
    expiration_style: ExpirationStyle = ExpirationStyle.EUROPEAN
    settlement_type: str = "CASH"
    
    # Identification
    security_id: Optional[str] = None
    security_id_source: str = "8"  # Exchange Symbol
    
    # Market data
    tick_size: Decimal = Decimal("0.05")
    min_price_increment: Decimal = Decimal("0.05")
    
    # Additional metadata
    is_tradable: bool = True
    last_trading_date: Optional[date] = None
    
    def __post_init__(self):
        """Initialize derived fields"""
        if self.last_trading_date is None:
            self.last_trading_date = self.expiry_date
        
        if self.security_id is None:
            self.security_id = self.generate_security_id()
    
    def generate_security_id(self) -> str:
        """Generate TT-compatible security ID for SPXW options"""
        # Format: SPXW_YYMMDD_C/P_Strike
        exp_str = self.expiry_date.strftime("%y%m%d")
        opt_type = "C" if self.option_type.upper() == "CALL" else "P"
        strike_str = f"{int(self.strike_price * 1000):08d}"  # Strike in 1/1000ths
        
        return f"SPXW_{exp_str}_{opt_type}_{strike_str}"
    
    def get_maturity_month_year(self) -> str:
        """Get maturity in YYYYMM format for FIX"""
        return self.expiry_date.strftime("%Y%m")
    
    def get_maturity_date(self) -> str:
        """Get maturity date in YYYYMMDD format for FIX"""
        return self.expiry_date.strftime("%Y%m%d")
    
    def get_put_or_call(self) -> int:
        """Get put/call indicator for FIX (0=Put, 1=Call)"""
        return 1 if self.option_type.upper() == "CALL" else 0
    
    def is_itm(self, underlying_price: Decimal) -> bool:
        """Check if option is in the money"""
        if self.option_type.upper() == "CALL":
            return underlying_price > self.strike_price
        else:
            return underlying_price < self.strike_price
    
    def is_otm(self, underlying_price: Decimal) -> bool:
        """Check if option is out of the money"""
        return not self.is_itm(underlying_price)
    
    def is_atm(self, underlying_price: Decimal, tolerance: Decimal = Decimal("0.50")) -> bool:
        """Check if option is at the money within tolerance"""
        return abs(underlying_price - self.strike_price) <= tolerance
    
    def days_to_expiry(self) -> int:
        """Calculate days to expiry"""
        return (self.expiry_date - date.today()).days
    
    def is_expired(self) -> bool:
        """Check if option has expired"""
        return date.today() > self.expiry_date
    
    def to_fix_instrument_fields(self) -> Dict[int, str]:
        """Convert to FIX instrument fields"""
        return {
            55: self.symbol,              # Symbol
            48: self.security_id,         # SecurityID
            22: self.security_id_source,  # SecurityIDSource
            167: self.security_type,      # SecurityType
            207: self.exchange,           # SecurityExchange
            15: self.currency,            # Currency
            200: self.get_maturity_month_year(),  # MaturityMonthYear
            541: self.get_maturity_date(),        # MaturityDate
            202: str(self.strike_price),          # StrikePrice
            201: self.get_put_or_call(),          # PutOrCall
        }


@dataclass_json
@dataclass
class SPXWChain:
    """SPXW options chain for a specific expiry"""
    underlying_symbol: str
    expiry_date: date
    options: List[SPXWInstrument]
    
    # Market data
    underlying_price: Optional[Decimal] = None
    last_updated: Optional[datetime] = None
    
    def get_calls(self) -> List[SPXWInstrument]:
        """Get all call options"""
        return [opt for opt in self.options if opt.option_type.upper() == "CALL"]
    
    def get_puts(self) -> List[SPXWInstrument]:
        """Get all put options"""
        return [opt for opt in self.options if opt.option_type.upper() == "PUT"]
    
    def get_strikes(self) -> List[Decimal]:
        """Get all unique strike prices"""
        return sorted(list(set(opt.strike_price for opt in self.options)))
    
    def get_option(self, strike: Decimal, option_type: str) -> Optional[SPXWInstrument]:
        """Get specific option by strike and type"""
        for opt in self.options:
            if opt.strike_price == strike and opt.option_type.upper() == option_type.upper():
                return opt
        return None
    
    def get_atm_options(self, tolerance: Decimal = Decimal("0.50")) -> List[SPXWInstrument]:
        """Get at-the-money options"""
        if self.underlying_price is None:
            return []
        
        return [opt for opt in self.options 
                if opt.is_atm(self.underlying_price, tolerance)]
    
    def get_itm_options(self) -> List[SPXWInstrument]:
        """Get in-the-money options"""
        if self.underlying_price is None:
            return []
        
        return [opt for opt in self.options if opt.is_itm(self.underlying_price)]
    
    def get_otm_options(self) -> List[SPXWInstrument]:
        """Get out-of-the-money options"""
        if self.underlying_price is None:
            return []
        
        return [opt for opt in self.options if opt.is_otm(self.underlying_price)]


class SPXWInstrumentFactory:
    """Factory for creating SPXW instruments"""
    
    @staticmethod
    def create_option(
        strike_price: Decimal,
        expiry_date: date,
        option_type: str,
        spxw_type: SPXWType = SPXWType.WEEKLY
    ) -> SPXWInstrument:
        """Create a SPXW option instrument"""
        return SPXWInstrument(
            symbol="SPXW",
            underlying_symbol="SPX",
            strike_price=strike_price,
            expiry_date=expiry_date,
            option_type=option_type.upper(),
            spxw_type=spxw_type
        )
    
    @staticmethod
    def create_chain(
        expiry_date: date,
        strikes: List[Decimal],
        spxw_type: SPXWType = SPXWType.WEEKLY
    ) -> SPXWChain:
        """Create a complete options chain for an expiry"""
        options = []
        
        for strike in strikes:
            # Create call and put for each strike
            call = SPXWInstrumentFactory.create_option(
                strike, expiry_date, "CALL", spxw_type
            )
            put = SPXWInstrumentFactory.create_option(
                strike, expiry_date, "PUT", spxw_type
            )
            
            options.extend([call, put])
        
        return SPXWChain(
            underlying_symbol="SPX",
            expiry_date=expiry_date,
            options=options
        )
    
    @staticmethod
    def parse_option_symbol(symbol: str) -> Optional[SPXWInstrument]:
        """Parse option symbol into instrument
        
        Expected format: SPXW_240315_C_4200000 (weekly)
        or SPXW_2024_03_C_4200000 (monthly)
        """
        try:
            parts = symbol.split("_")
            if len(parts) < 4 or parts[0] != "SPXW":
                return None
            
            # Parse expiry date
            if len(parts[1]) == 6:  # YYMMDD format
                expiry_date = datetime.strptime(parts[1], "%y%m%d").date()
                spxw_type = SPXWType.WEEKLY
            else:  # Assume YYYY_MM format
                year = int(parts[1])
                month = int(parts[2])
                # Assume third Friday for monthly
                expiry_date = date(year, month, 15)  # Simplified
                spxw_type = SPXWType.MONTHLY
                parts = [parts[0]] + [f"{year}{month:02d}"] + parts[3:]
            
            option_type = "CALL" if parts[2].upper() == "C" else "PUT"
            strike_price = Decimal(parts[3]) / Decimal("1000")  # Convert from 1/1000ths
            
            return SPXWInstrumentFactory.create_option(
                strike_price, expiry_date, option_type, spxw_type
            )
            
        except (ValueError, IndexError):
            return None


# Common SPXW strike ranges and increments
class SPXWStrikeRanges:
    """Common strike ranges for SPXW options"""
    
    @staticmethod
    def get_weekly_strikes(center_strike: Decimal, width: int = 200) -> List[Decimal]:
        """Get weekly SPXW strikes around center strike"""
        strikes = []
        
        # 25-point increments for standard range
        start = center_strike - width
        end = center_strike + width
        
        current = start
        while current <= end:
            if current % 25 == 0:  # 25-point increments
                strikes.append(current)
            current += 25
        
        # Add 5-point increments near ATM
        atm_range = 50
        start_fine = center_strike - atm_range
        end_fine = center_strike + atm_range
        
        current = start_fine
        while current <= end_fine:
            if current % 5 == 0 and current not in strikes:
                strikes.append(current)
            current += 5
        
        return sorted(strikes)
    
    @staticmethod
    def get_monthly_strikes(center_strike: Decimal, width: int = 500) -> List[Decimal]:
        """Get monthly SPXW strikes around center strike"""
        strikes = []
        
        # 50-point increments for wider range
        start = center_strike - width
        end = center_strike + width
        
        current = start
        while current <= end:
            if current % 50 == 0:
                strikes.append(current)
            current += 50
        
        # Add 25-point increments in middle range
        mid_range = 200
        start_mid = center_strike - mid_range
        end_mid = center_strike + mid_range
        
        current = start_mid
        while current <= end_mid:
            if current % 25 == 0 and current not in strikes:
                strikes.append(current)
            current += 25
        
        return sorted(strikes)
