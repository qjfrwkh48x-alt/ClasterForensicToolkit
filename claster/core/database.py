"""
Database abstraction layer using SQLite for case management and evidence tracking.
Maintains chain of custody, file metadata, and analysis results.
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from contextlib import contextmanager
from claster.core.logger import get_logger
from claster.core.exceptions import DatabaseError
from claster.core.config import get_config

logger = get_logger(__name__)

class Database:
    """
    SQLite database manager for forensic case data.
    Schema includes tables for evidence items, hashes, analysis results, and chain of custody.
    """

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file. If None, derived from config.
        """
        if db_path is None:
            config = get_config()
            case_dir = config.case_directory
            case_name = config.case_name
            db_path = case_dir / f"{case_name}.db"

        self.db_path = Path(db_path)
        self._connection: Optional[sqlite3.Connection] = None
        logger.debug(f"Database path set to: {self.db_path}")

    def connect(self) -> None:
        """Establish a connection to the database and ensure schema exists."""
        if self._connection is not None:
            return

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._connection = sqlite3.connect(
                str(self.db_path),
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                check_same_thread=False  # We'll manage threads with context
            )
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA journal_mode = WAL")  # Better concurrency
            self._initialize_schema()
            logger.info(f"Connected to database: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise DatabaseError(f"Database connection failed: {e}")

    def _initialize_schema(self) -> None:
        """Create tables if they don't exist."""
        with self._connection:
            # Version tracking
            self._connection.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Check current version
            cursor = self._connection.execute("SELECT MAX(version) FROM schema_version")
            row = cursor.fetchone()
            current_version = row[0] if row and row[0] is not None else 0

            if current_version < self.SCHEMA_VERSION:
                self._create_tables()
                self._connection.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (self.SCHEMA_VERSION,)
                )
                logger.info(f"Database schema upgraded to version {self.SCHEMA_VERSION}")

    def _create_tables(self) -> None:
        """Create all required tables."""
        # Cases table (though we use single case per DB, can be extended)
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_name TEXT NOT NULL,
                examiner TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Evidence items (files, disks, memory dumps, etc.)
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                evidence_id TEXT UNIQUE NOT NULL,  -- User-assigned or auto
                source_path TEXT,                   -- Original location
                stored_path TEXT,                   -- Where we stored it (if copied)
                file_name TEXT,
                file_size INTEGER,
                file_extension TEXT,
                description TEXT,
                acquired_at TIMESTAMP,
                acquired_by TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
            )
        """)

        # Hashes for evidence items
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS hashes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_id INTEGER NOT NULL,
                algorithm TEXT NOT NULL,
                hash_value TEXT NOT NULL,
                verified BOOLEAN DEFAULT 0,
                computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (evidence_id) REFERENCES evidence(id) ON DELETE CASCADE,
                UNIQUE(evidence_id, algorithm)
            )
        """)

        # Chain of custody log
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS custody_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_id INTEGER NOT NULL,
                action TEXT NOT NULL,               -- 'acquired', 'copied', 'analyzed', 'transferred'
                from_person TEXT,
                to_person TEXT,
                location TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (evidence_id) REFERENCES evidence(id) ON DELETE CASCADE
            )
        """)

        # Analysis results (generic key-value store for module outputs)
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_id INTEGER,
                module TEXT NOT NULL,
                result_type TEXT NOT NULL,
                data JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (evidence_id) REFERENCES evidence(id) ON DELETE CASCADE
            )
        """)

        # Events timeline (for PFI and reporting)
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                event_source TEXT,                  -- e.g., 'MFT', 'EVTX', 'Registry'
                event_type TEXT,
                description TEXT,
                artifact_data JSON,
                evidence_id INTEGER,
                FOREIGN KEY (evidence_id) REFERENCES evidence(id) ON DELETE SET NULL
            )
        """)

        # Indexes for performance
        self._connection.execute("CREATE INDEX IF NOT EXISTS idx_evidence_case ON evidence(case_id)")
        self._connection.execute("CREATE INDEX IF NOT EXISTS idx_hashes_evidence ON hashes(evidence_id)")
        self._connection.execute("CREATE INDEX IF NOT EXISTS idx_timeline_time ON timeline(timestamp)")
        self._connection.execute("CREATE INDEX IF NOT EXISTS idx_timeline_source ON timeline(event_source)")

        # Insert default case if none exists
        cursor = self._connection.execute("SELECT COUNT(*) FROM cases")
        if cursor.fetchone()[0] == 0:
            config = get_config()
            self._connection.execute(
                "INSERT INTO cases (case_name, examiner) VALUES (?, ?)",
                (config.case_name, config.get('examiner', 'Unknown'))
            )
            logger.info(f"Created default case: {config.case_name}")

    @contextmanager
    def get_connection(self):
        """Context manager for database connections (auto-commit/rollback)."""
        if self._connection is None:
            self.connect()
        try:
            yield self._connection
        except Exception:
            self._connection.rollback()
            raise
        else:
            self._connection.commit()

    def add_evidence(
        self,
        source_path: Union[str, Path],
        evidence_id: Optional[str] = None,
        description: str = "",
        acquired_by: str = "",
        copy_to_evidence_dir: bool = True
    ) -> int:
        """
        Register a new evidence item in the database.
        Optionally copy the file to the evidence directory.

        Returns:
            The database ID of the evidence record.
        """
        source_path = Path(source_path)
        if not source_path.exists():
            raise DatabaseError(f"Source file does not exist: {source_path}")

        config = get_config()
        if evidence_id is None:
            evidence_id = f"EVID-{datetime.now().strftime('%Y%m%d%H%M%S')}-{source_path.name}"

        stored_path = None
        if copy_to_evidence_dir:
            evidence_dir = config.evidence_directory
            evidence_dir.mkdir(parents=True, exist_ok=True)
            # Create a subdirectory with evidence_id to avoid collisions
            target_dir = evidence_dir / evidence_id
            target_dir.mkdir(exist_ok=True)
            stored_path = target_dir / source_path.name
            import shutil
            shutil.copy2(source_path, stored_path)
            logger.info(f"Evidence copied to: {stored_path}")

        file_size = source_path.stat().st_size
        file_name = source_path.name
        file_extension = source_path.suffix

        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO evidence 
                (case_id, evidence_id, source_path, stored_path, file_name, file_size, file_extension, 
                 description, acquired_at, acquired_by)
                VALUES ((SELECT id FROM cases LIMIT 1), ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_id,
                    str(source_path),
                    str(stored_path) if stored_path else None,
                    file_name,
                    file_size,
                    file_extension,
                    description,
                    datetime.now().isoformat(),
                    acquired_by
                )
            )
            evidence_db_id = cursor.lastrowid

            # Add initial custody log entry
            conn.execute(
                """
                INSERT INTO custody_log (evidence_id, action, to_person, notes)
                VALUES (?, 'acquired', ?, ?)
                """,
                (evidence_db_id, acquired_by, f"Acquired from {source_path}")
            )

        logger.info(f"Evidence registered with ID: {evidence_id} (DB id: {evidence_db_id})")
        return evidence_db_id

    def add_hash(self, evidence_db_id: int, algorithm: str, hash_value: str, verified: bool = False) -> None:
        """Record a hash for an evidence item."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO hashes (evidence_id, algorithm, hash_value, verified, computed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (evidence_db_id, algorithm, hash_value, verified, datetime.now().isoformat())
            )
        logger.debug(f"Hash {algorithm}:{hash_value} recorded for evidence {evidence_db_id}")

    def add_timeline_event(
        self,
        timestamp: datetime,
        event_source: str,
        event_type: str,
        description: str,
        artifact_data: Optional[Dict] = None,
        evidence_id: Optional[int] = None
    ) -> None:
        """Add an event to the global timeline."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO timeline (timestamp, event_source, event_type, description, artifact_data, evidence_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp.isoformat(),
                    event_source,
                    event_type,
                    description,
                    json.dumps(artifact_data) if artifact_data else None,
                    evidence_id
                )
            )

    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.debug("Database connection closed.")

# Global database instance (singleton)
_db_instance: Optional[Database] = None

def get_db() -> Database:
    """Get the global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
        _db_instance.connect()
    return _db_instance