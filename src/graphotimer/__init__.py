import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import click
import matplotlib
import numpy as np
import pandas as pd
from rich.console import Console
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .logs import log_error, log_info, log_warn

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

console = Console()
JSON_FILE = ".graphotimer.json"
EXCEL_COLUMNS = ["date", "start_time", "end_time", "action_name", "duration_minutes"]


class DataManager:
    @staticmethod
    def load_json_data() -> List[Dict]:
        if not os.path.exists(JSON_FILE):
            return []
        try:
            with open(JSON_FILE, "r") as file:
                return json.load(file)
        except (json.JSONDecodeError, IOError) as error:
            log_error(f"Error loading JSON data: {error}", console)
            return []

    @staticmethod
    def save_json_data(data: List[Dict]) -> None:
        try:
            with open(JSON_FILE, "w") as file:
                json.dump(data, file, indent=2)
        except IOError as error:
            log_error(f"Error saving JSON data: {error}", console)

    @staticmethod
    def save_to_excel(data: Dict, filename: str) -> None:
        try:
            df = pd.DataFrame([data])
            if os.path.exists(filename):
                existing_df = pd.read_excel(filename)
                updated_df = pd.concat([existing_df, df], ignore_index=True)
                updated_df.to_excel(filename, index=False)
            else:
                df.to_excel(filename, index=False)
            log_info(f"Data saved to {filename}", console)
        except Exception as error:
            log_error(f"Error saving to Excel: {error}", console)


class TimeValidator:
    @staticmethod
    def validate_time_range(start: datetime, end: datetime) -> bool:
        if start.date() != end.date():
            log_error("Start and end times must be on the same day", console)
            return False
        if start >= end:
            log_error("End time must be after start time", console)
            return False
        if (end - start) > timedelta(hours=24):
            log_error("Time range cannot exceed 24 hours", console)
            return False
        return True

    @staticmethod
    def convert_string_to_date(
        datetime_string: str, template: str = "%Y-%m-%d %H:%M"
    ) -> datetime:
        try:
            return datetime.strptime(datetime_string, template)
        except ValueError as error:
            log_error(
                f'Cannot convert string "{datetime_string}" to date using "{template}" template ({error})',
                console,
            )
            return datetime.now()


