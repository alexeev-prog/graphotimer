# GraphoTimer
A Python command-line tool for tracking and visualizing your daily schedule with interactive charts.

## Features

- **Time Tracking**: Log activities with start/end times and descriptions
- **Data Storage**: Automatic JSON storage with optional Excel export
- **Visualization**:
  - Static visualizations using Matplotlib
  - Interactive charts using Plotly
- **Analysis**:
  - Daily time distribution charts
  - Average time usage statistics
  - Typical day visualization

## Installation

1. Clone the repository:
```bash
git clone https://github.com/alexeev-prog/graphotimer
cd graphotimer
```

2. Install using uv:
```bash
uv pip install .
```

## Usage

### Adding Activities

```bash
graphotimer add --start-time "09:00" --end-time "10:30" --action-name "Meeting"
```

Optional parameters:
- `--date`: Date in YYYY-MM-DD format (default: today)
- `--excel`: Excel filename to export data

### Viewing Visualizations

Matplotlib (static):
```bash
graphotimer mpl_show
```

Plotly (interactive):
```bash
graphotimer plotly_show
```

## Data Format

Activities are stored in JSON format with the following structure:
```json
{
  "date": "2025-01-01",
  "start_time": "09:00",
  "end_time": "10:30",
  "action_name": "Meeting",
  "duration_minutes": 90
}
```

## Examples

1. Track a work session:
```bash
graphotimer add --start-time "09:00" --end-time "12:00" --action-name "Coding"
```

2. Track with custom date and export to Excel:
```bash
graphotimer add --date "2025-01-01" --start-time "14:00" --end-time "15:30" --action-name "Design" --excel "schedule.xlsx"
```

## Technical Details

- **Data Storage**: JSON file (`.graphotimer.json`) in current directory
- **Time Processing**: 15-minute intervals for accurate averaging
- **Visualization**:
  - Color-coded activities
  - Automatic gap detection (shown as "Free Time")
  - Responsive design for both static and interactive charts

## Dependencies

- click: Command-line interface
- matplotlib: Static visualizations
- pandas: Data processing and Excel export
- plotly: Interactive visualizations
- rich: Enhanced console output
- numpy: Numerical calculations
