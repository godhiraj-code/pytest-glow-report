import multiprocessing
import sqlite3

import pytest

from beautiful_report.core import HistoryManager


def _create_v1_database(path, with_errors=False):
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE runs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, "
                     "passed INTEGER, failed INTEGER, skipped INTEGER, duration REAL)")
        conn.execute("INSERT INTO runs VALUES (1, '2026-10-23T12:00:00', 3, 1, 2, 4.5)")
        if with_errors:
            conn.execute("ALTER TABLE runs ADD COLUMN errors INTEGER NOT NULL DEFAULT 0")
        conn.execute("PRAGMA user_version = 1")


def _open_history_together(path, barrier, results):
    try:
        barrier.wait(timeout=30)
        HistoryManager(path)
        results.put(None)
    except Exception as exc:
        results.put(repr(exc))


@pytest.mark.parametrize("existing_v1", [False, True], ids=["new", "version-1"])
def test_eight_processes_migrate_history_together(tmp_path, existing_v1):
    path = tmp_path / "history.sqlite"
    if existing_v1:
        _create_v1_database(path)
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(9)
    results = context.Queue()
    processes = [context.Process(target=_open_history_together, args=(str(path), barrier, results))
                 for _ in range(8)]
    try:
        for process in processes:
            process.start()
        barrier.wait(timeout=30)
        outcomes = [results.get(timeout=30) for _ in processes]
        for process in processes:
            process.join(timeout=10)
        assert outcomes == [None] * 8
        assert all(process.exitcode == 0 for process in processes)
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=10)
        results.close()
        results.join_thread()
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
        assert [row[1] for row in conn.execute("PRAGMA table_info(runs)")].count("errors") == 1
        rows = conn.execute("SELECT * FROM runs").fetchall()
        assert rows == ([(1, "2026-10-23T12:00:00", 3, 1, 2, 4.5, 0)] if existing_v1 else [])


def test_existing_errors_column_completes_version_one_migration(tmp_path):
    path = tmp_path / "history.sqlite"
    _create_v1_database(path, with_errors=True)
    HistoryManager(str(path))
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
        assert conn.execute("SELECT errors FROM runs").fetchall() == [(0,)]


def test_duplicate_errors_column_is_safe_and_sets_version_two(tmp_path, monkeypatch):
    path = tmp_path / "history.sqlite"
    _create_v1_database(path, with_errors=True)

    class StaleColumnInspection(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            result = super().execute(sql, *args, **kwargs)
            if sql == "PRAGMA table_info(runs)":
                return [row for row in result if row[1] != "errors"]
            return result

    connect = sqlite3.connect
    monkeypatch.setattr(sqlite3, "connect", lambda path: connect(path, factory=StaleColumnInspection))
    HistoryManager(str(path))
    with connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
        assert conn.execute("SELECT errors FROM runs").fetchall() == [(0,)]


@pytest.mark.parametrize("message", ["database is locked", "duplicate column name: another_column"])
def test_migration_does_not_swallow_other_database_errors(tmp_path, monkeypatch, message):
    path = tmp_path / "history.sqlite"
    _create_v1_database(path)

    class BrokenMigration(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            if sql.startswith("ALTER TABLE"):
                raise sqlite3.OperationalError(message)
            return super().execute(sql, *args, **kwargs)

    connect = sqlite3.connect
    monkeypatch.setattr(sqlite3, "connect", lambda path: connect(path, factory=BrokenMigration))
    with pytest.raises(sqlite3.OperationalError, match=message):
        HistoryManager(str(path))
    with connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        assert conn.execute("SELECT * FROM runs").fetchall() == [(1, "2026-10-23T12:00:00", 3, 1, 2, 4.5)]