class TimeProcessor:
    @staticmethod
    def process_time_data(
        data: List[Dict],
    ) -> Dict[str, List[Tuple[float, float, str]]]:
        daily_data = {}

        for entry in data:
            date = entry["date"]
            start_time = datetime.strptime(entry["start_time"], "%H:%M")
            end_time = datetime.strptime(entry["end_time"], "%H:%M")

            start_minutes = start_time.hour * 60 + start_time.minute
            end_minutes = end_time.hour * 60 + end_time.minute

            if date not in daily_data:
                daily_data[date] = []

            daily_data[date].append((start_minutes, end_minutes, entry["action_name"]))

        for date in daily_data:
            daily_data[date].sort(key=lambda x: x[0])
            daily_data[date] = TimeProcessor._fill_time_gaps(daily_data[date])

        return daily_data

    @staticmethod
    def _fill_time_gaps(
        time_entries: List[Tuple[float, float, str]],
    ) -> List[Tuple[float, float, str]]:
        filled_entries = []
        last_end = 0

        for start, end, action in time_entries:
            if start > last_end:
                filled_entries.append((last_end, start, "Free Time"))

            filled_entries.append((start, end, action))
            last_end = end

        if last_end < 24 * 60:
            filled_entries.append((last_end, 24 * 60, "Free Time"))

        return filled_entries

    @staticmethod
    def calculate_averages(
        daily_data: Dict[str, List[Tuple[float, float, str]]],
    ) -> Dict[str, float]:
        activity_totals = {}
        day_count = len(daily_data)

        for date_entries in daily_data.values():
            for start, end, action in date_entries:
                duration = (end - start) / 60
                activity_totals[action] = activity_totals.get(action, 0) + duration

        return {action: total / day_count for action, total in activity_totals.items()}

    @staticmethod
    def create_average_day(
        daily_data: Dict[str, List[Tuple[float, float, str]]],
    ) -> List[Tuple[float, float, str]]:
        if not daily_data:
            return []

        time_slots = {i: {} for i in range(0, 24 * 60, 15)}

        for date_entries in daily_data.values():
            for start, end, action in date_entries:
                for slot_start in range(int(start // 15) * 15, int(end // 15) * 15, 15):
                    if slot_start in time_slots:
                        time_slots[slot_start][action] = (
                            time_slots[slot_start].get(action, 0) + 1
                        )

        average_day = []
        current_action = None
        current_start = 0

        for slot_start in sorted(time_slots.keys()):
            slot_data = time_slots[slot_start]
            dominant_action = (
                max(slot_data.items(), key=lambda x: x[1])[0]
                if slot_data
                else "Free Time"
            )

            if dominant_action != current_action:
                if current_action is not None:
                    average_day.append((current_start, slot_start, current_action))
                current_action = dominant_action
                current_start = slot_start

        if current_action is not None:
            average_day.append((current_start, 24 * 60, current_action))

        return average_day


class MatplotlibVisualizer:
    @staticmethod
    def create_plot(daily_data: Dict[str, List[Tuple[float, float, str]]]) -> None:
        try:
            dates = sorted(daily_data.keys())
            if not dates:
                log_warn("No data available for visualization", console)
                return

            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12))
            fig.suptitle("Time Distribution Analysis", fontsize=16)

            all_activities = {
                activity
                for activities in daily_data.values()
                for _, _, activity in activities
            }

            color_map = MatplotlibVisualizer._create_color_map(all_activities)

            MatplotlibVisualizer._plot_daily_distribution(
                ax1, daily_data, dates, color_map
            )

            if len(dates) > 1:
                averages = TimeProcessor.calculate_averages(daily_data)
                MatplotlibVisualizer._plot_average_distribution(
                    ax2, averages, color_map
                )

                average_day = TimeProcessor.create_average_day(daily_data)
                MatplotlibVisualizer._plot_average_day(ax3, average_day, color_map)
            else:
                ax2.axis("off")
                ax2.text(
                    0.5,
                    0.5,
                    "Multiple days needed for averages",
                    ha="center",
                    va="center",
                    transform=ax2.transAxes,
                )
                ax3.axis("off")
                ax3.text(
                    0.5,
                    0.5,
                    "Multiple days needed for average day",
                    ha="center",
                    va="center",
                    transform=ax3.transAxes,
                )

            plt.tight_layout()
            plt.show()

        except Exception as error:
            log_error(f"Error creating matplotlib plot: {error}", console)

    @staticmethod
    def _create_color_map(activities):
        colors = plt.cm.Set3(np.linspace(0, 1, len(activities)))
        color_map = {
            activity: colors[i] for i, activity in enumerate(sorted(activities))
        }
        color_map["Free Time"] = (0.9, 0.9, 0.9, 1.0)
        return color_map

    @staticmethod
    def _plot_daily_distribution(ax, daily_data, dates, color_map):
        day_heights = 0.6
        spacing = 0.4

        for i, date in enumerate(dates):
            y_pos = i * (day_heights + spacing)

            for start, end, activity in daily_data[date]:
                duration = (end - start) / 60
                ax.barh(
                    y_pos,
                    duration,
                    height=day_heights,
                    left=start / 60,
                    color=color_map[activity],
                    edgecolor="black",
                    linewidth=0.5,
                )

            ax.text(-1, y_pos, date, va="center", ha="right", fontweight="bold")

        ax.set_xlabel("Time of Day (Hours)")
        ax.set_ylabel("Date")
        ax.set_title("Daily Time Distribution")
        ax.set_xlim(0, 24)
        ax.set_ylim(-0.5, len(dates) * (day_heights + spacing) - spacing)
        ax.set_yticks([])
        ax.grid(True, axis="x", alpha=0.3)

        ax.set_xticks(range(0, 25, 3))
        ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 25, 3)])

        legend_handles = [
            Rectangle((0, 0), 1, 1, color=color_map[activity], label=activity)
            for activity in sorted(color_map.keys())
        ]
        ax.legend(handles=legend_handles, bbox_to_anchor=(1.05, 1), loc="upper left")

    @staticmethod
    def _plot_average_distribution(ax, averages, color_map):
        activities = list(averages.keys())
        values = [averages[activity] for activity in activities]
        colors = [color_map.get(activity, "gray") for activity in activities]

        bars = ax.barh(
            activities, values, color=colors, edgecolor="black", linewidth=0.5
        )
        ax.bar_label(bars, fmt="%.1f h", padding=3)
        ax.set_xlabel("Average Hours per Day")
        ax.set_title("Average Time Distribution")
        ax.grid(True, axis="x", alpha=0.3)

    @staticmethod
    def _plot_average_day(ax, average_day, color_map):
        y_pos = 0
        day_height = 0.8

        for start, end, activity in average_day:
            duration = (end - start) / 60
            ax.barh(
                y_pos,
                duration,
                height=day_height,
                left=start / 60,
                color=color_map[activity],
                edgecolor="black",
                linewidth=0.5,
            )

        ax.set_xlabel("Time of Day (Hours)")
        ax.set_ylabel("Average Day")
        ax.set_title("Typical Average Day")
        ax.set_xlim(0, 24)
        ax.set_ylim(-0.5, 0.5)
        ax.set_yticks([])
        ax.grid(True, axis="x", alpha=0.3)

        ax.set_xticks(range(0, 25, 3))
        ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 25, 3)])


