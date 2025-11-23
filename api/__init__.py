"""
API module for HHS Social Media Scraper.

This module provides API documentation, validation, and error handling.
"""

from flask_restx import Api

# Initialize Flask-RESTX API
restx_api = None

def init_api(app, **kwargs):
    """Initialize Flask-RESTX API instance."""
    global restx_api
    
    # Add after_request hook to add API version headers
    @app.after_request
    def add_api_headers(response):
        """Add API version headers to all responses."""
        response.headers['X-API-Version'] = '1.0'
        response.headers['X-API-Doc'] = '/api/docs'
        return response
    
    restx_api = Api(
        app,
        version='1.0',
        title='HHS Social Media API',
        description='API for HHS Social Media Scraper - Social media metrics and account management',
        doc='/api/docs',
        default='v1',
        default_label='Version 1',
        **kwargs
    )
    return restx_api

def get_api():
    """Get the Flask-RESTX API instance."""
    return restx_api

