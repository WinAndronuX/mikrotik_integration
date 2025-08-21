// Copyright (c) 2025, ronoh and contributors
// For license information, please see license.txt

frappe.ui.form.on('Customer Subscription', {
    refresh: function(frm) {
        // Add action buttons based on status
        if (frm.doc.docstatus === 1) {  // Submitted
            if (frm.doc.status === "Active") {
                frm.add_custom_button(__('Suspend'), function() {
                    frm.call('suspend').then(() => frm.refresh());
                }, __('Actions'));
                
                frm.add_custom_button(__('Extend Validity'), function() {
                    let d = new frappe.ui.Dialog({
                        title: __('Extend Subscription'),
                        fields: [
                            {
                                label: __('Days'),
                                fieldname: 'days',
                                fieldtype: 'Int',
                                reqd: 1,
                                description: __('Number of days to extend')
                            }
                        ],
                        primary_action_label: __('Extend'),
                        primary_action: function(values) {
                            frm.call('extend_validity', {
                                days: values.days
                            }).then(() => {
                                d.hide();
                                frm.refresh();
                            });
                        }
                    });
                    d.show();
                }, __('Actions'));
            }
            else if (frm.doc.status === "Suspended") {
                frm.add_custom_button(__('Reactivate'), function() {
                    frm.call('reactivate').then(() => frm.refresh());
                }, __('Actions'));
            }

            // Show credentials button
            frm.add_custom_button(__('Show Credentials'), function() {
                frappe.msgprint({
                    title: __('MikroTik Credentials'),
                    indicator: 'blue',
                    message: __(
                        'Username: {0}<br>Password: {1}',
                        [frm.doc.username_mikrotik, frm.doc.password_mikrotik]
                    )
                });
            }, __('View'));

            // Add usage check button
            frm.add_custom_button(__('Check Usage'), function() {
                frappe.call({
                    method: 'mikrotik_integration.api.get_current_usage',
                    args: {
                        subscription: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message) {
                            let usage = r.message;
                            frappe.msgprint({
                                title: __('Current Usage'),
                                indicator: 'blue',
                                message: __(
                                    'Data Used: {0} MB<br>Last Login: {1}',
                                    [
                                        format_number(usage.data_used_mb, null, 0),
                                        usage.last_login ? frappe.datetime.str_to_user(usage.last_login) : 'Never'
                                    ]
                                )
                            });
                        }
                    }
                });
            }, __('View'));
        }

        // Add provision button in draft
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Test Provision'), function() {
                // Validate required fields
                if (!frm.doc.mikrotik_settings || !frm.doc.connection_type) {
                    frappe.msgprint({
                        title: __('Missing Information'),
                        indicator: 'red',
                        message: __('Please fill in MikroTik Settings and Connection Type first')
                    });
                    return;
                }

                frappe.call({
                    method: 'mikrotik_integration.mikrotik_integration.api.test_provision',
                    args: {
                        subscription: frm.doc.name
                    },
                    freeze: true,
                    freeze_message: __('Testing MikroTik Connection...'),
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            frappe.msgprint({
                                title: __('Test Successful'),
                                indicator: 'green',
                                message: r.message.message || __('Connection test successful. User can be provisioned.')
                            });
                        } else if (r.message) {
                            frappe.msgprint({
                                title: __('Test Failed'),
                                indicator: 'red',
                                message: r.message.message || __('Connection test failed.')
                            });
                        }
                    }
                });
            });
        }
    },

    setup: function(frm) {
        // Set filters for linked fields
        frm.set_query('internet_plan', function() {
            return {
                filters: {
                    'status': 'Active'
                }
            };
        });

        frm.set_query('mikrotik_settings', function() {
            return {
                filters: {
                    'disabled': 0
                }
            };
        });
    },

    validate: function(frm) {
        // Ensure start date is not in the past for new subscriptions
        if (!frm.doc.docstatus && !frm.doc.amended_from) {
            let today = frappe.datetime.get_today();
            if (frm.doc.start_date < today) {
                frappe.msgprint({
                    title: __('Validation'),
                    indicator: 'red',
                    message: __('Start Date cannot be in the past')
                });
                return false;
            }
        }
    },

    start_date: function(frm) {
        // Update expiry date when start date changes
        if (frm.doc.internet_plan && frm.doc.start_date) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Internet Plan',
                    name: frm.doc.internet_plan
                },
                callback: function(r) {
                    if (r.message) {
                        let plan = r.message;
                        frm.set_value('expiry_date', 
                            frappe.datetime.add_days(frm.doc.start_date, plan.validity_days));
                    }
                }
            });
        }
    },

    internet_plan: function(frm) {
        // Set connection type and price from plan
        if (frm.doc.internet_plan) {
            frappe.model.with_doc('Internet Plan', frm.doc.internet_plan, function() {
                let plan = frappe.get_doc('Internet Plan', frm.doc.internet_plan);
                frm.set_value('connection_type', plan.connection_type);
                frm.set_value('price', plan.price);
                frm.set_value('currency', plan.currency);
                
                // Update expiry date
                if (frm.doc.start_date) {
                    frm.set_value('expiry_date', 
                        frappe.datetime.add_days(frm.doc.start_date, plan.validity_days));
                }
            });
        }
    }
});
