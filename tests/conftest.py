from datetime import date

import pytest

from app.db import get_conn


@pytest.fixture()
def conn(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "teste.db"))
    c = get_conn()
    yield c
    c.close()


@pytest.fixture()
def hoje():
    return date.today()
