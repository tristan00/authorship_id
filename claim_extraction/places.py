from pathlib import Path
import re

TOKEN = re.compile(r"[^\W_]+")

COUNTRY_ALIASES = {
    "united states": ("usa", "u.s.", "u.s.a.", "america", "the states", "united states of america", "estados unidos", "eeuu", "ee.uu."),
    "united kingdom": ("uk", "u.k.", "britain", "great britain"), "new zealand": ("nz", "aotearoa"), "ireland": ("eire", "republic of ireland"),
    "netherlands": ("holland",), "czech republic": ("czechia",), "bosnia and herzegovina": ("bosnia",), "north macedonia": ("macedonia",),
    "turkey": ("türkiye", "turkiye"), "saudi arabia": ("ksa",), "united arab emirates": ("uae", "emirates"), "china": ("mainland china",),
    "south korea": ("korea", "s. korea"), "vietnam": ("viet nam",), "myanmar": ("burma",), "philippines": ("pinas",), "trinidad and tobago": ("trinidad",),
    "ivory coast": ("côte d'ivoire", "cote d'ivoire"), "democratic republic of the congo": ("drc", "dr congo"), "republic of the congo": ("congo",),
    "germany": ("deutschland",), "spain": ("españa", "espana"), "italy": ("italia",), "switzerland": ("schweiz", "suisse", "svizzera"), "austria": ("österreich", "osterreich"),
    "sweden": ("sverige",), "norway": ("norge",), "denmark": ("danmark",), "finland": ("suomi",), "poland": ("polska",), "mexico": ("méxico",), "brazil": ("brasil",),
}

DEMONYMS = {
    "american": "united states", "canadian": "canada", "british": "united kingdom", "brit": "united kingdom", "english": "united kingdom", "scottish": "united kingdom",
    "welsh": "united kingdom", "irish": "ireland", "australian": "australia", "aussie": "australia", "kiwi": "new zealand", "new zealander": "new zealand",
    "german": "germany", "french": "france", "spanish": "spain", "italian": "italy", "portuguese": "portugal", "dutch": "netherlands", "belgian": "belgium",
    "swiss": "switzerland", "austrian": "austria", "swedish": "sweden", "swede": "sweden", "norwegian": "norway", "danish": "denmark", "dane": "denmark",
    "finnish": "finland", "icelandic": "iceland", "polish": "poland", "czech": "czech republic", "slovak": "slovakia", "hungarian": "hungary", "romanian": "romania",
    "bulgarian": "bulgaria", "greek": "greece", "croatian": "croatia", "serbian": "serbia", "slovenian": "slovenia", "bosnian": "bosnia and herzegovina",
    "albanian": "albania", "ukrainian": "ukraine", "russian": "russia", "belarusian": "belarus", "lithuanian": "lithuania", "latvian": "latvia", "estonian": "estonia",
    "armenian": "armenia", "turkish": "turkey", "israeli": "israel", "palestinian": "palestine", "lebanese": "lebanon", "jordanian": "jordan", "syrian": "syria",
    "iraqi": "iraq", "iranian": "iran", "persian": "iran", "saudi": "saudi arabia", "emirati": "united arab emirates", "egyptian": "egypt", "moroccan": "morocco",
    "algerian": "algeria", "tunisian": "tunisia", "nigerian": "nigeria", "ghanaian": "ghana", "kenyan": "kenya", "ethiopian": "ethiopia", "south african": "south africa",
    "ugandan": "uganda", "indian": "india", "pakistani": "pakistan", "bangladeshi": "bangladesh", "sri lankan": "sri lanka", "nepali": "nepal", "nepalese": "nepal",
    "afghan": "afghanistan", "chinese": "china", "taiwanese": "taiwan", "japanese": "japan", "korean": "south korea", "vietnamese": "vietnam", "thai": "thailand",
    "cambodian": "cambodia", "malaysian": "malaysia", "singaporean": "singapore", "indonesian": "indonesia", "filipino": "philippines", "filipina": "philippines",
    "pinoy": "philippines", "pinay": "philippines", "mexican": "mexico", "guatemalan": "guatemala", "honduran": "honduras", "salvadoran": "el salvador", "cuban": "cuba",
    "jamaican": "jamaica", "dominican": "dominican republic", "haitian": "haiti", "puerto rican": "puerto rico", "colombian": "colombia", "venezuelan": "venezuela",
    "ecuadorian": "ecuador", "peruvian": "peru", "bolivian": "bolivia", "chilean": "chile", "argentinian": "argentina", "argentine": "argentina", "uruguayan": "uruguay",
    "brazilian": "brazil",

    "scot": "united kingdom", "northern irish": "united kingdom", "kazakh": "kazakhstan", "uzbek": "uzbekistan", "mongolian": "mongolia", "burmese": "myanmar",
    "laotian": "laos", "maltese": "malta", "cypriot": "cyprus", "luxembourgish": "luxembourg", "montenegrin": "montenegro", "macedonian": "north macedonia",
    "moldovan": "moldova", "azerbaijani": "azerbaijan", "azeri": "azerbaijan", "qatari": "qatar", "kuwaiti": "kuwait", "bahraini": "bahrain", "omani": "oman",
    "yemeni": "yemen", "libyan": "libya", "sudanese": "sudan", "somali": "somalia", "rwandan": "rwanda", "tanzanian": "tanzania", "zimbabwean": "zimbabwe",
    "zambian": "zambia", "cameroonian": "cameroon", "senegalese": "senegal", "congolese": "democratic republic of the congo", "angolan": "angola",
    "nicaraguan": "nicaragua", "costa rican": "costa rica", "panamanian": "panama", "trinidadian": "trinidad and tobago", "bahamian": "bahamas", "barbadian": "barbados",
    "paraguayan": "paraguay", "slovene": "slovenia", "slovakian": "slovakia", "hong konger": "hong kong", "hongkonger": "hong kong", "mozambican": "mozambique",
    "malagasy": "madagascar", "namibian": "namibia", "malawian": "malawi", "ivorian": "ivory coast", "malian": "mali", "liberian": "liberia", "eritrean": "eritrea",
    "mauritian": "mauritius", "fijian": "fiji", "bhutanese": "bhutan", "maldivian": "maldives", "kyrgyz": "kyrgyzstan", "tajik": "tajikistan", "turkmen": "turkmenistan",
    "kosovar": "kosovo", "belizean": "belize", "guyanese": "guyana", "surinamese": "suriname", "salvadorean": "el salvador",

}

