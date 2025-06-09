# Copyright (c) 2025, ronoh and Contributors
# See license.txt

# import frappe
from frappe.tests.utils import FrappeTestCase
import frappe


class TestConnectionType(FrappeTestCase):
	def setUp(self):
		# Create test profile
		self.test_profile = frappe.get_doc({
			"doctype": "Connection Type",
			"connection_code": "TEST_PROFILE",
			"service_name": "hotspot",
			"profile_name": "test-profile",
			"speed_limit_rx": "1M",
			"speed_limit_tx": "512K"
		}).insert()

	def test_bandwidth_validation(self):
		"""Test bandwidth format validation"""
		# Test invalid format
		profile = frappe.copy_doc(self.test_profile)
		profile.speed_limit_rx = "1MB"  # Invalid format
		self.assertRaises(frappe.ValidationError, profile.insert)

		# Test valid formats
		valid_formats = ["1M", "512K", "2M", "256K"]
		for speed in valid_formats:
			profile = frappe.copy_doc(self.test_profile)
			profile.connection_code = f"TEST_{speed}"
			profile.speed_limit_rx = speed
			profile.insert()
			self.assertTrue(frappe.db.exists("Connection Type", profile.name))

	def tearDown(self):
		frappe.db.rollback()
