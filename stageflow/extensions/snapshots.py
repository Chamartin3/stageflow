"""Snapshot providers for regression detection in StageFlow."""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any

from stageflow.core.element import Element
from stageflow.core.result import StatusResult


class SnapshotProvider(ABC):
    """
    Abstract base class for snapshot providers.

    Snapshot providers store and retrieve element state snapshots
    for regression detection and historical analysis.
    """

    @abstractmethod
    def store_snapshot(
        self, element_id: str, element: Element, result: StatusResult, metadata: dict[str, Any] = None
    ):
        """
        Store a snapshot of element state.

        Args:
            element_id: Unique identifier for the element
            element: Element instance
            result: Evaluation result
            metadata: Additional metadata to store
        """
        pass

    @abstractmethod
    def get_snapshot(self, element_id: str, timestamp: str | None = None) -> dict[str, Any] | None:
        """
        Retrieve a snapshot for an element.

        Args:
            element_id: Unique identifier for the element
            timestamp: Specific timestamp to retrieve (latest if None)

        Returns:
            Snapshot data or None if not found
        """
        pass

    @abstractmethod
    def get_snapshot_history(
        self, element_id: str, limit: int = 10, since: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Get snapshot history for an element.

        Args:
            element_id: Unique identifier for the element
            limit: Maximum number of snapshots to return
            since: Only return snapshots after this timestamp

        Returns:
            List of snapshot data ordered by timestamp (newest first)
        """
        pass

    @abstractmethod
    def delete_snapshots(self, element_id: str, before: str | None = None):
        """
        Delete snapshots for an element.

        Args:
            element_id: Unique identifier for the element
            before: Only delete snapshots before this timestamp (all if None)
        """
        pass

    @abstractmethod
    def list_elements(self) -> list[str]:
        """
        List all element IDs that have snapshots.

        Returns:
            List of element IDs
        """
        pass


class InMemorySnapshotProvider(SnapshotProvider):
    """
    In-memory snapshot provider for development and testing.

    Stores snapshots in memory with automatic cleanup of old snapshots.
    """

    def __init__(self, max_snapshots_per_element: int = 100, cleanup_interval_hours: int = 24):
        """
        Initialize in-memory snapshot provider.

        Args:
            max_snapshots_per_element: Maximum snapshots to keep per element
            cleanup_interval_hours: Hours between automatic cleanup runs
        """
        self._snapshots: dict[str, list[dict[str, Any]]] = {}
        self._max_snapshots = max_snapshots_per_element
        self._cleanup_interval = timedelta(hours=cleanup_interval_hours)
        self._last_cleanup = datetime.now()

    def store_snapshot(
        self, element_id: str, element: Element, result: StatusResult, metadata: dict[str, Any] = None
    ):
        """Store snapshot in memory."""
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "element_data": element.to_dict(),
            "result": {
                "state": result.state.value,
                "current_stage": result.current_stage,
                "proposed_stage": result.proposed_stage,
                "actions": result.actions,
                "errors": result.errors,
                "metadata": result.metadata,
            },
            "metadata": metadata or {},
        }

        if element_id not in self._snapshots:
            self._snapshots[element_id] = []

        self._snapshots[element_id].append(snapshot)

        # Trim to max snapshots
        if len(self._snapshots[element_id]) > self._max_snapshots:
            self._snapshots[element_id] = self._snapshots[element_id][-self._max_snapshots :]

        # Periodic cleanup
        if datetime.now() - self._last_cleanup > self._cleanup_interval:
            self._cleanup_old_snapshots()

    def get_snapshot(self, element_id: str, timestamp: str | None = None) -> dict[str, Any] | None:
        """Get snapshot from memory."""
        if element_id not in self._snapshots:
            return None

        snapshots = self._snapshots[element_id]
        if not snapshots:
            return None

        if timestamp is None:
            # Return latest snapshot
            return snapshots[-1]

        # Find snapshot with matching timestamp
        for snapshot in reversed(snapshots):
            if snapshot["timestamp"] == timestamp:
                return snapshot

        return None

    def get_snapshot_history(
        self, element_id: str, limit: int = 10, since: str | None = None
    ) -> list[dict[str, Any]]:
        """Get snapshot history from memory."""
        if element_id not in self._snapshots:
            return []

        snapshots = self._snapshots[element_id]

        # Filter by since timestamp
        if since:
            since_dt = datetime.fromisoformat(since)
            snapshots = [
                s for s in snapshots if datetime.fromisoformat(s["timestamp"]) > since_dt
            ]

        # Return latest snapshots, limited by count
        return list(reversed(snapshots[-limit:]))

    def delete_snapshots(self, element_id: str, before: str | None = None):
        """Delete snapshots from memory."""
        if element_id not in self._snapshots:
            return

        if before is None:
            # Delete all snapshots for element
            del self._snapshots[element_id]
        else:
            # Delete snapshots before timestamp
            before_dt = datetime.fromisoformat(before)
            self._snapshots[element_id] = [
                s
                for s in self._snapshots[element_id]
                if datetime.fromisoformat(s["timestamp"]) >= before_dt
            ]

            # Remove element entry if no snapshots remain
            if not self._snapshots[element_id]:
                del self._snapshots[element_id]

    def list_elements(self) -> list[str]:
        """List all element IDs with snapshots."""
        return list(self._snapshots.keys())

    def _cleanup_old_snapshots(self):
        """Clean up old snapshots beyond the maximum limit."""
        self._last_cleanup = datetime.now()

        for element_id in list(self._snapshots.keys()):
            snapshots = self._snapshots[element_id]
            if len(snapshots) > self._max_snapshots:
                self._snapshots[element_id] = snapshots[-self._max_snapshots :]

    def get_stats(self) -> dict[str, Any]:
        """Get provider statistics."""
        total_snapshots = sum(len(snapshots) for snapshots in self._snapshots.values())
        return {
            "provider_type": "in_memory",
            "element_count": len(self._snapshots),
            "total_snapshots": total_snapshots,
            "max_snapshots_per_element": self._max_snapshots,
            "last_cleanup": self._last_cleanup.isoformat(),
        }


class FileSnapshotProvider(SnapshotProvider):
    """
    File-based snapshot provider for persistent storage.

    Stores snapshots as JSON files in a directory structure.
    """

    def __init__(self, storage_dir: str):
        """
        Initialize file-based snapshot provider.

        Args:
            storage_dir: Directory to store snapshot files
        """
        import json
        from pathlib import Path

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._json = json

    def store_snapshot(
        self, element_id: str, element: Element, result: StatusResult, metadata: dict[str, Any] = None
    ):
        """Store snapshot as JSON file."""
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "element_data": element.to_dict(),
            "result": {
                "state": result.state.value,
                "current_stage": result.current_stage,
                "proposed_stage": result.proposed_stage,
                "actions": result.actions,
                "errors": result.errors,
                "metadata": result.metadata,
            },
            "metadata": metadata or {},
        }

        # Create element directory
        element_dir = self.storage_dir / element_id
        element_dir.mkdir(exist_ok=True)

        # Write snapshot file
        timestamp = snapshot["timestamp"].replace(":", "-")  # Safe for filenames
        snapshot_file = element_dir / f"snapshot_{timestamp}.json"

        with open(snapshot_file, "w", encoding="utf-8") as f:
            self._json.dump(snapshot, f, indent=2)

    def get_snapshot(self, element_id: str, timestamp: str | None = None) -> dict[str, Any] | None:
        """Get snapshot from JSON file."""
        element_dir = self.storage_dir / element_id
        if not element_dir.exists():
            return None

        if timestamp is None:
            # Get latest snapshot
            snapshot_files = list(element_dir.glob("snapshot_*.json"))
            if not snapshot_files:
                return None
            latest_file = max(snapshot_files, key=lambda f: f.stat().st_mtime)
        else:
            # Find specific timestamp
            safe_timestamp = timestamp.replace(":", "-")
            snapshot_file = element_dir / f"snapshot_{safe_timestamp}.json"
            if not snapshot_file.exists():
                return None
            latest_file = snapshot_file

        try:
            with open(latest_file, encoding="utf-8") as f:
                return self._json.load(f)
        except (OSError, self._json.JSONDecodeError):
            return None

    def get_snapshot_history(
        self, element_id: str, limit: int = 10, since: str | None = None
    ) -> list[dict[str, Any]]:
        """Get snapshot history from JSON files."""
        element_dir = self.storage_dir / element_id
        if not element_dir.exists():
            return []

        snapshot_files = list(element_dir.glob("snapshot_*.json"))
        if not snapshot_files:
            return []

        # Sort by modification time (newest first)
        snapshot_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        snapshots = []
        since_dt = datetime.fromisoformat(since) if since else None

        for snapshot_file in snapshot_files[:limit]:
            try:
                with open(snapshot_file, encoding="utf-8") as f:
                    snapshot = self._json.load(f)

                # Filter by since timestamp
                if since_dt:
                    snapshot_dt = datetime.fromisoformat(snapshot["timestamp"])
                    if snapshot_dt <= since_dt:
                        continue

                snapshots.append(snapshot)
            except (OSError, self._json.JSONDecodeError, KeyError):
                continue

        return snapshots

    def delete_snapshots(self, element_id: str, before: str | None = None):
        """Delete snapshot JSON files."""
        element_dir = self.storage_dir / element_id
        if not element_dir.exists():
            return

        if before is None:
            # Delete all snapshots for element
            import shutil
            shutil.rmtree(element_dir)
        else:
            # Delete snapshots before timestamp
            before_dt = datetime.fromisoformat(before)
            snapshot_files = list(element_dir.glob("snapshot_*.json"))

            for snapshot_file in snapshot_files:
                try:
                    with open(snapshot_file, encoding="utf-8") as f:
                        snapshot = self._json.load(f)

                    snapshot_dt = datetime.fromisoformat(snapshot["timestamp"])
                    if snapshot_dt < before_dt:
                        snapshot_file.unlink()
                except (OSError, self._json.JSONDecodeError, KeyError):
                    continue

            # Remove directory if empty
            if not list(element_dir.glob("*")):
                element_dir.rmdir()

    def list_elements(self) -> list[str]:
        """List all element IDs with snapshots."""
        element_dirs = [d for d in self.storage_dir.iterdir() if d.is_dir()]
        return [d.name for d in element_dirs]


# Global snapshot provider instance
_global_snapshot_provider: SnapshotProvider | None = InMemorySnapshotProvider()


def set_global_snapshot_provider(provider: SnapshotProvider):
    """Set the global snapshot provider."""
    global _global_snapshot_provider
    _global_snapshot_provider = provider


def get_global_snapshot_provider() -> SnapshotProvider | None:
    """Get the global snapshot provider."""
    return _global_snapshot_provider
