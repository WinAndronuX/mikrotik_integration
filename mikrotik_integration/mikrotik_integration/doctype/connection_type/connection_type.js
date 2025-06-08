// Copyright (c) 2025, ronoh and contributors
// For license information, please see license.txt

frappe.ui.form.on("Connection Type", {
    refresh(frm) {
        // Show inherited values from parent profile
        if (frm.doc.parent_profile) {
            frm.add_custom_button(__('Show Inherited Values'), function() {
                show_inherited_values(frm);
            });
        }

        // Format bandwidth fields on save
        ['speed_limit_rx', 'speed_limit_tx', 'burst_limit_rx', 'burst_limit_tx'].forEach(field => {
            frm.set_value_if_missing(field, '');
        });
    },

    validate(frm) {
        // Validate bandwidth format
        ['speed_limit_rx', 'speed_limit_tx', 'burst_limit_rx', 'burst_limit_tx'].forEach(field => {
            let value = frm.doc[field];
            if (value) {
                value = value.toUpperCase();
                if (!value.endsWith('K') && !value.endsWith('M')) {
                    frappe.throw(__(`${frappe.meta.get_label(frm.doctype, field)} must end with K or M`));
                }
                let num = value.slice(0, -1);
                if (isNaN(num)) {
                    frappe.throw(__(`${frappe.meta.get_label(frm.doctype, field)} must be a number followed by K or M`));
                }
                frm.set_value(field, value);
            }
        });
    },

    parent_profile(frm) {
        if (frm.doc.parent_profile) {
            show_inherited_values(frm);
        }
    }
});

function show_inherited_values(frm) {
    frappe.call({
        method: 'get_bandwidth_limits',
        doc: frm.doc,
        callback: function(r) {
            if (r.message) {
                let html = '<table class="table table-bordered">';
                html += '<tr><th>' + __('Field') + '</th><th>' + __('Inherited Value') + '</th></tr>';
                
                for (let field in r.message) {
                    if (r.message[field] && !frm.doc[field]) {
                        html += `<tr>
                            <td>${frappe.meta.get_label(frm.doctype, field)}</td>
                            <td>${r.message[field]}</td>
                        </tr>`;
                    }
                }
                
                html += '</table>';
                
                frappe.msgprint({
                    title: __('Inherited Values from Parent Profile'),
                    indicator: 'blue',
                    message: html
                });
            }
        }
    });
}
