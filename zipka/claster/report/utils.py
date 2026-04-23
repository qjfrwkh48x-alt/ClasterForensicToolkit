"""
Reporting utilities.
"""

def format_timestamp(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else ''