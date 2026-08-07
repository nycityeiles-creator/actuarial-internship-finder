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
# COMPANIES WE ESPECIALLY WANT TO SEARCH
# ============================================================

TARGET_COMPANIES = [
    "Aon",
    "WTW",
    "Willis Towers Watson",
    "Mercer",
    "Milliman",
    "Chubb",
    "MetLife",
    "New York Life",
    "Guardian Life",
    "Travelers",
    "Zurich",
    "Swiss Re",
    "Munich Re",
    "Guy Carpenter",
    "Marsh McLennan",
    "Gallagher",
    "Lockton",
    "Liberty Mutual",
    "Nationwide",
    "Prudential",
    "MassMutual",
    "Cigna",
    "Aetna",
    "CVS Health",
    "UnitedHealth Group",
    "Optum",
    "Humana",
    "Elevance Health",
    "Segal",
    "Deloitte",
    "PwC",
    "EY",
    "KPMG",
]


# ============================================================
# GENERAL WEB SEARCHES
# ============================================================

SEARCH_QUERIES = [

    # NYC
    '"actuarial intern" "2027" "New York, NY"',
    '"actuarial internship" "2027" "New York, NY"',
    '"summer 2027" "actuarial intern" "New York City"',
    '"summer 2027" "actuarial internship" NYC',

    '"actuarial intern" "New York, NY" site:myworkdayjobs.com',
    '"actuarial intern" "New York, NY" site:greenhouse.io',
    '"actuarial intern" "New York, NY" site:lever.co',
    '"actuarial intern" "New York, NY" site:jobs.smartrecruiters.com',

    # Remote
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
# JOB SITE INFORMATION
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
    "company",
    "title",
    "location_type",
    "first_seen_utc",
    "priority_score",
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

        parts = urlsplit(url.strip())

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
# COMPANY NAME CLEANING
# ============================================================

def normalize_company_name(company):

    if not company:
        return None

    company = clean_text(company)

    company = re.sub(
        r"\s+[|-]\s+Careers?$",
        "",
        company,
        flags=re.IGNORECASE
    )

    company = re.sub(
        r"\s+[|-]\s+Jobs?$",
        "",
        company,
        flags=re.IGNORECASE
    )

    company = company.strip(
        " -|:"
    )

    if len(company) < 2:
        return None

    return company


# ============================================================
# IDENTIFY COMPANY
# ============================================================

def identify_company(
    title,
    snippet,
    url,
    known_company=None
):

    # --------------------------------------------------------
    # BEST CASE:
    # We searched for a specific company ourselves.
    # --------------------------------------------------------

    if known_company:
        return normalize_company_name(
            known_company
        )

    combined = (
        f"{title} {snippet}"
        .lower()
    )

    # --------------------------------------------------------
    # CHECK OUR KNOWN ACTUARIAL EMPLOYERS
    # --------------------------------------------------------

    for company in TARGET_COMPANIES:

        if company.lower() in combined:

            return normalize_company_name(
                company
            )

    # --------------------------------------------------------
    # TRY TO EXTRACT COMPANY FROM TITLE
    #
    # Examples:
    #
    # Actuarial Intern - Chubb
    # Actuarial Internship | New York Life
    # Actuarial Intern at MetLife
    # --------------------------------------------------------

    separators = [
        " at ",
        " - ",
        " | ",
        " – ",
        " — ",
    ]

    for separator in separators:

        if separator.lower() not in title.lower():
            continue

        parts = re.split(
            re.escape(separator),
            title,
            flags=re.IGNORECASE
        )

        if len(parts) < 2:
            continue

        # Usually company appears at the end.
        possible_company = (
            parts[-1]
            .strip()
        )

        possible_company_lower = (
            possible_company.lower()
        )

        # Avoid confusing location with company.
        location_words = (
            "new york",
            "remote",
            "nyc",
            "manhattan",
            "brooklyn",
            "queens",
            "bronx",
            "intern",
            "internship",
        )

        if any(
            word in possible_company_lower
            for word in location_words
        ):
            continue

        company = normalize_company_name(
            possible_company
        )

        if company:
            return company

    # --------------------------------------------------------
    # TRY DOMAIN NAME
    #
    # Example:
    # careers.metlife.com
    # jobs.chubb.com
    # --------------------------------------------------------

    domain = domain_from_url(url)

    generic_domains = (
        "linkedin.com",
        "indeed.com",
        "glassdoor.com",
        "ziprecruiter.com",
        "myworkdayjobs.com",
        "greenhouse.io",
        "lever.co",
        "smartrecruiters.com",
        "icims.com",
        "taleo.net",
    )

    if not any(
        generic in domain
        for generic in generic_domains
    ):

        parts = domain.split(".")

        if len(parts) >= 2:

            candidate = parts[-2]

            candidate = (
                candidate
                .replace("-", " ")
                .replace("_", " ")
                .title()
            )

            if candidate not in (
                "Careers",
                "Jobs",
                "Career",
            ):

                return normalize_company_name(
                    candidate
                )

    # If we cannot confidently identify a company:
    return None


# ============================================================
# LOCATION
# ============================================================

def get_location_type(
    title,
    snippet
):

    combined = (
        f"{title} {snippet}"
        .lower()
    )

    is_nyc = any(
        term in combined
        for term in NYC_TERMS
    )

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
# CHECK WHETHER RESULT IS VALID
# ============================================================

def is_relevant(
    title,
    snippet
):

    title_lower = title.lower()

    combined = (
        f"{title} {snippet}"
        .lower()
    )

    if any(
        phrase in title_lower
        for phrase in BAD_TITLE_PHRASES
    ):
        return False

    has_actuarial = (
        "actuar" in combined
    )

    has_internship = any(
        term in combined
        for term in (
            "intern",
            "internship",
            "summer analyst",
            "student program",
        )
    )

    location_type = (
        get_location_type(
            title,
            snippet
        )
    )

    return (
        has_actuarial
        and has_internship
        and location_type is not None
    )


# ============================================================
# PRIORITY SCORE
# ============================================================

def priority_score(
    title,
    snippet,
    url,
    company
):

    combined = (
        f"{title} {snippet}"
        .lower()
    )

    title_lower = title.lower()

    domain = domain_from_url(url)

    score = 0

    if "actuar" in title_lower:
        score += 5

    if "intern" in title_lower:
        score += 5

    if TARGET_YEAR in combined:
        score += 7

    if "summer" in combined:
        score += 3

    if any(
        term in combined
        for term in NYC_TERMS
    ):
        score += 4

    if any(
        term in combined
        for term in REMOTE_TERMS
    ):
        score += 4

    if company:
        score += 3

    if any(
        job_domain in domain
        for job_domain in DIRECT_JOB_DOMAINS
    ):
        score += 5

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

            if not url:
                continue

            existing[
                canonicalize_url(url)
            ] = row

    return existing


# ============================================================
# PROCESS ONE SEARCH RESULT
# ============================================================

def process_result(
    result,
    query,
    found,
    known_company=None
):

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
        return

    if not is_relevant(
        title,
        snippet
    ):
        return

    clean_url = (
        canonicalize_url(url)
    )

    company = (
        identify_company(
            title,
            snippet,
            clean_url,
            known_company
        )
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # NO COMPANY = NO JOB
    # --------------------------------------------------------

    if not company:

        print(
            "Skipping result because "
            "company could not be identified:"
        )

        print(title)

        return

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
            clean_url,
            company
        )
    )

    candidate = {

        "company":
            company,

        "title":
            title,

        "location_type":
            location_type,

        "first_seen_utc":
            datetime.now(
                timezone.utc
            ).isoformat(
                timespec="seconds"
            ),

        "priority_score":
            str(score),

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
        or score >
        int(
            old_candidate[
                "priority_score"
            ]
        )
    ):

        found[
            clean_url
        ] = candidate


