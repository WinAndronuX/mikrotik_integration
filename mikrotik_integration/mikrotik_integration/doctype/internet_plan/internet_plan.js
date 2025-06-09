// Copyright (c) 2025, ronoh and contributors
// For license information, please see license.txt

frappe.ui.form.on('Internet Plan', {
    refresh(frm) {
        // Show reseller price if markup is set
        if (frm.doc.reseller_markup) {
            frm.add_custom_button(__('Calculate Reseller Price'), function() {
                frappe.call({
                    method: 'get_reseller_price',
                    doc: frm.doc,
                    callback: function(r) {
                        if (r.message) {
                            frappe.msgprint({
                                title: __('Reseller Price'),
                                indicator: 'green',
                                message: __('Reseller Price: {0} {1}', [
                                    frm.doc.currency,
                                    format_currency(r.message, frm.doc.currency)
                                ])
                            });
                        }
                    }
                });
            }, __('Actions'));
        }

        // Show profile details from Connection Type
        if (frm.doc.connection_type) {
            frm.add_custom_button(__('View Profile Details'), function() {
                frappe.set_route('Form', 'Connection Type', frm.doc.connection_type);
            }, __('Actions'));
        }

        // Preview subscription end date
        frm.add_custom_button(__('Preview End Date'), function() {
            let start_date = frappe.datetime.nowdate();
            let end_date = frappe.datetime.add_days(start_date, frm.doc.validity_days);
            frappe.msgprint({
                title: __('Subscription Period Preview'),
                indicator: 'blue',
                message: __('If subscribed today:<br>Start: {0}<br>End: {1}', [
                    frappe.datetime.str_to_user(start_date),
                    frappe.datetime.str_to_user(end_date)
                ])
            });
        }, __('Actions'));
    },


    validate(frm) {
        // Validate basic requirements
        if (frm.doc.validity_days <= 0) {
            frappe.throw(__('Validity Days must be greater than 0'));
        }
        
        if (frm.doc.data_quota_mb && frm.doc.data_quota_mb <= 0) {
            frappe.throw(__('Data Quota must be greater than 0 MB'));
        }
        
        if (frm.doc.price <= 0) {
            frappe.throw(__('Price must be greater than 0'));
        }
    },

    price(frm) {
        // When price changes, update the form
        frm.refresh_field('price');
        if (frm.doc.reseller_markup) {
            frm.trigger('reseller_markup');
        }
    },

    reseller_markup(frm) {
        // Calculate and show reseller price when markup changes
        if (frm.doc.reseller_markup && frm.doc.price) {
            let markup = flt(frm.doc.reseller_markup) / 100.0;
            let reseller_price = flt(frm.doc.price * (1 + markup), 2);
            
            frappe.show_alert({
                message: __('Reseller Price: {0} {1}', [
                    frm.doc.currency,
                    format_currency(reseller_price, frm.doc.currency)
                ]),
                indicator: 'green'
            });
        }
    }
});
