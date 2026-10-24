from datetime import datetime, timedelta, timezone
from typing import List, Set

# Curated job platform domains (sender addresses ending with or containing these)
JOB_PLATFORM_DOMAINS: List[str] = [
    "linkedin.com",
    "internshala.com",
    "hirist.com",
    "hirist.tech",
    "naukri.com",
    "foundit.in",
    "foundit.com",
    "indeed.com",
    "wellfound.com",
    "instahyre.com",
    "acciojob.com",
    "acciojob-team.com",
    "jobhai.com",
    "auroskkil.com",
    "greenhouse.io",
    "lever.co",
    "myworkday.com",
    "workday.com",
    "smartrecruiters.com",
    "ashbyhq.com",
    "bamboohr.com",
    "icims.com",
    "jobvite.com",
    "cutshort.io",
    "cuvette.tech",
    "unstop.com",
    "glassdoor.com",
]

# Core recruitment intent keywords for subject and content search
JOB_INTENT_KEYWORDS: List[str] = [
    "job",
    "hiring",
    "interview",
    "offer",
    "application",
    "career",
    "opening",
    "recruiter",
    "vacancy",
    "internship",
    "shortlisted",
    "assessment",
    "opportunity",
]

EXCLUDED_DOMAINS: List[str] = [
    # E-commerce & Shopping
    "amazon.in",
    "amazon.com",
    "flipkart.com",
    "myntra.com",
    "swiggy.in",
    "zomato.com",
    "meesho.com",
    "ajio.com",
    "tatacliq.com",
    "fashionnotification.tatacliq.com",
    
    # Travel, Commute & Flights
    "makemytrip.com",
    "zen-makemytrip.com",
    "uber.com",
    "ola.cabs",
    "irctc.co.in",
    "goibibo.com",
    "ixigo.com",
    "easemytrip.com",
    "redbus.in",
    "agoda.com",
    "booking.com",
    "airindia.com",
    "indigo.in",

    # EdTech, Course Selling & Academies (Non-job promos)
    "alison.com",
    "eduskillsfoundation.org",
    "springboard.infosys.com",
    "udemy.com",
    "coursera.org",
    "simplilearn.com",
    "scaler.com",
    "upgrad.com",
    "codingninjas.com",

    # Developer Marketing / Newsletters / Corporate Announcements
    "openrouter.ai",
    "lamatic.ai",
    "labs.lamatic.ai",
    "google.com",  # Google One / AI Pro promos (individual job platforms like google careers are under greenhouse/ashby/lever)
    "accounts.google.com",

    # Financial / Virtual Cards / Spam
    "gokiwi.in",
    "mcafee.com",

    # Social & Media
    "hinge.co",
    "instagram.com",
    "facebookmail.com",
    "twitter.com",
    "x.com",
    "snapchat.com",
    "netflix.com",
    "spotify.com",

    # Marketing, Sales & Design Tools (Non-Job)
    "canva.com",
    "apollo.io",
    "aceronline.co.in",
]


def build_x_gm_raw_query(since_days: int = 30) -> str:
    """
    Constructs an optimized X-GM-RAW query string for Gmail IMAP search.
    Logic: (platform sender domains OR job keywords) - denylist, fetched incrementally SINCE date.
    """
    # 1. Platform domains OR clause
    domain_queries = " OR ".join([f"from:{domain}" for domain in JOB_PLATFORM_DOMAINS])

    # 2. Keywords OR clause
    keyword_queries = " OR ".join([f"subject:{kw}" for kw in JOB_INTENT_KEYWORDS])

    # 3. Excluded domains minus clause
    denylist_queries = " ".join([f"-from:{domain}" for domain in EXCLUDED_DOMAINS])

    # 4. Incremental SINCE date filter (format: YYYY/MM/DD)
    since_dt = datetime.now(timezone.utc) - timedelta(days=since_days)
    since_str = since_dt.strftime("%Y/%m/%d")

    # Combine: ( (from:domain1 OR from:domain2 ...) OR (subject:kw1 OR subject:kw2 ...) ) -from:deny1 -from:deny2 after:YYYY/MM/DD
    raw_query = f"(({domain_queries}) OR ({keyword_queries})) {denylist_queries} after:{since_str}"
    return raw_query
