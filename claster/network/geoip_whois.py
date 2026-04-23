"""
GeoIP and WHOIS lookups.
"""

import whois
import requests
from typing import Dict, Optional, Any
from pathlib import Path

from claster.core.logger import get_logger

logger = get_logger(__name__)

try:
    import geoip2.database
    GEOIP_AVAILABLE = True
except ImportError:
    GEOIP_AVAILABLE = False

def geoip_lookup(ip: str, db_path: Optional[str] = None) -> Dict[str, Optional[str]]:
    """
    Perform GeoIP lookup using MaxMind GeoLite2 database or fallback to ip-api.com.

    Args:
        ip: IP address.
        db_path: Path to GeoLite2-City.mmdb. If None, uses free web API.

    Returns:
        Dictionary with country, city, coordinates, etc.
    """
    if GEOIP_AVAILABLE and db_path and Path(db_path).exists():
        try:
            reader = geoip2.database.Reader(db_path)
            response = reader.city(ip)
            return {
                'country': response.country.name,
                'country_code': response.country.iso_code,
                'city': response.city.name,
                'latitude': response.location.latitude,
                'longitude': response.location.longitude,
                'timezone': response.location.time_zone,
                'source': 'local_db',
            }
        except Exception as e:
            logger.error(f"GeoIP local lookup failed: {e}")

    # Fallback to ip-api.com (free, no API key)
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,lat,lon,timezone", timeout=5)
        data = resp.json()
        if data.get('status') == 'success':
            return {
                'country': data.get('country'),
                'country_code': data.get('countryCode'),
                'city': data.get('city'),
                'region': data.get('regionName'),
                'latitude': data.get('lat'),
                'longitude': data.get('lon'),
                'timezone': data.get('timezone'),
                'source': 'ip-api.com',
            }
    except Exception as e:
        logger.error(f"GeoIP web lookup failed: {e}")

    return {'error': 'Lookup failed'}

def whois_lookup(domain: str) -> Dict[str, Any]:
    """
    Perform WHOIS lookup for a domain.

    Returns:
        Dictionary with registrar, creation date, expiration, name servers, etc.
    """
    try:
        w = whois.whois(domain)
        # Convert datetime objects to string for serialization
        result = {}
        for key, value in w.items():
            if isinstance(value, (list, tuple)):
                result[key] = [str(v) if hasattr(v, 'isoformat') else v for v in value]
            elif hasattr(value, 'isoformat'):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result
    except Exception as e:
        logger.error(f"WHOIS lookup failed for {domain}: {e}")
        return {'error': str(e)}