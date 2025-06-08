# MikroTik Integration Documentation

## Overview
The MikroTik Integration app provides seamless integration between ERPNext and MikroTik RouterOS devices for ISP management. It enables automated user provisioning, bandwidth management, and M-Pesa payment integration.

## Key Features
- Automated user management in MikroTik routers
- Multiple connection types support (PPPoE, Hotspot, L2TP, PPTP, OpenVPN)
- Integrated M-Pesa payments using frappe-mpsa-payments
- Usage tracking and quota management
- Real-time status updates
- Automated subscription management

## Architecture

### DocTypes Overview

1. **Customer Subscription**
   - Core doctype managing internet subscriptions
   - Links to ERPNext Customer doctype
   - Handles user provisioning, payments, and status management
   - Integrates with M-Pesa for payments
   - Fields:
     - customer (Link to ERPNext Customer)
     - internet_plan (Link to Internet Plan)
     - connection_type (Link to Connection Type)
     - mikrotik_settings (Link to MikroTik Settings)
     - status (Select: Draft, Active, Suspended, Expired)
     - payment_method (Select: M-Pesa, Other)
     - payment_status (Select: Pending, Completed, Failed)

2. **Internet Plan**
   - Defines available internet packages
   - Manages pricing and quotas
   - Fields:
     - plan_name
     - validity_days
     - data_quota_mb
     - price
     - description

3. **Connection Type**
   - Configures MikroTik service types
   - Manages bandwidth profiles
   - Fields:
     - service_name (hotspot, pppoe, l2tp, pptp, openvpn)
     - profile_name
     - speed_limit_rx/tx
     - burst_limit_rx/tx

4. **MikroTik Settings**
   - Stores router connection details
   - Manages API credentials
   - Fields:
     - router_name
     - ip_address
     - api_username
     - api_password
     - api_port

5. **MikroTik API Log**
   - Tracks API operations
   - Maintains audit trail
   - Fields:
     - router
     - operation
     - parameters
     - status
     - timestamp

### Integration with ERPNext

1. **Customer Integration**
   - Links to ERPNext Customer doctype
   - Inherits customer details and contact information
   - Synchronizes customer status

2. **Payment Integration**
   - Uses ERPNext Payment Entry doctype
   - Integrates with Sales Invoice
   - M-Pesa payments handled through frappe-mpsa-payments

3. **Accounting Integration**
   - Creates journal entries for payments
   - Updates accounts receivable
   - Tracks subscription revenue

## M-Pesa Integration

The app integrates with frappe-mpsa-payments for M-Pesa payment processing. This integration is handled automatically through document events and requires minimal custom code.

### Integration Overview

1. **Document Setup**
   - Customer Subscription doctype is configured to work with frappe-mpsa-payments
   - Payment references are automatically linked using subscription_id and bill_ref_number
   - No additional M-Pesa configuration needed beyond frappe-mpsa-payments setup

2. **Payment Flow**
   - User initiates subscription payment
   - frappe-mpsa-payments handles STK Push and validation
   - Callbacks are processed automatically
   - Subscription status updates based on payment status

3. **Automatic Service Provisioning**
   - On successful payment, service is automatically activated
   - MikroTik user credentials are provisioned
   - Real-time status updates are broadcast

### Implementation Details

The integration leverages frappe-mpsa-payments' built-in functionality:

