"""Matplotlib and Seaborn timeline visualization."""

from __future__ import annotations

import logging

from autosilenttrimmer.core.config import VisualizerConfig
from autosilenttrimmer.core.constants import (
    PLOT_COLOR_GRID,
    PLOT_COLOR_LEGEND_BG,
    PLOT_COLOR_TEXT,
    PLOT_STYLE_THEME,
    PLOT_SUFFIX,
    PLOT_THEME_RC,
)
from autosilenttrimmer.core.exceptions import DependencyMissingException
from autosilenttrimmer.domain.contracts.visualizer import IVisualizer
from autosilenttrimmer.domain.entities.segment import MediaSegment

logger = logging.getLogger(__name__)


class MatplotlibTimelinePlotter(IVisualizer):
    """Renders speech vs silence timeline visualization to an image file."""

    def __init__(self, config: VisualizerConfig | None = None) -> None:
        self._config = config or VisualizerConfig()

    def generate_timeline_plot(
        self,
        segments: list[MediaSegment],
        total_duration: float,
        output_path: str,
    ) -> str:
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.patches as mpatches
            import matplotlib.pyplot as plt
            import seaborn as sns
        except ImportError as e:
            raise DependencyMissingException(
                "Scientific timeline visualization requires 'matplotlib' and 'seaborn'."
            ) from e

        effective_duration = max(1.0, total_duration)

        sns.set_theme(style=PLOT_STYLE_THEME, rc=dict(PLOT_THEME_RC))

        fig, ax = plt.subplots(figsize=(self._config.fig_width, self._config.fig_height))
        ax.set_xlim(0, effective_duration)
        ax.set_ylim(0, 1)
        ax.set_yticks([])
        ax.axhspan(0, 1, color=self._config.silence_color, alpha=1.0)

        xranges = [(seg.start, seg.duration) for seg in segments]
        if xranges:
            ax.broken_barh(xranges, (0, 1), facecolors=self._config.speech_color, alpha=0.85)

        ax.set_xlabel("Timeline (Seconds)", fontsize=12, fontweight="bold")
        ax.set_title(
            "Speech Segmentation & Voice Activity Detection Timeline",
            fontsize=16,
            fontweight="bold",
            pad=20,
        )

        speech_patch = mpatches.Patch(
            color=self._config.speech_color, label="Active Speech (Retained)"
        )
        silence_patch = mpatches.Patch(
            color=self._config.silence_color, label="Silence / Noise (Discarded)"
        )
        ax.legend(
            handles=[speech_patch, silence_patch],
            loc="upper right",
            facecolor=PLOT_COLOR_LEGEND_BG,
            edgecolor=PLOT_COLOR_GRID,
            labelcolor=PLOT_COLOR_TEXT,
        )

        plt.tight_layout()
        plot_path = output_path + PLOT_SUFFIX
        plt.savefig(plot_path, dpi=self._config.dpi, bbox_inches="tight")
        plt.close(fig)
        return plot_path
