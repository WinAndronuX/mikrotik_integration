frappe.pages['mikrotik-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'MikroTik Dashboard',
        single_column: true
    });

    // Add page classes
    $(wrapper).find('.page-body').addClass('mikrotik-dashboard bg-gray-50 dark:bg-gray-900');

    // Add dark mode toggle that syncs with Frappe
    page.add_menu_item('Toggle Dark Mode', () => {
        frappe.ui.set_theme(frappe.ui.get_theme() === 'dark' ? 'light' : 'dark');
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

        // Add refresh button with loading animation
        this.page.set_primary_action(__('Refresh'), () => {
            let btn = me.page.btn_primary;
            btn.html(`<span class="loading-animation">${__('Refreshing')}</span>`);
            me.refresh().finally(() => {
                btn.html(__('Refresh'));
            });
        });

        // Add filter section
        this.page.add_field({
            fieldtype: 'Link',
            label: __('Router'),
            fieldname: 'router',
            options: 'MikroTik Settings',
            change: () => me.refresh()
        });

        // Add date range filter
        this.page.add_field({
            fieldtype: 'DateRange',
            label: __('Date Range'),
            fieldname: 'date_range',
            default: [
                frappe.datetime.add_days(frappe.datetime.now_date(), -30),
                frappe.datetime.now_date()
            ],
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
            <div class="stat-card bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm hover:shadow-md transition-all duration-300">
                <div class="absolute top-0 left-0 right-0 h-1 ${color}-bg opacity-75"></div>
                <div class="stat-title text-gray-600 dark:text-gray-400">${title}</div>
                <div class="stat-value text-2xl font-semibold text-gray-900 dark:text-white">${value}</div>
            </div>
        `).appendTo(this.stats_section);
    }

    make_active_users_section() {
        this.active_users_section = $('<div class="dashboard-section">').appendTo(this.page.main);
        
        // Add section header
        let header = $('<div class="section-header">').appendTo(this.active_users_section);
        $('<h2 class="section-title">' + __('Currently Active Users') + '</h2>').appendTo(header);
        
        // Add search field
        let search = $('<div class="search-box">').appendTo(header);
        this.user_filter = frappe.ui.form.make_control({
            parent: search,
            df: {
                fieldtype: 'Data',
                placeholder: __('Search users...'),
                onchange: () => this.filter_users()
            },
            render_input: true
        });
        
        // Create datatable wrapper
        let table_wrapper = $('<div class="data-table-wrapper">').appendTo(this.active_users_section);
        
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
        this.api_logs_section = $('<div class="dashboard-section">').appendTo(this.page.main);
        
        // Add section header
        let header = $('<div class="section-header">').appendTo(this.api_logs_section);
        let title_wrapper = $('<div class="d-flex align-items-center">').appendTo(header);
        $('<h2 class="section-title">' + __('Recent Failed API Calls') + '</h2>').appendTo(title_wrapper);
        this.error_count = $('<span class="badge bg-danger ms-2">0</span>').appendTo(title_wrapper);
        
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
        this.usage_chart_section = $('<div class="dashboard-section bg-white dark:bg-gray-800 rounded-lg shadow-sm">').appendTo(this.page.main);
        
        // Add title
        $('<div class="section-header border-b border-gray-200 dark:border-gray-700 p-4">'
          + '<h2 class="section-title text-lg font-semibold text-gray-900 dark:text-white">'
          + __('Daily Bandwidth Usage')
          + '</h2></div>').appendTo(this.usage_chart_section);
        
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
        
        // Clear existing data
        this.clear_data();
        
        // Fetch all data
        return frappe.call({
            method: 'mikrotik_integration.mikrotik_integration.api.get_dashboard_data',
            args: { router: router },
            callback: function(r) {
                if (r.message) {
                    me.render_data(r.message);
                    me.page.set_indicator(__('Last updated: {0}', [
                        frappe.datetime.now_datetime()
                    ]), 'green');
                }
            },
            error: function(r) {
                me.page.set_indicator(__('Failed to load data'), 'red');
                frappe.msgprint({
                    title: __('Error'),
                    message: __('Failed to load dashboard data. Please try again.'),
                    indicator: 'red'
                });
            }
        });
    }

    clear_data() {
        // Clear stats
        this.active_subs_card.find('.stat-value').text('...');
        this.total_usage_card.find('.stat-value').text('...');
        this.revenue_card.find('.stat-value').text('...');
        this.pending_payments_card.find('.stat-value').text('...');
        
        // Clear tables
        this.active_users_table.refresh([]);
        this.api_logs_table.refresh([]);
        
        // Clear chart
        this.usage_chart.update({
            labels: [],
            datasets: [{
                values: []
            }]
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