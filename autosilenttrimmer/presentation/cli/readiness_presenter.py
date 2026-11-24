"""Terminal formatter for SystemReadinessReport."""

from __future__ import annotations

from autosilenttrimmer.domain.models.readiness import (
    ReadinessItem,
    SystemReadinessReport,
)


class ReadinessPresenter:
    """Renders SystemReadinessReport into clean, aligned terminal table format."""

    @staticmethod
    def present(report: SystemReadinessReport) -> None:
        """Render diagnostic results to stdout."""
        # Group items by category
        categories: dict[str, list[ReadinessItem]] = {}
        for item in report.items:
            categories.setdefault(item.category, []).append(item)

        print("-" * 90)
        print(f"{'Component':<36} {'Status':<18} {'Details'}")
        print("-" * 90)

        for category, items in categories.items():
            print(f"[{category}]")
            for item in items:
                status_str = f"[{item.status.value}]"
                print(f"  {item.component:<34} {status_str:<18} {item.detail}")
            print()

        # Remediation section
        remediation_items = [item for item in report.items if item.remediation]
        if remediation_items:
            print("-" * 90)
            print("Remediation Guidance:")
            print("-" * 90)
            for item in remediation_items:
                print(f"* {item.component} ({item.status.value}):")
                print(f"    {item.remediation}")
            print()

        # Final verdict
        print("-" * 90)
        status_label = "READY FOR INFERENCE" if report.is_ready else "CRITICAL DEPENDENCY FAILURE"
        gpu_label = "ENABLED" if report.has_gpu_acceleration else "DISABLED (CPU MODE)"
        print(f"System Status       : {status_label}")
        print(f"Hardware Acceleration : {gpu_label}")

        summary_parts = [f"{k}: {v}" for k, v in report.summary.items()]
        print(f"Summary Metrics     : {', '.join(summary_parts)}")
        print("-" * 90)
