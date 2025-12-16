# Evaluation Report Generation & Analysis

This module provides comprehensive report generation and analysis capabilities for Kurt evaluation results.

## Features

### 1. Multi-Format Report Generation
- **Markdown Reports**: Human-readable comparison tables with feedback highlights
- **JSON Reports**: Structured data for programmatic access
- **CSV Reports**: Pipe-delimited format for easy importing to spreadsheets

### 2. GitHub Integration
- Automatic GitHub links for source files
- Configurable repository and branch URLs
- Links directly to evaluation result files

### 3. Google Sheets Sync
- Export reports directly to Google Sheets
- Automatic formatting and conditional highlighting
- Summary sheets with aggregate metrics

## Usage

### Basic Report Generation

```bash
# Generate comparison report for two scenarios
uv run python -m eval.cli report-question \
  --scenarios answer_motherduck_with_kg,answer_motherduck_without_kg \
  --questions eval/questions.yaml \
  --output eval/results/comparison_report.md
```

### With GitHub Links

```bash
# Add GitHub links to the report
uv run python -m eval.cli report-question \
  --scenarios scenario1,scenario2 \
  --questions eval/questions.yaml \
  --github-repo https://github.com/your-org/your-repo \
  --github-branch main \
  --output eval/results/comparison_report.md
```

### Sync to Google Sheets

```bash
# Sync report to Google Sheets (requires credentials)
uv run python -m eval.cli report-question \
  --scenarios scenario1,scenario2 \
  --questions eval/questions.yaml \
  --sync-gsheet \
  --gsheet-name "My Eval Report" \
  --output eval/results/comparison_report.md
```

## Google Sheets Setup

1. **Install Dependencies**:
   ```bash
   pip install google-api-python-client google-auth pandas
   ```

2. **Set Up Service Account**:
   - Create a Google Cloud project
   - Enable Google Sheets and Drive APIs
   - Create a service account and download credentials JSON
   - Set environment variable:
     ```bash
     export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
     ```

3. **Share Sheet Access**:
   - Share any existing sheets with the service account email

## Report Format

### CSV Columns
- Question #
- Scenario
- Question Text
- Answer (truncated to 500 chars)
- Answer File
- GitHub Link (if enabled)
- Sources
- Source Delta (overlap percentage)
- Judge Scores (overall, accuracy, completeness, relevance, clarity)
- Judge Feedback
- Tokens Used
- Duration

### Markdown Report Sections
1. **Summary Statistics**: Average scores, total tokens, duration
2. **Results Comparison Table**: Side-by-side metrics
3. **Feedback Highlights**: Per-question judge feedback

### JSON Report Structure
```json
{
  "with_kg": {
    "questions": {...},
    "summary": {
      "average_score": 0.85,
      "total_tokens": 5000,
      "total_duration": 120.5,
      "cached_responses": 2
    }
  },
  "without_kg": {...},
  "per_question": [...],
  "generated_at": "2024-12-04T10:30:00"
}
```

## API Usage

```python
from eval.framework.analysis.compare import generate_report_from_dirs
from eval.framework.analysis.gsheet_sync import GSheetReportSync

# Generate report
generate_report_from_dirs(
    with_dir="eval/results/scenario_with_kg",
    without_dir="eval/results/scenario_without_kg",
    questions_file="eval/questions.yaml",
    output_file="eval/results/report.md",
    github_repo="https://github.com/org/repo",
    github_branch="main"
)

# Sync to Google Sheets
sync = GSheetReportSync(
    repo_url="https://github.com/org/repo",
    branch="main"
)

sheet_url = sync.sync_report(
    csv_path="eval/results/scenario_comparison.csv",
    json_path="eval/results/report.json",
    spreadsheet_name="My Eval Report"
)
```

## Testing

```bash
# Run unit tests
uv run pytest eval/tests/test_report_generation.py -v
```

## Files

- `compare.py`: Core report generation logic
- `gsheet_sync.py`: Google Sheets synchronization
- `aggregate.py`: Transcript aggregation utilities
- `test_report_generation.py`: Comprehensive unit tests