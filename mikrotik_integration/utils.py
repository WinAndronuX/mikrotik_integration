import frappe
from frappe.utils import now
from datetime import datetime

def sync_all_routers():
    """Sync all MikroTik routers"""
    try:
        routers = frappe.get_all("MikroTik Settings", fields=["name"])
        for router in routers:
            try:
                router_doc = frappe.get_doc("MikroTik Settings", router.name)
                # Test connection
                api = router_doc.get_api_connection()
                api.get_resource('/system/identity').get()
                # Update last sync time
                router_doc.last_sync = now()
                router_doc.save()
                api.close()
                frappe.db.commit()
            except Exception as e:
                frappe.log_error(
                    f"Error syncing router {router.name}: {str(e)}",
                    "Router Sync Error"
                )
    except Exception as e:
        frappe.log_error(f"Error in sync_all_routers: {str(e)}")

def format_bytes(bytes):
    """Format bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024
    return f"{bytes:.2f} PB"

def parse_mikrotik_date(date_str):
    """Parse MikroTik date format to datetime"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%b/%d/%Y %H:%M:%S")
    except:
        try:
            return datetime.strptime(date_str, "%m/%d/%Y %H:%M:%S")
        except:
            return None