# Replication Package: GitHub Issue Bug Classification Study

This package reproduces the data collection and analysis for the InEx-Bug dataset on intrinsic vs. extrinsic bugs.

---

## Contents

```
.
├── README.md
├── harvest_data.py
├── analysis.py
├── requirements.txt
├── dataset_example.csv
├── issues_anonymized.jsonl
```

---

## Input Dataset (CSV)

**Columns:**
- `html_url`: Full GitHub issue URL  
- `FINAL Classification`: Manual label (`Intrinsic`, `Extrinsic`, `Not  a Bug`, `Unknown`)

Example:
```csv
html_url,FINAL Classification
https://github.com/owner/repo/issues/1,Intrinsic
```

---

## Output Dataset (JSONL)

Each line is one issue with full metadata.

### Top-Level Fields
| Key | Type | Description |
|------|------|-------------|
| owner, repo | string | Repository identifiers |
| number, id | int | Issue number and ID |
| html_url | string | GitHub issue URL |
| title, body | string | Title and description |
| state, state_reason, locked | string / bool | State info |
| created_at, updated_at, closed_at | string / null | Timestamps |
| comments_count | int | Number of comments |
| final_classification | string | Label from input CSV |
| is_bot_close | bool | True if closed by automation |
| author | object | Issue author info |
| closed_by | object / null | User who closed issue |
| timestamp_metrics | object | Derived timing data |
| participant_metrics | object | Participation info |
| reopen_metrics | object | Reopen history |
| closing_pr | object / null | PR metadata |
| closing_commit | object / null | Commit metadata |
| assignees | array | Assigned users |
| labels | array | Issue labels |
| milestone | object / null | Milestone data |
| comments | array | All comments |
| comments_text | string | Combined text transcript |

---

### Nested Objects

#### author
`username`, `id`, `author_association`

#### closed_by
`username`, `id`

#### timestamp_metrics
`time_to_close_seconds`, `time_to_first_response_seconds`,  
`time_to_first_comment_seconds`, `time_open_days`

#### participant_metrics
`total_participants`, `unique_commenters`, `maintainer_participants`,  
`has_maintainer_response`, `participant_usernames`,  
`commenter_usernames`, `maintainer_usernames`

#### reopen_metrics
`was_reopened`, `reopen_count`, `time_to_reopen_seconds`,  
`final_resolution_time_seconds`, `reopen_timestamps`

#### closing_pr
Includes:  
`number`, `title`, `state`, `body`, `html_url`, `created_at`, `updated_at`,  
`closed_at`, `merged`, `merged_at`, `merge_commit_sha`, `head_ref`,  
`head_sha`, `base_ref`, `comments`, `review_comments`, `commits`,  
`changed_files`, `files_changed`, `additions`, `deletions`, `total_changes`,  
`approved_count`, `changes_requested_count`, `commented_count`,  
`total_reviews`, `unique_reviewers`, `reviewer_usernames`,  
`author`, `merged_by` (each with `username`, `id`, `name`, `email`)

#### closing_commit
`sha`, `html_url`, `message`, `additions`, `deletions`,  
`total_changes`, `files_changed`,  
`author`, `committer` (each: `username`, `id`, `name`, `email`)

#### assignees
`username`, `id`

#### labels
`name`, `description`, `color`

#### milestone
`number`, `title`, `state`, `due_on`

#### comments
`id`, `created_at`, `updated_at`, `body`,  
`author`: `{username, id, author_association}`

---

## Requirements

- Python 3.8+
- GitHub personal access token (for collection)

```
pip install -r requirements.txt
```

`requirements.txt`:
```
requests>=2.28.0
pandas>=1.5.0
numpy>=1.23.0
matplotlib>=3.6.0
seaborn>=0.12.0
```

---

## Usage

### 1. Data Collection
```bash
export GITHUB_TOKEN="your_token"
python harvest_data.py dataset.csv issues.jsonl
```

Fetches issue metadata, comments, events, PRs, and commits.

### 2. Analysis
```bash
cp issues_anonymized.jsonl issues_final.jsonl
python analysis.py
```

Outputs:
- Console summaries (class distribution, maintainer activity, etc.)
- `closed_by_summary.txt`
- `figures/` directory

---

## Citation

```bibtex
@inproceedings{yourstudy2026,
  title={Your Study Title},
  author={Your Names},
  booktitle={Conference Name},
  year={2026}
}
```
