"""Reusable setup for integration tests only.

A fixture is a named setup function. Asking for `store` or `client` as a test
argument tells pytest to run that fixture and provide its result. Default scope
is one test, so every test starts with its own catalog and empty order table.

Syntax used in this file:
- conftest.py is a special filename pytest automatically loads for fixtures in
  this directory and its children. Test files do not need to import it.
- @pytest.fixture is a decorator: @ applies extra behavior/metadata to the next
  function. Here it registers that function as reusable test setup.
- tmp_path is a built-in pytest fixture providing a unique temporary Path.
  The / operator on a Path joins a directory and filename; it is not division.
- return gives the prepared resource to the test. yield gives it to the test
  and pauses this fixture; pytest resumes afterward to finish cleanup, even if
  an assertion fails. A fixture can request other fixtures through its arguments.
- with ... as ... enters a context manager: a resource with setup and cleanup.
  For TestClient, entering runs app startup; leaving runs shutdown and closes
  client resources. Keeping yield inside with keeps the client open for the test.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.repository import Store


@pytest.fixture
def store(tmp_path):
    # tmp_path is built into pytest: a unique temporary directory for this test.
    # We use real SQLite files without touching the demo's data/store.sqlite3.
    database = Store(tmp_path / "store.sqlite3")
    database.initialize()
    return database


@pytest.fixture
def client(tmp_path):
    # TestClient connects directly to the app in this Python process. It runs
    # real routes, validation, pricing, and SQL, but does not open a network port.
    app = create_app(tmp_path / "api.sqlite3")
    with TestClient(app) as test_client:
        # The context manager runs application startup, including table creation.
        # yield provides the client, then resumes cleanup after the test finishes.
        yield test_client
