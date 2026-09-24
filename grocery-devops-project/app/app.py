import os
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from prometheus_client import CollectorRegistry
from prometheus_flask_exporter import PrometheusMetrics

from models import db, Product, Customer, Order, OrderItem


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    db_path = os.environ.get("DATABASE_URL", "sqlite:///grocery.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = db_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    # Prometheus metrics for monitoring (exposes /metrics).
    # A fresh registry is used per app instance so create_app() can be called
    # multiple times safely (e.g. once per test) without duplicate-metric errors.
    metrics = PrometheusMetrics(app, registry=CollectorRegistry())
    metrics.info("grocery_app_info", "Grocery Ordering App", version="1.0.0")

    with app.app_context():
        db.create_all()

    # ---------- Health check (used by Docker/Jenkins/monitoring) ----------
    @app.route("/health")
    def health():
        return jsonify(status="ok", time=datetime.utcnow().isoformat())

    # ---------- Home / Dashboard ----------
    @app.route("/")
    def index():
        stats = {
            "total_products": Product.query.count(),
            "total_customers": Customer.query.count(),
            "pending_orders": Order.query.filter_by(status="Pending").count(),
        }
        return render_template("index.html", stats=stats)

    # ---------- Products ----------
    @app.route("/products")
    def list_products():
        products = Product.query.order_by(Product.category, Product.name).all()
        return render_template("products.html", products=products)

    @app.route("/products/add", methods=["GET", "POST"])
    def add_product():
        if request.method == "POST":
            name = request.form["name"].strip()
            category = request.form.get("category", "General").strip() or "General"
            price = float(request.form["price"])
            stock = int(request.form.get("stock", 0))

            if not name or price < 0:
                flash("Valid product name and price are required.", "danger")
                return redirect(url_for("add_product"))

            product = Product(name=name, category=category, price=price, stock=stock)
            db.session.add(product)
            db.session.commit()
            flash(f'Product "{name}" added.', "success")
            return redirect(url_for("list_products"))

        return render_template("add_product.html")

    @app.route("/products/<int:product_id>/delete", methods=["POST"])
    def delete_product(product_id):
        product = Product.query.get_or_404(product_id)
        db.session.delete(product)
        db.session.commit()
        flash("Product removed.", "success")
        return redirect(url_for("list_products"))

    # ---------- Customers ----------
    @app.route("/customers")
    def list_customers():
        customers = Customer.query.order_by(Customer.name).all()
        return render_template("customers.html", customers=customers)

    @app.route("/customers/add", methods=["GET", "POST"])
    def add_customer():
        if request.method == "POST":
            name = request.form["name"].strip()
            email = request.form["email"].strip()
            address = request.form.get("address", "").strip()

            if not name or not email:
                flash("Name and email are required.", "danger")
                return redirect(url_for("add_customer"))

            customer = Customer(name=name, email=email, address=address)
            db.session.add(customer)
            db.session.commit()
            flash(f'Customer "{name}" registered.', "success")
            return redirect(url_for("list_customers"))

        return render_template("add_customer.html")

    # ---------- Cart (session based) ----------
    def _get_cart():
        return session.setdefault("cart", {})  # {product_id_str: quantity}

    @app.route("/cart")
    def view_cart():
        cart = _get_cart()
        items = []
        total = 0.0
        for pid, qty in cart.items():
            product = Product.query.get(int(pid))
            if product:
                subtotal = product.price * qty
                total += subtotal
                items.append({"product": product, "quantity": qty, "subtotal": subtotal})
        customers = Customer.query.all()
        return render_template("cart.html", items=items, total=round(total, 2), customers=customers)

    @app.route("/cart/add", methods=["POST"])
    def add_to_cart():
        product_id = request.form["product_id"]
        quantity = int(request.form.get("quantity", 1))
        product = Product.query.get_or_404(int(product_id))

        if quantity < 1 or quantity > product.stock:
            flash("Requested quantity exceeds available stock.", "danger")
            return redirect(url_for("list_products"))

        cart = _get_cart()
        cart[product_id] = cart.get(product_id, 0) + quantity
        session["cart"] = cart
        flash(f"Added {quantity} x {product.name} to cart.", "success")
        return redirect(url_for("list_products"))

    @app.route("/cart/remove/<int:product_id>", methods=["POST"])
    def remove_from_cart(product_id):
        cart = _get_cart()
        cart.pop(str(product_id), None)
        session["cart"] = cart
        return redirect(url_for("view_cart"))

    @app.route("/cart/checkout", methods=["POST"])
    def checkout():
        cart = _get_cart()
        customer_id = request.form.get("customer_id")

        if not cart:
            flash("Your cart is empty.", "danger")
            return redirect(url_for("view_cart"))
        if not customer_id:
            flash("Please select a customer.", "danger")
            return redirect(url_for("view_cart"))

        order = Order(customer_id=int(customer_id), status="Pending")
        db.session.add(order)
        db.session.flush()  # get order.id before commit

        for pid, qty in cart.items():
            product = Product.query.get(int(pid))
            if not product or product.stock < qty:
                db.session.rollback()
                flash(f"Not enough stock for {product.name if product else 'a product'}.", "danger")
                return redirect(url_for("view_cart"))
            product.stock -= qty
            item = OrderItem(order_id=order.id, product_id=product.id, quantity=qty, price_at_order=product.price)
            db.session.add(item)

        db.session.commit()
        session["cart"] = {}
        flash(f"Order #{order.id} placed successfully.", "success")
        return redirect(url_for("list_orders"))

    # ---------- Orders ----------
    @app.route("/orders")
    def list_orders():
        orders = Order.query.order_by(Order.order_date.desc()).all()
        return render_template("orders.html", orders=orders)

    @app.route("/orders/<int:order_id>")
    def order_detail(order_id):
        order = Order.query.get_or_404(order_id)
        return render_template("order_detail.html", order=order)

    @app.route("/orders/<int:order_id>/status", methods=["POST"])
    def update_order_status(order_id):
        order = Order.query.get_or_404(order_id)
        new_status = request.form.get("status")
        if new_status in ("Pending", "Delivered", "Cancelled"):
            order.status = new_status
            db.session.commit()
            flash(f"Order #{order.id} marked as {new_status}.", "success")
        return redirect(url_for("order_detail", order_id=order.id))

    # ---------- Simple JSON API (useful for automated tests) ----------
    @app.route("/api/products")
    def api_products():
        return jsonify([p.to_dict() for p in Product.query.all()])

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
