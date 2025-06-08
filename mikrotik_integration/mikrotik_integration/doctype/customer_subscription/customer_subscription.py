# Copyright (c) 2025, ronoh and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, now, random_string, today
from rq.decorators import job
import json

class CustomerSubscription(Document):
    def validate(self):
        """Validate subscription details"""
        self.validate_dates()
        self.validate_customer()
        self.set_subscription_id()
        self.set_credentials()
        
    def validate_dates(self):
        """Validate and set dates"""
        if not self.expiry_date:
            plan = frappe.get_doc("Internet Plan", self.internet_plan)
            self.expiry_date = add_days(self.start_date, plan.validity_days)

    def validate_customer(self):
        """Ensure customer exists and is active"""
        customer = frappe.get_doc("Customer", self.customer)
        if not customer.disabled:
            frappe.throw(_("Customer {0} is disabled").format(self.customer))

    def set_subscription_id(self):
        """Generate unique subscription ID if not set"""
        if not self.subscription_id:
            self.subscription_id = f"SUB-{frappe.generate_hash(length=8)}"

    def set_credentials(self):
        """Set MikroTik username and password if not set"""
        if not self.username_mikrotik:
            # Generate username based on customer name and subscription ID
            username = f"{self.customer_name.lower().replace(' ', '')}-{self.subscription_id[-4:]}"
            self.username_mikrotik = username[:32]  # MikroTik username length limit
        
        if not self.password_mikrotik:
            self.password_mikrotik = random_string(10)

    def before_submit(self):
        """Before activating subscription"""
        if self.status == "Draft":
            self.status = "Active"

    def on_submit(self):
        """When subscription is activated"""
        self.provision_mikrotik_user()

    def before_cancel(self):
        """Before cancelling subscription"""
        self.remove_mikrotik_user()
        self.status = "Expired"

    def provision_mikrotik_user(self):
        """Create user in MikroTik router"""
        try:
            router = frappe.get_doc("MikroTik Settings", self.mikrotik_settings)
            conn_type = frappe.get_doc("Connection Type", self.connection_type)
            
            # Get API connection
            api = router.get_api_connection()
            
            # Prepare command based on connection type
            if conn_type.service_name == "hotspot":
                cmd = "/ip hotspot user add"
            elif conn_type.service_name in ["pppoe", "l2tp", "pptp"]:
                cmd = "/ppp secret add"
            elif conn_type.service_name == "openvpn":
                cmd = "/interface ovpn-server user add"
            else:
                frappe.throw(_("Unsupported connection type: {0}").format(conn_type.service_name))

            # Get bandwidth limits
            limits = conn_type.get_bandwidth_limits()
            
            # Build parameters
            params = {
                "name": self.username_mikrotik,
                "password": self.password_mikrotik,
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
            
            # Log success
            self.create_api_log(
                router=self.mikrotik_settings,
                operation=f"add_user_{conn_type.service_name}",
                parameters=json.dumps(params),
                status="Success"
            )
            
            api.close()
            
        except Exception as e:
            # Log failure
            self.create_api_log(
                router=self.mikrotik_settings,
                operation="add_user_failed",
                parameters=str(e),
                status="Failed"
            )
            frappe.throw(_("Failed to provision MikroTik user: {0}").format(str(e)))

    def remove_mikrotik_user(self):
        """Remove user from MikroTik router"""
        try:
            router = frappe.get_doc("MikroTik Settings", self.mikrotik_settings)
            conn_type = frappe.get_doc("Connection Type", self.connection_type)
            
            # Get API connection
            api = router.get_api_connection()
            
            # Prepare command based on connection type
            if conn_type.service_name == "hotspot":
                cmd = "/ip hotspot user remove"
                filter_cmd = "/ip hotspot user print where name="
            elif conn_type.service_name in ["pppoe", "l2tp", "pptp"]:
                cmd = "/ppp secret remove"
                filter_cmd = "/ppp secret print where name="
            elif conn_type.service_name == "openvpn":
                cmd = "/interface ovpn-server user remove"
                filter_cmd = "/interface ovpn-server user print where name="
            else:
                frappe.throw(_("Unsupported connection type: {0}").format(conn_type.service_name))

            # Find user
            users = api.get_resource(filter_cmd).get(name=self.username_mikrotik)
            if users:
                # Remove user
                api.get_resource(cmd).remove(id=users[0].get("id"))
                
                # Log success
                self.create_api_log(
                    router=self.mikrotik_settings,
                    operation=f"remove_user_{conn_type.service_name}",
                    parameters=self.username_mikrotik,
                    status="Success"
                )
            
            api.close()
            
        except Exception as e:
            # Log failure
            self.create_api_log(
                router=self.mikrotik_settings,
                operation="remove_user_failed",
                parameters=str(e),
                status="Failed"
            )
            frappe.throw(_("Failed to remove MikroTik user: {0}").format(str(e)))

    def create_api_log(self, router, operation, parameters, status):
        """Create an API Log entry"""
        log = frappe.get_doc({
            "doctype": "MikroTik API Log",
            "router": router,
            "operation": operation,
            "parameters": parameters,
            "response": "",  # Can be updated if needed
            "status": status
        })
        log.insert(ignore_permissions=True)

    def get_valid_status(self):
        """Check if subscription is valid based on dates and quota"""
        if self.status == "Expired":
            return False
            
        if self.expiry_date < frappe.utils.today():
            return False
            
        # Check data quota if applicable
        plan = frappe.get_doc("Internet Plan", self.internet_plan)
        if plan.data_quota_mb and self.data_used_mb >= plan.data_quota_mb:
            return False
            
        return True

    @frappe.whitelist()
    def extend_validity(self, days):
        """Extend subscription validity"""
        if self.docstatus != 1:
            frappe.throw(_("Can only extend submitted subscriptions"))
            
        self.expiry_date = add_days(self.expiry_date, days)
        
        if self.status == "Expired":
            self.status = "Active"
            self.provision_mikrotik_user()
            
        self.save()

    @frappe.whitelist()
    def suspend(self):
        """Suspend subscription"""
        if self.status != "Active":
            frappe.throw(_("Can only suspend active subscriptions"))
            
        self.remove_mikrotik_user()
        self.status = "Suspended"
        self.save()

    @frappe.whitelist()
    def reactivate(self):
        """Reactivate suspended subscription"""
        if self.status != "Suspended":
            frappe.throw(_("Can only reactivate suspended subscriptions"))
            
        if not self.get_valid_status():
            frappe.throw(_("Subscription has expired or exceeded quota"))
            
        self.provision_mikrotik_user()
        self.status = "Active"
        self.save()

    @frappe.whitelist()
    def request_payment(self):
        """Request M-Pesa payment using frappe-mpsa-payments"""
        if self.payment_method != "M-Pesa":
            frappe.throw(_("This method is only for M-Pesa payments"))
            
        if self.payment_status == "Completed":
            frappe.throw(_("Payment already completed"))
            
        try:
            # Create a new Mpesa Express Request using frappe-mpsa-payments
            stk_push = frappe.get_doc({
                "doctype": "Mpesa Express Request",
                "phone_number": self.phone_number,
                "amount": self.price,
                "bill_ref_number": self.subscription_id,
                "subscription": self.name,
                "reference_doctype": self.doctype,
                "reference_name": self.name
            }).insert()
            
            stk_push.submit()
            return {"success": True, "message": "Payment initiated successfully"}
                
        except Exception as e:
            frappe.log_error(f"M-Pesa payment error for subscription {self.name}: {str(e)}")
            return {"success": False, "message": str(e)}

    def handle_payment_success(self, payment_reference=None, payment_type="M-Pesa"):
        """Centralized payment success handler"""
        try:
            self.payment_status = "Completed"
            self.payment_date = now()
            
            if payment_type == "M-Pesa":
                self.mpesa_transaction_id = payment_reference
            elif payment_type == "Invoice":
                self.billing_invoice = payment_reference

            if self.status == "Draft":
                self.status = "Active"
                self.provision_mikrotik_user()
                self.broadcast_status_update("active", f"Service activated after {payment_type} payment")
            elif self.status == "Suspended":
                self.reactivate()
                self.broadcast_status_update("reactivated", f"Service reactivated after {payment_type} payment")

            self.save()
            return True

        except Exception as e:
            frappe.log_error(f"Error processing {payment_type} payment for subscription {self.name}: {str(e)}")
            return False

    def on_payment_authorized(self, payment_doc):
        """Called by frappe-mpsa-payments when payment is authorized"""
        return self.handle_payment_success(payment_doc.trans_id, "M-Pesa")

    def broadcast_status_update(self, event_type, message):
        """Broadcast real-time status update"""
        try:
            frappe.publish_realtime(f'subscription_{self.name}_update', {
                'event': event_type,
                'message': message,
                'subscription_id': self.name,
                'status': self.status,
                'timestamp': now()
            })
        except Exception as e:
            frappe.log_error(f"Error broadcasting status update: {str(e)}")

    def on_update(self):
        """Handle subscription updates"""
        try:
            if self.has_value_changed('status'):
                self.broadcast_status_update('status_changed', f'Status changed to {self.status}')
                
            # Handle automatic suspension on expiry
            if self.status == "Active" and self.expiry_date < today():
                self.suspend()
                self.broadcast_status_update('expired', 'Subscription expired')
                
        except Exception as e:
            frappe.log_error(f"Error in on_update for subscription {self.name}: {str(e)}")

@frappe.whitelist()
def sync_usage_data():
    """Sync usage data for active subscriptions"""
    active = frappe.get_all(
        "Customer Subscription",
        filters={
            "status": "Active"
        },
        fields=["name", "username_mikrotik", "connection_type", 
                "mikrotik_settings", "internet_plan"]
    )
    
    for sub in active:
        try:
            subscription = frappe.get_doc("Customer Subscription", sub.name)
            router = frappe.get_doc("MikroTik Settings", subscription.mikrotik_settings)
            conn_type = frappe.get_doc("Connection Type", subscription.connection_type)
            
            # Get API connection
            api = router.get_api_connection()
            
            # Get usage data
            usage = frappe.get_doc("mikrotik_integration.api.mikrotik_api").get_usage(
                api, conn_type, subscription.username_mikrotik
            )
            
            # Update subscription
            if usage:
                subscription.data_used_mb = usage.get("data_used_mb", 0)
                if usage.get("last_login"):
                    subscription.last_login = usage["last_login"]
                
                # Check quota
                plan = frappe.get_doc("Internet Plan", subscription.internet_plan)
                if (plan.data_quota_mb and 
                    subscription.data_used_mb >= plan.data_quota_mb):
                    subscription.suspend()
                
                subscription.save()
                
                # Update last sync time on router
                router.last_sync = now()
                router.save()
            
            api.close()
            frappe.db.commit()
            
        except Exception as e:
            frappe.log_error(
                f"Error syncing usage for subscription {sub.name}: {str(e)}",
                "Usage Sync Error"
            )
            frappe.db.rollback()

@frappe.whitelist()
def process_expired_subscriptions():
    """Process expired subscriptions"""
    expired = frappe.get_all(
        "Customer Subscription",
        filters={
            "status": "Active",
            "expiry_date": ["<=", today()]
        },
        fields=["name"]
    )
    
    for sub in expired:
        try:
            subscription = frappe.get_doc("Customer Subscription", sub.name)
            subscription.suspend()
            subscription.broadcast_status_update('expired', 'Subscription expired')
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(
                f"Error processing expired subscription {sub.name}: {str(e)}",
                "Subscription Expiry Error"
            )
            frappe.db.rollback()

@job('short', timeout=1500)
def sync_router_status():
    """Sync router status for all active subscriptions"""
    active_subs = frappe.get_all(
        "Customer Subscription",
        filters={"status": ["in", ["Active", "Suspended"]]},
        fields=["name", "mikrotik_settings", "username_mikrotik", "status"]
    )
    
    for sub in active_subs:
        try:
            subscription = frappe.get_doc("Customer Subscription", sub.name)
            router = frappe.get_doc("MikroTik Settings", subscription.mikrotik_settings)
            
            # Check actual status in router
            router_status = router.check_user_status(subscription.username_mikrotik)
            
            # Sync status if different
            if router_status != subscription.status:
                subscription.status = router_status
                subscription.save()
                subscription.broadcast_status_update('router_sync', f'Status synced from router: {router_status}')
                
            frappe.db.commit()
            
        except Exception as e:
            frappe.log_error(f"Error syncing router status for {sub.name}: {str(e)}")
            frappe.db.rollback()

@frappe.whitelist()
def handle_invoice_submission(doc, method=None):
    """Handle Sales Invoice submission to update subscription status"""
    try:
        # Check if invoice is linked to a subscription
        subscription_id = frappe.db.get_value("Customer Subscription", 
            {"billing_invoice": doc.name}, "name")
            
        if subscription_id:
            subscription = frappe.get_doc("Customer Subscription", subscription_id)
            
            if doc.docstatus == 1:  # On Submit
                if not subscription.handle_payment_success(doc.name, "Invoice"):
                    frappe.throw(_("Failed to process subscription payment"))
            elif doc.docstatus == 2:  # On Cancel
                frappe.throw(_("Cannot cancel invoice linked to active subscription"))
            
    except Exception as e:
        frappe.log_error(
            f"Error processing Sales Invoice {doc.name} for subscription: {str(e)}",
            "Invoice Processing Error"
        )
        raise


