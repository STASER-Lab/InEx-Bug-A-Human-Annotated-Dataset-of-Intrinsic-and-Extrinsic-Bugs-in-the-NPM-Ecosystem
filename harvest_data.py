#!/usr/bin/env python3
"""
GitHub issue harvester - data collection + timestamp analysis + participants + closing PR details

LIMITATION: Closing PR detection only works when the issue was closed by merging a PR.
Direct commits to main/master without a PR are tracked separately in closing_commit field.

Usage:
  export GITHUB_TOKEN="..."
  python harvest_data.py dataset.csv issues.jsonl
"""
import csv, json, os, sys, time, re
from datetime import datetime
import requests

# ---------- Config ----------
INPUT_CSV    = sys.argv[1] if len(sys.argv) > 1 else "datasetFinal.csv"
OUTPUT_JSONL = sys.argv[2] if len(sys.argv) > 2 else "issues.jsonl"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    print("ERROR: Set GITHUB_TOKEN environment variable")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# ---------- Timestamp utilities ----------
def parse_timestamp(iso_string):
    """Convert ISO timestamp string to datetime object"""
    if not iso_string:
        return None
    return datetime.fromisoformat(iso_string.replace("Z", "+00:00"))

def calculate_time_diff(start_time, end_time):
    """Calculate time difference in seconds between two ISO timestamps"""
    start = parse_timestamp(start_time)
    end = parse_timestamp(end_time)
    if not start or not end:
        return None
    return int((end - start).total_seconds())

# ---------- Parse GitHub URL ----------
def parse_url(url):
    """Extract owner, repo, number from GitHub issue URL"""
    parts = url.strip().split("/")
    return parts[-4], parts[-3], int(parts[-1])

# ---------- Fetch from GitHub with rate limiting ----------
def fetch(url):
    """Get data from GitHub API with basic rate limit handling"""
    while True:
        r = requests.get(url, headers=headers)
        if r.status_code == 403 and r.headers.get("X-RateLimit-Remaining") == "0":
            reset = int(r.headers.get("X-RateLimit-Reset", 0))
            sleep_time = max(0, reset - int(time.time()) + 1)
            print(f"Rate limited, sleeping {sleep_time}s...")
            time.sleep(sleep_time)
            continue
        r.raise_for_status()
        return r.json()

# ---------- Fetch paginated data ----------
def fetch_paginated(url):
    """Get all pages of data"""
    items = []
    page = 1
    while True:
        data = fetch(f"{url}?per_page=100&page={page}")
        if not data:
            break
        items.extend(data)
        if len(data) < 100:
            break
        page += 1
    return items

# ---------- Fetch issue data ----------
def fetch_issue(owner, repo, number):
    """Get issue data from GitHub API"""
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
    return fetch(url)

# ---------- Fetch commit details ----------
def fetch_commit_details(owner, repo, commit_sha):
    """Get commit information"""
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}"
    try:
        return fetch(url)
    except Exception as e:
        print(f"  Could not fetch commit {commit_sha} details: {e}")
        return None

# ---------- Fetch PR details ----------
def fetch_pr_details(owner, repo, pr_number):
    """Get detailed PR information"""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    try:
        return fetch(url)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None  # Silently skip 404s (cross-repo or deleted PRs)
        print(f"  Could not fetch PR #{pr_number} details: {e}")
        return None
    except Exception as e:
        print(f"  Could not fetch PR #{pr_number} details: {e}")
        return None

# ---------- Fetch PR reviews ----------
def fetch_pr_reviews(owner, repo, pr_number):
    """Get all reviews for a PR"""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
    try:
        return fetch_paginated(url)
    except Exception as e:
        print(f"  Could not fetch PR #{pr_number} reviews: {e}")
        return []

# ---------- Fetch comments ----------
def fetch_comments(owner, repo, number):
    """Get all comments for an issue"""
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}/comments"
    return fetch_paginated(url)

