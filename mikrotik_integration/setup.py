import frappe

def after_install():
    """Set up required dependencies"""
    try:
        import routeros_api
    except ImportError:
        frappe.throw(
            "Required package 'routeros_api' is missing. Please run: pip install routeros_api"
        )