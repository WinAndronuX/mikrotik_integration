# Copyright (c) 2025, ronoh and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days
import json


class MikroTikAPILog(Document):
    def validate(self):
        """Validate log entry"""
        self.validate_json_fields()
        if not self.timestamp:
            self.timestamp = frappe.utils.now()

    def validate_json_fields(self):
        """Ensure parameters and response are valid JSON if not empty"""
        for field in ['parameters', 'response']:
            value = self.get(field)
            if value:
                try:
                    if isinstance(value, str):
                        # Try to parse if it's a string
                        json.loads(value)
                    else:
                        # If it's already a dict/list, convert to JSON string
                        self.set(field, json.dumps(value, indent=2))
                except ValueError:
                    frappe.throw(_("{0} must be valid JSON").format(
                        frappe.meta.get_label(self.doctype, field)
                    ))

    @staticmethod
    def clear_old_logs(days=30):
        """Delete logs older than specified days"""
        frappe.db.delete(
            "MikroTik API Log",
            {
                "timestamp": ("<=", frappe.utils.add_days(None, -days))
            }
        )
        frappe.db.commit()

    @staticmethod
    def get_stats(router=None, status=None, operation=None):
        """Get statistics about API calls"""
        filters = {}
        if router:
            filters["router"] = router
        if status:
            filters["status"] = status
        if operation:
            filters["operation"] = operation

        return frappe.db.get_all(
            "MikroTik API Log",
            filters=filters,
            fields=[
                "status",
                "operation",
                "router",
                "COUNT(*) as count",
                "MAX(timestamp) as last_occurrence"
            ],
            group_by="status, operation, router"
        )


@frappe.whitelist()
def clear_old_logs(days=30):
    """Delete logs older than specified days"""
    try:
        frappe.db.delete(
            "MikroTik API Log",
            {
                "timestamp": ("<=", add_days(None, -days))
            }
        )
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            f"Error clearing old API logs: {str(e)}",
            "API Log Cleanup Error"
        )