# ---------- Fetch timeline ----------
def fetch_timeline(owner, repo, number):
    """Get timeline events for an issue (more comprehensive than events API)"""
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}/timeline"
    try:
        # Timeline API requires special accept header
        timeline_headers = headers.copy()
        timeline_headers["Accept"] = "application/vnd.github.mockingbird-preview+json"
        
        items = []
        page = 1
        while True:
            r = requests.get(f"{url}?per_page=100&page={page}", headers=timeline_headers)
            if r.status_code == 403 and r.headers.get("X-RateLimit-Remaining") == "0":
                reset = int(r.headers.get("X-RateLimit-Reset", 0))
                sleep_time = max(0, reset - int(time.time()) + 1)
                print(f"Rate limited, sleeping {sleep_time}s...")
                time.sleep(sleep_time)
                continue
            r.raise_for_status()
            data = r.json()
            if not data:
                break
            items.extend(data)
            if len(data) < 100:
                break
            page += 1
        return items
    except Exception as e:
        print(f"  Could not fetch timeline: {e}")
        return []

# ---------- Build comments text transcript ----------
def build_comments_text(comments):
    """Create formatted text transcript of all comments"""
    if not comments:
        return ""
    
    blocks = []
    for comment in sorted(comments, key=lambda c: c.get("created_at", "")):
        timestamp = parse_timestamp(comment.get("created_at"))
        if timestamp:
            ts_str = timestamp.strftime("%Y-%m-%d %H:%MZ")
        else:
            ts_str = "0000-00-00 00:00Z"
        
        author = comment.get("user") or {}
        username = author.get("login") or "unknown"
        assoc = comment.get("author_association") or "UNKNOWN"
        body = comment.get("body") or ""
        
        blocks.append(f"[{ts_str}] [{assoc}] {username}:\n{body}")
    
    return "\n\n---\n\n".join(blocks)

# ---------- Calculate reopening metrics ----------
def calculate_reopen_metrics(issue, events):
    """Calculate metrics related to issue reopening"""
    metrics = {
        "was_reopened": False,
        "reopen_count": 0,
        "time_to_reopen_seconds": None,
        "final_resolution_time_seconds": None,
        "reopen_timestamps": []
    }
    
    # Find all closed and reopened events
    closed_events = [e for e in events if e.get("event") == "closed"]
    reopened_events = [e for e in events if e.get("event") == "reopened"]
    
    if not reopened_events:
        return metrics
    
    # Issue was reopened at least once
    metrics["was_reopened"] = True
    metrics["reopen_count"] = len(reopened_events)
    metrics["reopen_timestamps"] = [e.get("created_at") for e in reopened_events]
    
    # Time to first reopen (from first close to first reopen)
    if closed_events and reopened_events:
        first_close = min(closed_events, key=lambda e: e.get("created_at", ""))
        first_reopen = min(reopened_events, key=lambda e: e.get("created_at", ""))
        
        metrics["time_to_reopen_seconds"] = calculate_time_diff(
            first_close.get("created_at"),
            first_reopen.get("created_at")
        )
    
    # Final resolution time (from creation to last close, if currently closed)
    if issue.get("state") == "closed":
        created_at = issue.get("created_at")
        closed_at = issue.get("closed_at")
        
        if created_at and closed_at:
            metrics["final_resolution_time_seconds"] = calculate_time_diff(created_at, closed_at)
    
    return metrics

# ---------- Calculate timestamp metrics ----------
def calculate_timestamps(issue, comments):
    """Calculate all time-based metrics"""
    created_at = issue.get("created_at")
    closed_at = issue.get("closed_at")
    
    metrics = {
        "time_to_close_seconds": None,
        "time_to_first_comment_seconds": None,
        "time_to_first_response_seconds": None,
        "time_open_days": None
    }
    
    # Time to close
    if created_at and closed_at:
        metrics["time_to_close_seconds"] = calculate_time_diff(created_at, closed_at)
        metrics["time_open_days"] = round(metrics["time_to_close_seconds"] / 86400, 2)
    
    # Time to first comment (any comment)
    if comments and created_at:
        first_comment = min(comments, key=lambda c: c.get("created_at", ""))
        metrics["time_to_first_comment_seconds"] = calculate_time_diff(
            created_at, 
            first_comment.get("created_at")
        )
    
    # Time to first response (comment from someone other than issue author)
    if comments and created_at:
        author_username = issue.get("user", {}).get("login")
        other_comments = [
            c for c in comments 
            if c.get("user", {}).get("login") != author_username
        ]
        if other_comments:
            first_response = min(other_comments, key=lambda c: c.get("created_at", ""))
            metrics["time_to_first_response_seconds"] = calculate_time_diff(
                created_at,
                first_response.get("created_at")
            )
    
    return metrics

