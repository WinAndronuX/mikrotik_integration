import frappe
from frappe import _
from frappe.utils import now, add_days, get_first_day, get_last_day
from frappe.utils.data import format_date
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

@frappe.whitelist()
def get_dashboard_data(router=None):
    """Get data for MikroTik dashboard"""
    stats = get_subscription_stats(router)
    active_users = get_active_users(router)
    failed_api_calls = get_failed_api_calls(router)
    usage_chart = get_usage_chart_data(router)

    return {
        "stats": stats,
        "active_users": active_users,
        "failed_api_calls": failed_api_calls,
        "usage_chart": usage_chart
    }

def get_subscription_stats(router=None):
    """Get subscription statistics"""
    filters = {"docstatus": 1}
    if router:
        filters["mikrotik_settings"] = router

    # Get active subscriptions count
    active_subs = frappe.get_all(
        "Customer Subscription",
        filters=dict(filters, status="Active"),
        pluck="name"
    )

    # Get pending payments count
    pending_payments = frappe.get_all(
        "Customer Subscription",
        filters=dict(filters, payment_status="Pending"),
        pluck="name"
    )

    # Calculate monthly revenue
    month_start = get_first_day(now())
    month_end = get_last_day(now())
    completed_payments = frappe.get_all(
        "Customer Subscription",
        filters=dict(
            filters,
            payment_status="Completed",
            payment_date=["between", [month_start, month_end]]
        ),
        fields=["sum(price) as total", "currency"]
    )

    # Get total usage for today
    today_usage = frappe.get_all(
        "Customer Subscription",
        filters=dict(filters, status="Active"),
        fields=["sum(data_used_mb) as total"]
    )

    return {
        "active_subscriptions": len(active_subs),
        "pending_payments": len(pending_payments),
        "monthly_revenue": completed_payments[0].total if completed_payments else 0,
        "currency": completed_payments[0].currency if completed_payments else frappe.defaults.get_global_default("currency"),
        "total_usage_mb": today_usage[0].total if today_usage else 0
    }

def get_active_users(router=None):
    """Get list of currently active users"""
    filters = {
        "docstatus": 1,
        "status": "Active"
    }
    if router:
        filters["mikrotik_settings"] = router

    users = frappe.get_all(
        "Customer Subscription",
        filters=filters,
        fields=[
            "customer as customer",
            "customer_name",
            "username_mikrotik as username",
            "connection_type",
            "data_used_mb as data_used",
            "last_login as uptime",
            "payment_status",
            "expiry_date as expiry"
        ]
    )

    # Format the data
    for user in users:
        user.data_used = f"{user.data_used} MB"
        user.uptime = format_date(user.uptime) if user.uptime else "Never"
        user.expiry = format_date(user.expiry)
        user.customer = f"{user.customer_name} ({user.customer})"

    return users

def get_failed_api_calls(router=None):
    """Get recent failed API calls"""
    filters = {
        "status": "Failed",
        "creation": [">=", add_days(now(), -1)]  # Last 24 hours
    }
    if router:
        filters["router"] = router

    return frappe.get_all(
        "MikroTik API Log",
        filters=filters,
        fields=[
            "creation as timestamp",
            "operation",
            "router",
            "status"
        ],
        order_by="creation desc",
        limit=10
    )

def get_usage_chart_data(router=None):
    """Get daily bandwidth usage data"""
    filters = {
        "docstatus": 1,
        "status": "Active",
        "creation": [">=", add_days(now(), -30)]  # Last 30 days
    }
    if router:
        filters["mikrotik_settings"] = router

    daily_usage = frappe.get_all(
        "Customer Subscription",
        filters=filters,
        fields=[
            "DATE(creation) as date",
            "sum(data_used_mb) as usage"
        ],
        group_by="DATE(creation)",
        order_by="date"
    )

    return {
        "labels": [format_date(d.date) for d in daily_usage],
        "values": [d.usage for d in daily_usage]
    }