```python
# Payment initialization is handled by frappe-mpsa-payments
def initiate_mpesa_payment(self):
    """Request M-Pesa payment via frappe-mpsa-payments"""
    if self.payment_method != "M-Pesa":
        frappe.throw(_("This method is only for M-Pesa payments"))
        
    if self.payment_status == "Completed":
        frappe.throw(_("Payment already completed"))
        
    # Create Mpesa Express Request - handled by frappe-mpsa-payments
    stk_push = frappe.get_doc({
        "doctype": "Mpesa Express Request",
        "phone_number": self.phone_number,
        "amount": self.price,
        "bill_ref_number": self.subscription_id,
        "subscription": self.name,
        "description": f"Internet Subscription - {self.internet_plan}"
    }).insert()
    
    return {"success": True, "message": "Payment initiated. Check your phone to complete."}

# Payment callback is handled by frappe-mpsa-payments hooks
def handle_mpesa_callback(self, callback_data):
    """Process M-Pesa payment callback"""
    try:
        if callback_data.get("ResultCode") == "0":
            self.payment_status = "Completed"
            self.payment_date = now()
            self.mpesa_transaction_id = callback_data.get("TransID")
            
            if self.status == "Draft":
                self.status = "Active"
                self.provision_mikrotik_user()
            elif self.status == "Suspended":
                self.reactivate()
                
            self.save()
            
        return self.payment_status == "Completed"
            
    except Exception as e:
        frappe.log_error(f"M-Pesa callback error: {str(e)}")
        return False
```

### Key Benefits

1. **Simplified Integration**
   - Uses frappe-mpsa-payments' proven payment handling
   - Automatic payment entry creation
   - Built-in error handling and logging

2. **Reliable Processing**
   - Payment validation by frappe-mpsa-payments
   - Automatic currency conversion
   - Secure payment handling

3. **Easy Maintenance**
   - No duplicate payment processing code
   - Centralized M-Pesa configuration
   - Standardized payment flows

## Scheduled Tasks

1. **Usage Sync (Hourly)**
   - Updates data usage statistics
   - Checks quota limits
   - Updates last login times

2. **Expiry Check (Daily)**
   - Processes expired subscriptions
   - Suspends overdue accounts
   - Sends notifications

3. **Router Status Sync (Every 2 minutes)**
   - Verifies user status in router
   - Synchronizes status changes
   - Updates connection state

## Real-time Updates

The app uses Frappe's realtime events for status updates:

```python
def broadcast_status_update(self, event_type, message):
    frappe.publish_realtime(f'subscription_{self.name}_update', {
        'event': event_type,
        'message': message,
        'subscription_id': self.name,
        'status': self.status,
        'timestamp': now()
    })
```

## Error Handling

- Comprehensive error logging
- Transaction management
- Automated retry mechanisms
- Error notifications

## Setup Instructions

1. Install Prerequisites:
   ```bash
   bench get-app https://github.com/navariltd/frappe-mpsa-payments
   bench get-app https://github.com/your-repo/mikrotik_integration
   bench --site your-site install-app mikrotik_integration
   ```

2. Configure M-Pesa Settings:
   - Set up frappe-mpsa-payments
   - Configure callback URLs
   - Set up payment credentials

3. Configure MikroTik Settings:
   - Add router details
   - Set up API access
   - Configure service profiles

## Best Practices

1. **Security**
   - Use secure API credentials
   - Implement rate limiting
   - Regular security audits

2. **Performance**
   - Optimize API calls
   - Implement caching
   - Use background jobs

3. **Maintenance**
   - Regular log cleanup
   - Monitor system resources
   - Backup configurations

## Troubleshooting

Common issues and solutions:

1. **Payment Issues**
   - Verify M-Pesa credentials
   - Check callback URLs
   - Review payment logs

2. **Router Issues**
   - Verify API access
   - Check network connectivity
   - Review API logs

3. **Subscription Issues**
   - Check customer status
   - Verify plan details
   - Review usage data

## API Reference

The app exposes several API endpoints:

1. **Subscription Management**
   - Create/Update subscriptions
   - Manage user status
   - Handle payments

2. **Usage Tracking**
   - Get usage statistics
   - Check quota status
   - Monitor connections

3. **Payment Integration**
   - Initiate payments
   - Handle callbacks
   - Process refunds

## Support and Updates

For support:
- GitHub Issues: [Link to repo]
- Documentation: [Link to docs]
- Community Forum: [Link to forum]

## License
MIT License - See LICENSE.txt for details