# ---------- Calculate participants ----------
def calculate_participants(issue, comments):
    """Count unique participants and categorize them"""
    participants = set()
    commenters = set()
    maintainers = set()
    
    # Add issue author
    author_username = issue.get("user", {}).get("login")
    if author_username:
        participants.add(author_username)
    
    # Add commenters
    for comment in comments:
        username = comment.get("user", {}).get("login")
        if username:
            participants.add(username)
            commenters.add(username)
            
            # Check if maintainer (OWNER, MEMBER, COLLABORATOR, or CONTRIBUTOR)
            assoc = comment.get("author_association", "")
            if assoc in ("OWNER", "MEMBER", "COLLABORATOR", "CONTRIBUTOR"):
                maintainers.add(username)
    
    return {
        "total_participants": len(participants),
        "unique_commenters": len(commenters),
        "maintainer_participants": len(maintainers),
        "has_maintainer_response": len(maintainers) > 0,
        "participant_usernames": sorted(list(participants)),
        "commenter_usernames": sorted(list(commenters)),
        "maintainer_usernames": sorted(list(maintainers))
    }

# ---------- Extract PR metrics ----------
def extract_pr_metrics(owner, repo, pr_number):
    """Fetch and extract metrics from a PR - matching commit detail level"""
    pr_data = fetch_pr_details(owner, repo, pr_number)
    if not pr_data:
        return None
    
    reviews = fetch_pr_reviews(owner, repo, pr_number)
    
    # Count unique reviewers
    reviewers = set()
    review_states = {
        "approved": 0,
        "changes_requested": 0,
        "commented": 0,
        "dismissed": 0
    }
    
    for review in reviews:
        reviewer_username = review.get("user", {}).get("login")
        if reviewer_username:
            reviewers.add(reviewer_username)
        
        state = review.get("state", "").lower()
        if state in review_states:
            review_states[state] += 1
    
    # Extract author and merger info (matching commit structure)
    pr_author = pr_data.get("user") or {}
    merged_by = pr_data.get("merged_by") or {}
    
    return {
        "number": pr_data.get("number"),
        "title": pr_data.get("title"),
        "html_url": pr_data.get("html_url"),
        "merged": bool(pr_data.get("merged_at")),
        "merged_at": pr_data.get("merged_at"),
        "created_at": pr_data.get("created_at"),
        "updated_at": pr_data.get("updated_at"),
        "closed_at": pr_data.get("closed_at"),
        "state": pr_data.get("state"),
        "body": pr_data.get("body"),
        
        # Author info (matching commit structure)
        "author": {
            "username": pr_author.get("login"),
            "id": pr_author.get("id"),
            "name": pr_author.get("name"),
            "email": pr_author.get("email")
        },
        
        # Merger info (like committer in commits)
        "merged_by": {
            "username": merged_by.get("login"),
            "id": merged_by.get("id"),
            "name": merged_by.get("name"),
            "email": merged_by.get("email")
        } if merged_by else None,
        
        # Code changes (matching commit structure)
        "commits": pr_data.get("commits"),
        "additions": pr_data.get("additions"),
        "deletions": pr_data.get("deletions"),
        "total_changes": (pr_data.get("additions") or 0) + (pr_data.get("deletions") or 0),
        "changed_files": pr_data.get("changed_files"),
        "files_changed": pr_data.get("changed_files"),
        
        # Review info
        "review_comments": pr_data.get("review_comments"),
        "comments": pr_data.get("comments"),
        "unique_reviewers": len(reviewers),
        "reviewer_usernames": sorted(list(reviewers)),
        "total_reviews": len(reviews),
        "approved_count": review_states["approved"],
        "changes_requested_count": review_states["changes_requested"],
        "commented_count": review_states["commented"],
        
        # Branch info
        "head_ref": pr_data.get("head", {}).get("ref"),
        "base_ref": pr_data.get("base", {}).get("ref"),
        "head_sha": pr_data.get("head", {}).get("sha"),
        "merge_commit_sha": pr_data.get("merge_commit_sha")
    }

