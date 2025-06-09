# Copyright (c) 2025, ronoh and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class InternetPlan(Document):
    def validate(self):
        """Validate Internet Plan settings"""
        self.validate_validity()
        self.validate_pricing()
        self.validate_connection_type()

    def validate_validity(self):
        """Validate validity and quota settings"""
        if self.validity_days <= 0:
            frappe.throw(_("Validity Days must be greater than 0"))
        
        if self.data_quota_mb and self.data_quota_mb <= 0:
            frappe.throw(_("Data Quota must be greater than 0 MB"))

    def validate_pricing(self):
        """Validate pricing and markup"""
        if flt(self.price) <= 0:
            frappe.throw(_("Price must be greater than 0"))
        
        if self.reseller_markup and flt(self.reseller_markup) < 0:
            frappe.throw(_("Reseller Markup cannot be negative"))

    def validate_connection_type(self):
        """Validate that the selected Connection Type exists and is active"""
        if self.connection_type:
            conn_type = frappe.get_doc("Connection Type", self.connection_type)
            if not conn_type:
                frappe.throw(_("Connection Type {0} does not exist").format(self.connection_type))

    def get_reseller_price(self):
        """Calculate price including reseller markup"""
        if not self.reseller_markup:
            return self.price
        
        markup_multiplier = 1 + (flt(self.reseller_markup) / 100)
        return flt(self.price * markup_multiplier, 2)

    # def after_insert(self):
    #     """After inserting a new plan"""
    #     self.create_pricing_rule()

    # def create_pricing_rule(self):
    #     """Create a Pricing Rule for this plan if it doesn't exist"""
    #     if not frappe.db.exists("Pricing Rule", {"internet_plan": self.name}):
    #         pass
            # pricing_rule = frappe.get_doc({
            #     "doctype": "Pricing Rule",
            #     "title": f"Pricing Rule for {self.plan_name}",
            #     "apply_on": "Item Code",
            #     "internet_plan": self.name,
            #     "selling": 1,
            #     "rate": self.price,
            #     "currency": self.currency,
            #     "valid_from": frappe.utils.nowdate(),
            #     "company": frappe.defaults.get_defaults().company
            # })
            # pricing_rule.insert(ignore_permissions=True)

    # def on_update(self):
    #     """Update related pricing rules when plan is updated"""
    #     pricing_rules = frappe.get_all(
    #         "Pricing Rule",
    #         filters={"internet_plan": self.name}
    #     )
        
    #     for rule in pricing_rules:
    #         pr = frappe.get_doc("Pricing Rule", rule.name)
    #         pr.rate = self.price
    #         pr.currency = self.currency
    #         pr.save(ignore_permissions=True)

    def before_save(self):
        """Set title field"""
        self.title = self.plan_name
