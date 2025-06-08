# Copyright (c) 2025, ronoh and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ConnectionType(Document):
    def validate(self):
        """Validate connection type settings"""
        self.validate_bandwidth_format()
        self.validate_parent_profile()
        self.validate_circular_inheritance()

    def validate_bandwidth_format(self):
        """Validate bandwidth limit formats"""
        for field in ['speed_limit_rx', 'speed_limit_tx', 'burst_limit_rx', 'burst_limit_tx']:
            if self.get(field):
                value = self.get(field).upper()
                if not value[-1] in ['K', 'M'] or not value[:-1].isdigit():
                    frappe.throw(_("{0} must be in format: NUMBER[K|M] (e.g., 2M or 512K)").format(
                        frappe.meta.get_label(self.doctype, field)
                    ))

    def validate_parent_profile(self):
        """Validate parent profile settings"""
        if self.parent_profile == self.name:
            frappe.throw(_("Parent Profile cannot be the same as the current profile"))

    def validate_circular_inheritance(self, visited=None):
        """Check for circular inheritance in parent profiles"""
        if visited is None:
            visited = set()
        
        if self.name in visited:
            frappe.throw(_("Circular inheritance detected in Connection Type profiles"))
        
        visited.add(self.name)
        
        if self.parent_profile:
            parent = frappe.get_doc("Connection Type", self.parent_profile)
            parent.validate_circular_inheritance(visited)

    def get_inherited_value(self, fieldname):
        """Get value for a field, considering inheritance from parent profile"""
        value = self.get(fieldname)
        if not value and self.parent_profile:
            parent = frappe.get_doc("Connection Type", self.parent_profile)
            return parent.get_inherited_value(fieldname)
        return value

    def get_bandwidth_limits(self):
        """Get all bandwidth limits, resolving from parent if needed"""
        return {
            'speed_limit_rx': self.get_inherited_value('speed_limit_rx'),
            'speed_limit_tx': self.get_inherited_value('speed_limit_tx'),
            'burst_limit_rx': self.get_inherited_value('burst_limit_rx'),
            'burst_limit_tx': self.get_inherited_value('burst_limit_tx')
        }