class PlotlyVisualizer:
    @staticmethod
    def create_plot(daily_data: Dict[str, List[Tuple[float, float, str]]]) -> None:
        try:
            dates = sorted(daily_data.keys())
            if not dates:
                log_warn("No data available for visualization", console)
                return

            all_activities = {
                activity
                for activities in daily_data.values()
                for _, _, activity in activities
            }

            color_map = PlotlyVisualizer._create_color_map(all_activities)

            if len(dates) > 1:
                fig = make_subplots(
                    rows=3,
                    cols=1,
                    subplot_titles=(
                        "Daily Time Distribution",
                        "Average Time Distribution",
                        "Typical Average Day",
                    ),
                    vertical_spacing=0.08,
                    row_heights=[0.5, 0.25, 0.25],
                )
            else:
                fig = make_subplots(
                    rows=1, cols=1, subplot_titles=("Daily Time Distribution",)
                )

            PlotlyVisualizer._plot_daily_distribution(fig, daily_data, dates, color_map)

            if len(dates) > 1:
                averages = TimeProcessor.calculate_averages(daily_data)
                PlotlyVisualizer._plot_average_distribution(fig, averages, color_map)

                average_day = TimeProcessor.create_average_day(daily_data)
                PlotlyVisualizer._plot_average_day(fig, average_day, color_map)

            fig.update_layout(
                height=900, showlegend=True, title_text="Time Distribution Analysis"
            )
            fig.show()
        except Exception as error:
            log_error(f"Error creating Plotly plot: {error}", console)

    @staticmethod
    def _create_color_map(activities):
        colors = plt.cm.Set3(np.linspace(0, 1, len(activities)))
        color_map = {}
        for i, activity in enumerate(sorted(activities)):
            r, g, b, a = colors[i]
            color_map[activity] = (
                f"rgba({int(r * 255)}, {int(g * 255)}, {int(b * 255)}, {a})"
            )
        color_map["Free Time"] = "rgba(230, 230, 230, 1.0)"
        return color_map

    @staticmethod
    def _plot_daily_distribution(fig, daily_data, dates, color_map):
        for i, date in enumerate(dates):
            for start, end, activity in daily_data[date]:
                duration = (end - start) / 60
                start_str = f"{start // 60:02d}:{start % 60:02d}"
                end_str = f"{end // 60:02d}:{end % 60:02d}"

                fig.add_trace(
                    go.Bar(
                        name=activity,
                        x=[duration],
                        y=[date],
                        orientation="h",
                        marker_color=color_map[activity],
                        base=start / 60,
                        hoverinfo="text",
                        hovertext=f"{activity}<br>{start_str} - {end_str}<br>{duration:.1f} hours",
                        legendgroup=activity,
                        showlegend=i == 0,
                    ),
                    row=1,
                    col=1,
                )

        fig.update_xaxes(
            title_text="Time of Day (Hours)",
            range=[0, 24],
            tickvals=list(range(0, 25, 3)),
            ticktext=[f"{h:02d}:00" for h in range(0, 25, 3)],
            row=1,
            col=1,
        )

    @staticmethod
    def _plot_average_distribution(fig, averages, color_map):
        activities = list(averages.keys())
        values = [averages[activity] for activity in activities]
        colors = [color_map.get(activity, "gray") for activity in activities]

        fig.add_trace(
            go.Bar(
                x=values,
                y=activities,
                orientation="h",
                marker_color=colors,
                text=[f"{v:.1f}h" for v in values],
                textposition="auto",
                hoverinfo="text",
                hovertext=[
                    f"{activity}<br>{value:.1f} hours average"
                    for activity, value in averages.items()
                ],
                showlegend=False,
            ),
            row=2,
            col=1,
        )

        fig.update_xaxes(title_text="Average Hours per Day", row=2, col=1)

    @staticmethod
    def _plot_average_day(fig, average_day, color_map):
        for start, end, activity in average_day:
            duration = (end - start) / 60
            start_str = f"{start // 60:02d}:{start % 60:02d}"
            end_str = f"{end // 60:02d}:{end % 60:02d}"

            fig.add_trace(
                go.Bar(
                    name=activity,
                    x=[duration],
                    y=["Average Day"],
                    orientation="h",
                    marker_color=color_map[activity],
                    base=start / 60,
                    hoverinfo="text",
                    hovertext=f"{activity}<br>{start_str} - {end_str}<br>{duration:.1f} hours",
                    legendgroup=activity,
                    showlegend=False,
                ),
                row=3,
                col=1,
            )

        fig.update_xaxes(
            title_text="Time of Day (Hours)",
            range=[0, 24],
            tickvals=list(range(0, 25, 3)),
            ticktext=[f"{h:02d}:00" for h in range(0, 25, 3)],
            row=3,
            col=1,
        )


