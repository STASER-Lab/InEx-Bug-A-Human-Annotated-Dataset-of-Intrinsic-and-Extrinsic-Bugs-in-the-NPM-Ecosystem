# Replication Package: GitHub Issue Bug Classification Study

This README provides a comprehensive description of every variable in the dataset produced by `harvest_data.py`. All field names, structures, and computations match the actual contents of `issues_anonymized.jsonl`.

---

## 1. finalDataset.csv

Each record in the input CSV must contain:

- **`html_url`**: Full GitHub issue URL (e.g., `https://github.com/owner/repo/issues/123`)
- **`FINAL Classification`**: Manually assigned label.  
  Possible values (exact): `Intrinsic`, `Extrinsic`, `Not  a Bug`, `Unknown`  
---

## 2. Output Dataset (JSONL)

Each line in `issues_anonymized.jsonl` represents a single GitHub issue with metadata and derived analytics.

---

### Top-Level Fields

#### `owner`
GitHub username of the repository owner (string).  
→ Extracted directly from the issue URL.

#### `repo`
Repository name (string).  
→ Extracted directly from the issue URL.

#### `number`
Integer issue number within the repository.

#### `id`
Unique GitHub issue ID (integer, stable across forks).

#### `html_url`
Direct link to the issue's web page on GitHub.

#### `title`
Issue title at creation time.

#### `body`
Full text body or description of the issue. Markdown formatting is preserved.

#### `state`
Current issue state — `"open"` or `"closed"`.  

#### `state_reason`
If closed, the reason — `"completed"`, `"not_planned"`, or `"reopened"`.  
→ Collected via `state_reason` in the REST API.

#### `locked`
Boolean. `true` if comments are restricted to collaborators.

#### `created_at`, `updated_at`, `closed_at`
ISO 8601 timestamps.  
→ Collected from GitHub API; `closed_at` may be `null` if still open.

#### `comments_count`
Total number of comments on the issue.

#### `final_classification`
Manual classification carried over from the input CSV.

#### `is_bot_close`
Boolean indicating if the issue was automatically closed by a known bot.  
→ Specifically detects closures by `stale[bot]` or `vue-bot` (case-insensitive).  
→ Added via `bot_detect.py` before anonymization to preserve bot detection capability.

---

### `author` (object)

Information about the user who created the issue.

- **`username`**: GitHub username of the author (anonymized in provided dataset).  
- **`id`**: Numeric GitHub user ID (anonymized in provided dataset).  
- **`author_association`**: Relationship to the repository — e.g., `"OWNER"`, `"MEMBER"`, `"CONTRIBUTOR"`, `"NONE"`.  
→ Extracted from the `user` object and `author_association` field in API responses.

---

### `closed_by` (object or null)

User who closed the issue, if applicable.

- **`username`**: GitHub username of the closer (anonymized in provided dataset).  
- **`id`**: GitHub user ID (anonymized in provided dataset).  
→ Null if issue is still open or was closed automatically.

---

### `timestamp_metrics` (object)

Derived timing metrics from issue creation, response, and closure.

- **`time_to_close_seconds`**: Seconds between `created_at` and `closed_at`. Null if still open.  
- **`time_to_first_response_seconds`**: Seconds from issue creation to the first maintainer (OWNER/MEMBER/COLLABORATOR) comment.  
- **`time_to_first_comment_seconds`**: Seconds from issue creation to first comment by *any* user.  
- **`time_open_days`**: Total duration between creation and closure (or current time if open), in days.

---

### `participant_metrics` (object)

Information about user participation and maintainer activity.

- **`total_participants`**: Number of unique usernames participating (author + commenters).  
- **`unique_commenters`**: Count of distinct commenters only.  
- **`maintainer_participants`**: Count of participants with maintainer roles.  
- **`has_maintainer_response`**: Boolean indicating whether at least one maintainer commented.  
- **`participant_usernames`**: Array of all usernames that appeared in comments or authored the issue (anonymized in provided dataset).  
- **`commenter_usernames`**: Array of usernames who commented (excluding author, anonymized in provided dataset).  
- **`maintainer_usernames`**: Subset of participant usernames identified as maintainers (anonymized in provided dataset).

→ These metrics are computed by parsing each comment's `author_association` field.

---

### `reopen_metrics` (object)

Captures issue reopen behavior using timeline events.

- **`was_reopened`**: True if any "reopened" event occurred.  
- **`reopen_count`**: Number of times reopened.  
- **`time_to_reopen_seconds`**: Time between initial closure and first reopen event.  
- **`final_resolution_time_seconds`**: Duration from first creation to final closure after all reopenings.  
- **`reopen_timestamps`**: Array of timestamps when reopen events occurred.

→ Extracted from timeline events with type `"reopened"` and `"closed"`.

---

### `closing_pr` (object or null)

Information on the pull request that closed the issue (if applicable).  
Detected by matching cross-reference events between issues and PRs.

