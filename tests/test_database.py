from db.repository import get_connection, initialize_database, load_active_criteria
from db.seed import seed_database


def test_seed_is_idempotent_and_criteria_load_from_sqlite(tmp_path):
    path = tmp_path / "test.sqlite3"
    seed_database(path)
    seed_database(path)
    connection = get_connection(path)
    try:
        initialize_database(connection)
        criteria = load_active_criteria(connection)
        assert len(criteria) == 5
        assert sum(item.weight for item in criteria) == 100
        assert criteria[0].name == "Technical Capability"
    finally:
        connection.close()
