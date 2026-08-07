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

MAX_RESULTS_PER_QUERY = 25
MAX_JOBS_IN_ISSUE = 25


# ============================================================
# WHAT WE SEARCH FOR
# ============================================================

SEARCH_QUERIES = [

    # -------------------------
    # NEW YORK CITY
    # -------------------------

    '"actuarial intern" "2027" "New York, NY"',
    '"actuarial internship" "2027" "New York, NY"',
    '"summer 2027" "actuarial intern" "New York City"',
    '"summer 2027" "actuarial internship" NYC',

    '"actuarial intern" "New York, NY" site:myworkdayjobs.com',
    '"actuarial intern" "New York, NY" site:greenhouse.io',
    '"actuarial intern" "New York, NY" site:lever.co',
    '"actuarial intern" "New York, NY" site:jobs.smartrecruiters.com',

    # -------------------------
    # REMOTE
    # -------------------------

    '"actuarial intern" "2027" remote',
    '"actuarial internship" "2027" remote',
    '"summer 2027" actuarial remote internship',

    '"actuarial intern" remote site:myworkdayjobs.com',
    '"actuarial intern" remote site:greenhouse.io',
    '"actuarial intern" remote site:lever.co',
    '"actuarial intern" remote site:jobs.smartrecruiters.com',
]


# ============================================================
# LOCATION FILTERS
# ============================================================

NYC_TERMS = (
    "new york, ny",
    "new york ny",
    "new york city",
    "new york, new york",
    "nyc",
    "manhattan",
    "brooklyn",
    "queens",
    "bronx",
    "staten island",
)


REMOTE_TERMS = (
    "remote",
    "fully remote",
    "work from home",
    "work-from-home",
    "virtual",
)


NOT_REMOTE_TERMS = (
    "not remote",
    "no remote",
    "onsite only",
    "on-site only",
    "must work onsite",
    "must work on-site",
)


# ============================================================
# CAREER WEBSITE PRIORITY
# ============================================================

DIRECT_JOB_DOMAINS = (
    "myworkdayjobs.com",
    "greenhouse.io",
    "lever.co",
    "smartrecruiters.com",
    "icims.com",
    "taleo.net",
    "successfactors.com",
)


LOWER_PRIORITY_DOMAINS = (
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "ziprecruiter.com",
    "simplyhired.com",
)


BAD_TITLE_PHRASES = (
    "reddit",
    "salary guide",
    "interview questions",
    "resume example",
    "actuarial exam",
    "study guide",
    "course",
    "certification",
)


