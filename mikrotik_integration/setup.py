import frappe

def validate_dependencies():
    """Validate required dependencies"""
    try:
        import routeros_api
        return True
    except ImportError:
        frappe.throw(
            "Required package 'routeros_api' is missing. Please run: pip install routeros_api"
        )
        return False

def after_install():
    """Setup app after installation"""
    validate_dependencies()

def after_migrate():
    """Update app after migration"""
    pass
    # Custom fields are handled via fixtures