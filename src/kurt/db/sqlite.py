"""SQLite database client for local mode."""

import os
from pathlib import Path

from rich.console import Console
from sqlmodel import Session, SQLModel, create_engine

from kurt.config import get_config_or_default
from kurt.db.base import DatabaseClient

console = Console()


class SQLiteClient(DatabaseClient):
    """SQLite database client for local Kurt projects."""

    def __init__(self):
        """Initialize SQLite client."""
        self._engine = None
        self._config = None

    def get_config(self):
        """Get Kurt configuration (cached)."""
        if self._config is None:
            self._config = get_config_or_default()
        return self._config

    def get_database_path(self) -> Path:
        """Get the path to the SQLite database file from config."""
        config = self.get_config()
        return config.get_absolute_db_path()

    def get_database_url(self) -> str:
        """Get the SQLite database URL."""
        db_path = self.get_database_path()
        return f"sqlite:///{db_path}"

    def ensure_kurt_directory(self) -> Path:
        """Ensure .kurt database directory exists."""
        config = self.get_config()
        db_dir = config.get_db_directory()
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir

    def get_mode_name(self) -> str:
        """Get the name of this database mode."""
        return "local"

    def init_database(self) -> None:
        """
        Initialize the SQLite database.

        Creates .kurt directory and initializes database with all tables.
        """
        # Import models to register them with SQLModel
        from kurt.models.models import Document, DocumentClusterEdge, Entity, TopicCluster

        # Ensure .kurt directory exists
        kurt_dir = self.ensure_kurt_directory()
        console.print(f"[dim]Creating directory: {kurt_dir}[/dim]")

        # Get database path
        db_path = self.get_database_path()

        # Check if database already exists
        if db_path.exists():
            console.print(f"[yellow]Database already exists at: {db_path}[/yellow]")
            overwrite = console.input("Overwrite? (y/N): ")
            if overwrite.lower() != "y":
                console.print("[dim]Keeping existing database[/dim]")
                return
            os.remove(db_path)
            console.print("[dim]Removed existing database[/dim]")

        # Create database engine
        db_url = self.get_database_url()
        console.print(f"[dim]Creating database at: {db_path}[/dim]")
        engine = create_engine(db_url, echo=False)
        self._engine = engine

        # Create all tables
        console.print("[dim]Running migrations...[/dim]")
        SQLModel.metadata.create_all(engine)

        # Verify tables were created
        tables_created = []
        for table in SQLModel.metadata.tables.values():
            tables_created.append(table.name)

        console.print(f"[green]✓[/green] Created {len(tables_created)} tables:")
        for table_name in sorted(tables_created):
            console.print(f"  • {table_name}")

        console.print(f"\n[green]✓[/green] Database initialized successfully")
        console.print(f"[dim]Mode: local (SQLite)[/dim]")
        console.print(f"[dim]Location: {db_path}[/dim]")

    def get_session(self) -> Session:
        """Get a database session."""
        if not self._engine:
            db_url = self.get_database_url()
            self._engine = create_engine(db_url, echo=False)
        return Session(self._engine)

    def check_database_exists(self) -> bool:
        """Check if the SQLite database file exists."""
        db_path = self.get_database_path()
        return db_path.exists()
