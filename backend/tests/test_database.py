import pytest
from sqlalchemy.orm import Session
from backend.app.database import engine, Base, SessionLocal
from backend.app.models.models import Product

@pytest.fixture(scope="module")
def db_session():
    # Setup
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    # Teardown
    session.close()

def test_product_creation(db_session: Session):
    gtin = "TEST99999999"
    # Ensure it doesn't already exist
    existing = db_session.query(Product).filter(Product.gtin == gtin).first()
    if existing:
        db_session.delete(existing)
        db_session.commit()

    product = Product(gtin=gtin, product_name="Test DB Product", category="test")
    db_session.add(product)
    db_session.commit()
    
    fetched = db_session.query(Product).filter(Product.gtin == gtin).first()
    assert fetched is not None
    assert fetched.product_name == "Test DB Product"
    
    # Clean up
    db_session.delete(fetched)
    db_session.commit()

def test_transaction_rollback(db_session: Session):
    gtin = "TEST_ROLLBACK"
    product = Product(gtin=gtin, product_name="Rollback Product")
    db_session.add(product)
    db_session.flush() # pending insertion
    
    # Simulate an error and rollback
    db_session.rollback()
    
    fetched = db_session.query(Product).filter(Product.gtin == gtin).first()
    assert fetched is None
