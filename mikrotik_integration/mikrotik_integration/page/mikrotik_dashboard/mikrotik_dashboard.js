frappe.pages['mikrotik-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'MikroTik Dashboard',
        single_column: true
    });

    // Initialize page
    frappe.mikrotik_dashboard = new frappe.MikroTikDashboard(page);
};

frappe.MikroTikDashboard = class MikroTikDashboard {
    constructor(page) {
        this.page = page;
        this.make();
        this.refresh();
    }

    make() {
        let me = this;

        // Add refresh button
        this.page.set_primary_action(__('Refresh'), () => me.refresh());

        // Add filter section
        this.page.add_field({
            fieldtype: 'Link',
            label: __('Router'),
            fieldname: 'router',
            options: 'MikroTik Settings',
            change: () => me.refresh()
        });

        // Create sections
        this.make_stats_section();
        this.make_active_users_section();
        this.make_api_logs_section();
        this.make_usage_chart_section();
    }

    make_stats_section() {
        this.stats_section = $('<div class="stats-section">').appendTo(this.page.main);
        
        // Create stat cards
        this.active_subs_card = this.make_stat_card(
            __('Active Subscriptions'),
            '0',
            'blue'
        );
        this.total_usage_card = this.make_stat_card(
            __('Total Data Used Today'),
            '0 MB',
            'green'
        );
        this.revenue_card = this.make_stat_card(
            __('Monthly Revenue'),
            '0',
            'orange'
        );
        this.pending_payments_card = this.make_stat_card(
            __('Pending Payments'),
            '0',
            'yellow'
        );
    }

    make_stat_card(title, value, color) {
        return $(`
            <div class="stat-card" style="border-left: 3px solid var(--${color}-500)">
                <div class="stat-title text-muted">${title}</div>
                <div class="stat-value h3">${value}</div>
            </div>
        `).appendTo(this.stats_section);
    }

    make_active_users_section() {
        this.active_users_section = $('<div class="active-users-section">').appendTo(this.page.main);
        
        // Add title
        $('<h5 class="mb-3">' + __('Currently Active Users') + '</h5>').appendTo(this.active_users_section);
        
        // Create datatable
        this.active_users_table = new frappe.DataTable(
            this.active_users_section[0],
            {
                columns: [
                    {name: 'customer', width: 200},
                    {name: 'username', width: 150},
                    {name: 'connection_type', width: 120},
                    {name: 'data_used', width: 120},
                    {name: 'uptime', width: 120},
                    {name: 'payment_status', width: 120},
                    {name: 'expiry', width: 120}
                ],
                data: []
            }
        );
    }

    make_api_logs_section() {
        this.api_logs_section = $('<div class="api-logs-section mt-4">').appendTo(this.page.main);
        
        // Add title with count
        $('<h5 class="mb-3">' + __('Recent Failed API Calls') + '</h5>').appendTo(this.api_logs_section);
        
        // Create datatable
        this.api_logs_table = new frappe.DataTable(
            this.api_logs_section[0],
            {
                columns: [
                    {name: 'timestamp', width: 150},
                    {name: 'operation', width: 150},
                    {name: 'router', width: 150},
                    {name: 'status', width: 100}
                ],
                data: []
            }
        );
    }

    make_usage_chart_section() {
        this.usage_chart_section = $('<div class="usage-chart-section mt-4">').appendTo(this.page.main);
        
        // Add title
        $('<h5 class="mb-3">' + __('Daily Bandwidth Usage') + '</h5>').appendTo(this.usage_chart_section);
        
        // Create chart
        this.usage_chart = new frappe.Chart(
            this.usage_chart_section[0],
            {
                data: {
                    labels: [],
                    datasets: [
                        {
                            name: __("Data Usage (MB)"),
                            values: []
                        }
                    ]
                },
                type: 'line',
                height: 300,
                colors: ['#7cd6fd']
            }
        );
    }

    refresh() {
        let me = this;
        let router = this.page.fields_dict.router.get_value();
        
        // Show loading state
        this.page.set_indicator(__('Refreshing...'), 'blue');
        
        // Fetch all data
        return frappe.call({
            method: 'mikrotik_integration.api.get_dashboard_data',
            args: { router: router },
            callback: function(r) {
                if (r.message) {
                    me.render_data(r.message);
                    me.page.set_indicator(__('Last updated: {0}', [
                        frappe.datetime.now_datetime()
                    ]), 'green');
                }
            }
        });
    }

    render_data(data) {
        // Update stats
        this.active_subs_card.find('.stat-value').text(data.stats.active_subscriptions);
        this.total_usage_card.find('.stat-value').text(
            format_number(data.stats.total_usage_mb, null, 0) + ' MB'
        );
        this.revenue_card.find('.stat-value').text(
            format_currency(data.stats.monthly_revenue, data.stats.currency)
        );
        this.pending_payments_card.find('.stat-value').text(data.stats.pending_payments);
        
        // Update active users table
        this.active_users_table.refresh(data.active_users);
        
        // Update API logs table
        this.api_logs_table.refresh(data.failed_api_calls);
        
        // Update usage chart
        this.usage_chart.update({
            labels: data.usage_chart.labels,
            datasets: [{
                values: data.usage_chart.values
            }]
        });
    }
};