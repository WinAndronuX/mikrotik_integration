import frappe
from frappe import _
from frappe.utils import now
from mikrotik_integration.utils import format_bytes, parse_mikrotik_date

class MikrotikAPI:
    def __init__(self):
        self.api = None
        self.settings = None

    def get_usage(self, api, conn_type, username):
        """Get usage data for user from MikroTik router"""
        try:
            usage_data = {"data_used_mb": 0, "last_login": None}
            
            if conn_type.service_name == "hotspot":
                user = api.get_resource('/ip/hotspot/user/').get(name=username)
                active = api.get_resource('/ip/hotspot/active/').get(user=username)
            elif conn_type.service_name in ["pppoe", "l2tp", "pptp"]:
                user = api.get_resource('/ppp/secret/').get(name=username)
                active = api.get_resource('/ppp/active/').get(name=username)
            elif conn_type.service_name == "openvpn":
                user = api.get_resource('/interface/ovpn-server/user/').get(name=username)
                active = api.get_resource('/interface/ovpn-server/active/').get(name=username)
            else:
                frappe.throw(_("Unsupported connection type: {0}").format(conn_type.service_name))
                
            if user and len(user) > 0:
                # Get bytes in/out
                bytes_in = float(user[0].get('bytes-in', '0'))
                bytes_out = float(user[0].get('bytes-out', '0'))
                usage_data["data_used_mb"] = (bytes_in + bytes_out) / (1024 * 1024)  # Convert to MB
                
                # Get last login time if active
                if active and len(active) > 0:
                    usage_data["last_login"] = parse_mikrotik_date(active[0].get('last-logged', None))
                    
            return usage_data
            
        except Exception as e:
            frappe.log_error(
                f"Error getting usage data for user {username}: {str(e)}",
                "MikroTik API Error"
            )
            return None

    def check_user_status(self, api, conn_type, username):
        """Check if user is enabled in MikroTik router"""
        try:
            if conn_type.service_name == "hotspot":
                users = api.get_resource('/ip/hotspot/user/').get(name=username)
            elif conn_type.service_name in ["pppoe", "l2tp", "pptp"]:
                users = api.get_resource('/ppp/secret/').get(name=username)
            elif conn_type.service_name == "openvpn":
                users = api.get_resource('/interface/ovpn-server/user/').get(name=username)
            else:
                frappe.throw(_("Unsupported connection type: {0}").format(conn_type.service_name))
                
            if users and len(users) > 0:
                return "Active" if not users[0].get('disabled', 'false') == 'true' else "Suspended"
            return "Not Found"
            
        except Exception as e:
            frappe.log_error(
                f"Error checking status for user {username}: {str(e)}",
                "MikroTik API Error"
            )
            return "Error"

    def create_api_log(self, router, operation, parameters, status, response=""):
        """Create MikroTik API Log entry"""
        try:
            log = frappe.get_doc({
                "doctype": "MikroTik API Log",
                "router": router,
                "operation": operation,
                "parameters": parameters,
                "response": response,
                "status": status
            })
            log.insert(ignore_permissions=True)
            return log
        except Exception as e:
            frappe.log_error(f"Error creating API log: {str(e)}")
            return None