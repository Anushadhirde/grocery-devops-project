import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from app import create_app
from models import db, Product, Customer


@pytest.fixture
def app():
    flask_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )
    with flask_app.app_context():
        db.create_all()
    return flask_app


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_home_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data


def test_add_product(client):
    resp = client.post(
        "/products/add",
        data={"name": "Tomatoes", "category": "Vegetables", "price": "40", "stock": "50"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Tomatoes" in resp.data


def test_add_customer(client):
    resp = client.post(
        "/customers/add",
        data={"name": "Priya Sharma", "email": "priya@example.com", "address": "MG Road"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Priya Sharma" in resp.data


def test_add_to_cart_and_checkout(client, app):
    client.post("/products/add", data={"name": "Milk", "category": "Dairy", "price": "25", "stock": "10"})
    client.post("/customers/add", data={"name": "Ravi Kumar", "email": "ravi@example.com", "address": ""})

    with app.app_context():
        product = Product.query.filter_by(name="Milk").first()
        customer = Customer.query.filter_by(email="ravi@example.com").first()

    resp = client.post(
        "/cart/add", data={"product_id": product.id, "quantity": "2"}, follow_redirects=True
    )
    assert resp.status_code == 200

    resp = client.get("/cart")
    assert b"Milk" in resp.data

    resp = client.post(
        "/cart/checkout", data={"customer_id": customer.id}, follow_redirects=True
    )
    assert resp.status_code == 200
    assert b"placed successfully" in resp.data.lower() or b"orders" in resp.data.lower()

    with app.app_context():
        updated_product = Product.query.filter_by(name="Milk").first()
        assert updated_product.stock == 8  # 10 - 2


def test_cannot_order_more_than_stock(client, app):
    client.post("/products/add", data={"name": "Bread", "category": "Bakery", "price": "35", "stock": "1"})

    with app.app_context():
        product = Product.query.filter_by(name="Bread").first()

    resp = client.post(
        "/cart/add", data={"product_id": product.id, "quantity": "5"}, follow_redirects=True
    )
    assert resp.status_code == 200
    assert b"exceeds available stock" in resp.data.lower()


def test_api_products_json(client):
    client.post("/products/add", data={"name": "Eggs", "category": "Dairy", "price": "6", "stock": "100"})
    resp = client.get("/api/products")
    assert resp.status_code == 200
    data = resp.get_json()
    assert any(p["name"] == "Eggs" for p in data)


def test_metrics_endpoint_exists(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
