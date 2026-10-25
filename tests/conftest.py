import mongomock
import pytest
from mongoengine import connect, disconnect


@pytest.fixture(autouse=True)
def mongo_db():
    connect(
        "test_db",
        host="mongodb://localhost",
        mongo_client_class=mongomock.MongoClient,
    )
    yield
    disconnect()