US_STATES = {
    "alabama": "al", "alaska": "ak", "arizona": "az", "arkansas": "ar", "california": "ca", "colorado": "co", "connecticut": "ct", "delaware": "de", "florida": "fl",
    "georgia": "ga", "hawaii": "hi", "idaho": "id", "illinois": "il", "indiana": "in", "iowa": "ia", "kansas": "ks", "kentucky": "ky", "louisiana": "la", "maine": "me",
    "maryland": "md", "massachusetts": "ma", "michigan": "mi", "minnesota": "mn", "mississippi": "ms", "missouri": "mo", "montana": "mt", "nebraska": "ne", "nevada": "nv",
    "new hampshire": "nh", "new jersey": "nj", "new mexico": "nm", "new york": "ny", "north carolina": "nc", "north dakota": "nd", "ohio": "oh", "oklahoma": "ok",
    "oregon": "or", "pennsylvania": "pa", "rhode island": "ri", "south carolina": "sc", "south dakota": "sd", "tennessee": "tn", "texas": "tx", "utah": "ut",
    "vermont": "vt", "virginia": "va", "washington": "wa", "west virginia": "wv", "wisconsin": "wi", "wyoming": "wy",
}
US_STATE_DEMONYMS = {
    "alabamian": "alabama", "alaskan": "alaska", "arizonan": "arizona", "arkansan": "arkansas", "californian": "california", "coloradan": "colorado", "connecticuter": "connecticut",
    "delawarean": "delaware", "floridian": "florida", "hawaiian": "hawaii", "idahoan": "idaho", "illinoisan": "illinois", "hoosier": "indiana", "iowan": "iowa", "kansan": "kansas",
    "kentuckian": "kentucky", "louisianian": "louisiana", "mainer": "maine", "marylander": "maryland", "bay stater": "massachusetts", "michigander": "michigan",
    "minnesotan": "minnesota", "mississippian": "mississippi", "missourian": "missouri", "montanan": "montana", "nebraskan": "nebraska", "nevadan": "nevada",
    "new hampshirite": "new hampshire", "new jerseyan": "new jersey", "new mexican": "new mexico", "new yorker": "new york", "north carolinian": "north carolina",
    "north dakotan": "north dakota", "ohioan": "ohio", "oklahoman": "oklahoma", "oregonian": "oregon", "pennsylvanian": "pennsylvania", "rhode islander": "rhode island",
    "south carolinian": "south carolina", "south dakotan": "south dakota", "tennessean": "tennessee", "texan": "texas", "utahn": "utah", "vermonter": "vermont",
    "virginian": "virginia", "washingtonian": "washington", "west virginian": "west virginia", "wisconsinite": "wisconsin", "wyomingite": "wyoming",
}
CA_PROVINCE_DEMONYMS = {
    "albertan": "alberta", "british columbian": "british columbia", "manitoban": "manitoba", "new brunswicker": "new brunswick", "newfoundlander": "newfoundland and labrador",
    "nova scotian": "nova scotia", "ontarian": "ontario", "quebecer": "quebec", "quebecker": "quebec", "québécois": "quebec", "saskatchewanian": "saskatchewan",
}

