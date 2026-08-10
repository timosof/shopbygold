from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from datetime import datetime, timedelta
import secrets

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'  # Explicit table name
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='customer')
    phone = db.Column(db.String(20), nullable=True)
    avatar = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # --- ADDED: Helper for admin check (does not break anything) ---
    @property
    def is_admin(self):
        return self.role == 'admin'

    @is_admin.setter
    def is_admin(self, value):
        self.role = 'admin' if value else 'customer'
    # --- END ADDED ---

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_admin': self.is_admin, #newlly added
            'created_at': self.created_at.isoformat()
        }

class Product(db.Model):
    __tablename__ = 'products'  # Explicit table name
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500))
    stock = db.Column(db.Integer, default=0)
    category = db.Column(db.String(100), default='general')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'image_url': self.image_url,
            'stock': self.stock,
            'category': self.category,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='pending')

    customer_name = db.Column(db.String(200))
    customer_phone = db.Column(db.String(20))
    customer_address = db.Column(db.Text)
    delivery_state = db.Column(db.String(100), default='Not set')  # New field for delivery state
    delivery_fee = db.Column(db.Float, default=0)

    payment_reference = db.Column(db.String(100), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('orders', lazy=True))
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        items = []
        for item in self.items:
            # This gets the product name safely
            product = Product.query.get(item.product_id)
            product_name = product.name if product else f'Product #{item.product_id} [Deleted]'

            items.append({
                'product_id': item.product_id,
                'product_name': product_name, # ← THIS IS THE KEY
                'quantity': item.quantity,
                'price': item.price,
                'subtotal': item.price * item.quantity
            })

        return {
            'id': self.id,
            'user_id': self.user_id,
            'total': self.total,
            'status': self.status,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'customer_address': self.customer_address,
            'payment_reference': self.payment_reference,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'items': items,
            'delivery_state': self.delivery_state,
            'delivery_fee': self.delivery_fee
        }

class OrderItem(db.Model):
    __tablename__ = 'order_items'  # Explicit table name
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)  # CHANGED: orders.id
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)  # CHANGED: products.id
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

    product = db.relationship('Product', backref=db.backref('order_items', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'price': self.price,
            'product_name': self.product.name if self.product else 'Deleted Product'
        }
    
from datetime import datetime

class Review(db.Model):
    __tablename__ = 'review'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # FIXED: users.id
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)  # FIXED: products.id
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='reviews')
    product = db.relationship('Product', backref='reviews')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'product_id': self.product_id,
            'rating': self.rating,
            'comment': self.comment,
            'username': self.user.username if self.user else 'Anonymous',
            'created_at': self.created_at.isoformat()
        }

class Setting(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(500), nullable=False)
    
    def to_dict(self):
        return {'key': self.key, 'value': self.value}

class Cart(db.Model):
    __tablename__ = 'cart'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('cart', uselist=False))
    items = db.relationship('CartItem', backref='cart', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        items = [item.to_dict() for item in self.items]  # self.items is relationship
        total = sum(item['price'] * item['quantity'] for item in items)
        return {
            'id': self.id,
            'user_id': self.user_id,
            'items': items,
            'total': total
        }


class CartItem(db.Model):
    _tablename_ = 'cart_items'
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)
    
    product = db.relationship('Product', backref='cart_items')
    
    def to_dict(self):
        product = Product.query.get(self.product_id)
        return {
            'id': self.id,
            'cart_id': self.cart_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'price': float(self.price),
            'product': {
                'id': product.id,
                'name': product.name,
                'price': float(product.price),
                'image_url': product.image_url if product else None,
                'stock': product.stock if product else 0
            } if product else None
        }
    

class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref='reset_tokens')
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.token = secrets.token_urlsafe(32)
        self.expires_at = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
    
    def is_valid(self):
        return not self.used and datetime.utcnow() < self.expires_at

class ShippingFee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String(50), unique=True, nullable=False)
    fee = db.Column(db.Float, default=1500)
    created_at = db.Column(db.DateTime, default=db.func.now())

    def to_dict(self):
        return {"state": self.state, "fee": self.fee}

class Slider(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), default="Welcome to ShopByGold")
    subtitle = db.Column(db.String(300), default="Let Get The Shopping Started!")
    image_url = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(500), nullable=True) # where to go when clicked
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=db.func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'subtitle': self.subtitle,
            'image_url': self.image_url,
            'link': self.link,
            'is_active': self.is_active,
            'display_order': self.display_order
        }

class Newsletter(db.Model):
    __tablename__ = 'newsletter'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