CSV_FIELDS = [
    "first_seen_utc",
    "priority_score",
    "location_type",
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
# CLEAN TEXT
# ============================================================

def clean_text(text):

    text = str(text or "")

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return (
        text
        .replace("<", "")
        .replace(">", "")
    )


# ============================================================
# CLEAN URL
# ============================================================

def canonicalize_url(url):

    try:

        parts = urlsplit(
            url.strip()
        )

        kept_query = []

        for key, value in parse_qsl(
            parts.query,
            keep_blank_values=True
        ):

            lower_key = key.lower()

            if lower_key.startswith("utm_"):
                continue

            if lower_key in TRACKING_KEYS:
                continue

            kept_query.append(
                (key, value)
            )

        path = (
            parts.path.rstrip("/")
            or "/"
        )

        return urlunsplit(
            (
                parts.scheme.lower(),
                parts.netloc.lower(),
                path,
                urlencode(
                    kept_query,
                    doseq=True
                ),
                "",
            )
        )

    except Exception:

        return url.strip()


# ============================================================
# DOMAIN
# ============================================================

def domain_from_url(url):

    try:

        return (
            urlsplit(url)
            .netloc
            .lower()
            .removeprefix("www.")
        )

    except Exception:

        return ""


# ============================================================
# CHECK LOCATION
# ============================================================

def get_location_type(title, snippet):

    combined = (
        f"{title} {snippet}"
        .lower()
    )

    # -------------------------
    # NYC
    # -------------------------

    is_nyc = any(
        term in combined
        for term in NYC_TERMS
    )

    # -------------------------
    # REMOTE
    # -------------------------

    says_not_remote = any(
        term in combined
        for term in NOT_REMOTE_TERMS
    )

    is_remote = (
        any(
            term in combined
            for term in REMOTE_TERMS
        )
        and not says_not_remote
    )

    if is_nyc and is_remote:
        return "NYC / Remote"

    if is_nyc:
        return "NYC"

    if is_remote:
        return "Remote"

    return None


# ============================================================
# CHECK WHETHER RESULT IS AN ACTUARIAL INTERNSHIP
# ============================================================

def is_relevant(title, snippet):

    title_lower = title.lower()

    combined = (
        f"{title} {snippet}"
        .lower()
    )

    # Remove obvious junk
    if any(
        phrase in title_lower
        for phrase in BAD_TITLE_PHRASES
    ):
        return False

    # Must be actuarial
    has_actuarial = (
        "actuar" in combined
    )

    # Must be internship/student position
    has_internship = any(
        term in combined
        for term in (
            "intern",
            "internship",
            "summer analyst",
            "student program",
        )
    )

    # Must be NYC OR Remote
    location_type = get_location_type(
        title,
        snippet
    )

    correct_location = (
        location_type is not None
    )

    return (
        has_actuarial
        and has_internship
        and correct_location
    )


# ============================================================
# PRIORITY SCORE
# ============================================================

def priority_score(
    title,
    snippet,
    url
):

    combined = (
        f"{title} {snippet}"
        .lower()
    )

    title_lower = (
        title.lower()
    )

    domain = (
        domain_from_url(url)
    )

    score = 0

    # Actuarial in title
    if "actuar" in title_lower:
        score += 5

    # Intern in title
    if "intern" in title_lower:
        score += 5

    # Summer 2027
    if TARGET_YEAR in combined:
        score += 7

    if "summer" in combined:
        score += 3

    # NYC
    if any(
        term in combined
        for term in NYC_TERMS
    ):
        score += 4

    # Remote
    if any(
        term in combined
        for term in REMOTE_TERMS
    ):
        score += 4

    # Direct application pages get preference
    if any(
        job_domain in domain
        for job_domain in DIRECT_JOB_DOMAINS
    ):
        score += 5

    # Job aggregators rank slightly lower
    if any(
        job_domain in domain
        for job_domain in LOWER_PRIORITY_DOMAINS
    ):
        score -= 2

    return score


# ============================================================
# LOAD PREVIOUS JOBS
# ============================================================

def load_existing_jobs():

    if not os.path.exists(
        "jobs.csv"
    ):
        return {}

    existing = {}

    with open(
        "jobs.csv",
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row in reader:

            url = (
                row.get(
                    "url",
                    ""
                )
                .strip()
            )

            title = row.get(
                "title",
                ""
            )

            snippet = row.get(
                "snippet",
                ""
            )

            if not url:
                continue

            # Remove old jobs that don't
            # meet our NYC / Remote rule.
            if not is_relevant(
                title,
                snippet
            ):
                continue

            existing[
                canonicalize_url(url)
            ] = row

    return existing


# ============================================================
# SEARCH THE WEB
# ============================================================

def search_web():

    found = {}

    successful_queries = 0

    for query in SEARCH_QUERIES:

        print()
        print(
            "Searching:",
            query
        )

        try:

            results = DDGS(
                timeout=20
            ).text(

                query,

                region="us-en",

                safesearch="moderate",

                max_results=
                MAX_RESULTS_PER_QUERY,

                backend="auto",
            )

            successful_queries += 1

        except Exception as error:

            print(
                "Search failed:",
                error
            )

            continue

        for result in results or []:

            title = clean_text(
                result.get(
                    "title"
                )
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

            # IMPORTANT:
            # Reject anything that is
            # not NYC or Remote.
            if not is_relevant(
                title,
                snippet
            ):
                continue

            clean_url = (
                canonicalize_url(
                    url
                )
            )

            location_type = (
                get_location_type(
                    title,
                    snippet
                )
            )

            score = (
                priority_score(
                    title,
                    snippet,
                    clean_url
                )
            )

            candidate = {

                "first_seen_utc":
                    datetime.now(
                        timezone.utc
                    ).isoformat(
                        timespec="seconds"
                    ),

                "priority_score":
                    str(score),

                "location_type":
                    location_type,

                "title":
                    title,

                "source_domain":
                    domain_from_url(
                        clean_url
                    ),

                "url":
                    clean_url,

                "search_query":
                    query,

                "snippet":
                    snippet[:500],
            }

            old_candidate = (
                found.get(
                    clean_url
                )
            )

            if (
                old_candidate is None
                or
                score >
                int(
                    old_candidate[
                        "priority_score"
                    ]
                )
            ):

                found[
                    clean_url
                ] = candidate

        # Small delay so we don't
        # hammer search engines
        time.sleep(
            random.uniform(
                1.0,
                2.0
            )
        )

    if successful_queries == 0:

        raise RuntimeError(
            "All searches failed. "
            "Run the workflow again later."
        )

    return found


# ============================================================
# SAVE JOBS.CSV
# ============================================================

def save_master_csv(
    existing,
    new_jobs
):

    combined = dict(
        existing
    )

    for job in new_jobs:

        combined[
            canonicalize_url(
                job["url"]
            )
        ] = job

    rows = list(
        combined.values()
    )

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

        writer = (
            csv.DictWriter(
                file,
                fieldnames=CSV_FIELDS
            )
        )

        writer.writeheader()

        for row in rows:

            writer.writerow(
                {
                    field:
                    row.get(
                        field,
                        ""
                    )

                    for field
                    in CSV_FIELDS
                }
            )


# ============================================================
# CREATE NEW JOB ALERT
# ============================================================

def write_new_jobs_report(
    new_jobs
):

    ordered = sorted(

        new_jobs,

        key=lambda job:
        int(
            job[
                "priority_score"
            ]
        ),

        reverse=True,
    )

    with open(
        "new_jobs_count.txt",
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            str(
                len(ordered)
            )
        )

    now = (
        datetime.now(
            timezone.utc
        )
        .strftime(
            "%Y-%m-%d %H:%M UTC"
        )
    )

    lines = [

        f"# {len(ordered)} new actuarial internship(s)",

        "",

        f"Search completed: {now}",

        "",

        "Location filter: "
        "**New York City OR Remote**",

        "",

        f"Target season: "
        f"**Summer {TARGET_YEAR}**",

        "",
    ]

    if not ordered:

        lines.append(
            "No new NYC or remote "
            "actuarial internships "
            "were found."
        )

    else:

        for number, job in enumerate(
            ordered[
                :MAX_JOBS_IN_ISSUE
            ],
            start=1
        ):

            title = (
                job["title"]
                .replace(
                    "|",
                    "-"
                )
            )

            snippet = (
                job["snippet"]
                .replace(
                    "|",
                    "-"
                )
            )

            lines.extend(
                [
                    f"## {number}. "
                    f"{title}",

                    f"- **Location type:** "
                    f"{job['location_type']}",

                    f"- **Source:** "
                    f"{job['source_domain']}",

                    f"- **Priority score:** "
                    f"{job['priority_score']}",

                    f"- **Apply:** "
                    f"{job['url']}",
                ]
            )

            if snippet:

                lines.append(
                    f"- **Preview:** "
                    f"{snippet}"
                )

            lines.append("")

    report = "\n".join(
        lines
    )

    with open(
        "new_jobs.md",
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            report
        )

    summary_path = os.getenv(
        "GITHUB_STEP_SUMMARY"
    )

    if summary_path:

        with open(
            summary_path,
            "a",
            encoding="utf-8"
        ) as file:

            file.write(
                report
            )


# ============================================================
# RUN PROGRAM
# ============================================================

def main():

    print(
        "Actuarial Internship Finder"
    )

    print(
        "============================"
    )

    print(
        "ONLY searching for:"
    )

    print(
        "- New York City internships"
    )

    print(
        "- Remote internships"
    )

    print(
        f"- Preferably Summer {TARGET_YEAR}"
    )

    existing = (
        load_existing_jobs()
    )

    existing_urls = set(
        existing
    )

    found = (
        search_web()
    )

    new_jobs = [

        job

        for canonical_url, job
        in found.items()

        if canonical_url
        not in existing_urls
    ]

    print()
    print(
        "NYC / Remote jobs found:",
        len(found)
    )

    print(
        "Brand-new jobs:",
        len(new_jobs)
    )

    save_master_csv(
        existing,
        new_jobs
    )

    write_new_jobs_report(
        new_jobs
    )

    print()
    print(
        "Search finished."
    )

    print(
        "Results saved to jobs.csv"
    )


if __name__ == "__main__":
    main()
