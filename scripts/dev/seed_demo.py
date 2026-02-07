from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models import Customer, Order

def utcnow():
    return datetime.now(timezone.utc)

def main():
    db = SessionLocal()
    try:
        external_id = "telegram:12345"
        customer = db.scalar(select(Customer).where(Customer.external_id == external_id))
        if not customer:
            customer = Customer(
                id=uuid4(),
                external_id=external_id,
                channel="telegram",
                language_pref="am",
                created_at=utcnow(),
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)

        demo_orders = [
            ("ETH-1001", "shipped", "Bole", {"items": [{"sku": "SKU-1", "name": "Coffee", "qty": 2}]}),
            ("ETH-1002", "processing", "Kazanchis", {"items": [{"sku": "SKU-2", "name": "Tea", "qty": 1}]}),
        ]

        for order_id, status, area, items in demo_orders:
            existing = db.scalar(select(Order).where(Order.order_id == order_id))
            if existing:
                continue
            db.add(
                Order(
                    order_id=order_id,
                    customer_id=customer.id,
                    status=status,
                    delivery_area=area,
                    items=items,
                    notes="seeded demo order",
                    created_at=utcnow(),
                )
            )
        db.commit()
        print("Seeded demo customer + orders.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
