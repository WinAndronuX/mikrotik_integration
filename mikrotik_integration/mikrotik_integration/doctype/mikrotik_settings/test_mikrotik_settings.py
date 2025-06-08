# Copyright (c) 2025, ronoh and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from mikrotik_integration.mikrotik_integration.doctype.mikrotik_settings.mikrotik_settings import MikroTikSettings


class TestMikroTikSettings(FrappeTestCase):
    def setUp(self):
        # Create test router settings
        self.settings = frappe.get_doc({
            "doctype": "MikroTik Settings",
            "router_name": "Test Router",
            "api_host": "192.168.1.1",
            "api_port": 8728,
            "username": "admin",
            "password": "password123",
            "use_ssl": 0
        })
        
        try:
            self.settings.insert()
        except frappe.DuplicateEntryError:
            # If test record exists, get it
            self.settings = frappe.get_doc("MikroTik Settings", "Test Router")
    
    def tearDown(self):
        # Clean up test data
        if frappe.db.exists("MikroTik Settings", "Test Router"):
            frappe.delete_doc("MikroTik Settings", "Test Router")
    
    def test_settings_validation(self):
        """Test that required fields are properly enforced"""
        with self.assertRaises(frappe.ValidationError):
            invalid_settings = frappe.get_doc({
                "doctype": "MikroTik Settings",
                "router_name": "Invalid Router"
            }).insert()
    
    def test_connection_validation(self):
        """Test connection validation without actual API call"""
        # This will fail as we don't have a real router in test environment
        with self.assertRaises(Exception):
            self.settings.validate_connection()
    
    def test_get_settings(self):
        """Test get_mikrotik_settings utility function"""
        from mikrotik_integration.mikrotik_integration.doctype.mikrotik_settings.mikrotik_settings import get_mikrotik_settings
        
        # Test getting specific router settings
        settings = get_mikrotik_settings("Test Router")
        self.assertEqual(settings.router_name, "Test Router")
        
        # Test getting default settings
        settings = get_mikrotik_settings()
        self.assertIsNotNone(settings)