- **`number`**: Pull request number.  
- **`title`**: PR title text.  
- **`state`**: `"open"`, `"closed"`, or `"merged"`.  
- **`body`**: PR description.  
- **`html_url`**: Direct PR link.  
- **`created_at`, `updated_at`, `closed_at`**: PR timestamps.  
- **`merged`**: Boolean if merged.  
- **`merged_at`**: Merge timestamp.  
- **`merge_commit_sha`**: SHA of the merge commit.  
- **`head_ref`, `head_sha`, `base_ref`**: Source and target branches and commit SHAs.  
- **`comments`, `review_comments`, `commits`, `changed_files`, `files_changed`**: Counts of comments, reviews, commits, and files modified.  
- **`additions`, `deletions`, `total_changes`**: Lines added, removed, and total.  
- **`approved_count`, `changes_requested_count`, `commented_count`**: Review outcome tallies.  
- **`total_reviews`, `unique_reviewers`**: Aggregated review statistics.  
- **`reviewer_usernames`**: List of reviewer usernames (anonymized in provided dataset).  
- **`author`**: PR author (object: `username`, `id`, `name`, `email` - anonymized in provided dataset).  
- **`merged_by`**: User who merged PR (same structure, anonymized in provided dataset).

→ Populated using `/pulls/{number}` endpoint and review/comment API calls.

---

### `closing_commit` (object or null)

If the issue was closed by a direct commit (no PR), this object stores commit data.

- **`sha`**: Commit hash.  
- **`html_url`**: Link to commit on GitHub.  
- **`message`**: Commit message.  
- **`additions`, `deletions`, `total_changes`, `files_changed`**: Code diff statistics.  
- **`author`**, **`committer`**: Each contains `username`, `id`, `name`, `email` (may be null, anonymized in provided dataset).

→ Extracted from cross-reference timeline events with a linked commit SHA.

---

### `assignees` (array of objects)

Each object contains:

- **`username`**: Assigned user's GitHub handle (anonymized in provided dataset).  
- **`id`**: Numeric user ID (anonymized in provided dataset).

---

### `labels` (array of objects)

GitHub labels attached to the issue.

- **`name`**: Label name.  
- **`description`**: Short label description.  
- **`color`**: Hex color code (no `#`).

---

### `milestone` (object or null)

If the issue is associated with a milestone:

- **`number`**: Milestone number.  
- **`title`**: Milestone name.  
- **`state`**: `"open"` or `"closed"`.  
- **`due_on`**: Due date (ISO timestamp).

---

### `comments` (array of objects)

List of all comments on the issue.

Each comment object includes:
- **`id`**: Comment ID.  
- **`created_at`**, **`updated_at`**: Timestamps.  
- **`author`**: Nested object with `username`, `id`, `author_association` (username and id anonymized in provided dataset).  
- **`body`**: Comment text (Markdown preserved).

→ Collected through the `/issues/comments` endpoint, batched by pagination.

---

### `comments_text`

Human-readable concatenation of all comments for easy analysis.  
Each block follows the format:

```
[2024-01-15 10:30Z] [OWNER] username1:
Comment text here

---

[2024-01-15 14:20Z] [CONTRIBUTOR] username2:
Another comment...
```

*Note: Usernames in this field are anonymized in the provided dataset.*

---

## 3. Requirements

- Python 3.8+  
- GitHub personal access token with `repo` scope (read-only) - *only needed if collecting new data*

Install dependencies:

```bash
pip install -r requirements.txt
```

### requirements.txt

```
requests>=2.28.0
pandas>=1.5.0
numpy>=1.23.0
matplotlib>=3.6.0
seaborn>=0.12.0
```

---

## 4. Usage

### Option A: Using Provided Anonymized Dataset

If using the provided `issues_anonymized.jsonl` file:

```bash
python analysis.py
```

The provided dataset already includes the `is_bot_close` field and has all usernames/IDs anonymized.

---

### Option B: Collecting Fresh Data

If collecting and processing new data from scratch:

#### Step 1 — Data Collection

```bash
export GITHUB_TOKEN="your_token_here"
python harvest_data.py finalDataset.csv issues.jsonl
```

This script reads each issue URL from the CSV, queries the GitHub REST API, and enriches it with metadata, timeline events, comments, PRs, and commits.  
It automatically handles API rate limits.

#### Step 2 — Bot Detection

```bash
python bot_detect.py issues.jsonl issues_with_bot_flag.jsonl
```

Adds the `is_bot_close` field to detect issues closed by `stale[bot]` or `vue-bot`.  
**Important:** This step must be completed *before* anonymization to preserve bot detection capability.

#### Step 3 — Anonymization (Optional)

If you wish to anonymize usernames and user IDs for privacy:

```bash
python anonymize.py issues_with_bot_flag.jsonl issues_anonymized.jsonl
```

*Note: Anonymization script not included in this package as the provided dataset is already anonymized.*

#### Step 4 — Analysis

```bash
python analysis.py
```

Generates descriptive statistics and publication-quality visualizations in the `figures/` directory.

---

## 5. Files Included

- **`harvest_data.py`**: Main data collection script
- **`bot_detect.py`**: Adds bot closure detection field
- **`analysis.py`**: Generates statistics and visualizations
- **`finalDataset.csv`**: Input CSV with manually classified issues
- **`issues_anonymized.jsonl`**: Complete anonymized dataset (377 issues)
- **`requirements.txt`**: Python dependencies
- **`README.md`**: This file

---

## 6. Notes on Anonymization

The provided `issues_anonymized.jsonl` dataset has been anonymized to protect privacy:

---

## 7. Citation

```bibtex
@inproceedings{yourstudy2026,
  title={Your Study Title},
  author={Your Names},
  booktitle={Conference Name},
  year={2026}
}
```
