app_name = "mikrotik_integration"
app_title = "Mikrotik Integration"
app_publisher = "ronoh"
app_description = "Full MikroTik RouterOS integration for ERPNext"
app_email = "ronoelisha625@gmail.com"
app_license = "mit"

# Includes in <head>
# ------------------

app_include_js = [
    "/assets/mikrotik_integration/js/mikrotik_integration.js"
]

# DocTypes
# --------
doc_events = {
    "Customer Subscription": {
        "validate": "mikrotik_integration.mikrotik_integration.doctype.customer_subscription.customer_subscription.CustomerSubscription.validate",
        "on_submit": "mikrotik_integration.mikrotik_integration.doctype.customer_subscription.customer_subscription.CustomerSubscription.on_submit",
        "before_cancel": "mikrotik_integration.mikrotik_integration.doctype.customer_subscription.customer_subscription.CustomerSubscription.before_cancel"
    },
    "Sales Invoice": {
        "on_submit": "mikrotik_integration.mikrotik_integration.doctype.customer_subscription.customer_subscription.handle_invoice_submission"
    },
    # M-Pesa integration handlers
    "Mpesa Express Request": {
        "on_payment_authorized": "mikrotik_integration.mikrotik_integration.doctype.customer_subscription.customer_subscription.on_payment_authorized"
    },
    "Mpesa C2B Register": {
        "on_payment_authorized": "mikrotik_integration.mikrotik_integration.doctype.customer_subscription.customer_subscription.on_payment_authorized"
    }
}

# Scheduled Tasks
scheduler_events = {
    "daily": [
        "mikrotik_integration.mikrotik_integration.doctype.customer_subscription.customer_subscription.process_expired_subscriptions",
        "mikrotik_integration.mikrotik_integration.doctype.mikrotik_api_log.mikrotik_api_log.clear_old_logs"
    ],
    "hourly": [
        "mikrotik_integration.mikrotik_integration.doctype.customer_subscription.customer_subscription.sync_usage_data"
    ],
    "cron": {
        "*/2 * * * *": [
            "mikrotik_integration.mikrotik_integration.doctype.customer_subscription.customer_subscription.sync_router_status"
        ],
        "*/5 * * * *": [
            "mikrotik_integration.utils.sync_all_routers"
        ]
    }
}

# After migrate hooks
after_migrate = [
    "mikrotik_integration.setup.after_migrate"
]

# Dashboard charts
charts = [
    {
        "chart_name": "Subscription Status",
        "chart_type": "Count",
        "doctype": "Customer Subscription",
        "group_by": "status",
        "is_public": 1,
        "timespan": "Last Month",
        "time_interval": "Daily",
        "type": "Bar"
    }
]

# Custom DocPerm
# -------------

# Workspace
# --------
workspaces = {
    "MikroTik Admin": {
        "category": "Modules",
        "label": "MikroTik Admin",
        "icon": "octicon octicon-radio-tower",
        "module": "Mikrotik Integration",
        "is_hidden": 0,
        "idx": 0,
        "links": [
            {
                "label": "Dashboard",
                "name": "mikrotik-dashboard",
                "type": "page",
                "doctype": "",
                "onboard": 0
            },
            {
                "label": "Settings",
                "name": "MikroTik Settings",
                "type": "doctype",
                "onboard": 1
            },
            {
                "label": "Connection Types",
                "name": "Connection Type",
                "type": "doctype",
                "onboard": 1
            },
            {
                "label": "Internet Plans",
                "name": "Internet Plan",
                "type": "doctype",
                "onboard": 1
            },
            {
                "label": "Customer Subscriptions",
                "name": "Customer Subscription",
                "type": "doctype",
                "onboard": 1
            },
            {
                "label": "API Logs",
                "name": "MikroTik API Log",
                "type": "doctype",
                "onboard": 0
            }
        ]
    }
}

# Override DocType Classes
doctype_js = {
    "Customer Subscription": "public/js/customer_subscription.js",
    "Internet Plan": "public/js/internet_plan.js"
}

# Custom Fields
# ------------
fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [
            ["dt", "in", (
                "Sales Invoice",
                "Customer"
            )]
        ]
    },
    {
        "doctype": "Property Setter"
    },
    {
        "doctype": "Workspace"
    }
]