@click.group()
def cli():
    """A Python script to generate graphs based on your daily schedule."""


@cli.command()
@click.option(
    "--date",
    type=str,
    help="Date (default: today, format: YYYY-MM-DD)",
    default="today",
)
@click.option("--start-time", type=str, help="Start time (HH:MM)", required=True)
@click.option("--end-time", type=str, help="End time (HH:MM)", required=True)
@click.option("--action-name", type=str, help="Action name", required=True)
@click.option("--excel", type=str, help="Excel filename to save data")
def add(
    date: str, start_time: str, end_time: str, action_name: str, excel: Optional[str]
):
    if date == "today":
        date = datetime.now().strftime("%Y-%m-%d")

    validator = TimeValidator()
    start_dt = validator.convert_string_to_date(f"{date} {start_time}")
    end_dt = validator.convert_string_to_date(f"{date} {end_time}")

    if not validator.validate_time_range(start_dt, end_dt):
        return

    duration = (end_dt - start_dt).total_seconds() / 60
    entry = {
        "date": date,
        "start_time": start_time,
        "end_time": end_time,
        "action_name": action_name,
        "duration_minutes": duration,
    }

    data_manager = DataManager()
    data = data_manager.load_json_data()
    data.append(entry)
    data_manager.save_json_data(data)

    if excel:
        data_manager.save_to_excel(entry, excel)

    log_info(f"Added: {action_name} ({duration:.0f} minutes)", console)


@cli.command()
def mpl_show():
    """Show schedule distribution using matplotlib."""
    data = DataManager.load_json_data()
    if not data:
        log_warn("No data available", console)
        return

    processor = TimeProcessor()
    daily_data = processor.process_time_data(data)
    visualizer = MatplotlibVisualizer()
    visualizer.create_plot(daily_data)


@cli.command()
def plotly_show():
    """Show interactive schedule distribution using Plotly."""
    data = DataManager.load_json_data()
    if not data:
        log_warn("No data available", console)
        return

    processor = TimeProcessor()
    daily_data = processor.process_time_data(data)
    visualizer = PlotlyVisualizer()
    visualizer.create_plot(daily_data)


def main():
    cli()


if __name__ == "__main__":
    main()
