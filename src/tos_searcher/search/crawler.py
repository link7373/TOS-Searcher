from __future__ import annotations

import logging
import random
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from tos_searcher.config import Settings

logger = logging.getLogger(__name__)

TOS_PATHS = [
    "/terms",
    "/tos",
    "/terms-of-service",
    "/terms-and-conditions",
    "/legal",
    "/legal/terms",
    "/privacy",
    "/privacy-policy",
    "/user-agreement",
    "/eula",
    "/acceptable-use",
    "/community-guidelines",
]

SEED_DOMAINS = [
    "google.com",
    "facebook.com",
    "amazon.com",
    "twitter.com",
    "reddit.com",
    "netflix.com",
    "spotify.com",
    "apple.com",
    "microsoft.com",
    "adobe.com",
    "dropbox.com",
    "slack.com",
    "zoom.us",
    "squaremouth.com",
    "linkedin.com",
    "pinterest.com",
    "tumblr.com",
    "snapchat.com",
    "tiktok.com",
    "uber.com",
    "lyft.com",
    "airbnb.com",
    "etsy.com",
    "shopify.com",
    "stripe.com",
    "paypal.com",
    "venmo.com",
    "cashapp.com",
    "robinhood.com",
    "coinbase.com",
    "twitch.tv",
    "discord.com",
    "github.com",
    "gitlab.com",
    "stackoverflow.com",
    "medium.com",
    "substack.com",
    "wordpress.com",
    "squarespace.com",
    "wix.com",
    "godaddy.com",
    "namecheap.com",
    "cloudflare.com",
    "digitalocean.com",
    "heroku.com",
    "salesforce.com",
    "hubspot.com",
    "mailchimp.com",
    "canva.com",
    "figma.com",
    "notion.so",
    "asana.com",
    "trello.com",
    "monday.com",
    "airtable.com",
    "zapier.com",
    "ifttt.com",
    "grammarly.com",
    "duolingo.com",
    "coursera.org",
    "udemy.com",
    "khan-academy.org",
    "hulu.com",
    "disneyplus.com",
    "hbomax.com",
    "peacocktv.com",
    "paramountplus.com",
    "crunchyroll.com",
    "pandora.com",
    "soundcloud.com",
    "deezer.com",
    "tidal.com",
    "doordash.com",
    "grubhub.com",
    "instacart.com",
    "postmates.com",
    "expedia.com",
    "booking.com",
    "kayak.com",
    "tripadvisor.com",
    "zillow.com",
    "redfin.com",
    "realtor.com",
    "indeed.com",
    "glassdoor.com",
    "monster.com",
    "upwork.com",
    "fiverr.com",
    "rover.com",
    "taskrabbit.com",
    "thumbtack.com",
    "yelp.com",
    "nextdoor.com",
    "meetup.com",
    "eventbrite.com",
    "ticketmaster.com",
    "stubhub.com",
    "seatgeek.com",
    "geico.com",
    "progressive.com",
    "statefarm.com",
    "allstate.com",
    "lemonade.com",
]

TOS_LINK_KEYWORDS = frozenset([
    "terms",
    "tos",
    "legal",
    "privacy",
    "policy",
    "agreement",
    "conditions",
    "eula",
])


class DirectCrawler:
    name = "crawl"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._session = requests.Session()
        self._session.headers.update(
            {"User-Agent": random.choice(settings.user_agents)}
        )

    def discover_tos_urls(self) -> list[str]:
        """Generate candidate TOS URLs from seed domains."""
        urls: list[str] = []
        for domain in SEED_DOMAINS:
            for path in TOS_PATHS:
                urls.append(f"https://www.{domain}{path}")
        return urls

    def find_tos_links_on_page(self, base_url: str) -> list[str]:
        """Scrape a page looking for TOS-related links in the footer/body."""
        try:
            resp = self._session.get(base_url, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            found: list[str] = []
            for link in soup.find_all("a", href=True):
                href = str(link["href"]).lower()
                text = link.get_text().lower()
                if any(kw in href or kw in text for kw in TOS_LINK_KEYWORDS):
                    full_url = urljoin(base_url, str(link["href"]))
                    if full_url not in found:
                        found.append(full_url)
            return found
        except Exception as e:
            logger.debug("Failed to crawl %s: %s", base_url, e)
            return []
