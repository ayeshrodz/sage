"""Fifty realistic text transformations: the everyday "fill in the rest of this column" work.

Each type has a generator of realistic inputs and a reference implementation
that produces the gold output. No system ever sees the reference; systems
only see input -> output examples.
"""

from __future__ import annotations

import datetime as _dt
import random
from dataclasses import dataclass
from typing import Callable

FIRST = ["James", "Mary", "Wei", "Aisha", "Carlos", "Olga", "Kenji", "Fatima", "Liam", "Priya", "Mateo", "Chloe",
         "Arjun", "Sofia", "Noah", "Yuki", "Omar", "Elena", "Lucas", "Amara", "Ivan", "Hana", "Diego", "Zara",
         "Ethan", "Mei", "Samuel", "Leila", "Oscar", "Nia", "Ravi", "Grace", "Tomas", "Ines", "Kofi", "Anna"]
MIDDLE = ["Ann", "Lee", "Marie", "Jose", "Kai", "Rose", "Jun", "Noor"]
LAST = ["Smith", "Garcia", "Chen", "Patel", "Okafor", "Kowalski", "Nguyen", "Silva", "Johnson", "Tanaka", "Haddad",
        "Muller", "Rossi", "Kim", "Singh", "Brown", "Lopez", "Ivanova", "Mensah", "Anderson", "Fischer", "Dubois",
        "Moreau", "Sato", "Ali", "Costa", "Novak", "Walker", "Hughes", "Reyes"]
