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
                error_msg = _("Unsupported connection type: {0}").format(conn_type.service_name)
                self.log_api_error(api.host, "get_usage", {"username": username}, error_msg)
                frappe.throw(error_msg)
                
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
            self.log_api_error(
                api.host,
                "get_usage",
                {"username": username, "connection_type": conn_type.service_name},
                str(e)
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
                error_msg = _("Unsupported connection type: {0}").format(conn_type.service_name)
                self.log_api_error(api.host, "check_user_status", {"username": username}, error_msg)
                frappe.throw(error_msg)
                
            if users and len(users) > 0:
                return "Active" if not users[0].get('disabled', 'false') == 'true' else "Suspended"
            return "Not Found"
            
        except Exception as e:
            self.log_api_error(
                api.host,
                "check_user_status",
                {"username": username, "connection_type": conn_type.service_name},
                str(e)
            )
            return "Error"

    def log_api_error(self, router, operation, parameters, error=""):
        """Log MikroTik API errors to Frappe error log"""
        error_log = frappe.log_error(
            message=f"MikroTik API Error\nRouter: {router}\nOperation: {operation}\nParameters: {parameters}\nError: {error}",
            title="MikroTik API Error"
        )
        frappe.publish_realtime('mikrotik_api_error', {
            'name': error_log.name,
            'creation': error_log.creation,
            'operation': operation,
            'router': router
        })


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
    """Get recent failed API calls from error log"""
    filters = {
        "creation": [">=", add_days(now(), -1)],  # Last 24 hours
        "title": ["like", "MikroTik API Error%"]
    }

    # Search in error log for MikroTik API errors
    logs = frappe.get_all(
        "Error Log",
        filters=filters,
        fields=["creation as timestamp", "message"],
        order_by="creation desc",
        limit=10
    )

    # Parse the logs to extract operation and router
    formatted_logs = []
    for log in logs:
        error_lines = log.message.split("\n")
        router_name = ""
        operation = ""
        
        for line in error_lines:
            if line.startswith("Router:"):
                router_name = line.replace("Router:", "").strip()
            elif line.startswith("Operation:"):
                operation = line.replace("Operation:", "").strip()

        # Only include if we have both router and operation
        if router_name and operation:
            # Include if no specific router filter or matches filter
            if not router or router_name == router:  
                formatted_logs.append({
                    "timestamp": log.timestamp,
                    "operation": operation,
                    "router": router_name,
                    "status": "Failed"
                })

    return formatted_logs

@frappe.whitelist()
def test_provision(router, connection_type, username, password):
    """Test user provisioning on MikroTik router"""
    try:
        router_doc = frappe.get_doc("MikroTik Settings", router)
        conn_type = frappe.get_doc("Connection Type", connection_type)
        
        # Get API connection
        api = router_doc.get_api_connection()
        
        # Prepare command based on connection type
        if conn_type.service_name == "hotspot":
            cmd = "/ip hotspot user add"
        elif conn_type.service_name in ["pppoe", "l2tp", "pptp"]:
            cmd = "/ppp secret add"
        elif conn_type.service_name == "openvpn":
            cmd = "/interface ovpn-server user add"
        else:
            return {
                "success": False,
                "message": f"Unsupported connection type: {conn_type.service_name}"
            }

        # Get bandwidth limits
        limits = conn_type.get_bandwidth_limits()
        
        # Build parameters
        params = {
            "name": username,
            "password": password,
            "profile": conn_type.profile_name
        }
        
        if conn_type.service_name in ["pppoe", "l2tp", "pptp"]:
            params["service"] = conn_type.service_name
        
        # Apply bandwidth limits if not using profile
        if not conn_type.parent_profile:
            if limits.get("speed_limit_rx"):
                params["rate-limit"] = f"{limits['speed_limit_rx']}/{limits['speed_limit_tx']}"
            if limits.get("burst_limit_rx"):
                params["burst-limit"] = f"{limits['burst_limit_rx']}/{limits['burst_limit_tx']}"

        # Execute command
        api.get_resource(cmd).add(**params)
        
        # Test if user was created
        if conn_type.service_name == "hotspot":
            users = api.get_resource('/ip/hotspot/user/').get(name=username)
        elif conn_type.service_name in ["pppoe", "l2tp", "pptp"]:
            users = api.get_resource('/ppp/secret/').get(name=username)
        elif conn_type.service_name == "openvpn":
            users = api.get_resource('/interface/ovpn-server/user/').get(name=username)
            
        api.close()
        
        if users and len(users) > 0:
            # Clean up test user
            if conn_type.service_name == "hotspot":
                api.get_resource('/ip/hotspot/user/remove').remove(id=users[0].get('id'))
            elif conn_type.service_name in ["pppoe", "l2tp", "pptp"]:
                api.get_resource('/ppp/secret/remove').remove(id=users[0].get('id'))
            elif conn_type.service_name == "openvpn":
                api.get_resource('/interface/ovpn-server/user/remove').remove(id=users[0].get('id'))
                
            return {
                "success": True,
                "message": "Test provision successful"
            }
        else:
            return {
                "success": False,
                "message": "Failed to create test user"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }

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