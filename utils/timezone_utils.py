"""
Timezone utilities for consistent datetime handling across the application.
"""
import os
import pytz
from datetime import datetime
from typing import Optional

class TimezoneManager:
    """Centralized timezone management for the application."""
    
    def __init__(self):
        self.timezone_name = os.getenv("TIMEZONE", "Asia/Kolkata")
        self.time_format = os.getenv("TIME_FORMAT", "12_hour")
        self.display_suffix = os.getenv("DISPLAY_TIMEZONE_SUFFIX", "IST")
        
        # Initialize timezone objects
        self.local_tz = pytz.timezone(self.timezone_name)
        self.utc_tz = pytz.UTC
        
    def now_local(self) -> datetime:
        """Get current time in local timezone."""
        return datetime.now(self.local_tz)
        
    def now_utc(self) -> datetime:
        """Get current time in UTC."""
        return datetime.now(self.utc_tz)
        
    def to_local(self, dt: datetime) -> datetime:
        """Convert datetime to local timezone."""
        if dt.tzinfo is None:
            # Assume UTC if no timezone info
            dt = self.utc_tz.localize(dt)
        return dt.astimezone(self.local_tz)
        
    def to_utc(self, dt: datetime) -> datetime:
        """Convert datetime to UTC."""
        if dt.tzinfo is None:
            # Assume local timezone if no timezone info
            dt = self.local_tz.localize(dt)
        return dt.astimezone(self.utc_tz)
        
    def format_for_display(self, dt: datetime) -> str:
        """Format datetime for user display in 12-hour IST format."""
        local_dt = self.to_local(dt)
        
        if self.time_format == "12_hour":
            formatted = local_dt.strftime('%Y-%m-%d %I:%M %p')
            return f"{formatted} IST"
        else:
            formatted = local_dt.strftime('%Y-%m-%d %H:%M')
            return f"{formatted} {self.display_suffix}"
    
    def format_delivery_time_friendly(self, dt: datetime) -> str:
        """Format delivery time in a user-friendly way."""
        local_dt = self.to_local(dt)
        now = self.now_local()
        
        # Calculate time difference
        diff = local_dt - now
        minutes_diff = int(diff.total_seconds() / 60)
        
        if minutes_diff < 60:
            relative_time = f"in {minutes_diff} minutes"
        elif minutes_diff < 1440:  # Less than 24 hours
            hours = minutes_diff // 60
            remaining_minutes = minutes_diff % 60
            if remaining_minutes == 0:
                relative_time = f"in {hours} hour{'s' if hours != 1 else ''}"
            else:
                relative_time = f"in {hours}h {remaining_minutes}m"
        else:
            relative_time = "tomorrow"
        
        # Format absolute time
        if self.time_format == "12_hour":
            absolute_time = local_dt.strftime('%I:%M %p')
        else:
            absolute_time = local_dt.strftime('%H:%M')
        
        return f"{absolute_time} ({relative_time})"
            
    def format_time_only(self, dt: datetime) -> str:
        """Format only time portion for display."""
        local_dt = self.to_local(dt)
        
        if self.time_format == "12_hour":
            return local_dt.strftime('%I:%M %p')
        else:
            return local_dt.strftime('%H:%M')
            
    def format_for_storage(self, dt: datetime) -> str:
        """Format datetime for storage (ISO format with timezone)."""
        return dt.isoformat()
        
    def parse_from_storage(self, dt_string: str) -> datetime:
        """Parse datetime from storage format."""
        try:
            # Try parsing with timezone info
            return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        except ValueError:
            # Fallback: assume UTC if no timezone info
            dt = datetime.fromisoformat(dt_string)
            return self.utc_tz.localize(dt)
            
    def add_minutes(self, dt: datetime, minutes: int) -> datetime:
        """Add minutes to datetime, preserving timezone."""
        from datetime import timedelta
        return dt + timedelta(minutes=minutes)
        
    def format_delivery_time(self, dt: datetime) -> str:
        """Format delivery time for customer notification."""
        local_dt = self.to_local(dt)
        
        if self.time_format == "12_hour":
            time_str = local_dt.strftime('%I:%M %p')
            date_str = local_dt.strftime('%B %d, %Y')
            return f"{time_str} on {date_str}"
        else:
            return local_dt.strftime('%H:%M on %B %d, %Y')

# Global timezone manager instance
tz_manager = TimezoneManager()
