import csv
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ddgs import DDGS


# ============================================================
# SETTINGS
# ============================================================

TARGET_YEAR = "2027"

# Much faster than our old version
MAX_RESULTS_PER_QUERY = 15

# Individual DDGS request timeout
SEARCH_TIMEOUT_SECONDS = 6

# HARD LIMIT for the entire searching portion
MAX_TOTAL_SEARCH_SECONDS = 150

MAX_JOBS_IN_ISSUE = 30


# ============================================================
# ACTUARIAL EMPLOYERS
#
# We do NOT run 3 searches for every company anymore.
# Instead, companies are grouped together into a few searches.
# ============================================================

TARGET_COMPANIES = [
    "Aon",
    "WTW",
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


# Different names that may appear in search results
COMPANY_ALIASES = {
    "WTW": [
        "WTW",
        "Willis Towers Watson",
    ],

    "Mercer": [
        "Mercer",
    ],

    "Aon": [
        "Aon",
    ],

    "Milliman": [
        "Milliman",
    ],

    "Chubb": [
        "Chubb",
    ],

    "MetLife": [
        "MetLife",
        "Met Life",
    ],

    "New York Life": [
        "New York Life",
        "NYL",
    ],

    "Guardian Life": [
        "Guardian Life",
        "Guardian",
    ],

    "Travelers": [
        "Travelers",
        "The Travelers Companies",
    ],

    "Zurich": [
        "Zurich",
        "Zurich Insurance",
    ],

    "Swiss Re": [
        "Swiss Re",
        "SwissRe",
    ],

    "Munich Re": [
        "Munich Re",
        "MunichRe",
    ],

    "Guy Carpenter": [
        "Guy Carpenter",
    ],

    "Marsh McLennan": [
        "Marsh McLennan",
        "Marsh & McLennan",
        "Marsh",
    ],

    "Gallagher": [
        "Gallagher",
        "Arthur J. Gallagher",
        "AJG",
    ],

    "Lockton": [
        "Lockton",
    ],

    "Liberty Mutual": [
        "Liberty Mutual",
    ],

    "Nationwide": [
        "Nationwide",
    ],

    "Prudential": [
        "Prudential",
        "Prudential Financial",
    ],

    "MassMutual": [
        "MassMutual",
        "Mass Mutual",
    ],

    "Cigna": [
        "Cigna",
        "The Cigna Group",
    ],

    "Aetna": [
        "Aetna",
    ],

    "CVS Health": [
        "CVS Health",
    ],

    "UnitedHealth Group": [
        "UnitedHealth Group",
        "United Healthcare",
        "UnitedHealthcare",
    ],

    "Optum": [
        "Optum",
    ],

    "Humana": [
        "Humana",
    ],

    "Elevance Health": [
        "Elevance Health",
        "Anthem",
    ],

    "Segal": [
        "Segal",
        "The Segal Group",
    ],

    "Deloitte": [
        "Deloitte",
    ],

    "PwC": [
        "PwC",
        "PricewaterhouseCoopers",
    ],

    "EY": [
        "EY",
        "Ernst & Young",
    ],

    "KPMG": [
        "KPMG",
    ],
}


# ============================================================
# LOCATION FILTER
#
# ONLY NYC OR REMOTE
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
    "virtual position",
    "remote - us",
    "remote us",
    "remote, us",
    "remote united states",
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
# ATS / JOB SYSTEMS
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


AGGREGATOR_DOMAINS = (
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "ziprecruiter.com",
    "simplyhired.com",
)


GENERIC_COMPANY_WORDS = (
    "jobs",
    "job",
    "careers",
    "career",
    "apply",
    "employment",
    "workday",
    "greenhouse",
    "lever",
    "smartrecruiters",
    "linkedin",
    "indeed",
    "glassdoor",
)


BAD_TITLE_PHRASES = (
    "reddit",
    "salary guide",
    "interview questions",
    "resume example",
    "actuarial exam",
    "study guide",
    "certification",
    "course",
    "top actuarial internships",
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
# BUILD OUR SEARCHES
#
# Total = 14 searches
# ============================================================

def build_search_queries():

    queries = [

        # ----------------------------------------------------
        # NYC
        # ----------------------------------------------------

        '"actuarial intern" "New York, NY" 2027',

        '"actuarial internship" "New York City" 2027',

        '"summer 2027" "actuarial intern" NYC',


        # ----------------------------------------------------
        # REMOTE
        # ----------------------------------------------------

        '"actuarial intern" remote 2027',

        '"actuarial internship" remote 2027',

        '"summer 2027" "actuarial internship" remote',


        # ----------------------------------------------------
        # MAJOR RECRUITING SYSTEMS
        # ----------------------------------------------------

        'site:myworkdayjobs.com "actuarial intern" '
        '("New York" OR remote)',

        'site:greenhouse.io "actuarial intern" '
        '("New York" OR remote)',

        'site:lever.co "actuarial intern" '
        '("New York" OR remote)',

        'site:smartrecruiters.com "actuarial intern" '
        '("New York" OR remote)',
    ]

    # --------------------------------------------------------
    # GROUP COMPANIES 8 AT A TIME
    #
    # 32 companies / 8 = only 4 additional searches
    # --------------------------------------------------------

    group_size = 8

    for index in range(
        0,
        len(TARGET_COMPANIES),
        group_size
    ):

        group = TARGET_COMPANIES[
            index:index + group_size
        ]

        company_part = " OR ".join(
            f'"{company}"'
            for company in group
        )

        query = (
            f"({company_part}) "
            f'"actuarial intern" '
            f'("New York" OR remote) '
            f'{TARGET_YEAR}'
        )

        queries.append(query)

    return queries


# ============================================================
# TEXT CLEANING
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
# URL CLEANING
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

            if lower_key.startswith(
                "utm_"
            ):
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
# LOCATION DETECTION
# ============================================================

def get_location_type(
    title,
    snippet
):

    combined = (
        f"{title} {snippet}"
        .lower()
    )

    nyc = any(
        term in combined
        for term in NYC_TERMS
    )

    explicitly_not_remote = any(
        term in combined
        for term in NOT_REMOTE_TERMS
    )

    remote = (
        any(
            term in combined
            for term in REMOTE_TERMS
        )
        and not explicitly_not_remote
    )

    if nyc and remote:
        return "NYC / Remote"

    if nyc:
        return "NYC"

    if remote:
        return "Remote"

    return None


# ============================================================
# COMPANY DETECTION
# ============================================================

def company_from_known_list(
    title,
    snippet
):

    combined = (
        f"{title} {snippet}"
    )

    # Longer aliases first so
    # "New York Life" wins over smaller matches
    all_aliases = []

    for company, aliases in COMPANY_ALIASES.items():

        for alias in aliases:

            all_aliases.append(
                (
                    company,
                    alias
                )
            )

    all_aliases.sort(
        key=lambda item:
        len(item[1]),
        reverse=True
    )

    for company, alias in all_aliases:

        pattern = (
            r"(?<![A-Za-z0-9])"
            + re.escape(alias)
            + r"(?![A-Za-z0-9])"
        )

        if re.search(
            pattern,
            combined,
            flags=re.IGNORECASE
        ):

            return company

    return None


def humanize_slug(text):

    text = (
        text
        .replace("-", " ")
        .replace("_", " ")
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    if not text:
        return None

    if text.lower() in GENERIC_COMPANY_WORDS:
        return None

    if len(text) < 2:
        return None

    return text.title()


def company_from_ats_url(url):

    try:

        parts = urlsplit(url)

        host = (
            parts.netloc
            .lower()
            .removeprefix("www.")
        )

        path_parts = [
            part
            for part in parts.path.split("/")
            if part
        ]


        # ----------------------------------------------------
        # WORKDAY
        #
        # Example:
        # travelers.wd5.myworkdayjobs.com
        # ----------------------------------------------------

        if host.endswith(
            "myworkdayjobs.com"
        ):

            first_part = host.split(".")[0]

            if not re.fullmatch(
                r"wd\d+",
                first_part
            ):

                return humanize_slug(
                    first_part
                )


        # ----------------------------------------------------
        # LEVER
        #
        # jobs.lever.co/company-name/job-id
        # ----------------------------------------------------

        if host.endswith(
            "lever.co"
        ):

            if path_parts:

                return humanize_slug(
                    path_parts[0]
                )


        # ----------------------------------------------------
        # GREENHOUSE
        # ----------------------------------------------------

        if host.endswith(
            "greenhouse.io"
        ):

            if path_parts:

                ignored = {
                    "jobs",
                    "job",
                }

                for part in path_parts:

                    if (
                        part.lower()
                        not in ignored
                    ):

                        return humanize_slug(
                            part
                        )


        # ----------------------------------------------------
        # SMARTRECRUITERS
        # ----------------------------------------------------

        if host.endswith(
            "smartrecruiters.com"
        ):

            if path_parts:

                return humanize_slug(
                    path_parts[0]
                )

    except Exception:

        pass

    return None


def company_from_title(title):

    # Common formats:
    #
    # Actuarial Intern - Chubb
    # Actuarial Intern | Chubb
    # Actuarial Intern at MetLife

    separators = [
        " at ",
        " | ",
        " - ",
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

        candidate = (
            parts[-1]
            .strip()
        )

        candidate_lower = (
            candidate.lower()
        )

        bad_candidate_terms = (
            "new york",
            "remote",
            "nyc",
            "manhattan",
            "brooklyn",
            "queens",
            "bronx",
            "intern",
            "internship",
            "2027",
        )

        if any(
            term in candidate_lower
            for term in bad_candidate_terms
        ):
            continue

        if (
            2 <= len(candidate) <= 60
        ):
            return candidate

    return None


def company_from_regular_domain(url):

    domain = domain_from_url(url)

    if not domain:
        return None

    # Do not guess company name from
    # aggregators or generic ATS domains
    if any(
        generic in domain
        for generic in
        DIRECT_JOB_DOMAINS
        + AGGREGATOR_DOMAINS
    ):
        return None

    pieces = domain.split(".")

    if len(pieces) < 2:
        return None

    # Usually:
    # careers.metlife.com
    # jobs.chubb.com
    #
    # second-to-last component = employer
    candidate = pieces[-2]

    return humanize_slug(
        candidate
    )


def identify_company(
    title,
    snippet,
    url
):

    # Best:
    # company name actually appears
    company = company_from_known_list(
        title,
        snippet
    )

    if company:
        return company


    # Next:
    # ATS URL tells us employer
    company = company_from_ats_url(
        url
    )

    if company:
        return company


    # Next:
    # title contains employer
    company = company_from_title(
        title
    )

    if company:
        return company


    # Finally:
    # actual employer domain
    company = company_from_regular_domain(
        url
    )

    if company:
        return company


    # No reliable company:
    # THROW IT AWAY
    return None


# ============================================================
# INTERNSHIP FILTER
# ============================================================

def is_actuarial_internship(
    title,
    snippet
):

    title_lower = title.lower()

    combined = (
        f"{title} {snippet}"
        .lower()
    )

    if any(
        bad in title_lower
        for bad in BAD_TITLE_PHRASES
    ):
        return False


    # Must actually be actuarial
    if "actuar" not in combined:
        return False


    # Strong internship signal.
    internship_in_title = any(
        term in title_lower
        for term in (
            "intern",
            "internship",
            "summer analyst",
        )
    )

    internship_in_text = any(
        term in combined
        for term in (
            "actuarial intern",
            "actuarial internship",
            "summer actuarial",
        )
    )

    if not (
        internship_in_title
        or internship_in_text
    ):
        return False


    # MUST BE NYC OR REMOTE
    if get_location_type(
        title,
        snippet
    ) is None:

        return False

    return True


# ============================================================
# SCORING
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

    title_lower = (
        title.lower()
    )

    domain = (
        domain_from_url(url)
    )

    score = 0


    if "actuar" in title_lower:
        score += 5


    if "intern" in title_lower:
        score += 5


    if TARGET_YEAR in combined:
        score += 8


    if "summer" in combined:
        score += 3


    location = get_location_type(
        title,
        snippet
    )

    if location == "NYC":
        score += 5

    elif location == "Remote":
        score += 5

    elif location == "NYC / Remote":
        score += 6


    # We successfully know the company
    if company:
        score += 3


    # Direct career pages are better
    if any(
        job_domain in domain
        for job_domain
        in DIRECT_JOB_DOMAINS
    ):
        score += 5


    # Aggregators are usable,
    # but direct employer pages rank higher
    if any(
        aggregator in domain
        for aggregator
        in AGGREGATOR_DOMAINS
    ):
        score -= 2

    return score


# ============================================================
# DUPLICATE IDENTIFIER
#
# This prevents the same job appearing
# through LinkedIn + Workday + Google, etc.
# ============================================================

def normalize_for_key(text):

    text = text.lower()

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text
    )

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def job_key(job):

    return (
        normalize_for_key(
            job.get(
                "company",
                ""
            )
        ),

        normalize_for_key(
            job.get(
                "title",
                ""
            )
        ),

        job.get(
            "location_type",
            ""
        ),
    )


# ============================================================
# LOAD OLD JOBS
# ============================================================

def load_existing_jobs():

    existing = {}

    if not os.path.exists(
        "jobs.csv"
    ):
        return existing

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

            title = clean_text(
                row.get(
                    "title",
                    ""
                )
            )

            snippet = clean_text(
                row.get(
                    "snippet",
                    ""
                )
            )

            url = clean_text(
                row.get(
                    "url",
                    ""
                )
            )

            if not title or not url:
                continue


            location = get_location_type(
                title,
                snippet
            )

            if not location:
                continue


            company = clean_text(
                row.get(
                    "company",
                    ""
                )
            )

            # Upgrade older CSV rows
            # that didn't yet have Company
            if not company:

                company = identify_company(
                    title,
                    snippet,
                    url
                )

            if not company:
                continue


            row["company"] = company

            row["location_type"] = (
                location
            )

            row["url"] = (
                canonicalize_url(
                    url
                )
            )

            key = job_key(row)

            existing[key] = row

    return existing


# ============================================================
# PROCESS A SEARCH RESULT
# ============================================================

def process_result(
    result,
    query
):

    title = clean_text(
        result.get(
            "title"
        )
    )

    url = clean_text(
        result.get(
            "href"
        )
        or result.get(
            "url"
        )
    )

    snippet = clean_text(
        result.get(
            "body"
        )
        or result.get(
            "snippet"
        )
    )


    if not title or not url:
        return None


    if not is_actuarial_internship(
        title,
        snippet
    ):
        return None


    url = canonicalize_url(
        url
    )


    company = identify_company(
        title,
        snippet,
        url
    )


    # ========================================================
    # YOUR COMPANY REQUIREMENT:
    #
    # If we don't know who the employer is,
    # DO NOT SAVE IT.
    # ========================================================

    if not company:

        print(
            "  Skipped - no identifiable company:",
            title
        )

        return None


    location_type = get_location_type(
        title,
        snippet
    )


    score = priority_score(
        title,
        snippet,
        url,
        company
    )


    return {

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
                url
            ),

        "url":
            url,

        "search_query":
            query,

        "snippet":
            snippet[:500],
    }


# ============================================================
# SEARCH WEB
# ============================================================

def search_web():

    queries = (
        build_search_queries()
    )

    print(
        f"Running {len(queries)} "
        "targeted searches."
    )

    print(
        f"Maximum search time: "
        f"{MAX_TOTAL_SEARCH_SECONDS} seconds."
    )

    print()


    found = {}

    successful_queries = 0

    start_time = (
        time.monotonic()
    )


    # One DDGS object for the entire run
    search_engine = DDGS(
        timeout=
        SEARCH_TIMEOUT_SECONDS
    )


    for number, query in enumerate(
        queries,
        start=1
    ):

        elapsed = (
            time.monotonic()
            - start_time
        )


        # ====================================================
        # HARD STOP
        #
        # Even if search engines are being slow,
        # stop after 150 seconds and save whatever we found.
        # ====================================================

        if (
            elapsed
            >= MAX_TOTAL_SEARCH_SECONDS
        ):

            print()
            print(
                "Search time limit reached."
            )

            print(
                "Saving results found so far."
            )

            break


        print(
            f"[{number}/{len(queries)}] "
            f"{query}"
        )


        try:

            results = (
                search_engine.text(
                    query,
                    region="us-en",
                    safesearch="moderate",

                    # Search postings from
                    # approximately the last year
                    timelimit="y",

                    max_results=
                    MAX_RESULTS_PER_QUERY,

                    backend="auto",
                )
            )

            successful_queries += 1


        except Exception as error:

            print(
                "  Search failed:",
                type(error).__name__,
                str(error)[:150]
            )

            continue


        print(
            "  Raw results:",
            len(results or [])
        )


        for result in results or []:

            job = process_result(
                result,
                query
            )


            if not job:
                continue


            key = job_key(
                job
            )


            existing_match = (
                found.get(
                    key
                )
            )


            # If same internship appears twice,
            # keep the higher-quality version.
            if existing_match:

                old_score = int(
                    existing_match.get(
                        "priority_score",
                        0
                    )
                    or 0
                )

                new_score = int(
                    job.get(
                        "priority_score",
                        0
                    )
                    or 0
                )

                if new_score <= old_score:
                    continue


            found[key] = job


        # Very small pause.
        # Old version had far more pauses
        # across 100+ queries.
        time.sleep(
            0.25
        )


    if successful_queries == 0:

        raise RuntimeError(
            "Every web search failed. "
            "Try again later."
        )


    elapsed = (
        time.monotonic()
        - start_time
    )


    print()
    print(
        f"Search portion finished "
        f"in {elapsed:.1f} seconds."
    )

    print(
        f"Valid unique jobs found: "
        f"{len(found)}"
    )


    return found


# ============================================================
# SAVE MASTER CSV
# ============================================================

def save_master_csv(
    existing,
    found
):

    combined = dict(
        existing
    )


    for key, job in found.items():

        if key in combined:

            # Preserve the original
            # date we first discovered it
            old_first_seen = (
                combined[key]
                .get(
                    "first_seen_utc"
                )
            )

            old_score = int(
                combined[key].get(
                    "priority_score",
                    0
                )
                or 0
            )

            new_score = int(
                job.get(
                    "priority_score",
                    0
                )
                or 0
            )


            # Update to a better version
            # of the same listing if found
            if new_score > old_score:

                if old_first_seen:

                    job[
                        "first_seen_utc"
                    ] = (
                        old_first_seen
                    )

                combined[key] = job

        else:

            combined[key] = job


    rows = list(
        combined.values()
    )


    rows.sort(

        key=lambda row: (

            int(
                row.get(
                    "priority_score",
                    0
                )
                or 0
            ),

            row.get(
                "first_seen_utc",
                ""
            ),
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
# CREATE GITHUB ALERT
# ============================================================

def write_new_jobs_report(
    new_jobs
):

    ordered = sorted(

        new_jobs,

        key=lambda job:
        int(
            job.get(
                "priority_score",
                0
            )
            or 0
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

        f"# 🚨 {len(ordered)} new actuarial internship(s)",

        "",

        f"Search completed: {now}",

        "",

        "**Filters:**",

        "- Actuarial internship",

        "- New York City OR Remote",

        "- Must have identifiable company",

        f"- Summer {TARGET_YEAR} prioritized",

        "",
    ]


    if not ordered:

        lines.append(
            "No new matching internships "
            "were discovered this run."
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

                    f"### {job['title']}",

                    "",

                    f"- **Company:** "
                    f"{job['company']}",

                    f"- **Location:** "
                    f"{job['location_type']}",

                    f"- **Priority Score:** "
                    f"{job['priority_score']}",

                    f"- **Source:** "
                    f"{job['source_domain']}",

                    f"- **Apply / View Job:** "
                    f"{job['url']}",

                    "",
                ]
            )


            if job.get(
                "snippet"
            ):

                lines.append(
                    f"> "
                    f"{job['snippet']}"
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


    # Also display results right
    # on the GitHub Action summary
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
# MAIN
# ============================================================

def main():

    print(
        "===================================="
    )

    print(
        "ACTUARIAL INTERNSHIP FINDER"
    )

    print(
        "===================================="
    )

    print()

    print(
        "Searching for:"
    )

    print(
        "• Actuarial internships"
    )

    print(
        "• New York City OR Remote"
    )

    print(
        "• Specific identifiable employer"
    )

    print(
        f"• Summer {TARGET_YEAR} prioritized"
    )

    print()


    # --------------------------------------------------------
    # OLD DATABASE
    # --------------------------------------------------------

    existing = (
        load_existing_jobs()
    )


    existing_keys = set(
        existing.keys()
    )


    print(
        "Previously saved jobs:",
        len(existing)
    )

    print()


    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    found = (
        search_web()
    )


    # --------------------------------------------------------
    # DETERMINE WHAT IS NEW
    # --------------------------------------------------------

    new_jobs = [

        job

        for key, job
        in found.items()

        if key
        not in existing_keys
    ]


    print()

    print(
        "Unique valid jobs this search:",
        len(found)
    )

    print(
        "Brand-new jobs:",
        len(new_jobs)
    )


    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    save_master_csv(
        existing,
        found
    )


    write_new_jobs_report(
        new_jobs
    )


    print()

    print(
        "===================================="
    )

    print(
        "DONE"
    )

    print(
        "===================================="
    )

    print(
        "Master database: jobs.csv"
    )

    print(
        "New-job report: new_jobs.md"
    )


if __name__ == "__main__":
    main()
