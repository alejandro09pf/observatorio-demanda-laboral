import re
from typing import Optional, List
from config.settings import get_settings

settings = get_settings()

def validate_country(country: str) -> bool:
    """Validate country code."""
    return country in settings.supported_countries

def validate_portal(portal: str) -> bool:
    """Validate portal name."""
    return portal in settings.supported_portals

def validate_skill(skill: str) -> bool:
    """Validate skill text."""
    if not skill or len(skill.strip()) < 2:
        return False
    
    # Must contain at least one letter
    if not re.search(r'[a-zA-Z]', skill):
        return False
    
    # Check length
    if len(skill) > 100:
        return False
    
    return True 