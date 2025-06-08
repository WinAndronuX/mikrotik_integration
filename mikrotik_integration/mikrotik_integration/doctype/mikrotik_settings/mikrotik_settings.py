# Copyright (c) 2025, ronoh and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
import routeros_api


class MikroTikSettings(Document):
    def validate(self):
        """Validate MikroTik settings and test connection"""
        self.validate_connection()
    
    def validate_connection(self):
        """Test connection to MikroTik router"""
        try:
            api = self.get_api_connection()
            # Try a simple command to test connection
            api.get_resource('/system/identity').get()
            frappe.msgprint(_('Successfully connected to MikroTik router'))
            api.close()
        except Exception as e:
            frappe.throw(_('Failed to connect to MikroTik router: {0}').format(str(e)))
    
    def get_api_connection(self):
        """Create and return a RouterOS API connection"""
        try:
            # Create connection pool
            pool = routeros_api.RouterOsApiPool(
                host=self.api_host,
                username=self.username,
                password=self.password,
                port=self.api_port,
                use_ssl=self.use_ssl,
                plaintext_login=True
            )
            return pool.get_api()
        except Exception as e:
            frappe.throw(_('Could not establish connection to router: {0}').format(str(e)))

    def after_save(self):
        """Clear the cache after saving settings"""
        frappe.cache().delete_key('mikrotik_settings')

    @frappe.whitelist()
    def test_connection(self):
        """Endpoint for testing connection from the frontend"""
        self.validate_connection()
        return True

def get_mikrotik_settings(router_name=None):
    """Get MikroTik settings, optionally filtered by router name"""
    filters = {"name": router_name} if router_name else {}
    return frappe.get_doc("MikroTik Settings", filters)
