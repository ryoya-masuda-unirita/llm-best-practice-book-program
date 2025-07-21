import asyncio
import time
from collections import defaultdict
from typing import Dict, List

from src.logger import make_logger

logger = make_logger(__name__)


class StreamMetrics:
    def __init__(self):
        self.active_streams: Dict[str, dict] = {}
        self.completed_streams: List[dict] = []
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.provider_stats: Dict[str, dict] = defaultdict(
            lambda: {"total_requests": 0, "total_tokens": 0, "total_duration": 0.0, "error_count": 0}
        )

    def start_stream(self, stream_id: str, provider: str, user_id: str = None, session_id: str = None):
        self.active_streams[stream_id] = {
            "stream_id": stream_id,
            "provider": provider,
            "user_id": user_id,
            "session_id": session_id,
            "start_time": time.time(),
            "token_count": 0,
            "status": "active",
        }

        self.provider_stats[provider]["total_requests"] += 1

        logger.info(
            "Stream tracking started",
            extra={
                "stream_id": stream_id,
                "provider": provider,
                "user_id": user_id,
                "session_id": session_id,
                "event_type": "monitoring_start",
            },
        )

    def update_token_count(self, stream_id: str, token_count: int):
        if stream_id in self.active_streams:
            self.active_streams[stream_id]["token_count"] = token_count

    def complete_stream(self, stream_id: str, total_tokens: int, duration: float):
        if stream_id in self.active_streams:
            stream_data = self.active_streams.pop(stream_id)
            stream_data.update(
                {"end_time": time.time(), "duration": duration, "total_tokens": total_tokens, "status": "completed"}
            )

            self.completed_streams.append(stream_data)

            provider = stream_data["provider"]
            self.provider_stats[provider]["total_tokens"] += total_tokens
            self.provider_stats[provider]["total_duration"] += duration

            logger.info(
                "Stream tracking completed",
                extra={
                    "stream_id": stream_id,
                    "total_tokens": total_tokens,
                    "duration": duration,
                    "provider": provider,
                    "event_type": "monitoring_complete",
                },
            )

    def error_stream(self, stream_id: str, error_type: str):
        if stream_id in self.active_streams:
            stream_data = self.active_streams.pop(stream_id)
            stream_data.update({"end_time": time.time(), "error_type": error_type, "status": "error"})

            self.completed_streams.append(stream_data)
            self.error_counts[error_type] += 1

            provider = stream_data["provider"]
            self.provider_stats[provider]["error_count"] += 1

            logger.error(
                "Stream tracking error",
                extra={
                    "stream_id": stream_id,
                    "error_type": error_type,
                    "provider": provider,
                    "event_type": "monitoring_error",
                },
            )

    def get_active_streams_count(self) -> int:
        return len(self.active_streams)

    def get_provider_stats(self, provider: str = None) -> dict:
        if provider:
            stats = self.provider_stats[provider].copy()
            if stats["total_requests"] > 0:
                stats["avg_duration"] = stats["total_duration"] / stats["total_requests"]
                stats["avg_tokens"] = stats["total_tokens"] / stats["total_requests"]
                stats["error_rate"] = stats["error_count"] / stats["total_requests"]
            return stats
        return dict(self.provider_stats)

    def get_recent_streams(self, minutes: int = 10) -> List[dict]:
        cutoff_time = time.time() - (minutes * 60)
        return [stream for stream in self.completed_streams if stream.get("start_time", 0) >= cutoff_time]

    def cleanup_old_data(self, hours: int = 24):
        cutoff_time = time.time() - (hours * 3600)
        self.completed_streams = [
            stream for stream in self.completed_streams if stream.get("start_time", 0) >= cutoff_time
        ]

        logger.info(
            f"Cleaned up old stream data (older than {hours} hours)", extra={"event_type": "monitoring_cleanup"}
        )


class HealthChecker:
    def __init__(self, metrics: StreamMetrics):
        self.metrics = metrics
        self.last_health_check = time.time()

    def check_system_health(self) -> dict:
        current_time = time.time()
        health_status = {
            "timestamp": current_time,
            "status": "healthy",
            "active_streams": self.metrics.get_active_streams_count(),
            "issues": [],
        }

        recent_streams = self.metrics.get_recent_streams(5)
        total_recent = len(recent_streams)
        error_recent = len([s for s in recent_streams if s["status"] == "error"])

        if total_recent > 0:
            error_rate = error_recent / total_recent
            if error_rate > 0.5:
                health_status["status"] = "degraded"
                health_status["issues"].append(f"High error rate: {error_rate:.2%}")

        if self.metrics.get_active_streams_count() > 100:
            health_status["status"] = "degraded"
            health_status["issues"].append("High number of active streams")

        for provider, stats in self.metrics.get_provider_stats().items():
            if stats["error_rate"] > 0.3:
                health_status["status"] = "degraded"
                health_status["issues"].append(f"High error rate for {provider}: {stats['error_rate']:.2%}")

        self.last_health_check = current_time

        logger.info(
            f"Health check completed: {health_status['status']}",
            extra={
                "health_status": health_status["status"],
                "active_streams": health_status["active_streams"],
                "issues_count": len(health_status["issues"]),
                "event_type": "health_check",
            },
        )

        return health_status


stream_metrics = StreamMetrics()
health_checker = HealthChecker(stream_metrics)


async def periodic_cleanup():
    while True:
        await asyncio.sleep(3600)  # Run every hour
        stream_metrics.cleanup_old_data()


async def periodic_health_check():
    while True:
        health_status = health_checker.check_system_health()
        if health_status["status"] != "healthy":
            logger.warning(f"System health degraded: {health_status['issues']}", extra={"event_type": "health_alert"})
        await asyncio.sleep(300)  # Check every 5 minutes
