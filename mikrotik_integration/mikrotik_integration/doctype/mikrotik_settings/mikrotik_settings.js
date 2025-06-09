// Copyright (c) 2025, ronoh and contributors
// For license information, please see license.txt

frappe.ui.form.on('MikroTik Settings', {
    refresh(frm) {
        // Update status indicator
        frappe.call({
            method: 'check_connection_status',
            doc: frm.doc,
            callback: function(r) {
                if (r.message) {
                    frm.page.set_indicator('Connected', 'green');
                } else {
                    frm.page.set_indicator('Disconnected', 'red');
                }
            }
        });

        frm.add_custom_button(__('Check Connection'), function() {
            frappe.call({
                method: 'check_connection_status',
                doc: frm.doc,
                freeze: true,
                freeze_message: __('Pinging router...'),
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint({
                            title: __('Connection Status'),
                            indicator: 'green',
                            message: __('Router is connected and responding')
                        });
                    } else {
                        frappe.msgprint({
                            title: __('Connection Status'),
                            indicator: 'red',
                            message: __('Router is not responding')
                        });
                    }
                }
            });
        }, __('Actions'));
    },
    
    api_host: function(frm) {
        // Remove toggle_reqd since fields are now optional
    },
    
    validate: function(frm) {
        // Only host is required
        if (!frm.doc.api_host) {
            frappe.throw(__('Router Host/IP is required'));
        }
    }
});
