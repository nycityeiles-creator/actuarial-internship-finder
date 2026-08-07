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

MAX_RESULTS_PER_QUERY = 15
SEARCH_TIMEOUT_SECONDS = 6

# Stop searching after 2.5 minutes even if a search provider is slow
MAX_TOTAL_SEARCH_SECONDS = 150

MAX_JOBS_IN_ISSUE = 30


# ============================================================
# ACTUARIAL EMPLOYERS WE RECOGNIZE
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


# ============================================================
# COMPANY ALIASES
# ============================================================

COMPANY_ALIASES = {

    "Aon": [
        "Aon",
    ],

    "WTW": [
        "WTW",
        "Willis Towers Watson",
    ],

    "Mercer": [
        "Mercer",
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
        "The Guardian Life Insurance Company",
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
    ],

    "Gallagher": [
        "Gallagher",
        "Arthur J. Gallagher",
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
        "UnitedHealthcare",
        "United Healthcare",
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
# ONLY:
# - NEW YORK CITY
# - REMOTE
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
# JOB SITES
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
    "indeed.com",
    "linkedin.com",
    "glassdoor.com",
    "ziprecruiter.com",
    "simplyhired.com",
    "monster.com",
    "careerbuilder.com",
)


# ============================================================
# THESE CAN NEVER BE THE COMPANY
# ============================================================

INVALID_COMPANY_NAMES = (
    "indeed",
    "indeed.com",
    "linkedin",
    "linkedin.com",
    "glassdoor",
    "glassdoor.com",
    "ziprecruiter",
    "zip recruiter",
    "ziprecruiter.com",
    "simplyhired",
    "simply hired",
    "monster",
    "monster.com",
    "careerbuilder",
    "career builder",
    "google",
    "google jobs",
    "bing",
    "jobs",
    "job",
    "careers",
    "career",
    "employment",
    "apply",
    "workday",
    "myworkdayjobs",
    "myworkdayjobs.com",
    "greenhouse",
    "greenhouse.io",
    "lever",
    "lever.co",
    "smartrecruiters",
    "smartrecruiters.com",
    "icims",
    "icims.com",
    "taleo",
    "successfactors",
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
# SEARCH QUERIES
# ============================================================

def build_search_queries():

    queries = [

        # NYC
        '"actuarial intern" "New York, NY" 2027',
        '"actuarial internship" "New York City" 2027',
        '"summer 2027" "actuarial intern" NYC',

        # Remote
        '"actuarial intern" remote 2027',
        '"actuarial internship" remote 2027',
        '"summer 2027" "actuarial internship" remote',

        # Career systems
        'site:myworkdayjobs.com "actuarial intern" ("New York" OR remote)',
        'site:greenhouse.io "actuarial intern" ("New York" OR remote)',
        'site:lever.co "actuarial intern" ("New York" OR remote)',
        'site:smartrecruiters.com "actuarial intern" ("New York" OR remote)',
    ]

    # Search several companies at once instead of
    # making 3 separate searches for every employer.
    group_size = 9

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

        queries.append(
            f"({company_part}) "
            f'"actuarial intern" '
            f'("New York" OR remote) '
            f'{TARGET_YEAR}'
        )

    return queries


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
# GET DOMAIN
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
# VALIDATE COMPANY
#
# THIS IS THE IMPORTANT FIX
# ============================================================

def validate_company(company):

    if not company:
        return None

    company = clean_text(company)

    company = (
        company
        .replace("®", "")
        .replace("™", "")
        .strip(" -|:")
    )

    normalized = (
        company
        .lower()
        .replace("www.", "")
        .strip()
    )

    normalized_without_domain = re.sub(
        r"\.(com|org|net|co)$",
        "",
        normalized
    )

    for invalid in INVALID_COMPANY_NAMES:

        invalid_normalized = (
            invalid
            .lower()
            .replace("www.", "")
        )

        invalid_without_domain = re.sub(
            r"\.(com|org|net|co)$",
            "",
            invalid_normalized
        )

        if (
            normalized == invalid_normalized
            or
            normalized_without_domain
            == invalid_without_domain
        ):

            return None

    if len(company) < 2:
        return None

    if len(company) > 80:
        return None

    return company


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

    is_nyc = any(
        term in combined
        for term in NYC_TERMS
    )

    explicitly_not_remote = any(
        term in combined
        for term in NOT_REMOTE_TERMS
    )

    is_remote = (
        any(
            term in combined
            for term in REMOTE_TERMS
        )
        and not explicitly_not_remote
    )

    if is_nyc and is_remote:
        return "NYC / Remote"

    if is_nyc:
        return "NYC"

    if is_remote:
        return "Remote"

    return None


# ============================================================
# COMPANY FROM RECOGNIZED COMPANY LIST
# ============================================================

def company_from_known_list(
    title,
    snippet
):

    combined = (
        f"{title} {snippet}"
    )

    aliases = []

    for company, names in COMPANY_ALIASES.items():

        for alias in names:

            aliases.append(
                (
                    company,
                    alias
                )
            )

    # Longest company names first
    aliases.sort(
        key=lambda item:
        len(item[1]),
        reverse=True
    )

    for company, alias in aliases:

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

            return validate_company(
                company
            )

    return None


# ============================================================
# CLEAN COMPANY SLUG
# ============================================================

def humanize_slug(text):

    text = (
        str(text)
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

    candidate = text.title()

    return validate_company(
        candidate
    )


# ============================================================
# COMPANY FROM ATS URL
# ============================================================

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

            first = host.split(".")[0]

            if not re.fullmatch(
                r"wd\d+",
                first
            ):

                return humanize_slug(
                    first
                )

        # ----------------------------------------------------
        # LEVER
        #
        # jobs.lever.co/company/job
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

            ignored = {
                "jobs",
                "job",
                "embed",
            }

            for part in path_parts:

                if (
                    part.lower()
                    not in ignored
                ):

                    company = humanize_slug(
                        part
                    )

                    if company:
                        return company

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


# ============================================================
# COMPANY FROM TITLE
# ============================================================

def company_from_title(title):

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

        # Don't mistake locations/job terms for company names
        bad_terms = (
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
            "summer",
        )

        if any(
            term in candidate_lower
            for term in bad_terms
        ):

            continue

        company = validate_company(
            candidate
        )

        if company:
            return company

    return None


# ============================================================
# COMPANY FROM DIRECT EMPLOYER DOMAIN
#
# careers.metlife.com -> Metlife
# jobs.chubb.com -> Chubb
# ============================================================

def company_from_regular_domain(url):

    domain = domain_from_url(url)

    if not domain:
        return None

    # NEVER derive employer from Indeed/LinkedIn/etc.
    if any(
        aggregator in domain
        for aggregator in AGGREGATOR_DOMAINS
    ):
        return None

    # ATS domains have their own extraction logic
    if any(
        ats in domain
        for ats in DIRECT_JOB_DOMAINS
    ):
        return None

    pieces = domain.split(".")

    if len(pieces) < 2:
        return None

    candidate = pieces[-2]

    return humanize_slug(
        candidate
    )


# ============================================================
# IDENTIFY THE ACTUAL EMPLOYER
# ============================================================

def identify_company(
    title,
    snippet,
    url
):

    domain = domain_from_url(url)

    # --------------------------------------------------------
    # 1. BEST METHOD
    #
    # Recognized company appears in title/description
    # --------------------------------------------------------

    company = company_from_known_list(
        title,
        snippet
    )

    company = validate_company(
        company
    )

    if company:
        return company

    # --------------------------------------------------------
    # 2. ATS URL
    #
    # Workday / Greenhouse / Lever may reveal employer
    # --------------------------------------------------------

    company = company_from_ats_url(
        url
    )

    company = validate_company(
        company
    )

    if company:
        return company

    # --------------------------------------------------------
    # 3. JOB TITLE
    #
    # Actuarial Intern - Chubb
    # --------------------------------------------------------

    company = company_from_title(
        title
    )

    company = validate_company(
        company
    )

    if company:
        return company

    # --------------------------------------------------------
    # 4. DIRECT EMPLOYER DOMAIN
    #
    # Only if source is NOT Indeed, LinkedIn, etc.
    # --------------------------------------------------------

    is_aggregator = any(
        aggregator in domain
        for aggregator in AGGREGATOR_DOMAINS
    )

    if not is_aggregator:

        company = company_from_regular_domain(
            url
        )

        company = validate_company(
            company
        )

        if company:
            return company

    # --------------------------------------------------------
    # WE CANNOT CONFIDENTLY IDENTIFY EMPLOYER
    #
    # Throw result away.
    # --------------------------------------------------------

    return None


# ============================================================
# ACTUARIAL INTERNSHIP FILTER
# ============================================================

def is_actuarial_internship(
    title,
    snippet
):

    title_lower = (
        title.lower()
    )

    combined = (
        f"{title} {snippet}"
        .lower()
    )

    if any(
        phrase in title_lower
        for phrase in BAD_TITLE_PHRASES
    ):

        return False

    # Must actually be actuarial
    if "actuar" not in combined:
        return False

    # Must actually be internship-related
    internship_signal = any(
        term in combined
        for term in (
            "actuarial intern",
            "actuarial internship",
            "summer actuarial",
            "actuary intern",
        )
    )

    title_intern_signal = (
        "intern" in title_lower
    )

    if not (
        internship_signal
        or title_intern_signal
    ):

        return False

    # Must be NYC or remote
    if get_location_type(
        title,
        snippet
    ) is None:

        return False

    return True


# ============================================================
# SCORE RESULT
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

    if company:
        score += 3

    # Direct career systems get preference
    if any(
        job_domain in domain
        for job_domain in DIRECT_JOB_DOMAINS
    ):

        score += 5

    # Aggregators still allowed,
    # but rank below direct company pages
    if any(
        aggregator in domain
        for aggregator in AGGREGATOR_DOMAINS
    ):

        score -= 2

    return score


# ============================================================
# NORMALIZE FOR DUPLICATES
# ============================================================

def normalize_for_key(text):

    text = (
        str(text or "")
        .lower()
    )

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
# LOAD EXISTING JOBS
#
# ALSO CLEANS OLD BAD ROWS LIKE:
# Company = Indeed
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

            # Must still satisfy NYC / Remote
            location = get_location_type(
                title,
                snippet
            )

            if not location:
                continue

            old_company = validate_company(
                row.get(
                    "company",
                    ""
                )
            )

            # If old CSV says Indeed/LinkedIn/etc,
            # attempt to find the REAL employer.
            if not old_company:

                old_company = identify_company(
                    title,
                    snippet,
                    url
                )

            # Still can't identify employer?
            # Remove this old row entirely.
            if not old_company:

                print(
                    "Removing old row with "
                    "unidentified employer:",
                    title
                )

                continue

            row[
                "company"
            ] = old_company

            row[
                "location_type"
            ] = location

            row[
                "url"
            ] = canonicalize_url(
                url
            )

            key = job_key(
                row
            )

            existing[
                key
            ] = row

    return existing


# ============================================================
# PROCESS ONE SEARCH RESULT
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
    # HARD REQUIREMENT
    #
    # NO REAL COMPANY = DO NOT SAVE JOB
    # ========================================================

    if not company:

        print(
            "  SKIPPED - could not identify real employer:",
            title
        )

        return None

    # Extra final validation
    company = validate_company(
        company
    )

    if not company:

        print(
            "  SKIPPED - invalid employer:",
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

    queries = build_search_queries()

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

        # Hard stop
        if elapsed >= MAX_TOTAL_SEARCH_SECONDS:

            print()
            print(
                "Search time limit reached."
            )

            print(
                "Saving jobs found so far."
            )

            break

        print(
            f"[{number}/{len(queries)}] "
            f"{query}"
        )

        try:

            results = list(
                search_engine.text(
                    query,
                    region="us-en",
                    safesearch="moderate",
                    timelimit="y",
                    max_results=
                    MAX_RESULTS_PER_QUERY,
                    backend="auto",
                )
                or []
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
            len(results)
        )

        for result in results:

            job = process_result(
                result,
                query
            )

            if not job:
                continue

            key = job_key(
                job
            )

            previous = found.get(
                key
            )

            if previous:

                old_score = int(
                    previous.get(
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

                # Keep better version of duplicate listing
                if new_score <= old_score:
                    continue

            found[
                key
            ] = job

        # Tiny pause between searches
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
        f"Search finished in "
        f"{elapsed:.1f} seconds."
    )

    print(
        f"Valid unique jobs found: "
        f"{len(found)}"
    )

    return found


# ============================================================
# SAVE MASTER JOB DATABASE
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

            old_first_seen = (
                combined[key]
                .get(
                    "first_seen_utc"
                )
            )

            old_score = int(
                combined[key]
                .get(
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

            if new_score > old_score:

                if old_first_seen:

                    job[
                        "first_seen_utc"
                    ] = old_first_seen

                combined[
                    key
                ] = job

        else:

            combined[
                key
            ] = job

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
# WRITE NEW JOB ALERT
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

        f"# {len(ordered)} new actuarial internship(s)",

        "",

        f"Search completed: {now}",

        "",

        "**Filters:**",

        "- Actuarial internship",

        "- New York City OR Remote",

        "- Must have identifiable real employer",

        "- Job boards are NOT treated as employers",

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

                    f"- **Found on:** "
                    f"{job['source_domain']}",

                    f"- **Apply / View:** "
                    f"{job['url']}",

                    "",
                ]
            )

            if job.get(
                "snippet"
            ):

                lines.append(
                    f"> {job['snippet']}"
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
# MAIN PROGRAM
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
        "Requirements:"
    )

    print(
        "- Actuarial internship"
    )

    print(
        "- New York City OR Remote"
    )

    print(
        "- Must identify REAL employer"
    )

    print(
        "- Indeed/LinkedIn/etc. are sources only"
    )

    print(
        f"- Summer {TARGET_YEAR} prioritized"
    )

    print()

    # --------------------------------------------------------
    # LOAD PREVIOUS DATABASE
    # --------------------------------------------------------

    existing = load_existing_jobs()

    existing_keys = set(
        existing.keys()
    )

    print(
        "Previously saved valid jobs:",
        len(existing)
    )

    print()

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    found = search_web()

    # --------------------------------------------------------
    # FIND BRAND-NEW JOBS
    # --------------------------------------------------------

    new_jobs = [

        job

        for key, job
        in found.items()

        if key not in existing_keys
    ]

    print()

    print(
        "Valid jobs found this search:",
        len(found)
    )

    print(
        "Brand-new jobs:",
        len(new_jobs)
    )

    # --------------------------------------------------------
    # SAVE DATABASE
    # --------------------------------------------------------

    save_master_csv(
        existing,
        found
    )

    # --------------------------------------------------------
    # CREATE ALERT
    # --------------------------------------------------------

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
