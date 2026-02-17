import asyncio
from dataclasses import dataclass

from app.services.nexus_client import NexusModsClient


@dataclass
class DownloadTask:
    mod_id: int
    name: str
    game_domain: str
    nexus_mod_id: int
    file_id: int | None = None
    status: str = "pending"  # pending, downloading, complete, failed
    progress: float = 0.0
    error: str | None = None


class DownloadManager:
    """Manages mod download queue and progress tracking."""

    def __init__(self):
        self._tasks: dict[int, DownloadTask] = {}
        self._nexus = NexusModsClient()

    def add_task(self, task: DownloadTask) -> None:
        self._tasks[task.mod_id] = task

    def get_status(self) -> list[DownloadTask]:
        return list(self._tasks.values())

    async def start_downloads(self) -> None:
        """Start downloading all pending tasks."""
        pending = [t for t in self._tasks.values() if t.status == "pending"]
        # Download up to 3 concurrently
        semaphore = asyncio.Semaphore(3)

        async def download_one(task: DownloadTask):
            async with semaphore:
                await self._download_mod(task)

        await asyncio.gather(
            *(download_one(task) for task in pending),
            return_exceptions=True,
        )

    async def _download_mod(self, task: DownloadTask) -> None:
        """Download a single mod from Nexus."""
        task.status = "downloading"
        try:
            # Get files for this mod
            if task.file_id is None:
                files = await self._nexus.get_mod_files(
                    task.game_domain, task.nexus_mod_id
                )
                if not files:
                    task.status = "failed"
                    task.error = "No files found for this mod"
                    return
                # Pick the primary file, or first file
                primary = next(
                    (f for f in files if f.get("isPrimary")), files[0]
                )
                task.file_id = primary["fileId"]

            # Get download link
            link = await self._nexus.get_download_link(
                task.game_domain, task.nexus_mod_id, task.file_id
            )

            if link and link.startswith("http"):
                # TODO: Actually download the file using httpx streaming
                # For now, just mark as complete with the link
                task.progress = 100.0
                task.status = "complete"
            else:
                task.status = "failed"
                task.error = "Could not get download link (premium may be required)"

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
