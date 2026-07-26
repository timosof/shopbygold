from flask_mail import Message
from flask import current_app
from models import OrderItem, Product

def send_order_confirmation(app, order, user_email):
    try:
        with app.app_context():
            # FIX: Safe mail init
            if 'mail' not in current_app.extensions:
                print("Mail not initialized on Render")
                return False
                
            mail = current_app.extensions['mail']
            
            # FIX: Get items safely (works whether relationship is 'items' or 'order_items')
            try:
                # Try both possible relationship names
                order_items_list = getattr(order, 'items', None) or getattr(order, 'order_items', None)
                if not order_items_list:
                    # Fallback: Query directly
                    order_items_list = OrderItem.query.filter_by(order_id=order.id).all()
            except:
                order_items_list = OrderItem.query.filter_by(order_id=order.id).all()

            items_html = ""
            for item in order_items_list:
                try:
                    product = Product.query.get(item.product_id)
                    product_name = product.name if product else f"Product #{item.product_id}"
                    qty = item.quantity
                    price = float(item.price)
                    subtotal = price * qty
                    items_html += f'''
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{product_name}</td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">x{qty}</td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">₦{price:,.2f}</td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">₦{subtotal:,.2f}</td>
                    </tr>
                    '''
                except Exception as e:
                    print(f"Item render error: {e}")
                    continue

            # Email to customer
            msg = Message(
                subject=f'Order #{order.id} Confirmed - ShopByGold',
                recipients=[user_email]
            )
            msg.html = f'''
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #EAB308;">Thanks for your order!</h2>
                <p>Hi {order.customer_name},</p>
                <p>Your order <strong>#{order.id}</strong> has been received.</p>
                <div style="background: #f9f9f9; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <h3>Order Items:</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="background: #EAB308; color: white;">
                            <th style="padding: 8px;">Product</th>
                            <th style="padding: 8px;">Qty</th>
                            <th style="padding: 8px;">Price</th>
                            <th style="padding: 8px;">Subtotal</th>
                        </tr>
                        {items_html}
                    </table>
                    <h3 style="text-align: right;">Total: ₦{float(order.total):,.2f}</h3>
                </div>
                <div style="background: #f9f9f9; padding: 15px; border-radius: 8px;">
                    <p><b>Name:</b> {order.customer_name}</p>
                    <p><b>Phone:</b> {order.customer_phone}</p>
                    <p><b>Address:</b> {order.customer_address}</p>
                    <p><b>State:</b> {getattr(order, 'delivery_state', 'Not set')}</p>
                    <p><b>Delivery Fee:</b> ₦{float(getattr(order, 'delivery_fee', 0) or 0):,.2f}</p>
                    <p><b>Status:</b> {order.status.upper()}</p>
                </div>
            '''
            mail.send(msg)
            print(f"Customer email sent to {user_email}")

            # Email to admin
            admin_email = current_app.config.get('MAIL_USERNAME')
            if admin_email:
                admin_msg = Message(
                    subject=f'New Order #{order.id} - ₦{float(order.total):,.2f}',
                    recipients=[admin_email]
                )
                admin_msg.html = f'''
                <h2>New Order #{order.id}</h2>
                <p><b>Customer:</b> {order.customer_name} ({user_email})</p>
                <p><b>Phone:</b> {order.customer_phone}</p>
                <p><b>Address:</b> {order.customer_address}, {getattr(order, 'delivery_state', '')}</p>
                <p><b>Total:</b> ₦{float(order.total):,.2f}</p>
                <table border="1" width="100%">{items_html}</table>
                '''
                mail.send(admin_msg)
                print(f"Admin email sent to {admin_email}")
            
            return True
    except Exception as e:
        print(f"EMAIL CRITICAL ERROR: {e}")
        import traceback
        print(traceback.format_exc())
        return False  # Never crash the order