# ---------- Extract commit metrics ----------
def extract_commit_metrics(owner, repo, commit_sha):
    """Fetch and extract metrics from a commit"""
    commit_data = fetch_commit_details(owner, repo, commit_sha)
    if not commit_data:
        return None
    
    stats = commit_data.get("stats", {})
    author = commit_data.get("commit", {}).get("author", {})
    committer = commit_data.get("commit", {}).get("committer", {})
    
    return {
        "sha": commit_data.get("sha"),
        "message": commit_data.get("commit", {}).get("message"),
        "html_url": commit_data.get("html_url"),
        "author": {
            "username": commit_data.get("author", {}).get("login"),
            "name": author.get("name"),
            "email": author.get("email"),
            "date": author.get("date")
        },
        "committer": {
            "username": commit_data.get("committer", {}).get("login"),
            "name": committer.get("name"),
            "email": committer.get("email"),
            "date": committer.get("date")
        },
        "additions": stats.get("additions"),
        "deletions": stats.get("deletions"),
        "total_changes": stats.get("total"),
        "files_changed": len(commit_data.get("files", []))
    }

# ---------- Closing detection (PR or direct commit) ----------
def find_closing_method(owner, repo, issue_number, issue_created_at, issue_closed_at, events):
    """
    Detect how the issue was closed: via PR merge or direct commit.
    
    Returns a tuple: (closing_pr, closing_commit)
    - closing_pr: PR metrics if closed by PR, else None
    - closing_commit: Commit metrics if closed by direct commit, else None
    """
    if not issue_closed_at:
        return None, None
    
    # Parse issue timestamps for validation
    issue_created_time = parse_timestamp(issue_created_at)
    issue_closed_time = parse_timestamp(issue_closed_at)
    
    # Find the last closed event (in case of reopening)
    closed_events = [e for e in events if e.get("event") == "closed"]
    if not closed_events:
        return None, None
    
    # Get the most recent close event
    closed_event = max(closed_events, key=lambda e: e.get("created_at", ""))
    
    # Strategy 1: Check if the closed event references a PR directly via source
    source = closed_event.get("source", {})
    if source.get("type") == "issue":  # PRs show up as type "issue"
        pr_number = source.get("issue", {}).get("number")
        if pr_number:
            print(f"    Closed by PR #{pr_number}, fetching details...")
            pr_metrics = extract_pr_metrics(owner, repo, pr_number)
            
            # Verify PR was merged after issue was created and close to when issue was closed
            if pr_metrics and pr_metrics.get("merged"):
                pr_merged_time = parse_timestamp(pr_metrics.get("merged_at"))
                if pr_merged_time and issue_created_time and issue_closed_time:
                    # Check if merged after issue creation
                    if pr_merged_time < issue_created_time:
                        print(f"    PR #{pr_number} was merged before issue was created, ignoring")
                    else:
                        # Check if merged within 7 days of issue closing
                        time_diff = abs((pr_merged_time - issue_closed_time).total_seconds())
                        if time_diff > 86400 :  # 7 days in seconds
                            print(f"    PR #{pr_number} was merged too far from close time ({time_diff/86400 :.1f} days), ignoring")
                        else:
                            return pr_metrics, None
    
    # Strategy 2: Look for cross-referenced events (timeline API provides these)
    cross_ref_events = [e for e in events 
                        if e.get("event") == "cross-referenced"]
    
    if cross_ref_events:
        for ref_event in sorted(cross_ref_events, key=lambda e: e.get("created_at", ""), reverse=True):
            ref_source = ref_event.get("source", {})
            if ref_source.get("type") == "issue":  # This is a PR reference
                pr_number = ref_source.get("issue", {}).get("number")
                if pr_number:
                    print(f"    Found cross-referenced PR #{pr_number}, fetching details...")
                    pr_metrics = extract_pr_metrics(owner, repo, pr_number)
                    
                    # Check if this PR was merged after issue creation and close to issue closing
                    if pr_metrics and pr_metrics.get("merged"):
                        pr_merged_time = parse_timestamp(pr_metrics.get("merged_at"))
                        if pr_merged_time and issue_created_time and issue_closed_time:
                            # Check if merged after issue creation
                            if pr_merged_time < issue_created_time:
                                print(f"    PR #{pr_number} was merged before issue was created, skipping")
                                continue
                            # Check if merged within 7 days of issue closing
                            time_diff = abs((pr_merged_time - issue_closed_time).total_seconds())
                            if time_diff > 604800:  # 7 days in seconds
                                print(f"    PR #{pr_number} was merged too far from close time ({time_diff/86400:.1f} days), skipping")
                                continue
                            print(f"    Confirmed: PR #{pr_number} was merged close to issue closing")
                            return pr_metrics, None
    
    # Strategy 3: Look for referenced events with source.issue (direct PR reference)
    referenced_events = [e for e in events 
                        if e.get("event") == "referenced"]
    
    if referenced_events:
        for ref_event in sorted(referenced_events, key=lambda e: e.get("created_at", ""), reverse=True):
            # Check if the referenced event has a direct PR reference in source
            ref_source = ref_event.get("source", {})
            if ref_source.get("type") == "issue":  # This is a PR reference
                pr_number = ref_source.get("issue", {}).get("number")
                if pr_number:
                    print(f"    Found referenced PR #{pr_number} (from source), fetching details...")
                    pr_metrics = extract_pr_metrics(owner, repo, pr_number)
                    
                    # Check if this PR was merged after issue creation and close to issue closing
                    if pr_metrics and pr_metrics.get("merged"):
                        pr_merged_time = parse_timestamp(pr_metrics.get("merged_at"))
                        if pr_merged_time and issue_created_time and issue_closed_time:
                            # Check if merged after issue creation
                            if pr_merged_time < issue_created_time:
                                print(f"    PR #{pr_number} was merged before issue was created, skipping")
                                continue
                            # Check if merged within 7 days of issue closing
                            time_diff = abs((pr_merged_time - issue_closed_time).total_seconds())
                            if time_diff > 604800:  # 7 days in seconds
                                print(f"    PR #{pr_number} was merged too far from close time ({time_diff/86400:.1f} days), skipping")
                                continue
                            print(f"    Confirmed: PR #{pr_number} was merged close to issue closing")
                            return pr_metrics, None
            
            # Also try commit-based lookup for referenced events
            ref_commit_id = ref_event.get("commit_id")
            if ref_commit_id:
                try:
                    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{ref_commit_id}/pulls"
                    prs = fetch(url)
                    
                    if prs:
                        pr_number = prs[0].get("number")
                        print(f"    Found referenced PR #{pr_number} (from commit), fetching details...")
                        pr_metrics = extract_pr_metrics(owner, repo, pr_number)
                        
                        if pr_metrics and pr_metrics.get("merged"):
                            pr_merged_time = parse_timestamp(pr_metrics.get("merged_at"))
                            if pr_merged_time and issue_created_time and issue_closed_time:
                                # Check if merged after issue creation
                                if pr_merged_time < issue_created_time:
                                    print(f"    PR #{pr_number} was merged before issue was created, skipping")
                                    continue
                                # Check if merged within 7 days of issue closing
                                time_diff = abs((pr_merged_time - issue_closed_time).total_seconds())
                                if time_diff > 604800:  # 7 days in seconds
                                    print(f"    PR #{pr_number} was merged too far from close time ({time_diff/86400:.1f} days), skipping")
                                    continue
                                print(f"    Confirmed: PR #{pr_number} was merged close to issue closing")
                                return pr_metrics, None
                except Exception:
                    continue
    
    # Strategy 4: Try commit-based detection from closed event
    commit_sha = closed_event.get("commit_id")
    commit_url = closed_event.get("commit_url")
    
    if not commit_sha and commit_url:
        parts = commit_url.rstrip('/').split('/')
        if len(parts) > 0:
            commit_sha = parts[-1]
    
    if commit_sha:
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}/pulls"
            prs = fetch(url)
            
            if prs:
                pr_number = prs[0].get("number")
                print(f"    Closed by PR #{pr_number} (via commit), fetching details...")
                pr_metrics = extract_pr_metrics(owner, repo, pr_number)
                
                # Verify PR was merged after issue was created and close to when issue was closed
                if pr_metrics and pr_metrics.get("merged"):
                    pr_merged_time = parse_timestamp(pr_metrics.get("merged_at"))
                    if pr_merged_time and issue_created_time and issue_closed_time:
                        # Check if merged after issue creation
                        if pr_merged_time < issue_created_time:
                            print(f"    PR #{pr_number} was merged before issue was created, ignoring")
                            return None, None
                        # Check if merged within 7 days of issue closing
                        time_diff = abs((pr_merged_time - issue_closed_time).total_seconds())
                        if time_diff > 604800:  # 7 days in seconds
                            print(f"    PR #{pr_number} was merged too far from close time ({time_diff/86400:.1f} days), ignoring")
                            return None, None
                        return pr_metrics, None
            else:
                print(f"    Closed by direct commit {commit_sha[:7]}, fetching details...")
                commit_metrics = extract_commit_metrics(owner, repo, commit_sha)
                return None, commit_metrics
                
        except Exception as e:
            print(f"  Could not fetch closing method for commit {commit_sha}: {e}")
    
    return None, None

