// Copyright (c) 2025, ronoh and contributors
// For license information, please see license.txt

frappe.ui.form.on('MikroTik Settings', {
    refresh(frm) {
        frm.add_custom_button(__('Test Connection'), function() {
            frappe.call({
                method: 'test_connection',
                doc: frm.doc,
                freeze: true,
                freeze_message: __('Testing connection to MikroTik router...'),
                callback: function(r) {
                    if (r.exc) {
                        frappe.msgprint({
                            title: __('Connection Failed'),
                            indicator: 'red',
                            message: __('Could not connect to MikroTik router. Please check your settings.')
                        });
                    }
                }
            });
        }, __('Actions'));
    },
    
    api_host: function(frm) {
        frm.toggle_reqd(['api_port', 'username', 'password'], frm.doc.api_host);
    },
    
    validate: function(frm) {
        // Ensure required fields are filled when router settings are provided
        if (frm.doc.api_host) {
            ['api_port', 'username', 'password'].forEach(field => {
                if (!frm.doc[field]) {
                    frappe.throw(__(`${frappe.meta.get_label(frm.doctype, field, frm.doc.name)} is required`));
                }
            });
        }
    }
});
