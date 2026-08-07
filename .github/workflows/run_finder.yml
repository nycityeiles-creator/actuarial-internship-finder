import csv
import os
import random
import re
import time
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ddgs import DDGS


# ============================================================
# SETTINGS
# ============================================================

TARGET_YEAR = "2027"

# Maximum search results requested for each Google/Bing/etc. query
MAX_RESULTS_PER_QUERY = 20

# Maximum number of jobs displayed in a GitHub alert
MAX_JOBS_IN_ISSUE = 25


# These are the searches our robot will perform.
SEARCH_QUERIES = [
    '"actuarial intern" "2027"',
    '"actuarial internship" "2027"',
    '"summer 2027" actuarial internship',
    '"actuarial intern" insurance careers',
    '"actuarial internship" consulting careers',
    '"actuarial intern" site:myworkdayjobs.com',
    '"actuarial intern" site:greenhouse.io',
    '"actuarial intern" site:lever.co',
    '"actuarial intern" site:jobs.smartrecruiters.com',
]


# Career systems get a higher priority score.
DIRECT_JOB_DOMAINS = (
    "myworkdayjobs.com",
    "greenhouse.io",
    "lever.co",
    "smartrecruiters.com",
    "icims.com",
    "taleo.net",
    "successfactors.com",
)


# These are still allowed, but direct employer pages are preferred.
LOWER_PRIORITY_DOMAINS = (
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "ziprecruiter.com",
    "simplyhired.com",
)


# Helps remove obvious non-job search results.
BAD_TITLE_PHRASES = (
    "reddit",
    "salary guide",
    "interview questions",
    "resume example",
    "actuarial exam",
    "study guide",
)


CSV_FIELDS = [
    "first_seen_utc",
    "priority_score",
    "title",
    "source_domain",
    "url",
    "search_query",
    "snippet",
]


TRACKING_KEYS = {
    "ref",
    "referrer",
    "source",
    "src",
    "trk",
    "trackingid",
    "gh_src",
}


# ============================================================
# CLEANING FUNCTIONS
# ============================================================

def clean_text(text):
    """Remove weird spacing and basic HTML characters."""
    text = str(text or "")
    text = re.sub(r"\s+", " ", text).strip()

    return text.replace("<", "").replace(">", "")


def canonicalize_url(url):
    """
    Removes common tracking information from URLs.

    This helps prevent the same internship from appearing
    multiple times just because the link is slightly different.
    """

    try:
        parts = urlsplit(url.strip())

        kept_query = []

        for key, value in parse_qsl(parts.query, keep_blank_values=True):

            lower_key = key.lower()

            if lower_key.startswith("utm_"):
                continue

            if lower_key in TRACKING_KEYS:
                continue

            kept_query.append((key, value))

        path = parts.path.rstrip("/") or "/"

        return urlunsplit(
            (
                parts.scheme.lower(),
                parts.netloc.lower(),
                path,
                urlencode(kept_query, doseq=True),
                "",
            )
        )

    except Exception:
        return url.strip()


def domain_from_url(url):
    """Gets the website name from a URL."""

    try:
        return urlsplit(url).netloc.lower().removeprefix("www.")

    except Exception:
        return ""


# ============================================================
# JOB FILTER
# ============================================================

def is_relevant(title, snippet):
    """
    Decide whether a search result actually looks like
    an actuarial internship.
    """

    title_lower = title.lower()

    combined = f"{title} {snippet}".lower()

    # Remove obvious junk
    if any(
        phrase in title_lower
        for phrase in BAD_TITLE_PHRASES
    ):
        return False

    # Must contain something actuarial
    has_actuarial = "actuar" in combined

    # Must look like an internship/student program
    has_internship = any(
        word in combined
        for word in (
            "intern",
            "internship",
            "summer program",
            "student program",
        )
    )

    return has_actuarial and has_internship


# ============================================================
# PRIORITY SCORE
# ============================================================

def priority_score(title, snippet, url):
    """
    Give the best jobs higher scores.

    Summer 2027 + direct employer career pages receive
    the highest scores.
    """

    combined = f"{title} {snippet}".lower()

    title_lower = title.lower()

    domain = domain_from_url(url)

    score = 0

    # Actuarial is directly in the job title
    if "actuar" in title_lower:
        score += 4

    # Internship is directly in the title
    if "intern" in title_lower:
        score += 4

    # Our target year
    if TARGET_YEAR in combined:
        score += 5

    # Summer internship
    if "summer" in combined:
        score += 2

    # Direct employer recruiting system
    if any(
        job_domain in domain
        for job_domain in DIRECT_JOB_DOMAINS
    ):
        score += 4

    # Aggregators get slightly lower priority
    if any(
        job_domain in domain
        for job_domain in LOWER_PRIORITY_DOMAINS
    ):
        score -= 2

    return score


# ============================================================
# READ OLD JOBS
# ============================================================