# ---------- Read CSV ----------
def read_csv(path):
    """Read URLs and classifications from CSV"""
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

# ---------- Build output ----------
def build_output(row):
    """Collect all available data for one issue"""
    url = row.get("html_url", "").strip()
    if not url or "github.com" not in url:
        return None
    
    try:
        owner, repo, number = parse_url(url)
        print(f"  Fetching {owner}/{repo}#{number}")
        
        # Fetch all raw data
        issue = fetch_issue(owner, repo, number)
        comments = fetch_comments(owner, repo, number)
        events = fetch_timeline(owner, repo, number)
        
        # Build comments text transcript
        comments_text = build_comments_text(comments)
        
        # Calculate metrics
        timestamp_metrics = calculate_timestamps(issue, comments)
        participant_metrics = calculate_participants(issue, comments)
        reopen_metrics = calculate_reopen_metrics(issue, events)
        
        # Find how issue was closed (PR or direct commit)
        closing_pr = None
        closing_commit = None
        if issue.get("state") == "closed":
            closing_pr, closing_commit = find_closing_method(
                owner, repo, number,
                issue.get("created_at"),
                issue.get("closed_at"),
                events
            )
        
        # Extract user data
        author = issue.get("user") or {}
        closed_by = issue.get("closed_by") or {}
        
        # Extract labels
        labels = [
            {
                "name": l.get("name"),
                "description": l.get("description"),
                "color": l.get("color")
            }
            for l in (issue.get("labels") or [])
        ]
        
        # Extract assignees
        assignees = [
            {
                "username": u.get("login"),
                "id": u.get("id")
            }
            for u in (issue.get("assignees") or [])
        ]
        
        # Extract milestone
        milestone = None
        if issue.get("milestone"):
            ms = issue["milestone"]
            milestone = {
                "number": ms.get("number"),
                "title": ms.get("title"),
                "state": ms.get("state"),
                "due_on": ms.get("due_on")
            }
        
        # Extract comments
        comments_data = [
            {
                "id": c.get("id"),
                "created_at": c.get("created_at"),
                "updated_at": c.get("updated_at"),
                "author": {
                    "username": c.get("user", {}).get("login"),
                    "id": c.get("user", {}).get("id"),
                    "author_association": c.get("author_association")
                },
                "body": c.get("body")
            }
            for c in comments
        ]
        
        return {
            # Basic info
            "owner": owner,
            "repo": repo,
            "number": issue.get("number"),
            "id": issue.get("id"),
            "html_url": issue.get("html_url"),
            "title": issue.get("title"),
            "body": issue.get("body"),
            
            # State
            "state": issue.get("state"),
            "state_reason": issue.get("state_reason"),
            "locked": issue.get("locked"),
            
            # Timestamps
            "created_at": issue.get("created_at"),
            "updated_at": issue.get("updated_at"),
            "closed_at": issue.get("closed_at"),
            
            # Metrics
            "timestamp_metrics": timestamp_metrics,
            "participant_metrics": participant_metrics,
            "reopen_metrics": reopen_metrics,
            
            # Author
            "author": {
                "username": author.get("login"),
                "id": author.get("id"),
                "author_association": issue.get("author_association")
            },
            
            # Closed by
            "closed_by": {
                "username": closed_by.get("login"),
                "id": closed_by.get("id")
            } if closed_by else None,
            
            # How was it closed?
            "closing_pr": closing_pr,
            "closing_commit": closing_commit,
            
            # Relationships
            "assignees": assignees,
            "labels": labels,
            "milestone": milestone,
            
            # Comments
            "comments_count": issue.get("comments"),
            "comments": comments_data,
            "comments_text": comments_text,
            
            # CSV classification
            "final_classification": row.get("FINAL Classification")
        }
        
    except Exception as e:
        print(f"Error processing {url}: {e}")
        return None

# ---------- Main ----------
def main():
    rows = read_csv(INPUT_CSV)
    
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as out:
        for i, row in enumerate(rows, 1):
            print(f"Processing {i}/{len(rows)}...")
            obj = build_output(row)
            if obj:
                out.write(json.dumps(obj, ensure_ascii=False) + "\n")
    
    print(f"Done! Output: {OUTPUT_JSONL}")

if __name__ == "__main__":
    main()