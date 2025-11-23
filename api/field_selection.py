"""
Field selection (sparse fieldsets) for API responses.
"""
from typing import List, Optional, Dict, Any
from flask import request

def parse_fields(fields_param: Optional[str] = None) -> Optional[List[str]]:
    """
    Parse fields parameter from request.
    
    Args:
        fields_param: Comma-separated field names (from query param or request)
        
    Returns:
        List of field names or None
    """
    if fields_param is None:
        fields_param = request.args.get('fields')
    
    if not fields_param:
        return None
    
    return [f.strip() for f in fields_param.split(',') if f.strip()]


def select_fields(data: Dict, fields: List[str]) -> Dict:
    """
    Select only specified fields from data dictionary.
    
    Args:
        data: Data dictionary
        fields: List of field names to include
        
    Returns:
        Dictionary with only selected fields
    """
    if not fields:
        return data
    
    result = {}
    for field in fields:
        if field in data:
            result[field] = data[field]
        # Handle nested fields (e.g., "account.platform")
        elif '.' in field:
            parts = field.split('.')
            value = data
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    value = None
                    break
            if value is not None:
                result[field] = value
    
    return result


def select_fields_from_list(data_list: List[Dict], fields: List[str]) -> List[Dict]:
    """
    Select fields from a list of dictionaries.
    
    Args:
        data_list: List of data dictionaries
        fields: List of field names to include
        
    Returns:
        List of dictionaries with only selected fields
    """
    if not fields:
        return data_list
    
    return [select_fields(item, fields) for item in data_list]


def apply_field_selection(data: Any, fields: Optional[List[str]] = None) -> Any:
    """
    Apply field selection to data (handles both dict and list).
    
    Args:
        data: Data (dict or list)
        fields: Optional list of fields (if None, reads from request)
        
    Returns:
        Data with field selection applied
    """
    if fields is None:
        fields = parse_fields()
    
    if not fields:
        return data
    
    if isinstance(data, dict):
        return select_fields(data, fields)
    elif isinstance(data, list):
        return select_fields_from_list(data, fields)
    else:
        return data

