"""HEASARC RXTE archive mirroring helpers for Phase 1 validation.

These helpers mirror selected RXTE/PCA observation products from the public
HEASARC HTTPS archive into ignored local raw-data directories. They do not run
HEASoft, unpack or modify FITS files, or make science classifications.
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from .raw_inventory import RawInventory, inventory_raw_files


HEASARC_RXTE_ARCHIVE_BASE_URL = "https://heasarc.gsfc.nasa.gov/FTP/xte/data/archive"
PHASE1_RXTE_SUBDIRECTORIES = ("pca", "stdprod", "orbit")
STDPATH_KEEP_PREFIXES = ("x",)
STDPATH_KEEP_SUFFIXES = (".gti.gz", ".xfl.gz")


class RxteArchiveError(ValueError):
    """Raised when RXTE archive discovery or mirroring fails."""


@dataclass(frozen=True)
class RxteArchiveProduct:
    """One downloadable product in a HEASARC RXTE observation tree."""

    obs_id: str
    relative_path: str
    url: str
    size_bytes: int | None = None


@dataclass(frozen=True)
class RxteArchiveMirrorResult:
    """Downloaded RXTE products plus local inventory metadata."""

    obs_id: str
    archive_url: str
    raw_path: Path
    products: tuple[RxteArchiveProduct, ...]
    inventory: RawInventory


def rxte_observation_archive_url(
    obs_id: str,
    *,
    base_url: str = HEASARC_RXTE_ARCHIVE_BASE_URL,
) -> str:
    """Return the public HEASARC observation-directory URL for one RXTE ObsID."""

    proposal = _proposal_from_obs_id(obs_id)
    ao = f"AO{proposal[0]}"
    return f"{base_url.rstrip('/')}/{ao}/P{proposal}/{obs_id}/"


def discover_phase1_rxte_products(
    obs_id: str,
    *,
    base_url: str = HEASARC_RXTE_ARCHIVE_BASE_URL,
) -> tuple[RxteArchiveProduct, ...]:
    """Discover Phase 1-relevant PCA and standard-product files for one ObsID."""

    observation_url = rxte_observation_archive_url(obs_id, base_url=base_url)
    products: list[RxteArchiveProduct] = []
    for subdirectory in PHASE1_RXTE_SUBDIRECTORIES:
        directory_url = urljoin(observation_url, f"{subdirectory}/")
        for filename in _list_archive_filenames(directory_url):
            if not _keep_phase1_file(subdirectory, filename):
                continue
            file_url = urljoin(directory_url, filename)
            products.append(
                RxteArchiveProduct(
                    obs_id=obs_id,
                    relative_path=f"{subdirectory}/{filename}",
                    url=file_url,
                    size_bytes=_head_content_length(file_url),
                )
            )
    return tuple(products)


def mirror_phase1_rxte_observation(
    obs_id: str,
    *,
    raw_root: Path | str,
    base_url: str = HEASARC_RXTE_ARCHIVE_BASE_URL,
    overwrite: bool = False,
) -> RxteArchiveMirrorResult:
    """Mirror Phase 1 RXTE/PCA products into ``raw_root/rxte/{obs_id}``."""

    products = discover_phase1_rxte_products(obs_id, base_url=base_url)
    if not products:
        raise RxteArchiveError(f"No Phase 1 RXTE products found for {obs_id}")

    raw_path = Path(raw_root) / "rxte" / obs_id
    raw_path.mkdir(parents=True, exist_ok=True)
    for product in products:
        destination = raw_path / product.relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and not overwrite:
            continue
        _download_file(product.url, destination)

    return RxteArchiveMirrorResult(
        obs_id=obs_id,
        archive_url=rxte_observation_archive_url(obs_id, base_url=base_url),
        raw_path=raw_path,
        products=products,
        inventory=inventory_raw_files(raw_path),
    )


def _proposal_from_obs_id(obs_id: str) -> str:
    proposal = obs_id.split("-", maxsplit=1)[0].strip()
    if len(proposal) != 5 or not proposal.isdigit():
        raise RxteArchiveError(f"Invalid RXTE ObsID: {obs_id}")
    return proposal


def _list_archive_filenames(directory_url: str) -> tuple[str, ...]:
    try:
        with urlopen(directory_url, timeout=60) as response:
            text = response.read().decode("utf-8", errors="replace")
    except Exception as exc:  # pragma: no cover - exercised against live archive
        raise RxteArchiveError(f"Cannot list RXTE archive directory: {directory_url}") from exc

    parser = _ArchiveLinkParser()
    parser.feed(text)
    return tuple(
        link
        for link in parser.links
        if not link.startswith("?")
        and not link.startswith("/")
        and not link.endswith("/")
        and link != "../"
    )


def _head_content_length(url: str) -> int | None:
    try:
        with urlopen(Request(url, method="HEAD"), timeout=60) as response:
            value = response.headers.get("Content-Length")
    except Exception:
        return None
    return int(value) if value and value.isdigit() else None


def _download_file(url: str, destination: Path) -> None:
    try:
        with urlopen(url, timeout=120) as response:
            with destination.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
    except Exception as exc:  # pragma: no cover - exercised against live archive
        raise RxteArchiveError(f"Cannot download {url} to {destination}") from exc


def _keep_stdprod_file(filename: str) -> bool:
    return filename.startswith(STDPATH_KEEP_PREFIXES) and filename.endswith(
        STDPATH_KEEP_SUFFIXES
    )


def _keep_orbit_file(filename: str) -> bool:
    return filename.startswith("FPorbit")


def _keep_phase1_file(subdirectory: str, filename: str) -> bool:
    if subdirectory == "stdprod":
        return _keep_stdprod_file(filename)
    if subdirectory == "orbit":
        return _keep_orbit_file(filename)
    return True


class _ArchiveLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.links.append(value)
