# Copyright (c) 2025, ronoh and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
import socket

class MikroTikSettings(Document):
    def validate(self):
        """Validate MikroTik settings"""
        pass
    
    def get_api_connection(self):
        """Create and return a RouterOS API connection"""
        try:
            host = self.api_host.strip()
            port = self.api_port or 8728  # Default API port
            
            # Create socket with longer timeout
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 5 second timeout
            
            # Connect directly without SSL
            sock.connect((host, port))
            sock.close()
            return True
            
        except Exception as e:
            frappe.throw(_('Could not establish connection to router: {0}').format(str(e)))

    def validate_connection(self):
        """Test connection to MikroTik router"""
        try:
            if self.get_api_connection():
                frappe.msgprint(_('Successfully connected to MikroTik router'))
        except Exception as e:
            frappe.throw(_('Failed to connect to MikroTik router: {0}').format(str(e)))

    def after_save(self):
        """Clear the cache after saving settings"""
        frappe.cache().delete_key('mikrotik_settings')

    @frappe.whitelist()
    def test_connection(self):
        """Endpoint for testing connection from the frontend"""
        self.validate_connection()
        return True

    @frappe.whitelist()
    def check_connection_status(self):
        """Simple ping test to router"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)  # Quick timeout for ping-like behavior
            sock.connect((self.api_host.strip(), self.api_port or 8728))
            sock.close()
            return True
        except:
            return False
    
def get_mikrotik_settings(router_name=None):
    """Get MikroTik settings, optionally filtered by router name"""
    filters = {"name": router_name} if router_name else {}
    return frappe.get_doc("MikroTik Settings", filters)

def get_data():
    """Get dashboard data for MikroTik Settings"""
    return {
        'fieldname': 'router_name',
        'non_standard_fieldnames': {},
        'transactions': [
            {
                'label': _('Status'),
                'items': ['connection_status']
            }
        ]
    }

def get_connection_status():
    """Get current connection status for all routers"""
    routers = frappe.get_all('MikroTik Settings', fields=['name', 'router_name', 'api_host'])
    return [{
        'name': router.name,
        'router_name': router.router_name,
        'status': 'Connected' if check_router_status(router.api_host) else 'Disconnected'
    } for router in routers]

def check_router_status(host):
    """Check if a specific router is responding"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect((host.strip(), 8728))
        sock.close()
        return True
    except:
        return False