REGION_ALIASES = {
    "california": ("cali", "socal", "norcal", "southern california", "northern california"), "new jersey": ("jersey",), "washington": ("washington state",),
    "district of columbia": ("dc", "d.c.", "washington dc", "washington d.c."), "quebec": ("québec",), "newfoundland and labrador": ("newfoundland",),
    "new south wales": ("nsw",), "queensland": ("qld",), "bavaria": ("bayern",), "north rhine-westphalia": ("nrw",), "saxony": ("sachsen",), "hesse": ("hessen",),
    "thuringia": ("thüringen",), "jammu and kashmir": ("kashmir",), "catalonia": ("catalunya",), "andalusia": ("andalucía", "andalucia"),
    "basque country": ("país vasco",), "canary islands": ("canarias",), "sicily": ("sicilia",), "sardinia": ("sardegna",), "tuscany": ("toscana",),
    "lombardy": ("lombardia",),
}

CITY_ALIASES = {"nyc": "new york city", "la": "los angeles", "l.a.": "los angeles", "sf": "san francisco", "philly": "philadelphia", "vegas": "las vegas",
                "okc": "oklahoma city", "slc": "salt lake city", "bombay": "mumbai", "bangalore": "bengaluru", "calcutta": "kolkata", "cdmx": "mexico city",
                "kl": "kuala lumpur", "saigon": "ho chi minh city", "kiev": "kyiv", "odessa": "odesa", "münchen": "munich", "cologne": "köln", "roma": "rome",
                "milano": "milan", "seville": "sevilla", "wien": "vienna", "lisboa": "lisbon", "rio": "rio de janeiro", "atl": "atlanta", "chi": "chicago",
                "nola": "new orleans", "pdx": "portland", "htx": "houston", "kc": "kansas city"}
COUNTRY_CODES = {"us": "united states"}
US_CENSUS_REGIONS = ("northeast", "midwest", "south", "west", "new england", "mid-atlantic", "east north central", "west north central", "south atlantic", "east south central",
                     "west south central", "mountain", "pacific")
REGION_CODES = {"canada": {"ab": "alberta", "bc": "british columbia", "mb": "manitoba", "nb": "new brunswick", "nl": "newfoundland and labrador", "ns": "nova scotia",
                           "nt": "northwest territories", "nu": "nunavut", "on": "ontario", "pe": "prince edward island", "qc": "quebec", "sk": "saskatchewan", "yt": "yukon"},
                "australia": {"nsw": "new south wales", "vic": "victoria", "qld": "queensland", "sa": "south australia", "tas": "tasmania", "nt": "northern territory",
                              "act": "australian capital territory"},
                "united states": {code: name for name, code in US_STATES.items()}}


def key(name):
    return " ".join(TOKEN.findall(name.lower()))


def gazetteer():
    with open(Path(__file__).with_name("gazetteer.tsv"), encoding="utf-8") as rows:
        next(rows)
        return {name: tuple(entry) for name, *entry in (line.rstrip("\n").split("\t") for line in rows)}


def table():
    loaded = gazetteer()
    found = {key(name): ("region", name, name, "united states", "") for name in US_STATES}
    for country, aliases in COUNTRY_ALIASES.items():
        found |= {key(name): ("country", country, "", country, "") for name in aliases}
    for region, aliases in REGION_ALIASES.items():
        found |= {key(name): (*loaded[key(region)][:4], "") for name in aliases}
    found |= {key(alias): (*loaded[key(city)][:4], "code" if len(alias) <= 2 else "") for alias, city in CITY_ALIASES.items()}
    for country, codes in REGION_CODES.items():
        for code, name in codes.items():
            found.setdefault(code, ("region", name, name, country, "code"))
    found |= {code: ("country", country, "", country, "code") for code, country in COUNTRY_CODES.items()}
    found |= {key(name): ("region", name, name, "united states", "1") for name in US_CENSUS_REGIONS}
    return {**loaded, **found}


PLACES = table()
NATIONS = {key(name): country for name, country in DEMONYMS.items()}
PEOPLES = {**{key(name): ("people", region, region, "united states", "") for name, region in US_STATE_DEMONYMS.items()},
           **{key(name): ("people", region, region, "canada", "") for name, region in CA_PROVINCE_DEMONYMS.items()}}
