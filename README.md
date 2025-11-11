# Replication Package: GitHub Issue Bug Classification Study

This replication package contains all scripts and documentation needed to reproduce the data collection and analysis from our study on intrinsic vs. extrinsic bug classifications in GitHub issues.

## Contents

```
.
├── README.md                      # This file
├── harvest_data.py                # Data collection script
├── analyze_data.py                # Statistical analysis script
├── requirements.txt               # Python dependencies
├── FinalClassification.csv        # Your input dataset 
├── issues.jsonl                   # Output collected issue data 

```

---

## Dataset Schema

### Input Dataset (dataset.csv)

**Required Columns:**
- `html_url` (string): Full GitHub issue URL (e.g., "https://github.com/owner/repo/issues/123")
- `FINAL Classification` (string): Manual classification of the issue
  - Valid values: "Intrinsic", "Extrinsic", "Not  a Bug", "Unknown"

**Example:**
```csv
html_url,FINAL Classification
https://github.com/owner/repo/issues/1,Intrinsic
https://github.com/owner/repo/issues/2,Extrinsic
```

### Output Dataset (issues.jsonl)

Each line is a JSON object representing one GitHub issue with comprehensive metadata.

#### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `owner` | string | Repository owner username |
| `repo` | string | Repository name |
| `number` | integer | Issue number |
| `id` | integer | GitHub's unique issue ID |
| `html_url` | string | Full URL to the issue |
| `title` | string | Issue title |
| `body` | string | Issue description/body text |
| `state` | string | Current state: "open" or "closed" |
| `state_reason` | string | Reason for state (e.g., "completed", "not_planned") |
| `locked` | boolean | Whether the issue is locked |
| `created_at` | string | ISO 8601 timestamp of creation |
| `updated_at` | string | ISO 8601 timestamp of last update |
| `closed_at` | string | ISO 8601 timestamp of closure (null if open) |
| `comments_count` | integer | Number of comments |
| `final_classification` | string | Classification from input CSV |

#### Nested Object: `author`

Information about the issue creator.

| Field | Type | Description |
|-------|------|-------------|
| `username` | string | GitHub username |
| `id` | integer | GitHub user ID |
| `author_association` | string | Relationship to repository (e.g., "OWNER", "MEMBER", "CONTRIBUTOR", "NONE") |

#### Nested Object: `closed_by`

Information about who closed the issue (null if open).

| Field | Type | Description |
|-------|------|-------------|
| `username` | string | GitHub username of closer |
| `id` | integer | GitHub user ID of closer |

#### Nested Object: `timestamp_metrics`

Calculated time-based metrics.

| Field | Type | Description |
|-------|------|-------------|
| `time_to_close_seconds` | integer | Seconds from creation to closure (null if open) |
| `time_to_first_response_seconds` | integer | Seconds from creation to first comment (null if no comments) |


#### Nested Object: `participant_metrics`

Information about discussion participants.

| Field | Type | Description |
|-------|------|-------------|
| `unique_commenters` | integer | Count of unique users who commented |
| `has_maintainer_comments` | boolean | Whether any maintainer (OWNER/MEMBER/COLLABORATOR) commented |

#### Nested Object: `reopen_metrics`

Information about issue reopening patterns.

| Field | Type | Description |
|-------|------|-------------|
| `was_reopened` | boolean | Whether issue was ever reopened |
| `reopen_count` | integer | Number of times issue was reopened |
| `time_to_reopen_seconds` | integer | Seconds from first close to first reopen (null if not reopened) |
| `final_resolution_time_seconds` | integer | Seconds from creation to final closure (null if not closed) |
| `reopen_timestamps` | array | ISO 8601 timestamps of all reopenings |

#### Nested Object: `closing_pr`

Pull request that closed the issue (null if not closed by PR).

| Field | Type | Description |
|-------|------|-------------|
| `pr_number` | integer | Pull request number |
| `created_at` | string | ISO 8601 timestamp of PR creation |
| `merged_at` | string | ISO 8601 timestamp of PR merge |
| `merged` | boolean | Whether PR was merged |
| `changed_files` | integer | Number of files changed in PR |
| `additions` | integer | Lines of code added |
| `deletions` | integer | Lines of code deleted |
| `reviews_count` | integer | Number of reviews on PR |
| `pr_url` | string | Full URL to the pull request |

#### Nested Object: `closing_commit`

Direct commit that closed the issue (null if not closed by direct commit).