# ============================================================
# SEARCH THE WEB
# ============================================================

def search_web():

    found = {}

    successful_queries = 0

    # --------------------------------------------------------
    # GENERAL SEARCH
    # --------------------------------------------------------

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

            process_result(
                result,
                query,
                found
            )

        time.sleep(
            random.uniform(
                1.0,
                1.7
            )
        )

    # --------------------------------------------------------
    # COMPANY-SPECIFIC SEARCH
    #
    # This is extremely useful because we KNOW the employer.
    # --------------------------------------------------------

    for company in TARGET_COMPANIES:

        queries = [

            f'"{company}" '
            f'"actuarial intern" '
            f'"New York"',

            f'"{company}" '
            f'"actuarial intern" '
            f'remote',

            f'"{company}" '
            f'"actuarial internship" '
            f'"{TARGET_YEAR}"',
        ]

        for query in queries:

            print()
            print(
                "Searching company:",
                company
            )

            print(
                "Query:",
                query
            )

            try:

                results = DDGS(
                    timeout=20
                ).text(

                    query,

                    region="us-en",

                    safesearch="moderate",

                    max_results=10,

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

                process_result(
                    result,
                    query,
                    found,
                    known_company=company
                )

            time.sleep(
                random.uniform(
                    0.8,
                    1.4
                )
            )

    if successful_queries == 0:

        raise RuntimeError(
            "All searches failed."
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

        writer = csv.DictWriter(
            file,
            fieldnames=CSV_FIELDS
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
# CREATE NEW-JOB REPORT
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

        "**Location:** NYC OR Remote",

        "",

        f"**Target:** Summer {TARGET_YEAR}",

        "",
    ]

    if not ordered:

        lines.append(
            "No new matching internships found."
        )

    else:

        for number, job in enumerate(
            ordered[
                :MAX_JOBS_IN_ISSUE
            ],
            start=1
        ):

            lines.extend(
                [
                    f"## {number}. "
                    f"{job['company']}",

                    f"**{job['title']}**",

                    "",

                    f"- **Company:** "
                    f"{job['company']}",

                    f"- **Location:** "
                    f"{job['location_type']}",

                    f"- **Score:** "
                    f"{job['priority_score']}",

                    f"- **Source:** "
                    f"{job['source_domain']}",

                    f"- **Apply:** "
                    f"{job['url']}",

                    "",
                ]
            )

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
        "Requirements:"
    )

    print(
        "- Actuarial internship"
    )

    print(
        "- NYC OR Remote"
    )

    print(
        "- Must have identifiable company"
    )

    print(
        f"- Prefer Summer {TARGET_YEAR}"
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
        "Valid jobs found:",
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