DOMAINS = ["acme.com", "globex.org", "initech.io", "umbrella.net", "hooli.com", "stark.dev", "wayne.biz", "vandelay.co"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WORDS = ["alpha", "river", "stone", "quick", "silver", "garden", "north", "ember", "cloud", "harbor", "maple",
         "orbit", "pixel", "summit", "velvet", "willow", "canyon", "delta", "falcon", "lunar"]
STREETS = ["Main St", "Oak Ave", "Maple Rd", "Cedar Ln", "Park Blvd", "Elm St", "Lake Dr", "Hill Rd"]
CITIES = [("Springfield", "IL"), ("Riverside", "CA"), ("Franklin", "TN"), ("Georgetown", "TX"), ("Salem", "OR"),
          ("Madison", "WI"), ("Fairview", "NJ"), ("Clinton", "MS"), ("Arlington", "VA"), ("Burlington", "VT")]
EXTS = ["pdf", "csv", "docx", "png", "txt", "xlsx", "json", "mp4"]
COLORS = ["BLK", "WHT", "RED", "BLU", "GRN", "GRY"]
TAGS = ["python", "ai", "data", "travel", "coffee", "music", "design", "news"]


@dataclass(frozen=True)
class TransformType:
    name: str
    area: str
    gen: Callable[[random.Random], str]
    f: Callable[[str], str]


def _name(r, middle=0.25):
    parts = [r.choice(FIRST)] + ([r.choice(MIDDLE)] if r.random() < middle else []) + [r.choice(LAST)]
    return " ".join(parts)


def _date(r):
    return _dt.date(1990, 1, 1) + _dt.timedelta(days=r.randrange(0, 40 * 365))


def _money(r):
    return round(r.uniform(1, 99999), 2)


def _phone(r):
    return f"{r.randint(201, 989)}{r.randint(200, 999)}{r.randint(0, 9999):04d}"


def _email(r):
    return f"{r.choice(FIRST).lower()}.{r.choice(LAST).lower()}@{r.choice(DOMAINS)}"


def _url(r):
    host = r.choice(["www.", ""]) + r.choice(["shop.", "docs.", "api.", ""]) + r.choice(["example.com", "acme.org",
                                                                                         "data.io", "news.net"])
    path = "/" + "/".join(r.sample(WORDS, r.randint(1, 3)))
    query = r.choice(["", "?id=" + str(r.randint(1, 999)), "?q=" + r.choice(WORDS)])
    return f"https://{host}{path}{query}"


def _address(r):
    city, state = r.choice(CITIES)
    return f"{r.randint(1, 9999)} {r.choice(STREETS)}, {city}, {state} {r.randint(10000, 99999)}"


def _camel(words):
    return words[0] + "".join(w.capitalize() for w in words[1:])


def _time12(t: str) -> str:
    h, m = map(int, t.split(":"))
    return f"{(h % 12) or 12}:{m:02d} {'AM' if h < 12 else 'PM'}"


def _compact(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _long_date(d: _dt.date) -> str:
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"


def _types() -> list[TransformType]:
    T = TransformType
    t = [
        # names
        T("first_name", "names", _name, lambda s: s.split()[0]),
        T("last_name", "names", _name, lambda s: s.split()[-1]),
        T("initials", "names", lambda r: _name(r, 0), lambda s: "".join(w[0] + "." for w in s.split())),
        T("last_comma_first", "names", lambda r: _name(r, 0), lambda s: f"{s.split()[1]}, {s.split()[0]}"),
        T("first_initial_last", "names", lambda r: _name(r, 0), lambda s: f"{s.split()[0][0]}. {s.split()[-1]}"),
        T("username", "names", lambda r: _name(r, 0), lambda s: (s.split()[0][0] + s.split()[-1]).lower()),
        T("name_titlecase", "names",
          lambda r: "".join(ch.upper() if r.random() < 0.5 else ch.lower() for ch in _name(r, 0)),
          lambda s: " ".join(w.capitalize() for w in s.split())),
        T("email_from_name", "names", lambda r: _name(r, 0),
          lambda s: f"{s.split()[0].lower()}.{s.split()[-1].lower()}@acme.com"),
        # email
        T("email_domain", "email", _email, lambda s: s.split("@")[1]),
        T("email_user", "email", _email, lambda s: s.split("@")[0]),
        T("company_from_email", "email", _email, lambda s: s.split("@")[1].split(".")[0].capitalize()),
        T("mask_email", "email", _email, lambda s: s[0] + "***@" + s.split("@")[1]),
        # phone
        T("phone_digits", "phone", lambda r: (lambda p: f"({p[:3]}) {p[3:6]}-{p[6:]}")(_phone(r)),
          lambda s: "".join(ch for ch in s if ch.isdigit())),
        T("phone_format", "phone", _phone, lambda s: f"({s[:3]}) {s[3:6]}-{s[6:]}"),
        T("area_code", "phone", lambda r: (lambda p: f"({p[:3]}) {p[3:6]}-{p[6:]}")(_phone(r)), lambda s: s[1:4]),
        T("phone_intl", "phone", lambda r: (lambda p: f"{p[:3]}-{p[3:6]}-{p[6:]}")(_phone(r)),
          lambda s: "+1 " + s.replace("-", " ")),
        # dates
        T("date_iso_to_dmy", "dates", lambda r: _date(r).isoformat(),
          lambda s: "/".join(reversed(s.split("-")))),
        T("date_iso_to_long", "dates", lambda r: _date(r).isoformat(),
          lambda s: _long_date(_dt.date.fromisoformat(s))),
        T("date_dmy_to_iso", "dates", lambda r: _date(r).strftime("%d/%m/%Y"),
          lambda s: "-".join(reversed(s.split("/")))),
        T("year_from_date", "dates", lambda r: _date(r).strftime("%d/%m/%Y"), lambda s: s.split("/")[-1]),
        T("date_long_to_iso", "dates", lambda r: _long_date(_date(r)),
          lambda s: _dt.date(int(s.split(", ")[1]), MONTHS.index(s.split()[0]) + 1,
                             int(s.split()[1].rstrip(","))).isoformat()),
        T("weekday", "dates", lambda r: _date(r).isoformat(), lambda s: DAYS[_dt.date.fromisoformat(s).weekday()]),
        T("quarter", "dates", lambda r: _date(r).isoformat(),
          lambda s: f"Q{(int(s[5:7]) - 1) // 3 + 1} {s[:4]}"),
        # money and numbers
        T("money_to_number", "numbers", lambda r: f"${_money(r):,.2f}", lambda s: s.replace("$", "").replace(",", "")),
        T("number_to_money", "numbers", lambda r: f"{_money(r)}", lambda s: f"${float(s):,.2f}"),
        T("percent", "numbers", lambda r: f"0.{r.randint(1, 999):03d}", lambda s: f"{round(float(s) * 100, 1)}%"),
        T("round_int", "numbers", lambda r: f"{r.randint(0, 999)}.{r.choice([1, 2, 3, 4, 6, 7, 8, 9])}",
          lambda s: str(int(float(s) + 0.5))),
        T("compact_number", "numbers", lambda r: str(r.choice([r.randint(1000, 999999), r.randint(1_000_000, 99_999_999)])),
          lambda s: _compact(int(s))),
        T("kg_to_g", "numbers", lambda r: f"{r.randint(1, 99)}.{r.randint(0, 9)} kg",
          lambda s: f"{int(round(float(s.split()[0]) * 1000))} g"),
        # urls and files
        T("url_domain", "web", _url, lambda s: s.split("/")[2].removeprefix("www.")),
        T("url_path", "web", _url, lambda s: "/" + s.split("/", 3)[3].split("?")[0]),
        T("file_ext", "files", lambda r: f"{r.choice(WORDS)}_{r.choice(WORDS)}.{r.choice(EXTS)}",
          lambda s: s.rsplit(".", 1)[1]),
        T("file_stem", "files", lambda r: f"{r.choice(WORDS)}_{r.choice(WORDS)}.{r.choice(EXTS)}",
          lambda s: s.rsplit(".", 1)[0]),
        T("path_basename", "files",
          lambda r: "/home/" + r.choice(FIRST).lower() + "/" + "/".join(r.sample(WORDS, r.randint(1, 3)))
          + f"/{r.choice(WORDS)}.{r.choice(EXTS)}", lambda s: s.rsplit("/", 1)[1]),
        # addresses
        T("zip_from_address", "address", _address, lambda s: s.split()[-1]),
        T("city_from_address", "address", _address, lambda s: s.split(", ")[1]),
        T("state_from_address", "address", _address, lambda s: s.split(", ")[2].split()[0]),
        # codes
        T("sku_number", "codes", lambda r: f"SKU-{r.randint(1, 99999):05d}-{r.choice(COLORS)}", lambda s: s.split("-")[1]),
        T("sku_color", "codes", lambda r: f"SKU-{r.randint(1, 99999):05d}-{r.choice(COLORS)}", lambda s: s.split("-")[2]),
        T("hex_to_rgb", "codes", lambda r: "#" + "".join(f"{r.randint(0, 255):02X}" for _ in range(3)),
          lambda s: f"rgb({int(s[1:3], 16)}, {int(s[3:5], 16)}, {int(s[5:7], 16)})"),
        # text
        T("slugify", "text", lambda r: " ".join(w.capitalize() for w in r.sample(WORDS, r.randint(2, 4))),
          lambda s: "-".join(s.lower().split())),
        T("camel_to_snake", "text", lambda r: _camel(r.sample(WORDS, r.randint(2, 3))),
          lambda s: "".join("_" + ch.lower() if ch.isupper() else ch for ch in s)),
        T("snake_to_camel", "text", lambda r: "_".join(r.sample(WORDS, r.randint(2, 3))),
          lambda s: _camel(s.split("_"))),
        T("reverse_words", "text", lambda r: " ".join(r.sample(WORDS, r.randint(2, 4))),
          lambda s: " ".join(reversed(s.split()))),
        T("count_words", "text", lambda r: " ".join(r.choices(WORDS, k=r.randint(2, 9))), lambda s: str(len(s.split()))),
        T("abbrev_3upper", "text", lambda r: r.choice(DAYS + MONTHS), lambda s: s[:3].upper()),
        T("collapse_spaces", "text",
          lambda r: (" " * r.randint(0, 2)) + "".join(w + " " * r.randint(1, 3) for w in r.sample(WORDS, 3)),
          lambda s: " ".join(s.split())),
        T("hashtags", "text",
          lambda r: " ".join(r.sample(WORDS, 2)) + " #" + " and #".join(r.sample(TAGS, r.randint(1, 3))) + " today",
          lambda s: " ".join(w for w in s.split() if w.startswith("#"))),
        T("mask_card", "codes", lambda r: " ".join(f"{r.randint(0, 9999):04d}" for _ in range(4)),
          lambda s: "**** **** **** " + s.split()[-1]),
        T("time_24_to_12", "times", lambda r: f"{r.randint(0, 23):02d}:{r.randint(0, 59):02d}", _time12),
    ]
    return t


TYPES: list[TransformType] = _types()
TYPE_INDEX = {t.name: i for i, t in enumerate(TYPES)}