| Field | Type | Description |
|-------|------|-------------|
| `commit_sha` | string | Git commit SHA hash |
| `commit_date` | string | ISO 8601 timestamp of commit |
| `additions` | integer | Lines added in commit |
| `deletions` | integer | Lines deleted in commit |
| `total_changes` | integer | Total line changes (additions + deletions) |
| `files_changed` | integer | Number of files changed in commit |

#### Array: `assignees`

List of users assigned to the issue.

| Field | Type | Description |
|-------|------|-------------|
| `username` | string | GitHub username |
| `id` | integer | GitHub user ID |

#### Array: `labels`

List of labels applied to the issue.

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Label name |
| `description` | string | Label description |
| `color` | string | Hex color code (without #) |

#### Nested Object: `milestone`

Milestone associated with the issue (null if none).

| Field | Type | Description |
|-------|------|-------------|
| `number` | integer | Milestone number |
| `title` | string | Milestone title |
| `state` | string | Milestone state: "open" or "closed" |
| `due_on` | string | ISO 8601 timestamp of due date |

#### Array: `comments`

List of all comments on the issue.

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Comment ID |
| `created_at` | string | ISO 8601 timestamp of creation |
| `updated_at` | string | ISO 8601 timestamp of last update |
| `author.username` | string | Commenter's username |
| `author.id` | integer | Commenter's user ID |
| `author.author_association` | string | Commenter's relationship to repository |
| `body` | string | Comment text |

#### Field: `comments_text`

Human-readable formatted transcript of all comments.

**Format:**
```
[2024-01-15 10:30Z] [OWNER] username1:
First comment text here

---

[2024-01-15 14:20Z] [CONTRIBUTOR] username2:
Second comment text here
```

---

## Requirements

### System Requirements
- Python 3.7 or higher
- Internet connection (for data collection only)
- GitHub Personal Access Token (for data collection only)

### Python Dependencies

Install required packages:

```bash
pip install -r requirements.txt
```

Required packages:
- `requests` >= 2.28.0
- `pandas` >= 1.5.0
- `numpy` >= 1.23.0
- `matplotlib` >= 3.6.0
- `seaborn` >= 0.12.0

---

## Usage

### Step 1: Data Collection

**Prerequisites:**
1. Obtain a GitHub Personal Access Token:
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Generate a token with `repo` scope (read access to repositories)
   - Copy the token

2. Set the token as an environment variable:
   ```bash
   export GITHUB_TOKEN="your_github_token_here"
   ```

**Run data collection:**

```bash
python collect_data.py dataset.csv issues.jsonl
```

**Arguments:**
- First argument (optional): Input CSV file path (default: `dataset.csv`)
- Second argument (optional): Output JSONL file path (default: `issues.jsonl`)

**What it does:**
- Reads GitHub issue URLs from the CSV
- For each issue, fetches:
  - Issue metadata
  - All comments and timeline events
  - Pull request information (if closed by PR)
  - Commit information (if closed by direct commit)
- Calculates various metrics
- Saves results to JSONL file (one JSON object per line)

**Expected duration:** ~30-60 seconds per issue (due to API rate limits)

**Note:** The script automatically handles GitHub API rate limits by sleeping when necessary.

### Step 2: Data Analysis

**Run analysis:**

```bash
python analyze.py
```

**What it does:**
- Loads data from `issues.jsonl`
- Performs comprehensive statistical analyses
- Generates visualization figures in `figures/` directory
- Exports `closed_by_summary.txt` with detailed closer information
- Prints all results to console

**Expected duration:** <1 minute for typical dataset sizes

---

## Output Files

### Console Output

The analysis script prints comprehensive statistics organized into sections:

1. **Bot-Closed Issues**: Analysis of automated closures
2. **Bug Classification Distribution**: Count and percentage of each classification
3. **Timing Analysis**: Time to close and time to first response metrics
4. **Maintainer Involvement**: Participation of repository maintainers
5. **Reopening Analysis**: Patterns of issue reopening
6. **Label Analysis**: Usage of GitHub labels
7. **Code Change Analysis**: Statistics on code changes (for PR-closed issues)
8. **Repository Distribution**: Distribution of issues across repositories

### Generated Files

**`closed_by_summary.txt`**
- Detailed breakdown of who closed issues
- Statistics by bug classification
- Top closers for each category

---

## Data Anonymization

The dataset included in this replication package has been anonymized to protect privacy

---

## Citation

If you use this replication package in your research, please cite:

```bibtex
@inproceedings{yourstudy2026,
  title={Your Study Title},
  author={Your Names},
  booktitle={Conference Name},
  year={2026}
}
```