def load_existing_jobs():

    if not os.path.exists("jobs.csv"):
        return {}

    existing = {}

    with open(
        "jobs.csv",
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            url = row.get("url", "").strip()

            if not url:
                continue

            existing[canonicalize_url(url)] = row

    return existing


# ============================================================
# SEARCH THE WEB
# ============================================================

def search_web():

    found = {}

    successful_queries = 0

    for query in SEARCH_QUERIES:

        print()
        print("Searching:", query)

        try:

            results = DDGS(timeout=20).text(
                query,
                region="us-en",
                safesearch="moderate",
                max_results=MAX_RESULTS_PER_QUERY,
                backend="auto",
            )

            successful_queries += 1

        except Exception as error:

            print("Search failed:")
            print(error)

            # Don't kill the entire program if one search engine fails.
            continue

        for result in results or []:

            title = clean_text(
                result.get("title")
            )

            url = clean_text(
                result.get("href")
                or result.get("url")
            )

            snippet = clean_text(
                result.get("body")
                or result.get("snippet")
            )

            if not title or not url:
                continue

            if not is_relevant(
                title,
                snippet
            ):
                continue

            clean_url = canonicalize_url(url)

            score = priority_score(
                title,
                snippet,
                clean_url
            )

            candidate = {

                "first_seen_utc":
                    datetime.now(timezone.utc)
                    .isoformat(timespec="seconds"),

                "priority_score":
                    str(score),

                "title":
                    title,

                "source_domain":
                    domain_from_url(clean_url),

                "url":
                    clean_url,

                "search_query":
                    query,

                "snippet":
                    snippet[:500],
            }

            # Remove duplicates
            old_candidate = found.get(clean_url)

            if (
                old_candidate is None
                or score >
                int(old_candidate["priority_score"])
            ):

                found[clean_url] = candidate

        # Don't hammer search engines with requests.
        time.sleep(
            random.uniform(0.8, 1.6)
        )

    if successful_queries == 0:

        raise RuntimeError(
            "All web searches failed. "
            "Try running the workflow again later."
        )

    return found


# ============================================================
# SAVE MASTER JOB DATABASE
# ============================================================

def save_master_csv(existing, new_jobs):

    combined = dict(existing)

    for job in new_jobs:

        combined[
            canonicalize_url(job["url"])
        ] = job

    rows = list(combined.values())

    # Highest priority jobs first
    rows.sort(
        key=lambda row: (
            int(
                row.get(
                    "priority_score"
                ) or 0
            ),
            row.get(
                "first_seen_utc"
            ) or "",
        ),
        reverse=True,
    )

    with open(
        "jobs.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=CSV_FIELDS
        )

        writer.writeheader()

        for row in rows:

            writer.writerow(
                {
                    field:
                    row.get(field, "")
                    for field in CSV_FIELDS
                }
            )


# ============================================================
# CREATE NEW-JOB ALERT
# ============================================================

def write_new_jobs_report(new_jobs):

    ordered = sorted(
        new_jobs,
        key=lambda job:
        int(job["priority_score"]),
        reverse=True,
    )

    # GitHub Actions reads this number later.
    with open(
        "new_jobs_count.txt",
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            str(len(ordered))
        )

    now = (
        datetime.now(timezone.utc)
        .strftime("%Y-%m-%d %H:%M UTC")
    )

    lines = [

        f"# {len(ordered)} new actuarial internship result(s)",

        "",

        f"Search completed: {now}",

        "",

        f"Target: Summer {TARGET_YEAR} actuarial internships.",

        "Higher-scoring results appear first.",

        "",
    ]

    if not ordered:

        lines.append(
            "No newly discovered postings this run."
        )

    else:

        for number, job in enumerate(
            ordered[:MAX_JOBS_IN_ISSUE],
            start=1
        ):

            title = (
                job["title"]
                .replace("|", "-")
            )

            snippet = (
                job["snippet"]
                .replace("|", "-")
            )

            lines.extend(
                [
                    f"## {number}. {title}",

                    f"- **Source:** "
                    f"{job['source_domain']}",

                    f"- **Priority score:** "
                    f"{job['priority_score']}",

                    f"- **Apply / Open:** "
                    f"{job['url']}",

                    f"- **Found from:** "
                    f"`{job['search_query']}`",
                ]
            )

            if snippet:

                lines.append(
                    f"- **Preview:** {snippet}"
                )

            lines.append("")

        if len(ordered) > MAX_JOBS_IN_ISSUE:

            lines.append(

                f"_Showing the top "
                f"{MAX_JOBS_IN_ISSUE}. "

                "The complete list is "
                "saved in jobs.csv._"
            )

    report = "\n".join(lines)

    with open(
        "new_jobs.md",
        "w",
        encoding="utf-8"
    ) as file:

        file.write(report)

    # Also display results directly inside GitHub Actions.
    summary_path = os.getenv(
        "GITHUB_STEP_SUMMARY"
    )

    if summary_path:

        with open(
            summary_path,
            "a",
            encoding="utf-8"
        ) as file:

            file.write(report)


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    print(
        "Actuarial Internship Finder"
    )

    print(
        "============================"
    )

    print(
        "Searching the public web "
        "for actuarial internships..."
    )

    # Load jobs we already know about
    existing = load_existing_jobs()

    existing_urls = set(existing)

    # Search the internet
    found = search_web()

    # Only keep jobs we haven't seen before
    new_jobs = [

        job

        for canonical_url, job
        in found.items()

        if canonical_url
        not in existing_urls
    ]

    print()
    print(
        "Relevant results found this run:",
        len(found)
    )

    print(
        "Brand-new results:",
        len(new_jobs)
    )

    # Save everything
    save_master_csv(
        existing,
        new_jobs
    )

    # Create alert report
    write_new_jobs_report(
        new_jobs
    )

    print()
    print("Finished.")

    print(
        "Master list: jobs.csv"
    )

    print(
        "New-job report: new_jobs.md"
    )


if __name__ == "__main__":
    main()
