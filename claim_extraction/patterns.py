import re
from collections import defaultdict

from . import timed
from .config import YEAR
from .places import CODES, DEMONYMS, PLACES
from .schema import canonical, fan_value

APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "´": "'", "ʼ": "'", "＇": "'", "`": "'"})
MASKED = re.compile(r"https?://\S+|www\.\S+|\]\([^)\s]*\)|^[ \t]*(?:>|&gt;)[^\n]*", re.M)
I = r"(?:i'm|im|i am|iam|i m|i'am|i'?ve been|i've always been)"
A = r"(?:an? )?"
HEDGE = re.compile(r"\b(?:if|would|wish|hope|imagine|pretend|unless|whether|wanna|want to|wants to|trying to|tryna|going to|gonna|might|maybe|someday|used to|"
                   r"not|never|no longer|anymore|former|formerly|when i was|back when|before i was)\b|n't\b")
SELF_HEDGE = re.compile(r"\b(?:if|would|wish|hope|imagine|pretend|unless|whether|wanna|want to|trying to|going to|gonna|might|maybe|used to|not|never|no longer|anymore|"
                        r"when i was|back when)\b|n't\b")
DISTANCE = re.compile(r"\s*(?:away|ago|long|deep|high|wide|tall|run|race|views|subs|followers|people|users|members|miles)")
UNITS = r"(?:years? ago|yrs? ago|minutes?|mins?|hours?|hrs?|days?|weeks?|months?|times|percent|%|lbs?|kgs?|pounds|miles|km|cm|dollars|bucks|k\b|grand|hp|mph|degrees|feet|ft|inches|in\b|seconds|secs?|euros?|points|pts|ounces|oz|inch)"


def prepared(text):
    text = text.translate(APOSTROPHES)
    return MASKED.sub(lambda match: " " * len(match.group()), text)


def clause(text, start):
    return max(text.rfind(mark, 0, start) for mark in ".!?\n;") + 1


def question(text, end):
    stop = min((found for found in (text.find(mark, end) for mark in ".!\n") if found >= 0), default=len(text))
    return "?" in text[end:stop]


def hedged(text, start, end, pattern=HEDGE):
    return bool(pattern.search(text, max(clause(text, start), start - 40), start)) or question(text, end)


def rule(attribute, pattern, value, hedge=HEDGE):
    return attribute, re.compile(pattern), value, hedge


def fixed(result):
    return lambda match: result


def group(table, number=1):
    return lambda match: table.get(match.group(number))


GENDERS = {"guy": "male", "man": "male", "dude": "male", "male": "male", "boy": "male", "bloke": "male", "lad": "male", "gentleman": "male", "dad": "male", "father": "male",
           "husband": "male", "hubby": "male", "mum": "female", "mom": "female", "mother": "female", "wife": "female", "woman": "female", "girl": "female", "female": "female",
           "lady": "female", "gal": "female", "chick": "female", "girlie": "female", "milf": "female", "dilf": "male", "m": "male", "f": "female", "nb": "non-binary", "non-binary": "non-binary",
           "nonbinary": "non-binary", "enby": "non-binary", "nb": "non-binary", "genderfluid": "non-binary", "agender": "non-binary", "genderqueer": "non-binary",
           "trans woman": "trans woman", "transwoman": "trans woman", "trans girl": "trans woman", "mtf": "trans woman", "trans man": "trans man", "transman": "trans man",
           "trans guy": "trans man", "ftm": "trans man", "trans": "transgender, unspecified", "transgender": "transgender, unspecified"}
GENDER_WORDS = r"(guy|man|dude|male|boy|bloke|lad|gentleman|dad|father|husband|mum|mom|mother|wife|woman|girl|female|lady|gal|chick)"
ADJECTIVES = (r"(?:(?:\d{2}[- ]?(?:years?|yrs?|y/?o)[- ]?(?:old )?|single|married|straight|gay|bi|bisexual|white|black|asian|latino|latina|hispanic|indian|young|old|older|middle[- ]aged|"
              r"tall|short|fat|chubby|skinny|fit|average|normal|regular|grown|cis|cisgender|divorced|disabled|autistic|working|stay[- ]at[- ]home|new|first[- ]time|"
              r"american|british|canadian|australian|christian|muslim|jewish|catholic|retired|lonely|horny|shy|curvy|petite|busy|proud) ){0,3}")
RELATIONS = {"wife": "married", "husband": "married", "hubby": "married", "wifey": "married", "spouse": "married", "girlfriend": "dating or in a relationship",
             "boyfriend": "dating or in a relationship", "gf": "dating or in a relationship", "bf": "dating or in a relationship", "partner": "dating or in a relationship",
             "bae": "dating or in a relationship", "fiance": "engaged", "fiancé": "engaged", "fiancee": "engaged", "fiancée": "engaged"}
STATUSES = {"single": "single", "married": "married", "engaged": "engaged", "divorced": "divorced", "separated": "separated", "widowed": "widowed", "a widow": "widowed",
            "a widower": "widowed", "in a relationship": "dating or in a relationship", "taken": "dating or in a relationship"}
ORIENTATIONS = {"gay": "gay", "lesbian": "lesbian", "bisexual": "bisexual", "bi": "bisexual", "pansexual": "pansexual", "pan": "pansexual", "asexual": "asexual", "ace": "asexual",
                "queer": "queer, unspecified", "straight": "straight", "heterosexual": "straight", "hetero": "straight", "homosexual": "gay"}
ETHNICITIES = {"white": "white", "caucasian": "white", "black": "black", "african american": "black", "asian": "east asian", "east asian": "east asian", "chinese": "east asian",
               "korean": "east asian", "japanese": "east asian", "taiwanese": "east asian", "south asian": "south asian", "indian": "south asian", "desi": "south asian",
               "pakistani": "south asian", "bangladeshi": "south asian", "southeast asian": "southeast asian", "filipino": "southeast asian", "filipina": "southeast asian",
               "vietnamese": "southeast asian", "thai": "southeast asian", "latino": "hispanic or latino", "latina": "hispanic or latino", "latinx": "hispanic or latino",
               "hispanic": "hispanic or latino", "mexican": "hispanic or latino", "arab": "middle eastern or north african", "middle eastern": "middle eastern or north african",
               "persian": "middle eastern or north african", "native american": "indigenous", "indigenous": "indigenous", "aboriginal": "indigenous",
               "pacific islander": "pacific islander", "mixed": "mixed", "mixed race": "mixed", "biracial": "mixed", "multiracial": "mixed"}
RELIGIONS = {"christian": "christian", "catholic": "christian", "protestant": "christian", "mormon": "christian", "lds": "christian", "baptist": "christian", "methodist": "christian",
             "lutheran": "christian", "evangelical": "christian", "orthodox christian": "christian", "muslim": "muslim", "jew": "jewish", "jewish": "jewish", "hindu": "hindu",
             "buddhist": "buddhist", "sikh": "sikh", "pagan": "pagan or other religion", "wiccan": "pagan or other religion", "witch": "pagan or other religion",
             "spiritual": "spiritual, no religion", "agnostic": "agnostic", "atheist": "atheist", "not religious": "atheist"}
POLITICS = {"communist": "communist or far left", "marxist": "communist or far left", "socialist": "socialist or left", "leftist": "socialist or left", "liberal": "progressive or liberal",
            "progressive": "progressive or liberal", "democrat": "progressive or liberal", "centrist": "centrist or moderate", "moderate": "centrist or moderate",
            "conservative": "conservative or right", "republican": "conservative or right", "libertarian": "libertarian", "anarchist": "anarchist",
            "nationalist": "nationalist or far right", "apolitical": "apolitical"}
MENTAL = {"adhd": "adhd", "add": "adhd", "autism": "autism", "autistic": "autism", "asperger's": "autism", "aspergers": "autism", "asd": "autism", "depression": "depression",
          "major depressive disorder": "depression", "mdd": "depression", "anxiety": "anxiety", "an anxiety disorder": "anxiety", "generalized anxiety disorder": "anxiety",
          "gad": "anxiety", "panic disorder": "anxiety", "social anxiety": "anxiety", "bipolar": "bipolar disorder", "bipolar disorder": "bipolar disorder", "ptsd": "ptsd",
          "cptsd": "ptsd", "c-ptsd": "ptsd", "ocd": "ocd", "anorexia": "eating disorder", "bulimia": "eating disorder", "an eating disorder": "eating disorder",
          "binge eating disorder": "eating disorder", "arfid": "eating disorder", "bpd": "personality disorder", "borderline personality disorder": "personality disorder",
          "borderline": "personality disorder", "npd": "personality disorder", "schizophrenia": "schizophrenia or psychosis", "schizoaffective disorder": "schizophrenia or psychosis",
          "psychosis": "schizophrenia or psychosis", "an addiction": "addiction", "addiction": "addiction", "alcoholism": "addiction", "neurodivergent": "neurodivergent, unspecified",
          "dyslexia": "other mental health condition", "tourette's": "other mental health condition", "did": "other mental health condition", "insomnia": "other mental health condition"}
PHYSICAL = {"diabetes": "diabetes", "type 1 diabetes": "diabetes", "type 2 diabetes": "diabetes", "t1d": "diabetes", "t2d": "diabetes", "lupus": "autoimmune disease",
            "rheumatoid arthritis": "autoimmune disease", "multiple sclerosis": "autoimmune disease", "hashimoto's": "autoimmune disease", "hashimotos": "autoimmune disease",
            "an autoimmune disease": "autoimmune disease", "graves disease": "autoimmune disease", "graves' disease": "autoimmune disease", "psoriatic arthritis": "autoimmune disease",
            "chronic pain": "chronic pain or fibromyalgia", "fibromyalgia": "chronic pain or fibromyalgia", "fibro": "chronic pain or fibromyalgia", "cancer": "cancer",
            "breast cancer": "cancer", "leukemia": "cancer", "lymphoma": "cancer", "a heart condition": "heart or blood condition", "heart disease": "heart or blood condition",
            "high blood pressure": "heart or blood condition", "hypertension": "heart or blood condition", "afib": "heart or blood condition", "anemia": "heart or blood condition",
            "pots": "heart or blood condition", "ibs": "digestive condition", "crohn's": "digestive condition", "crohns": "digestive condition", "ulcerative colitis": "digestive condition",
            "colitis": "digestive condition", "celiac": "digestive condition", "celiac disease": "digestive condition", "gastritis": "digestive condition", "gerd": "digestive condition",
            "acid reflux": "digestive condition", "pcos": "hormonal or reproductive condition", "endometriosis": "hormonal or reproductive condition",
            "hypothyroidism": "hormonal or reproductive condition", "hyperthyroidism": "hormonal or reproductive condition", "menopause": "hormonal or reproductive condition",
            "epilepsy": "neurological condition", "migraines": "neurological condition", "chronic migraines": "neurological condition", "parkinson's": "neurological condition",
            "seizures": "neurological condition", "eczema": "skin condition", "psoriasis": "skin condition", "acne": "skin condition", "rosacea": "skin condition",
            "dermatitis": "skin condition", "asthma": "respiratory condition or allergy", "allergies": "respiratory condition or allergy", "copd": "respiratory condition or allergy",
            "tinnitus": "vision or hearing impairment", "hearing loss": "vision or hearing impairment", "cerebral palsy": "physical disability", "eds": "other physical condition",
            "ehlers-danlos": "other physical condition", "me/cfs": "other physical condition", "long covid": "other physical condition", "arthritis": "other physical condition",
            "sleep apnea": "other physical condition", "kidney disease": "other physical condition"}
STATES_OF = {"autistic": ("mental_condition", "autism"), "bipolar": ("mental_condition", "bipolar disorder"), "schizophrenic": ("mental_condition", "schizophrenia or psychosis"),
             "anorexic": ("mental_condition", "eating disorder"), "bulimic": ("mental_condition", "eating disorder"), "an alcoholic": ("mental_condition", "addiction"),
             "an addict": ("mental_condition", "addiction"), "a recovering alcoholic": ("mental_condition", "addiction"), "a recovering addict": ("mental_condition", "addiction"),
             "neurodivergent": ("mental_condition", "neurodivergent, unspecified"), "diabetic": ("physical_condition", "diabetes"), "a diabetic": ("physical_condition", "diabetes"),
             "epileptic": ("physical_condition", "neurological condition"), "asthmatic": ("physical_condition", "respiratory condition or allergy"),
             "deaf": ("physical_condition", "vision or hearing impairment"), "hard of hearing": ("physical_condition", "vision or hearing impairment"),
             "blind": ("physical_condition", "vision or hearing impairment"), "legally blind": ("physical_condition", "vision or hearing impairment"),
             "disabled": ("physical_condition", "physical disability"), "a wheelchair user": ("physical_condition", "physical disability"), "an amputee": ("physical_condition", "physical disability"),
             "celiac": ("physical_condition", "digestive condition"), "a celiac": ("physical_condition", "digestive condition")}
BODIES = {"skinny": "very thin", "very thin": "very thin", "underweight": "very thin", "thin": "slim", "slim": "slim", "slender": "slim", "lean": "slim", "athletic": "athletic or muscular",
          "muscular": "athletic or muscular", "fit": "athletic or muscular", "buff": "athletic or muscular", "jacked": "athletic or muscular", "toned": "athletic or muscular",
          "average": "average", "average build": "average", "curvy": "curvy", "thick": "curvy", "chubby": "chubby or overweight", "overweight": "chubby or overweight",
          "fat": "chubby or overweight", "heavy": "chubby or overweight", "bbw": "chubby or overweight", "plus size": "chubby or overweight", "plus-size": "chubby or overweight",
          "big": "chubby or overweight", "obese": "obese", "morbidly obese": "obese", "petite": "slim"}
HAIRS = {"blonde": "blonde", "blond": "blonde", "brown": "brown", "brunette": "brown", "black": "black", "red": "red", "ginger": "red", "auburn": "red", "a redhead": "red",
         "redhead": "red", "a ginger": "red", "grey": "grey or white", "gray": "grey or white", "white": "grey or white", "silver": "grey or white", "pink": "dyed unusual color",
         "blue": "dyed unusual color", "purple": "dyed unusual color", "green": "dyed unusual color", "bald": "bald", "balding": "bald", "a blonde": "blonde"}
DIETS = {"vegan": "vegan", "vegetarian": "vegetarian", "veggie": "vegetarian", "pescatarian": "pescatarian", "pescetarian": "pescatarian", "keto": "keto or low carb",
         "halal": "halal or kosher", "kosher": "halal or kosher", "gluten free": "gluten free", "gluten-free": "gluten free"}
LANGUAGES = frozenset("english spanish french german italian portuguese dutch swedish norwegian danish finnish polish czech slovak hungarian romanian bulgarian greek croatian serbian "
                      "russian ukrainian turkish arabic hebrew persian farsi hindi urdu bengali punjabi tamil telugu marathi gujarati malayalam kannada chinese mandarin cantonese japanese "
                      "korean vietnamese thai tagalog filipino indonesian malay swahili afrikaans catalan basque welsh irish icelandic estonian latvian lithuanian albanian".split())
LANGUAGE_NAMES = {"farsi": "persian", "mandarin": "chinese", "filipino": "tagalog"}
JOBS = {
    "software or IT": "software engineer|software developer|developer|programmer|web developer|data scientist|data engineer|sysadmin|system administrator|devops engineer|"
                      "network engineer|it technician|it support|help desk|game developer|front end developer|frontend developer|backend developer|full stack developer|"
                      "cybersecurity analyst|security engineer|qa engineer|software tester|coder|dev|swe|it guy|it professional|machine learning engineer|ml engineer",
    "engineering": "engineer|mechanical engineer|electrical engineer|civil engineer|chemical engineer|aerospace engineer|structural engineer|process engineer|"
                   "manufacturing engineer|industrial engineer|biomedical engineer|environmental engineer|engineering student",
    "science or research": "scientist|researcher|biologist|chemist|physicist|professor|lab tech|lab technician|postdoc|research assistant|geologist|astronomer|neuroscientist|"
                           "microbiologist|ecologist|statistician|economist",
    "doctor, nurse or clinical health": "doctor|physician|nurse|rn|np|nurse practitioner|surgeon|dentist|pharmacist|paramedic|emt|physical therapist|physiotherapist|"
                                        "occupational therapist|radiologist|resident|anesthesiologist|psychiatrist|psychologist|therapist|veterinarian|vet tech|optometrist|"
                                        "midwife|dental hygienist|physician assistant|pa-c|doula|counselor|counsellor|nursing student|med student|medical student|gp",
    "health support or care work": "cna|caregiver|care worker|carer|support worker|home health aide|medical assistant|pharmacy tech|pharmacy technician|personal care assistant|"
                                   "phlebotomist|dental assistant|hospice worker",
    "teaching or education": "teacher|tutor|lecturer|educator|teaching assistant|substitute teacher|kindergarten teacher|preschool teacher|elementary teacher|"
                             "high school teacher|math teacher|english teacher|science teacher|music teacher|librarian|principal|special ed teacher",
    "law": "lawyer|attorney|paralegal|solicitor|barrister|judge|legal assistant|public defender|prosecutor|law student",
    "finance or accounting": "accountant|cpa|financial analyst|banker|actuary|auditor|bookkeeper|trader|financial advisor|investment banker|bank teller|underwriter",
    "business, management or consulting": "manager|consultant|ceo|founder|project manager|product manager|business analyst|executive|director|operations manager|hr manager|"
                                          "recruiter|entrepreneur|business owner|cto|cfo",
    "marketing, media or communications": "marketer|journalist|editor|copywriter|reporter|social media manager|marketing manager|pr specialist|content writer|digital marketer",
    "arts, design or entertainment": "artist|designer|graphic designer|musician|actor|actress|photographer|writer|author|illustrator|animator|dj|filmmaker|tattoo artist|"
                                     "streamer|content creator|youtuber|model|painter|singer|dancer|game designer|ux designer|interior designer|comedian|producer|composer|"
                                     "video editor|voice actor|cosplayer|novelist|poet",
    "sales or retail": "cashier|sales rep|salesman|saleswoman|retail worker|sales associate|realtor|real estate agent|store manager|car salesman|wholesaler",
    "food service or hospitality": "chef|cook|line cook|server|waiter|waitress|bartender|barista|dishwasher|baker|hotel manager|sous chef|busser|hostess",
    "skilled trade or construction": "electrician|plumber|carpenter|welder|mechanic|hvac tech|roofer|construction worker|contractor|lineman|tradesman|mason|"
                                     "machinist|auto mechanic|diesel mechanic|handyman|painter and decorator|apprentice electrician",
    "manufacturing or warehouse": "warehouse worker|factory worker|forklift driver|forklift operator|assembly line worker|production worker|picker|packer",
    "transport or delivery": "driver|truck driver|trucker|delivery driver|pilot|flight attendant|bus driver|uber driver|courier|mail carrier|mailman|postal worker|train conductor",
    "police, fire or security": "cop|police officer|firefighter|security guard|detective|correctional officer|sheriff|state trooper|dispatcher",
    "military": "soldier|marine|sailor|airman|infantryman",
    "government or public service": "civil servant|government employee|federal employee|city employee|public servant",
    "social work or religious work": "social worker|pastor|priest|minister|youth pastor|chaplain|nun|rabbi|imam|case worker|youth worker",
    "office or administrative": "receptionist|secretary|admin assistant|administrative assistant|office manager|data entry clerk|clerk|customer service rep|call center agent|"
                                "office worker|executive assistant",
    "cleaning, maintenance or personal service": "janitor|cleaner|housekeeper|maintenance worker|hairdresser|hairstylist|barber|nanny|groundskeeper|dog walker|nail tech|"
                                                 "esthetician|massage therapist|babysitter",
    "farming or outdoor work": "farmer|rancher|landscaper|gardener|forester|fisherman|arborist|park ranger",
    "sex work or adult content": "escort|sex worker|cam girl|camgirl|stripper|onlyfans creator|porn star|pornstar",
}
JOB_OF = {title: field for field, titles in JOBS.items() for title in titles.split("|")}
JOB_TITLES = "|".join(sorted(map(re.escape, JOB_OF), key=len, reverse=True))
SUBJECTS = {"computer science": "computer science or IT", "cs": "computer science or IT", "comp sci": "computer science or IT", "software engineering": "computer science or IT",
            "information technology": "computer science or IT", "it": "computer science or IT", "data science": "computer science or IT", "cybersecurity": "computer science or IT",
            "engineering": "engineering", "mechanical engineering": "engineering", "electrical engineering": "engineering", "civil engineering": "engineering",
            "chemical engineering": "engineering", "aerospace engineering": "engineering", "math": "mathematics or statistics", "maths": "mathematics or statistics",
            "mathematics": "mathematics or statistics", "statistics": "mathematics or statistics", "physics": "natural sciences", "chemistry": "natural sciences",
            "biology": "natural sciences", "biochemistry": "natural sciences", "geology": "natural sciences", "astronomy": "natural sciences", "neuroscience": "natural sciences",
            "environmental science": "natural sciences", "medicine": "medicine or health", "nursing": "medicine or health", "pharmacy": "medicine or health",
            "public health": "medicine or health", "kinesiology": "medicine or health", "physical therapy": "medicine or health", "psychology": "psychology",
            "sociology": "social sciences", "political science": "social sciences", "anthropology": "social sciences", "economics": "social sciences", "criminology": "social sciences",
            "international relations": "social sciences", "geography": "social sciences", "business": "business or finance", "finance": "business or finance",
            "accounting": "business or finance", "marketing": "business or finance", "management": "business or finance", "business administration": "business or finance",
            "law": "law", "education": "education", "history": "humanities", "english": "humanities", "philosophy": "humanities", "literature": "humanities",
            "linguistics": "humanities", "classics": "humanities", "theology": "humanities", "religious studies": "humanities", "art": "arts or design", "fine arts": "arts or design",
            "graphic design": "arts or design", "music": "arts or design", "film": "arts or design", "theater": "arts or design", "theatre": "arts or design",
            "architecture": "arts or design", "design": "arts or design", "journalism": "humanities", "communications": "social sciences"}
SUBJECT_NAMES = "|".join(sorted(map(re.escape, SUBJECTS), key=len, reverse=True))
KINDS = {"band": "artist", "artist": "artist", "singer": "artist", "rapper": "artist", "musician": "artist", "group": "artist", "musical artist": "artist", "composer": "artist",
         "show": "franchise", "tv show": "franchise", "series": "franchise", "anime": "franchise", "manga": "franchise", "movie": "franchise", "film": "franchise",
         "franchise": "franchise", "book series": "franchise", "cartoon": "franchise", "sitcom": "franchise", "comic": "franchise", "game": "video_game", "video game": "video_game",
         "videogame": "video_game", "book": "franchise", "novel": "franchise", "author": "author", "writer": "author", "team": "sports_team", "club": "sports_team",
         "player": "athlete", "athlete": "athlete", "driver": "athlete", "fighter": "athlete", "wrestler": "athlete", "character": "character", "pokemon": "character",
         "hero": "character", "villain": "character", "champion": "character", "streamer": "creator", "youtuber": "creator", "podcast": "creator", "podcaster": "creator",
         "creator": "creator", "actor": "celebrity", "actress": "celebrity", "comedian": "celebrity", "celebrity": "celebrity"}
KIND_WORDS = "|".join(sorted(map(re.escape, KINDS), key=len, reverse=True))
NAME = r"((?:[Tt]he )?[A-Z0-9][\w'&.:!+-]*(?:,? (?:of|the|and|&|de|la|le|vs\.?|in|on|a|to|[A-Z0-9][\w'&.:!+-]*)){0,6})"
TRAILING = re.compile(r"(?:\s+(?:of|the|and|&|de|la|le|vs\.?|in|on|a|to))+$|[\s,.:!]+$")
PLACE_NAMES = "|".join(sorted(map(re.escape, PLACES), key=len, reverse=True))
PLACE = rf"(?:the )?({PLACE_NAMES})(?![\w-])"
RESIDE = rf"(?:i live|i've lived|i'?ve been living|i'm living|im living|living|i'm currently living|i reside|i'm based|im based|i am based|based|i'm located|located|i'm currently|i'm|im|i am|we live|we're|we are|i moved|i've moved|i just moved|i relocated|here)\s+(?:currently\s+|now\s+|still\s+|also\s+|just\s+|right\s+)?(?:in|near|outside(?: of)?|around|to)\s+{PLACE}"
ORIGIN = rf"(?:i grew up|i was raised|i was born|born and raised|born|raised|i'm originally from|im originally from|i am originally from|originally from)\s+(?:in\s+)?{PLACE}"
FROM = rf"(?:i'm|im|i am|we're|we are)\s+(?:also\s+)?from\s+{PLACE}"
TAG = r"(?<![\w$#.,'/:+-])(?:(\d{2})\s?([mf])|([mf])\s?(\d{2}))(?![\w'%])"
FOR = r"(?<![a-z0-9])(?:(\d{2})\s*)?[\[\(]?\s*(nb|[mf])[mf]?\s*4\s*(?:[mfatr]|me|r|nb)\w*\s*[\]\)]?(?:\s*[-–|:#]?\s*(\d{2})(?!\d))?"
START = rf"^\W{{0,3}}(\d{{2}})(?=\s*[\[\(]?\s*[mf]?\s*4\s*[mfatr]|\s*[\[\(]\s*[mf]\s*[\]\)]|\s*,?\s+(?:[mf]|male|female)\b)"


OTHERS = re.compile(r"\b(?:my|his|her|their|our|your|he|she|him|boyfriend|girlfriend|bf|gf|husband|wife|hubby|partner|ex|friend|son|daughter|brother|sister|mom|dad|mother|"
                    r"father|dom|sub|guy|girl|man|woman|someone|somebody|with|e\.g|eg|example|like|for|to|and|older|younger|current|new|another|this|that)\W*$")
SELF = re.compile(r"(?:\b(?:i|me|myself|i'm|im|i am|ich|moi|yo)|^)\W*$")
COUPLE = re.compile(r"(?:nb|[mf])[mf]\s*4|couple")
PARTNERED = re.compile(r"\b(?:my|our) (?:wife|husband|hubby|gf|bf|girlfriend|boyfriend|partner)\b|\bmarried\b|\bhotwife\b|\bcouple\b|\bcuck")
SEEKING = re.compile(r"\blooking for\b|\bseeking\b|\banyone\b|\bhmu\b|\bdm me\b|\bhost(?:ing)?\b|\bwanna\b|\bwant(?:s)? (?:a|to|some)\b|\bneed(?:s)? (?:a|some)\b|\bavailable\b|\bsnap\b|\bkik\b|\btonight\b")
BOT_TEXT = re.compile(r"\bi am a bot\b|\bperformed automatically\b|\bplease (?:make sure|include|read)\b|\bpost (?:has been |was )?removed\b|\bmust (?:include|contain)\b")


def owned(lowered, start):
    before = lowered[max(0, start - 24):start]
    return bool(SELF.search(before)) or (start < 60 and not OTHERS.search(before))


def tags(text, lowered, found):
    if BOT_TEXT.search(lowered):
        return
    for match in re.finditer(FOR, lowered):
        if owned(lowered, match.start()):
            found.setdefault(("gender", GENDERS[match.group(2)]), match.start())
            if age := match.group(1) or match.group(3):
                found.setdefault(("age", age), match.start())
            tag = lowered[match.start():match.end()]
            if not COUPLE.search(tag) and not PARTNERED.search(lowered) and SEEKING.search(lowered):
                found.setdefault(("relationship_status", "single"), match.start())
            if pair := re.search(r"(nb|[mf])[mf]?\s*4\s*([mf])(?![a-z])", tag):
                found.setdefault(("sexual_orientation", "straight" if pair.group(1) != pair.group(2) else "gay" if pair.group(1) == "m" else "lesbian"), match.start())
    for match in re.finditer(TAG, lowered):
        if match.group(1) and (re.match(rf"\s*{UNITS}", lowered[match.end():]) or DISTANCE.match(lowered, match.end())):
            continue
        age, letter = (match.group(1), match.group(2)) if match.group(1) else (match.group(4), match.group(3))
        bracketed = lowered[match.start() - 1:match.start()] in ("(", "[")
        if not (owned(lowered, match.start() - bracketed) or (bracketed and not OTHERS.search(lowered[max(0, match.start() - 25):match.start() - 1]) and match.start() < 60)):
            continue
        found.setdefault(("gender", GENDERS[letter]), match.start())
        found.setdefault(("age", age), match.start())
    if match := re.match(START, lowered):
        found.setdefault(("age", match.group(1)), 0)


SINGLE = frozenset({"age", "gender"})
LETTERS = re.compile(r"[^\W\d_]{2}")


def ages(value):
    return value if 13 <= int(value) <= 99 else None


RULES = [
    rule("age", rf"\b{I} (?:only |almost |nearly |just |now |about |turning |currently |a |an )?(\d{{2}})(?:\s?(?:years? old|yo|y/o|yrs? old|yrs))?(?=$|[\s.,!;:)])(?!\s*{UNITS}|\s*(?:and|or|-)\s*\d)", lambda match: ages(match.group(1))),
    rule("age", r"\bas an? (\d{2})[- ]?(?:years?|yr)[- ]?old\b", lambda match: ages(match.group(1))),
    rule("age", r"(?:\bi(?:'ve| have)? |^|[.!?] )(?:just |recently |finally )?turned (\d{2})\b(?! (?:years|minutes|weeks|percent|%))", lambda match: ages(match.group(1))),
    rule("age", r"\bi'?m (?:a |an )?(\d{2})\s?(?:yo|y/o|y\.o\.?|years? old|yr old|year-old)\b", lambda match: ages(match.group(1))),
    rule("age", r"(?:^|[.!?\n] *)(\d{2}) (?:years? old|yo|y/o) (?:here|male|female|guy|girl|man|woman|m|f)\b", lambda match: ages(match.group(1))),
    rule("age", r"\bmy age is (\d{2})\b|\bage\s*[:=]\s*(\d{2})\b", lambda match: ages(match.group(1) or match.group(2))),
    rule("age", r"\bi was born in ((?:19[3-9]\d)|(?:200\d)|(?:201[0-3]))\b", lambda match: str(YEAR - int(match.group(1)))),
    rule("age", rf"^\W{{0,2}}[\[\(]?(\d{{2}})[\]\)]?(?=[\s,.!:\]]|$)(?!\s*{UNITS}|[.,:/]\d|\s*[-–/x+]\s*\d|\s*(?:and|or|to|-)\s+\d|\.\s*\d|\s+(?:of|out|times|people|years? ago|is|was|more|minutes|seconds|percent|k)\b)", lambda match: ages(match.group(1)), re.compile(r"$^")),
    rule("age", r"\b(?:i|me|i'm|im|i am|myself|ich)\b[^.!?\n()]{0,25}\((\d{2})\)", lambda match: ages(match.group(1)), SELF_HEDGE),
    rule("age", r"(?<!\bmy )(?<!\bhis )(?<!\bher )(?<!\byour )(?<!\bour )(?<!\btheir )(?<!\bthe )(?<!\ba )(?<!\ban )(?:^|(?<=[\s(\[,]))(\d{2})\s?(?:yo|y/o|y\.o\.?|yr old|year old|years old|yrs old)\b(?! (?:son|daughter|kid|brother|sister|girl|boy|cousin|nephew|niece|dog|cat|car|house|man|woman|guy|male|female|friend|wife|husband)\b)", lambda match: ages(match.group(1)), SELF_HEDGE),
    rule("age", r"\b(?:tengo|tenho|j'ai) (\d{2})(?: (?:años|anos|ans))?\b|\bya[sş] ?:? ?(\d{2})\b|\b(\d{2}) jahre alt\b|\bich bin (\d{2})\b", lambda match: ages(next(filter(None, match.groups()))), SELF_HEDGE),
    rule("age", r"[\[\(]\s*([mfw])\s*[,/]\s*(\d{2})\s*[\]\)]|[\[\(]\s*(\d{2})\s*[,/]\s*([mfw])\s*[\]\)]", lambda match: ages(match.group(2) or match.group(3)), SELF_HEDGE),
    rule("gender", r"[\[\(]\s*([mfw])\s*[,/]\s*\d{2}\s*[\]\)]|[\[\(]\s*\d{2}\s*[,/]\s*([mfw])\s*[\]\)]", lambda match: {"m": "male", "f": "female", "w": "female"}[match.group(1) or match.group(2)], SELF_HEDGE),
    rule("gender", rf"\b{I} (?:an? |the |also an? |just an? |only an? |still an? |actually an? |literally an? )?{ADJECTIVES}{GENDER_WORDS}\b(?! (?:friend|friends|of|enough|up|down|cave|crush|power|bun|time|code|scout|band|group|thing|stuff)\b)(?!'s)", group(GENDERS)),
    rule("gender", rf"\bas an? (?:fully )?{ADJECTIVES}{GENDER_WORDS}\b(?!'s| of\b)", group(GENDERS)),
    rule("gender", r"\bmy (?:\w+ ){0,3}?(cock|dick|penis|balls|bbc|bwc|foreskin|beard)\b|\bmy (?:\w+ ){0,3}?(pussy|boobs|tits|breasts|vagina|clit|period|cervix|uterus|bra|nipples)\b",
         lambda match: "male" if match.group(1) else "female", SELF_HEDGE),
    rule("gender", r"(?:^|[\s,(\]])(milf|hotwife|daddy|dilf|bull|twink|femboy|sissy|bimbo)(?: here| looking| seeking| loves| needs| wants| for| 4\b)", group({"milf": "female", "hotwife": "female", "bimbo": "female", "daddy": "male", "dilf": "male", "bull": "male", "twink": "male", "femboy": "male", "sissy": "male"}), SELF_HEDGE),
    rule("gender", rf"(?:^|[.!?,;] *)(?:a )?{ADJECTIVES}{GENDER_WORDS} here\b", group(GENDERS)),
    rule("gender", rf"\b{I} (?:a |an )?(non-binary|nonbinary|enby|genderfluid|agender|genderqueer|trans woman|transwoman|trans girl|trans man|transman|trans guy|mtf|ftm|transgender|trans)\b(?! (?:people|rights|friend|kids))", group(GENDERS)),
    rule("gender", r"\b(she|he|they)\s?/\s?(?:her|hers|him|his|them|they)\b", group({"she": "female", "he": "male", "they": "non-binary"}), SELF_HEDGE),
    rule("gender", r"(?:^|(?<=[\s,(\]]))[\(\[]\s*([mf])\s*[\)\]]", group(GENDERS), SELF_HEDGE),
    rule("gender", r"\b(?:soy|sou) (?:un |una |uma |um )?(hombre|mujer|chica|chico|homem|mulher)\b|\bje suis une? (homme|femme)\b|\bich bin (?:ein |eine )?(mann|frau)\b",
         lambda match: {"hombre": "male", "chico": "male", "homem": "male", "homme": "male", "mann": "male"}.get(next(filter(None, match.groups())), "female")),
    rule("relationship_status", r"\b(?:my|me|our) (wife|husband|hubby|wifey|spouse|girlfriend|boyfriend|gf|bf|fianc[ée]e?|bae|partner|missus|missis|wifes|husbands)(?:'s)?\b(?! (?:in crime|and i broke up))", group({**RELATIONS, "missus": "married", "missis": "married", "wifes": "married", "husbands": "married"})),
    rule("relationship_status", r"^\W*(wife|husband|hubby|boyfriend|girlfriend|bf|gf)(?:'s| is| and i)\b", group(RELATIONS), SELF_HEDGE),
    rule("relationship_status", r"\b(?:mi|minha|meu|mon|ma|meine|mein|min|mijn|moja|mia|mio) (esposa|marido|esposo|femme|mari|frau|mann|kone|mand|vrouw|man|żona|moglie|marito|novia|novio|namorada|namorado|copine|copain|freundin|freund|kæreste|vriendin|vriend)\b",
         group({"esposa": "married", "marido": "married", "esposo": "married", "femme": "married", "mari": "married", "frau": "married", "mann": "married", "kone": "married", "mand": "married",
                "vrouw": "married", "man": "married", "żona": "married", "moglie": "married", "marito": "married"} | dict.fromkeys(("novia", "novio", "namorada", "namorado", "copine", "copain", "freundin", "freund", "kæreste", "vriendin", "vriend"), "dating or in a relationship"))),
    rule("relationship_status", r"\b(?:happily|newly|recently|just) married\b|\b(?:our|my) (?:wedding|honeymoon|anniversary)\b|\bmy (?:in-laws|mother-in-law|father-in-law|father in law|mother in law)\b", fixed("married")),
    rule("relationship_status", r"\b(?:i've been|i'm|im|i am|we've been|we are|we're) (?:seeing|dating|with) (?:someone|my|this|a)\b|\bi(?:'m| am) in a (?:\w+ )?relationship\b|\bmy (?:relationship|bf/gf|so)\b", fixed("dating or in a relationship")),
    rule("relationship_status", r"\bmy ex[- ]?(?:wife|husband)\b|\bmy divorce\b|\bsince (?:my|the) divorce\b|\bafter (?:my|the) divorce\b", fixed("divorced")),
    rule("relationship_status", r"\b(?:i'm|im|i am) (?:still |currently |now )?(?:single|unattached|not seeing anyone|not dating)\b|\bmy (?:now )?ex(?: girlfriend| boyfriend| gf| bf)? (?:told|left|dumped|broke)\b|\b(?:she|he) (?:left|dumped) me\b|\bwe broke up\b", fixed("single")),
    rule("relationship_status", rf"\b{I} (?:happily |currently |still |also |newly |recently |now )?(single|married|engaged|divorced|separated|widowed|a widow|a widower|in a relationship|taken)\b", group(STATUSES)),
    rule("relationship_status", r"\b(?:i|we) (?:just |recently )?got (married|engaged|divorced)\b|\b(married) (?:for )?(?:\d+|a few|many|almost|over) years\b|\bmy (marriage)\b",
         lambda match: {"married": "married", "engaged": "engaged", "divorced": "divorced", "marriage": "married"}[next(filter(None, match.groups()))]),
    rule("relationship_status", r"\b(married) (?:man|woman|guy|dad|mom|mother|father|couple|male|female)\b", fixed("married")),
    rule("parental_status", r"\bmy (?:\w+ )?(son|daughter|kids?|children|child|toddler|stepson|stepdaughter|sons|daughters|twins|newborn|baby boy|baby girl|teenager|kiddo|kiddos|little one)(?:'s)?\b(?! (?:of|in law))", fixed("has children")),
    rule("parental_status", r"\bi have (?:\d+|a|one|two|three|four|five|six|2|3) (?:\w+ )?(?:kids?|children|child|sons?|daughters?|boys|girls)\b", fixed("has children")),
    rule("parental_status", rf"\b(?:{I}|as) (?:a |an )?(?:\w+ )?(?:mom|mum|mother|dad|father|parent|single mom|single dad|stepmom|stepdad|grandma|grandpa|grandmother|grandfather)\b(?! (?:of|to) (?:a|my) (?:dog|cat|pet))", fixed("has children")),
    rule("parental_status", r"\b(?:mom|mum|mother|dad|father) of (?:\d+|one|two|three|four|five)\b", fixed("has children"), SELF_HEDGE),
    rule("parental_status", r"\b(?:i'm|im|i am) (?:\d+ (?:weeks?|months?) )?pregnant\b|\b\d+ weeks pregnant\b|\bwe(?:'re| are) expecting\b|\bmy pregnancy\b", fixed("expecting a child")),
    rule("parental_status", r"\bi (?:don't|do not|dont) have (?:any )?(?:kids|children)\b|\bi'm child-?free\b|\bwe(?:'re| are) child-?free\b|\bno kids of my own\b", fixed("no children"), re.compile(r"\b(?:if|would|wish)\b")),
    rule("automated_account", r"\bi am a bot\b|\bi'm a bot\b|\bthis is a bot\b|\bthis action was performed automatically\b|\bsou um bot\b|\bsoy un bot\b|\bbeep boop\b", fixed("bot"), re.compile(r"$^")),
    rule("pets", r"\bmy (?:\w+ )?(dogs?|pup|puppy|puppies|doggo|pupper|golden retriever|lab|labrador|pitbull|pit bull|german shepherd|husky|corgi|chihuahua|poodle|beagle|dachshund)(?:'s)?\b", fixed("dog")),
    rule("pets", r"\bmy (?:\w+ )?(cats?|kitten|kitty|kitties|kittens)(?:'s)?\b", fixed("cat")),
    rule("pets", r"\bi (?:don't|do not|dont) have (?:any )?pets\b|\bi have no pets\b", fixed("no pets"), re.compile(r"\b(?:if|would|wish)\b")),
    rule("living_with", r"\bi live (alone|by myself|on my own)\b", fixed("alone")),
    rule("living_with", r"\bi (?:still )?live (?:at home )?with my (?:parents|mom|dad|mum|mother|father|folks|family)\b|\bi(?:'m| am) living with my parents\b|\bi live at home\b", fixed("parents")),
    rule("living_with", r"\bi live with my (?:wife|husband|partner|girlfriend|boyfriend|gf|bf|fianc\w*|kids|children|spouse)\b|\bwe live together\b", fixed("partner or family")),
    rule("living_with", r"\bmy (?:roommates?|roomates?|flatmates?|housemates?)\b|\bi live with (?:\w+ )?(?:roommates?|flatmates?|housemates?)\b", fixed("roommates")),
    rule("housing", r"\bi (?:own|bought) (?:a|my|our) (?:\w+ )?(?:house|home|condo|townhouse|townhome)\b|\b(?:my|our) mortgage\b|\b(?:as a|i'm a|im a) homeowner\b|\bwe (?:own|bought) (?:a|our) (?:house|home)\b|\bwhen (?:i|we) bought (?:my|our) house\b", fixed("homeowner")),
    rule("housing", r"\bmy (?:landlord|lease)\b|\bi rent (?:a|an|my)\b|\bi'm renting\b|\b(?:as a|i'm a) renter\b|\bmy rent (?:is|went)\b", fixed("renter")),
    rule("housing", r"\b(?:i'm|im|i am) (?:currently |now )?homeless\b|\bi live in my car\b", fixed("homeless")),
    rule("employment_status", r"\bi work (?:as|at|for|in|from home|remotely|part[- ]time|full[- ]time|nights|weekends|\d+ hours|retail|construction|the|a|an|with|on|two|2|three|long|12|10|8|overtime|doubles|every)\b|\bmy (?:boss|coworkers?|co-workers?|manager|employer|job|workplace|shift|shifts|work|paycheck|paychecks|salary|wage|wages|commute|office|clients|colleagues|work day|workday|work week|team lead|supervisor)\b|\b(?:at|after|before|from|off) work\b|\bi'?m at work\b|\bon my (?:lunch|break)\b|\bfor a living\b|\bi get paid\b|\bi(?:'ve| have) been (?:teaching|working)\b|\b(?:i'm|im|i am) (?:currently )?(?:working|doing an? (?:\w+ )?internship|employed|interning)\b|\bi'm on shift\b|\b(?:a|my) (?:\w+ )?(?:job|day job)\b(?= (?:and|but|so|that|where|which|i))", fixed("employed")),
    rule("employment_status", r"\b(?:i'm|im|i am) (?:a |an )?(?:old |now )?retired\b|\b\(retired\)|\bretired (?:now|since|for)\b|\bmy retirement\b(?! (?:account|fund|savings|plan|age))", fixed("retired")),
    rule("employment_status", r"\b(?:i'm|im|i am) (?:a |an )?(?:solo |serial |first[- ]time |startup )?(?:founder|co-?founder|entrepreneur|freelancer|contractor|business owner|small business owner)\b|\bmy (?:own )?(?:business|company|agency|startup|shop|store|salon|studio|practice|brand)\b(?! (?:card|account|class|school|trip))|\bi (?:have |just )?started (?:a|an|my own|my) (?:business|company|agency|startup)\b|\bi'm self employed\b|\bi freelance\b", fixed("self-employed or business owner")),
    rule("employment_status", r"\b(?:i'm|im|i am) (?:almost |nearly |currently |now )?(?:in )?(?:my )?(?:1st|2nd|3rd|4th|first|second|third|fourth|final|last) year (?:of|in|at)\b|\bmy (?:bs|ba|bsc|degree|major|course|courses|uni|university|college|thesis|dissertation|lecturer|lectures|semester|classes|professor|exams?|finals|coursework|program)\b|\bi'?m (?:studying|in school|in college|in uni)\b|\bwhile (?:i'm |im |i am )?studying\b|\bi study\b", fixed("student")),
    rule("employment_status", r"\b(?:i'm|im|i am) (?:currently |now )?(?:unemployed|jobless|between jobs|out of work)\b|\bi (?:just )?(?:lost|got laid off from|got fired from) my job\b|\bi got laid off\b", fixed("unemployed")),
    rule("employment_status", r"\b(?:i'm|im|i am) (?:now |recently |semi-|happily )?retired\b|\bsince i retired\b|\bi retired (?:in|last|a few|from)\b|\bas a retiree\b", fixed("retired")),
    rule("employment_status", r"\b(?:i'm|im|i am) (?:a |an )?(?:\w+ )?(?:student|undergrad|freshman|sophomore)\b|\bwhile i'm studying\b|\bmy (?:classes|professor|semester|exams|finals)\b", fixed("student")),
    rule("employment_status", r"\b(?:i'm|im|i am) self[- ]employed\b|\bi (?:own|run|started) (?:a|my own|my) (?:small )?(?:business|company|agency|shop|bar|restaurant|store|firm|practice)\b|\bi'm a (?:small )?business owner\b", fixed("self-employed or business owner")),
    rule("employment_status", r"\bstay[- ]at[- ]home (?:mom|mum|dad|parent|wife)\b|\b(?:i'm|im|i am) a homemaker\b|\bi'm a housewife\b", fixed("homemaker")),
    rule("employment_status", r"\b(?:i'm|im|i am) (?:on disability|unable to work)\b|\bi (?:can't|cannot) work (?:because|due)\b", fixed("unable to work")),
    rule("occupation", rf"\b(?:{I}|i work as|as|i'm working as|i became|i'm now) (?:an? )?(?:(?:registered|licensed|certified|senior|junior|full[- ]time|part[- ]time|freelance|professional|\w+) )?({JOB_TITLES})\b(?! (?:friend|of mine|degree|student|school|program|job|position)\b)(?!'s)", group(JOB_OF)),
    rule("occupation", rf"(?:^|[.!?\n] *)(?:an? )?(?:\w+ )?({JOB_TITLES}) here\b", group(JOB_OF), SELF_HEDGE),
    rule("occupation", r"\bi work (?:in|for a|at a) (tech|it|software|a hospital|healthcare|construction|retail|a restaurant|a warehouse|finance|marketing|law firm|a school|education|manufacturing)\b",
         group({"tech": "software or IT", "it": "software or IT", "software": "software or IT", "a hospital": "doctor, nurse or clinical health", "healthcare": "doctor, nurse or clinical health",
                "construction": "skilled trade or construction", "retail": "sales or retail", "a restaurant": "food service or hospitality", "a warehouse": "manufacturing or warehouse",
                "finance": "finance or accounting", "marketing": "marketing, media or communications", "law firm": "law", "a school": "teaching or education",
                "education": "teaching or education", "manufacturing": "manufacturing or warehouse"})),
    rule("education", rf"\b{I} (?:a |an )?(?:\w+ )?(?:college|university|uni|undergrad|undergraduate) student\b|\b{I} (?:currently )?in (?:college|uni|university)\b|\b{I} (?:a |an )?(?:college )?(?:freshman|sophomore) in college\b|\b(?:my|i'm in my) (?:freshman|sophomore|junior|senior|first|second|third|final) year (?:of|in|at) (?:college|uni|university)\b", fixed("college student")),
    rule("education", rf"\b{I} (?:a |an )?(?:grad|graduate|phd|ph\.d\.?|masters?|master's|doctoral|med|medical|law) student\b|\b{I} in (?:grad|graduate|med|law) school\b|\bmy (?:phd|dissertation)\b|\bi'm doing my (?:phd|masters|master's)\b", fixed("graduate student")),
    rule("education", rf"\b{I} (?:a |an )?(?:\w+ )?(?:high school|hs) (?:student|senior|junior|freshman|sophomore)\b|\b{I} (?:still )?in high school\b|\b{I} in (?:9th|10th|11th|12th) grade\b", fixed("high school student")),
    rule("education", r"\bi (?:have|hold|got|earned|finished|completed) (?:a |an |my )?(?:bachelor'?s|bachelors|ba|bs|bsc|b\.s\.|b\.a\.|undergrad(?:uate)? degree|four[- ]year degree|4[- ]year degree)\b|\bi graduated (?:from )?(?:college|university|uni)\b|\bi have a (?:\w+ )?degree\b(?! in progress)", fixed("bachelor's degree")),
    rule("education", r"\bi (?:have|hold|got|earned|finished|completed) (?:a |an |my )?(?:master'?s|masters|ma|ms|msc|m\.s\.|mba|msw|med)\b(?! student)", fixed("master's degree")),
    rule("education", r"\bi (?:have|hold|got|earned|finished|completed) (?:a |an |my )?(?:phd|ph\.d\.?|doctorate)\b", fixed("doctorate")),
    rule("education", r"\bi (?:have|hold|got|earned) (?:a |an |my )?(?:jd|j\.d\.|md|law degree|medical degree)\b", fixed("professional degree such as law or medicine")),
    rule("education", r"\bi (?:graduated|finished) (?:from )?high school\b|\bi (?:only )?have (?:a |my )?(?:high school diploma|ged)\b|\bi(?:'m| am) a high school graduate\b", fixed("high school diploma")),
    rule("education", r"\bi dropped out of high school\b|\bi never finished high school\b|\bi didn't finish high school\b", fixed("no high school diploma"), re.compile(r"\b(?:if|would|wish)\b")),
    rule("education", r"\bi dropped out of (?:college|uni|university)\b|\bi have some college\b|\bi never finished (?:college|my degree)\b", fixed("some college, no degree"), re.compile(r"\b(?:if|would|wish)\b")),
    rule("education", r"\bi (?:have|got|earned) (?:an? )?associate'?s(?: degree)?\b|\bi went to trade school\b", fixed("trade school or associate degree")),
    rule("field_of_study", rf"\bi (?:study|studied|majored in|major in|am majoring in|'m majoring in|m majoring in|have a degree in|got my degree in|have a (?:bachelor'?s|bachelors|master'?s|masters|phd|ba|bs|bsc|ms|msc) in|graduated in|did my degree in|am studying|'m studying|m studying)\s+({SUBJECT_NAMES})\b", group(SUBJECTS)),
    rule("field_of_study", rf"\b{I} (?:a |an )?({SUBJECT_NAMES}) (?:major|student|graduate|grad)\b|\bmy ({SUBJECT_NAMES}) (?:degree|major)\b", lambda match: SUBJECTS[match.group(1) or match.group(2)]),
    rule("sexual_orientation", rf"\b{I} (?:a |an )?(?:(?:\d{{2}}[- ]?(?:years?|yr)[- ]old|cis|single|married|black|white|asian|trans|young|old|older|proud|openly|also|both|totally|fully) )*(gay|lesbian|bisexual|bi|pansexual|asexual|queer|straight|heterosexual|homosexual)\b(?![-'])(?! (?:up|out|forward|away|from|to|edge|talking|with|couple|bar|club|friend|men|women|guys|people|porn|marriage|ally|rights|shooter|a)\b)", group(ORIENTATIONS)),
    rule("sexual_orientation", r"\bas an? (?:\w+ )?(gay|lesbian|bisexual|bi|straight|pansexual|asexual|queer) (?:man|woman|guy|girl|person|male|female|dude|couple|boy)\b", group(ORIENTATIONS)),
    rule("sexual_orientation", r"(?:^|[.!?,;] *)(gay|lesbian|bi|bisexual|straight|pansexual) (?:\w+ )?(?:male|female|guy|girl|man|woman|dude|couple) here\b", group(ORIENTATIONS)),
    rule("ethnicity", rf"\b{I} (?:a |an |half |half-|also )?({'|'.join(map(re.escape, ETHNICITIES))})(?: (?:man|woman|guy|girl|person|male|female|dude|american|myself|lady))?(?=$|[\s.,!;:)])(?! (?:people|folks|neighborhood|area|community|friends|culture|food|music|history|kids|family)\b)", group(ETHNICITIES)),
    rule("ethnicity", rf"\bas an? ({'|'.join(map(re.escape, ETHNICITIES))}) (?:man|woman|guy|girl|person|male|female|dude|american|mom|dad|mother|father|lady|kid)\b", group(ETHNICITIES)),
    rule("religion", rf"\b{I} (?:a |an |also a |also an |a devout |a practicing |a practising |a lifelong |an? ex-?\w+ turned )?({'|'.join(map(re.escape, RELIGIONS))})\b(?! (?:school|church|family|friends?|parents|household|university|college|country|state|music|community)\b)", group(RELIGIONS)),
    rule("religion", rf"\bas an? (?:\w+ )?({'|'.join(map(re.escape, RELIGIONS))})\b(?! (?:school|church|family|friends?|parents|household|university|college|country|state|music|community)\b)", group(RELIGIONS)),
    rule("political_identity", rf"\b{I} (?:a |an |also a |also an |a lifelong |a proud |a registered |pretty |very |fairly |quite )?({'|'.join(POLITICS)})\b(?! (?:party|candidate|politician|media|news|state|areas?|policies|policy|government|friends?)\b)", group(POLITICS)),
    rule("political_identity", rf"\bas an? (?:\w+ )?({'|'.join(POLITICS)})\b(?! (?:party|candidate|politician|media|news|state|areas?|policies|policy|government|friends?)\b)", group(POLITICS)),
    rule("mental_condition", rf"\b(?:i have|i've had|i was diagnosed with|i got diagnosed with|i've been diagnosed with|i'm diagnosed with|i suffer from|i struggle with|i deal with|i live with|i've got|i got|as someone with|as a person with|diagnosed with|i'm on meds for|i take meds for|i was recently diagnosed with)\s+(?:(?:severe|mild|moderate|chronic|clinical|major|diagnosed|combined[- ]type|inattentive[- ]type|crippling|bad|really bad|pretty bad|terrible|high[- ]functioning|level \d|untreated|unmedicated|both|some|a lot of|serious|horrible|debilitating) )*({'|'.join(map(re.escape, MENTAL))})\b", group(MENTAL)),
    rule("mental_condition", rf"\bmy (?:own )?({'|'.join(map(re.escape, MENTAL))})(?! (?:friend|kid|son|daughter|brother|sister|partner|husband|wife|mom|dad)\b)\b", group(MENTAL)),
    rule("mental_condition", rf"(?:^|[.!?,;(] *)(?:an? )?(?:fellow )?({'|'.join(map(re.escape, MENTAL))}) (?:here|person here|haver here|sufferer here)\b", group(MENTAL), SELF_HEDGE),
    rule("physical_condition", rf"\b(?:i have|i've had|i was diagnosed with|i got diagnosed with|i've been diagnosed with|i'm diagnosed with|i suffer from|i struggle with|i deal with|i live with|i've got|as someone with|as a person with|i was recently diagnosed with|i'm being treated for)\s+(?:(?:severe|mild|moderate|chronic|stage \w+|diagnosed|really bad|pretty bad|bad|terrible|crazy|debilitating|a mild|a severe|an autoimmune disease called) )*({'|'.join(map(re.escape, PHYSICAL))})\b", group(PHYSICAL)),
    rule("physical_condition", rf"\bmy (?:own )?({'|'.join(map(re.escape, PHYSICAL))})(?! (?:friend|kid|son|daughter|brother|sister|partner|husband|wife|mom|dad|medication)\b)\b", group(PHYSICAL)),
    rule("physical_condition", rf"(?:^|[.!?,;(] *)(?:an? )?(?:fellow )?({'|'.join(map(re.escape, PHYSICAL))}) (?:here|sufferer here|patient here)\b", group(PHYSICAL), SELF_HEDGE),
    rule("diet", rf"\b{I} (?:a |an |also a |also |a strict |fully |mostly |now )?(vegan|vegetarian|veggie|pescatarian|pescetarian)\b(?! (?:food|restaurant|options?|meals?|recipes?|friends?)\b)", group(DIETS)),
    rule("diet", r"\bas an? (vegan|vegetarian|pescatarian|pescetarian)\b(?! (?:food|restaurant|options?|meals?|recipes?)\b)", group(DIETS)),
    rule("diet", r"\bi (?:eat|love) meat\b|\bi'?m a (?:meat eater|carnivore|omnivore)\b", fixed("eats everything")),
    rule("smoking", r"\bi (?:smoke|vape)(?: cigarettes| cigs| a pack| daily| every day)?\b(?! (?:weed|pot|a joint|joints|blunts|cannabis|marijuana|meat|out)\b)|\b(?:i'm|im|i am) a (?:heavy |chain |social )?smoker\b|\bas a smoker\b|\bmy (?:vape|cigarettes)\b", fixed("smoker or vaper"), SELF_HEDGE),
    rule("smoking", r"\bi (?:don't|do not|dont|never) smoke\b|\bi quit smoking\b|\b(?:i'm|im|i am) a non-?smoker\b|\bi've never smoked\b", fixed("non-smoker"), re.compile(r"\b(?:if|would|wish)\b")),
    rule("military_status", rf"\b(?:{I}|as) (?:a |an )?(?:proud |disabled |combat |retired |former )?(?:army|navy|marine|marine corps|air force|military|usmc|combat|iraq|afghanistan|war|coast guard) (?:vet|veteran)\b|\b(?:{I}|as) (?:a |an )?(?:proud |disabled |combat )?veteran\b|\bwhen i was in the (?:army|navy|marines|air force|military|service|marine corps)\b|\bi (?:served|was) in the (?:army|navy|marines|air force|military|coast guard|marine corps)\b|\bi (?:served|did \w+ tours?) in (?:iraq|afghanistan|vietnam)\b", fixed("military veteran"), SELF_HEDGE),
    rule("military_status", r"\b(?:i'm|im|i am) (?:currently )?(?:in|serving in) the (?:army|navy|marines|air force|military|national guard|coast guard|marine corps)\b|\b(?:i'm|im|i am) (?:on )?active duty\b|\b(?:i'm|im|i am) (?:a |an )?(?:active duty )?(?:soldier|marine|sailor|airman|service member)\b", fixed("serving in the military")),
    rule("nationality", rf"\b{I} (?:a |an |also |half |proudly |a proud )?({'|'.join(map(re.escape, DEMONYMS))})(?: citizen| national)?(?=$|[\s.,!;:)])(?! (?:food|people|culture|company|government|accent|friend|girlfriend|boyfriend|wife|husband|music|movies?|guy|girl|man|woman|stuff|style|tv|teacher|class|course|school|version|player)\b)", group(DEMONYMS)),
    rule("nationality", rf"\bas an? ({'|'.join(map(re.escape, DEMONYMS))})(?: citizen| person| myself| national)?\b(?! (?:company|government|food|man|woman|guy|girl|accent)\b)", group(DEMONYMS)),
    rule("native_language", r"\b(?:my )?(?:first|native|mother) (?:language|tongue) is (\w+)\b|\b(\w+) is my (?:first|native|mother) (?:language|tongue)\b|\b(?:i'm|im|i am|as) an? native (\w+) speaker\b|\bnative (\w+) speaker here\b",
         lambda match: (lambda word: LANGUAGE_NAMES.get(word, word) if word in LANGUAGES else None)(next(filter(None, match.groups())))),
    rule("height", rf"\b{I} (?:only |about |around |almost |nearly |barely |like |just |a )?([4-7])\s*(?:'|ft|foot|feet)\s*(?:and )?(\d{{1,2}})?\s*(?:\"|''|in\b|inches)?(?![\d.])(?! (?:away|from|deep|long|wide)\b)",
         lambda match: str(round((int(match.group(1)) * 12 + int(match.group(2) or 0)) * 2.54)) if int(match.group(2) or 0) < 12 else None),
    rule("height", rf"\b{I} (?:only |about |around |almost |nearly |barely |like |just )?(1[4-9]\d|2[01]\d)\s*cm\b", lambda match: match.group(1)),
    rule("weight", rf"\bi (?:weigh|weight|'m at|am at|'m currently at|'m currently)\s+(?:about |around |roughly |almost |like |just under |over |under )?(\d{{2,3}}(?:\.\d)?)\s*(lbs?|pounds|kg|kgs|kilos)\b|\b{I} (\d{{2,3}})\s*(lbs?|pounds|kg|kgs)\b",
         lambda match: (lambda amount, unit: str(round(amount * (1 if unit.startswith("k") else .4536))))(float(match.group(1) or match.group(3)), match.group(2) or match.group(4))),
    rule("income", r"\bi (?:make|earn|made|bring in|bring home|gross|net|take home|clear)\s+(?:about |around |roughly |over |like |~|almost |just under |just over |close to |nearly )?\$?(\d[\d,]*(?:\.\d+)?)\s*(k|thousand)?\s*(?:a|per|/|an?)\s*(?:year|yr|annum)\b|\bmy (?:salary|income) is (?:about |around |roughly |over |like |~)?\$?(\d[\d,]*(?:\.\d+)?)\s*(k|thousand)?\b",
         lambda match: (lambda amount, scale: str(int(amount * (1000 if scale else 1))) if 1000 <= amount * (1000 if scale else 1) <= 100_000_000 else None)(float((match.group(1) or match.group(3)).replace(",", "")), match.group(2) or match.group(4))),
    rule("body_type", rf"\b{I} (?:very |really |pretty |quite |a bit |kinda |kind of |super |too |so |a little |slightly |a |an )?({'|'.join(map(re.escape, BODIES))})\b(?! (?:fan|deal|part|news|on|in|for|with|of|to|time|enough|guy|girl|man|woman)\b)", group(BODIES)),
    rule("body_type", r"(?:^|[\s,|/])(bbw|curvy|petite|chubby|athletic|muscular|slim)\s*(?:f|female|woman|girl|m|male|guy|here)\b", group(BODIES), SELF_HEDGE),
    rule("hair_color", r"\bmy (?:natural )?(blonde?|brown|black|red|ginger|auburn|grey|gray|white|silver|pink|blue|purple|green) hair\b|\bi have (?:long |short |curly |natural )?(blonde?|brown|black|red|ginger|auburn|grey|gray|white|silver|pink|blue|purple|green) hair\b",
         lambda match: HAIRS[match.group(1) or match.group(2)]),
    rule("hair_color", rf"\b{I} (?:a |an |naturally |going )?(blonde|blond|brunette|redhead|a redhead|ginger|a ginger|bald|balding)\b(?! (?:joke|moment|people)\b)", group(HAIRS)),
    rule("hair_color", r"(?:^|[\s,|/(])(blonde?|brunette|redhead|ginger)\s*(?:f|female|woman|girl|m|male|guy|here|milf|babe|beauty|bombshell|teen)\b|\bwith (?:long |short |curly |dark |light |natural |highlighted |dyed )*(blonde?|brown|black|red|ginger|auburn|grey|gray|silver|pink|blue|purple|green)(?: highlighted)? hair\b",
         lambda match: HAIRS[match.group(1) or match.group(2)], SELF_HEDGE),
    rule("mental_condition", rf"\bi (?:have|had|got|suffer from|struggle with|deal with|live with|was diagnosed with|got diagnosed with|have been diagnosed with|'ve been diagnosed with|'ve been dealing with|'ve been struggling with|am dealing with|'m dealing with|battle|fight|manage)\s+(?:\w+\s+){{0,3}}?({'|'.join(map(re.escape, MENTAL))})\b", group(MENTAL)),
    rule("mental_condition", r"\b(?:i'm|im|i am|i get|i got|i feel) (?:so |really |very |pretty |super |kinda |a (?:rather |very |really )?)?(anxious|depressed|suicidal|manic|psychotic|paranoid)(?: person)?\b",
         group({"anxious": "anxiety", "depressed": "depression", "suicidal": "depression", "manic": "bipolar disorder", "psychotic": "schizophrenia or psychosis", "paranoid": "anxiety"}), SELF_HEDGE),
    rule("mental_condition", r"\b(?:my|i take|i'm on|i am on|i started|on|gave me|prescribed me|i need) (?:\w+ )?(sertraline|zoloft|lexapro|escitalopram|ecsitalopram|citalopram|prozac|fluoxetine|wellbutrin|bupropion|effexor|venlafaxine|cymbalta|duloxetine|paxil|buspirone|buspar|lithium|lamictal|lamotrigine|seroquel|quetiapine|abilify|risperidone|adderall|vyvanse|ritalin|concerta|methylphenidate|strattera|xanax|klonopin|ativan|antidepressants|ssris?|stimulants|antipsychotics|mood stabilizers?)\b",
         group({"sertraline": "depression", "zoloft": "depression", "lexapro": "anxiety", "escitalopram": "anxiety", "ecsitalopram": "anxiety", "citalopram": "depression", "prozac": "depression", "fluoxetine": "depression",
                "wellbutrin": "depression", "bupropion": "depression", "effexor": "depression", "venlafaxine": "depression", "cymbalta": "depression", "duloxetine": "depression", "paxil": "anxiety",
                "buspirone": "anxiety", "buspar": "anxiety", "lithium": "bipolar disorder", "lamictal": "bipolar disorder", "lamotrigine": "bipolar disorder", "seroquel": "bipolar disorder",
                "quetiapine": "bipolar disorder", "abilify": "schizophrenia or psychosis", "risperidone": "schizophrenia or psychosis", "adderall": "adhd", "vyvanse": "adhd", "ritalin": "adhd",
                "concerta": "adhd", "methylphenidate": "adhd", "strattera": "adhd", "xanax": "anxiety", "klonopin": "anxiety", "ativan": "anxiety", "antidepressants": "depression",
                "ssri": "depression", "ssris": "depression", "stimulants": "adhd", "antipsychotics": "schizophrenia or psychosis", "mood stabilizer": "bipolar disorder", "mood stabilizers": "bipolar disorder"}), SELF_HEDGE),
    rule("mental_condition", rf"(?:^|[\s,(])(adhd|autism|autistic|ocd|ptsd|bpd|anxiety|depression|bipolar)(?:er)? (?:here|brain|person here|gang|squad|club)\b|\bas (?:an? )?(?:fellow )?(adhd|autistic|ocd|ptsd|bpd|bipolar|anxious|depressed) (?:person|woman|man|adult|guy|girl|individual|sufferer|haver)\b",
         lambda match: MENTAL.get(match.group(1) or match.group(2)) or {"anxious": "anxiety", "depressed": "depression"}.get(match.group(1) or match.group(2)), SELF_HEDGE),
    rule("physical_condition", rf"\bi (?:have|had|got|suffer from|struggle with|deal with|live with|was diagnosed with|got diagnosed with|have been diagnosed with|'ve been diagnosed with|'ve been dealing with|am dealing with|'m dealing with|was born with|battle|fight|manage)\s+(?:\w+\s+){{0,3}}?({'|'.join(map(re.escape, PHYSICAL))})\b", group(PHYSICAL)),
    rule("physical_condition", rf"\b(?:i'm|im|i am) (?:\w+ )?({'|'.join(map(re.escape, (name for name, (field, _) in STATES_OF.items() if field == 'physical_condition')))})\b(?! (?:people|person|friend|community|rights)\b)", lambda match: STATES_OF[match.group(1)][1], SELF_HEDGE),
    rule("mental_condition", rf"\b(?:i'm|im|i am) (?:\w+ )?({'|'.join(map(re.escape, (name for name, (field, _) in STATES_OF.items() if field == 'mental_condition')))})\b(?! (?:people|person|friend|community|rights|kids?|son|daughter)\b)", lambda match: STATES_OF[match.group(1)][1], SELF_HEDGE),
    rule("physical_condition", r"\bmy (?:\w+ )?(inhaler|epipen|insulin|metformin|chemo|chemotherapy|radiation|dialysis|levothyroxine|thyroid|period|periods|cycle|hearing aids?|wheelchair|cane|crutches|migraines?|seizures?|knee|back pain|arthritis|endo|ibs|gerd|reflux|tumor|tumour|diagnosis)\b",
         group({"inhaler": "respiratory condition or allergy", "epipen": "respiratory condition or allergy", "insulin": "diabetes", "metformin": "diabetes", "chemo": "cancer", "chemotherapy": "cancer",
                "radiation": "cancer", "dialysis": "other physical condition", "levothyroxine": "hormonal or reproductive condition", "thyroid": "hormonal or reproductive condition",
                "period": "hormonal or reproductive condition", "periods": "hormonal or reproductive condition", "cycle": "hormonal or reproductive condition", "hearing aid": "vision or hearing impairment",
                "hearing aids": "vision or hearing impairment", "wheelchair": "physical disability", "cane": "physical disability", "crutches": "other physical condition", "migraine": "neurological condition",
                "migraines": "neurological condition", "seizure": "neurological condition", "seizures": "neurological condition", "knee": "other physical condition", "back pain": "chronic pain or fibromyalgia",
                "arthritis": "other physical condition", "endo": "hormonal or reproductive condition", "ibs": "digestive condition", "gerd": "digestive condition", "reflux": "digestive condition",
                "tumor": "cancer", "tumour": "cancer"}), SELF_HEDGE),
    rule("physical_condition", r"\bi (?:wear|need|use) (?:hearing aids?|glasses|contacts|a wheelchair|a cane|an inhaler)\b|\bi'?m (?:legally )?(?:deaf|blind|hard of hearing)\b|\bi (?:was )?born without\b",
         lambda match: "physical disability" if "wheelchair" in match.group() or "cane" in match.group() or "without" in match.group() else "respiratory condition or allergy" if "inhaler" in match.group() else "vision or hearing impairment", SELF_HEDGE),
    rule("physical_condition", rf"(?:^|[\s,(])(t1d|t2d|t1|t2|type 1|type 2|diabetic|pcos|endo|celiac|coeliac|ibs|crohnie|spoonie|fibro|eds|pots|me/cfs) (?:here|warrior|gang|squad|life)\b", group({"t1d": "diabetes", "t2d": "diabetes", "t1": "diabetes", "t2": "diabetes", "type 1": "diabetes", "type 2": "diabetes", "diabetic": "diabetes", "pcos": "hormonal or reproductive condition", "endo": "hormonal or reproductive condition", "celiac": "digestive condition", "coeliac": "digestive condition", "ibs": "digestive condition", "crohnie": "digestive condition", "spoonie": "chronic pain or fibromyalgia", "fibro": "chronic pain or fibromyalgia", "eds": "other physical condition", "pots": "heart or blood condition", "me/cfs": "other physical condition"}), SELF_HEDGE),
    rule("education", r"\b(?:college|university|uni|undergrad|undergraduate|community college|first[- ]generation college|first[- ]gen college) student\b(?! (?:loans?|debt|visa|athlete|housing|discount)\b)|\b(?:i'm|im|i am) (?:currently )?(?:in|at) (?:college|uni|university)\b|\bmy (?:freshman|sophomore|junior|senior|first|second|third|1st|2nd|3rd|final|last) (?:year|semester) (?:of|in|at) (?:college|uni|university)\b|\b(?:i'm|im|i am) (?:almost |nearly |currently |now )?(?:in )?(?:my )?(?:1st|2nd|3rd|4th|first|second|third|fourth|final|last) year (?:of|in|at) (?!high school)", fixed("college student"), SELF_HEDGE),
    rule("education", r"\b(?:grad|graduate|phd|ph\.d\.?|doctoral|masters?|master's|msc|mba|med|medical|law|nursing|dental|pharmacy) (?:student|candidate)\b(?! (?:loans?|debt|visa|housing)\b)|\b(?:i'm|im|i am) (?:in|doing|finishing|starting) (?:my )?(?:grad school|graduate school|med school|medical school|law school|phd|masters|master's|doctorate|residency)\b|\bmy (?:phd|dissertation|doctorate|masters program|master's program|grad program|residency)\b|\bi (?:was )?(?:just |recently )?accepted into (?:a |the )?(?:\w+ ){0,3}(?:program|grad school|masters|phd)\b",
         lambda match: "professional degree such as law or medicine" if re.search(r"law school|med school|medical school|residency|medical student|law student|med student", match.group()) else "graduate student", SELF_HEDGE),
    rule("education", r"\b(?:high school|hs|highschool) (?:student|senior|junior|sophomore|freshman)\b|\b(?:i'm|im|i am) (?:a )?(?:senior|junior|sophomore|freshman) in (?:high school|highschool|hs)\b|\b(?:i'm|im|i am) (?:still )?in (?:high school|highschool|hs|(?:9th|10th|11th|12th) grade|year (?:9|10|11|12))\b|\bmy (?:high school|highschool) (?:teacher|classes|graduation)\b", fixed("high school student"), SELF_HEDGE),
    rule("education", r"\bmy (?:bachelor'?s|bachelors|ba|bs|bsc|b\.s\.|b\.a\.|undergrad|undergraduate degree|degree|diploma)\b|\bi (?:graduated|have graduated|just graduated) (?:from )?(?:college|university|uni|with (?:a|my) degree)\b|\bi(?:'ve| have) (?:finished|completed|done) (?:my )?(?:degree|bachelors|bachelor's|undergrad)\b|\bas an? (?:\w+ )?(?:graduate|grad)\b(?! student)|\b(?:college|university) graduate\b|\bi have a (?:college |university )?degree\b",
         lambda match: "bachelor's degree", SELF_HEDGE),
    rule("education", r"\bmy (?:master'?s|masters|msc|mba|msw)\b(?! (?:program|student))|\bi (?:have|got|earned|finished|completed) (?:a |an |my )?(?:master'?s|masters|msc|mba|msw)\b", fixed("master's degree"), SELF_HEDGE),
    rule("occupation", rf"\b(?:{I}|i work as|as|i'm working as|i became|i'm now|work as|working as|my job as|my career as|my role as|became|job as) (?:an? |the )?(?:(?:\w+[- ]?){{0,3}} )?({JOB_TITLES})s?\b(?! (?:friend|of mine|degree|student|school|program|job|position|training|course|license)\b)(?!'s)", group(JOB_OF)),
    rule("occupation", rf"\b(?:i|me) (?:\w+ ){{0,2}}(?:work|worked|working) (?:in|at|for|with) (?:a |an |the )?(?:\w+ )?(tech|it|software|hospital|healthcare|construction|retail|restaurant|warehouse|finance|marketing|law firm|school|education|manufacturing|bank|banking|insurance|accounting|sales|hospitality|hotel|government|military|nursing|pharmacy|daycare|factory|kitchen|bar|call center|customer service|logistics|trucking|real estate|advertising|media|journalism|film|entertainment|social work|ministry|church|security|engineering|research|academia|lab|clinic|dental office|vet clinic|salon)\b",
         group({"tech": "software or IT", "it": "software or IT", "software": "software or IT", "hospital": "doctor, nurse or clinical health", "healthcare": "doctor, nurse or clinical health", "construction": "skilled trade or construction",
                "retail": "sales or retail", "restaurant": "food service or hospitality", "warehouse": "manufacturing or warehouse", "finance": "finance or accounting", "marketing": "marketing, media or communications",
                "law firm": "law", "school": "teaching or education", "education": "teaching or education", "manufacturing": "manufacturing or warehouse", "bank": "finance or accounting", "banking": "finance or accounting",
                "insurance": "finance or accounting", "accounting": "finance or accounting", "sales": "sales or retail", "hospitality": "food service or hospitality", "hotel": "food service or hospitality",
                "government": "government or public service", "military": "military", "nursing": "doctor, nurse or clinical health", "pharmacy": "doctor, nurse or clinical health", "daycare": "teaching or education",
                "factory": "manufacturing or warehouse", "kitchen": "food service or hospitality", "bar": "food service or hospitality", "call center": "office or administrative", "customer service": "office or administrative",
                "logistics": "transport or delivery", "trucking": "transport or delivery", "real estate": "sales or retail", "advertising": "marketing, media or communications", "media": "marketing, media or communications",
                "journalism": "marketing, media or communications", "film": "arts, design or entertainment", "entertainment": "arts, design or entertainment", "social work": "social work or religious work",
                "ministry": "social work or religious work", "church": "social work or religious work", "security": "police, fire or security", "engineering": "engineering", "research": "science or research",
                "academia": "science or research", "lab": "science or research", "clinic": "doctor, nurse or clinical health", "dental office": "doctor, nurse or clinical health", "vet clinic": "doctor, nurse or clinical health",
                "salon": "cleaning, maintenance or personal service"}), SELF_HEDGE),
    rule("occupation", r"\bmy (patients|students|pupils|clients|customers|classroom|lesson plans?|caseload|shift at the hospital|unit|charge nurse|clinic)\b",
         group({"patients": "doctor, nurse or clinical health", "students": "teaching or education", "pupils": "teaching or education", "clients": "business, management or consulting",
                "customers": "sales or retail", "classroom": "teaching or education", "lesson plan": "teaching or education", "lesson plans": "teaching or education", "caseload": "social work or religious work",
                "shift at the hospital": "doctor, nurse or clinical health", "unit": "doctor, nurse or clinical health", "charge nurse": "doctor, nurse or clinical health", "clinic": "doctor, nurse or clinical health"}), SELF_HEDGE),
    rule("parental_status", r"\b(?:my|our) (?:\d+|one|two|three|four|five|six|little|youngest|oldest|eldest|middle|baby|teenage|adult|grown|newborn|first|second|third|\d+ ?(?:yo|y/o|year[- ]old|month[- ]old))?[- ]?(sons?|daughters?|kids?|children|toddlers?|twins|stepkids|stepson|stepdaughter|kiddos?|babies|boys|girls|grandkids|grandchildren|grandson|granddaughter|first born|firstborn|newborn|infant|little ones?)\b(?! (?:of|in law|in-law)\b)",
         lambda match: None if match.group(1) in ("boys", "girls") and not re.search(r"\b(?:\d+|one|two|three|little|baby|youngest|oldest|teenage)\b", match.group()) else "has children", SELF_HEDGE),
    rule("parental_status", r"\b(?:having|raising|with) (?:\w+ )?(?:toddlers|kids|young children|a toddler|a newborn|an infant)\b|\b(?:postpartum|pp|breastfeeding|nursing my (?:son|daughter|baby)|my last pregnancy|after (?:having|giving birth to) my)\b|\b(?:mom|mum|mother|dad|father|parent) (?:here|of (?:\d+|one|two|three|four|five|twins))\b|\bas an? (?:\w+ )?(?:mom|mum|mother|dad|father|parent|grandma|grandpa)\b",
         fixed("has children"), SELF_HEDGE),
    rule("body_type", rf"\b{I} (?:a |an |very |really |pretty |quite |a bit |kinda |kind of |super |too |so |a little |slightly |naturally |extra |also )*({'|'.join(map(re.escape, BODIES))})\b(?! (?:fan|deal|part|news|on|in|for|with|of|to|time|enough|guy|girl|man|woman|mood|chance|mess|game|difference|problem|issue|plus|day|week|month|year)\b)", group(BODIES), SELF_HEDGE),
    rule("body_type", r"\b(?:my|this|with a|with my) (?:\w+ )?(curvy|chubby|thick|thicc|petite|fat|skinny|slim|athletic|muscular|fit|tiny|bbw|plus[- ]size|average|toned|slender|dad) (?:body|build|frame|figure|bod|self)\b|\b(slim|athletic|average|slender|muscular|stocky|heavy|thin|fit|curvy|chubby|thick|thicc|petite|tiny)(?: and (?:fit|toned|athletic|slim))? build\b|\bbuilt like an hourglass\b|\bextra (thicc|thick)\b",
         lambda match: (lambda word: "curvy" if word in ("thicc", "thick", None) else {"tiny": "very thin", "dad": "average", "stocky": "chubby or overweight", "heavy": "chubby or overweight"}.get(word, BODIES.get(word)))(match.group(1) or match.group(2) or match.group(3)), SELF_HEDGE),
    rule("height", r"(?:^|[\s,|/(])([4-7])\s?(?:'|’|ft)\s?(\d{1,2})?\s?(?:\"|”|''|in\b)?(?=\s*[,|/]?\s*(?:\d{2,3}\s?(?:lbs?|kg|pounds)|tall|and\b|[,|/]|$))", lambda match: str(round((int(match.group(1)) * 12 + int(match.group(2) or 0)) * 2.54)) if int(match.group(2) or 0) < 12 else None, SELF_HEDGE),
    rule("weight", r"(?:^|[\s,|/(])(\d{2,3})(?:ish)?\s?(lbs?|pounds|kg|kgs)\b(?! (?:of|lost|down|weight|heavier|lighter|ago|gain|gained|more|less|bag|bags|box|dumbbells?|plates?|bench|squat|deadlift))", lambda match: (lambda amount, unit: str(round(amount * (1 if unit.startswith("k") else .4536))) if 35 <= amount * (1 if unit.startswith("k") else .4536) <= 250 else None)(float(match.group(1)), match.group(2)), SELF_HEDGE),
    rule("ethnicity", rf"(?:^|[\s,(\]])({'|'.join(map(re.escape, ETHNICITIES))}) (?:guy|girl|male|female|man|woman|dude|queen|king|couple|bottom|top|daddy|milf|bbw|twink|stud|bull|wife|hubby|baddie|boy|lady|mom|dad|chick|babe|beauty|femboy|sub|dom)\b(?= (?:here|looking|seeking|for|with|in|4|from|wants|needs|who|ready)\b)", group(ETHNICITIES), SELF_HEDGE),
    rule("ethnicity", rf"\b(?:i'm|im|i am|as) (?:a |an )?(?:proud |young |old |single |married |tall |short |\d{{2}}[- ]?(?:years?[- ]old|yo|y/o)[- ]?)?({'|'.join(map(re.escape, ETHNICITIES))}) (?:man|woman|guy|girl|person|male|female|dude|american|lady|mom|dad|mother|father|kid|teen|boy|immigrant|canadian|british|australian)\b", group(ETHNICITIES), SELF_HEDGE),
    rule("religion", r"\bmy (?:faith|church|mosque|synagogue|temple|pastor|priest|rabbi|imam|bible|quran|parish|congregation)\b|\bi (?:go to|attend) (?:church|mass|mosque|synagogue|temple)\b|\bi pray\b|\bas a (?:believer|follower of (?:christ|jesus))\b",
         lambda match: {"mosque": "muslim", "quran": "muslim", "imam": "muslim", "synagogue": "jewish", "rabbi": "jewish", "temple": "hindu"}.get(next((word for word in ("mosque", "quran", "imam", "synagogue", "rabbi", "temple") if word in match.group()), ""), "christian"), SELF_HEDGE),
    rule("living_with", r"\b(?:we|my (?:wife|husband|partner|girlfriend|boyfriend|gf|bf|fianc\w*) and i) (?:just |recently |finally )?moved in together\b|\bmoved in (?:with|together with) my (?:girlfriend|boyfriend|partner|gf|bf|fianc\w*)\b|\bmy (?:wife|husband|partner|girlfriend|boyfriend|gf|bf) and i live\b|\bwe live together\b|\bwho lives with me\b|\b(?:our|my) (?:house|home|apartment|place)\b(?= with my (?:wife|husband|partner))", fixed("partner or family"), SELF_HEDGE),
    rule("living_with", r"\bi (?:have )?(?:lived|live|am living|'m living|still live) (?:at home )?with my (?:mom and dad|parents|mom|dad|mum|mother|father|folks|grandparents)\b|\bmy parents' (?:house|place|home)\b(?= where i)|\bi live at home\b|\bliving at home with\b", fixed("parents"), SELF_HEDGE),
    rule("living_with", r"\b(?:my|our) (?:\w+ )?(?:roommates?|roomates?|room mates?|flatmates?|housemates?|roomie|roomies)\b", fixed("roommates"), SELF_HEDGE),
    rule("living_with", r"\bi live (?:all )?(alone|by myself|on my own)\b|\bliving (?:alone|by myself|on my own)\b|\bhappy alone\b|\bi'm (?:all )?alone\b", fixed("alone"), SELF_HEDGE),
    rule("smoking", r"\b(?:i|me) (?:\w+ )?(?:smoke|smoked|vape|vaped) (?:for|to|after|before|when|every|a|cigarettes|cigs|daily)\b|\bmy (?:cigarettes?|cigs|vape|juul|pack of)\b|\b(?:i'm|im|i am) a (?:heavy |chain |social |casual )?(?:smoker|vaper)\b", fixed("smoker or vaper"), SELF_HEDGE),
    rule("hair_color", r"\b(?:i'm|im|i am|i m) (?:a |an )?(?:\w+ )?(red ?head|redhead|ginger|blonde|blond|brunette)\b|(?:^|[\s,|/(])(red ?head|redhead|brunette)\b(?= (?:\w+ )?(?:here|bitch|boy|girl|guy|babe|milf|wife|mom|looking|f\b|m\b))|\b(?:i have|i've got|my|with) (?:long |short |thick |thin |curly |straight |wavy |natural |graying |greying |dark |light |bright )*(blonde?|brown|black|red|ginger|auburn|grey|gray|white|silver|pink|blue|purple|green)(?: buzz cut| curly| wavy)? hair\b",
         lambda match: HAIRS.get((match.group(1) or match.group(2) or match.group(3)).replace(" ", "")) or "red", SELF_HEDGE),
    rule("mental_condition", r"\b(audhd|au/dhd)\b", fixed("both adhd and autism"), SELF_HEDGE),
    rule("mental_condition", r"\b(adhd|autism|autistic|asd) (?:brain|makes my|affects my|ruins my|means i)\b|\bmy (?:adhd|autism) (?:brain|meds|medication|diagnosis)\b|\bfor my (adhd|autism|anxiety|depression|ocd|ptsd)\b",
         lambda match: MENTAL[next(filter(None, match.groups()), "adhd") if (match.group(1) or match.group(2)) else re.search(r"adhd|autism|anxiety|depression|ocd|ptsd", match.group()).group()], SELF_HEDGE),
    rule("mental_condition", r"\b(?:i'm|im|i am|i m) (?:literally |also |very |severely |pretty )?(dyslexic|dyspraxic|neurodivergent|neurodiverse|nd|on the spectrum)\b", lambda match: "autism" if "spectrum" in match.group() else "neurodivergent, unspecified", SELF_HEDGE),
    rule("field_of_study", rf"\b(?:degree|degrees|bachelors?|bachelor's|masters?|master's|phd|bsc|ba|bs|ms|msc|major|majoring|majored|graduate|student|year|diploma|course|studies|studying|study|studied) in ({SUBJECT_NAMES}|electronics(?: and communication)?(?: engineering)?|data analytics|it management|physical therapy|accountancy|ultrasound|nursing|chem)\b",
         lambda match: SUBJECTS.get(match.group(1)) or {"data analytics": "computer science or IT", "it management": "computer science or IT", "physical therapy": "medicine or health", "accountancy": "business or finance",
                                                       "ultrasound": "medicine or health", "chem": "natural sciences"}.get(match.group(1)) or "engineering", SELF_HEDGE),
    rule("field_of_study", rf"\b(?:as an? |i'm an? |im an? |i am an? )({SUBJECT_NAMES}) (?:graduate|grad|student|major)\b|\b(bcom|b\.com|bba|mba|cse|ece|eee|btech in cs|mbbs|llb|bsn|bscn|beng|bfa)\b",
         lambda match: SUBJECTS.get(match.group(1)) if match.group(1) else {"bcom": "business or finance", "b.com": "business or finance", "bba": "business or finance", "mba": "business or finance", "cse": "computer science or IT",
                                                                         "ece": "engineering", "eee": "engineering", "btech in cs": "computer science or IT", "mbbs": "medicine or health", "llb": "law", "bsn": "medicine or health",
                                                                         "bscn": "medicine or health", "beng": "engineering", "bfa": "arts or design"}[match.group(2)], SELF_HEDGE),
    rule("ethnicity", rf"(?:^|[\s,(\]])((?:spicy |hot |sexy |thick |young |cute |mature |shy )?(?:latina|latino|black|white|asian|indian|desi|arab|ebony|mixed)) (?:mami|papi|queen|king|domme|dom|sub|bottom|top|bull|stud|baddie|goddess|princess|daddy|milf|bbw|twink|boy|girl|guy|man|woman|male|female|couple|wife|hubby)\b",
         lambda match: ETHNICITIES.get(match.group(1).split()[-1]) or ("black" if match.group(1).split()[-1] == "ebony" else None), SELF_HEDGE),
    rule("ethnicity", r"\bwe (black|white|asian|latina|latino|hispanic|indian|desi|arab|indigenous|native) (?:women|men|people|folks|girls|guys)\b|\bsoy (latino|latina|mexicano|mexicana|negro|negra|blanco|blanca)\b|\bwhite ?boi\b|\b(?:i'm|im|i am|i m) (black|white|asian|latina|latino|hispanic|mixed|biracial|desi)(?=$|[\s.,!;:)])(?! (?:people|folks|neighborhood|area|community|friends|culture|food|music|history|kids|family|and \w+ing)\b)",
         lambda match: (lambda word: {"mexicano": "hispanic or latino", "mexicana": "hispanic or latino", "negro": "black", "negra": "black", "blanco": "white", "blanca": "white", "native": "indigenous"}.get(word) or ETHNICITIES.get(word) or "white")(next(filter(None, match.groups()), "white")), SELF_HEDGE),
    rule("native_language", r"\benglish (?:is not|isn't|is no|ain't|isnt) my (?:native|first|mother|main) (?:language|tongue)\b|\b(?:i'm|im|i am) not (?:a )?native (?:english )?speaker\b|\bnon[- ]native (?:english )?speaker\b|\bmy english (?:is|isn't) (?:not )?(?:bad|good|great|perfect)\b(?=.{0,40}(?:sorry|excuse|forgive|native))", fixed("not english"), re.compile(r"$^")),
    rule("native_language", r"\b(\w+) is the only language i (?:speak|know)\b|\bas (?:a )?native (\w+ )?speakers?\b", lambda match: (lambda word: (LANGUAGE_NAMES.get(word, word) if word in LANGUAGES else None) if word else "english")((match.group(1) or (match.group(2) or "").strip())), SELF_HEDGE),
    rule("military_status", r"\bmy (?:squadron|platoon|battalion|company commander|unit|deployment|command|chain of command|first sergeant|drill sergeant|mos|rate|ship|base|cos|nco|co|squad leader)\b|\bi(?:'m| am) (?:currently )?(?:deployed|stationed)\b|\bwhen i(?:'m| am) deployed\b|\b\d+(?:st|nd|rd|th) (?:meu|infantry|airborne|marines|cav|cavalry)\b",
         fixed("serving in the military"), SELF_HEDGE),
    rule("military_status", r"\bi served (?:my country|\d+ years|in|for|on|with|overseas|two tours|three tours)\b|\bretired (?:chief|sergeant|master sergeant|colonel|lieutenant|major|captain|petty officer|sgt|gunny|army|navy|marine|air force)\b|\bwhen i (?:got out|was enlisted|enlisted)\b|\b(?:i'm|im|i am) (?:a |an )?(?:old |retired |former )?(?:\w+ )?(?:veteran|vet)\b(?= (?:here|and|myself|of)|[.,!])", fixed("military veteran"), SELF_HEDGE),
    rule("political_identity", r"\b(?:i'm|im|i am|i m) (?:on the |firmly on the |pretty |very |far |more |center |centre |a )?(left|right|left[- ]wing|right[- ]wing|leftist|left[- ]leaning|right[- ]leaning|lefty|righty)\b(?! (?:handed|eye|side|hand|now|here|there)\b)",
         lambda match: "socialist or left" if match.group(1).startswith("left") or match.group(1) == "lefty" else "conservative or right", SELF_HEDGE),
    rule("political_identity", r"\bi(?:'m| am) (?:actually )?a (?:proud |big |huge |strong )?supporter of (?:the )?(democrats?|labour|labor|bernie|aoc|republicans?|gop|trump|maga|tories|conservatives|greens|ndp|liberals)\b",
         lambda match: {"democrat": "progressive or liberal", "democrats": "progressive or liberal", "labour": "socialist or left", "labor": "socialist or left", "bernie": "socialist or left", "aoc": "socialist or left", "greens": "socialist or left", "ndp": "socialist or left", "liberals": "progressive or liberal"}.get(match.group(1), "conservative or right"), SELF_HEDGE),
    rule("diet", r"(?:^|[.!?,;(] *)(vegan|vegetarian|veggie|pescatarian|pescetarian) here\b|\b(?:i've been|i went|been|went|i became|i turned) (vegan|vegetarian|pescatarian)\b", lambda match: DIETS[match.group(1) or match.group(2)], SELF_HEDGE),
    rule("smoking", r"\bnon[- ]?smoker\b|\b(?:i|we) don'?t smoke\b", fixed("non-smoker"), re.compile(r"\b(?:if|would|wish|prefer|looking for|seeking|must be|only)\b")),
    rule("religion", r"\b(?:allah|inshallah|insha'?allah|alhamdulillah|mashallah|masha'?allah|jazakallah|subhanallah|prophet muhammad|astaghfirullah)\b|\bramadan mubarak\b|\bmy (?:salah|wudu|deen|hijab)\b", fixed("muslim"), SELF_HEDGE),
    rule("religion", r"\b(?:bible study|my bible|jesus is my|my lord and savior|my savior|praise god|god bless|christ is king|my rosary|i'm (?:a )?catholic|as a catholic)\b", fixed("christian"), SELF_HEDGE),
    rule("religion", r"\bi(?:'m| am) not (?:a )?religious(?: person)?\b|\bi (?:don't|do not) (?:believe in god|follow (?:any )?religion)\b|\bi loathe (?:all )?religion\b", lambda match: "atheist" if "god" in match.group() or "loathe" in match.group() else "spiritual, no religion", re.compile(r"$^")),
    rule("income", r"\b(?:i|me) (?:make|made|earn|earned|bring in|take home|gross|net|pull|pulled)\s+(?:about |around |roughly |over |like |~|almost |just under |just over |close to |nearly |an? )?\$?(\d[\d,]*(?:\.\d+)?)\s*(k|thousand)?\s*(?:a|per|/|an?|each)\s*(year|yr|annum|month|mo|hour|hr|week|wk)\b",
         lambda match: (lambda amount: str(int(amount)) if 1000 <= amount <= 100_000_000 else None)(float(match.group(1).replace(",", "")) * (1000 if match.group(2) else 1) * {"year": 1, "yr": 1, "annum": 1, "month": 12, "mo": 12, "hour": 2080, "hr": 2080, "week": 52, "wk": 52}[match.group(3)]), SELF_HEDGE),
]
FAVORITE = re.compile(rf"(?i:\bmy (?:all[- ]time |absolute |personal |current |top |favou?rite |most favou?rite )*(?:favou?rite|fave|fav|favs) ({KIND_WORDS})(?: of all time| ever| right now| atm| at the moment)? (?:is|has to be|would be|would have to be|was always|remains|are)\s+){NAME}")
FAVORED = re.compile(rf"{NAME}(?i: (?:is|are|was|has always been|will always be) (?:still |definitely |probably |easily |honestly |hands down )?my (?:all[- ]time |absolute |personal |current |top |favou?rite |most favou?rite )*(?:favou?rite|fave|fav|goat)(?: ({KIND_WORDS}))?\b)")
FAN = re.compile(rf"(?i:\b(?:i'm|im|i am) (?:an? )?(?:huge|big|massive|die[- ]?hard|lifelong|life[- ]long|long[- ]?time|proud|loyal|true|real|giant|enormous|devoted) ){NAME}(?i: (?:fan|supporter|stan)\b)")
MAIN = re.compile(rf"(?i:\bi (?:main|mained|play as|always play as) ){NAME}")
SPORTS = re.compile(r"(?i:fc|united|city|athletic|rovers|wanderers|lakers|celtics|yankees|dodgers|cowboys|patriots|packers|eagles|giants|warriors|bulls|knicks|chiefs|steelers|bears|"
                    r"49ers|niners|raiders|ravens|broncos|seahawks|rams|jets|dolphins|bills|lions|vikings|saints|falcons|panthers|buccaneers|bucs|titans|colts|texans|jaguars|"
                    r"browns|bengals|chargers|cardinals|commanders|red sox|cubs|mets|astros|braves|phillies|padres|mariners|blue jays|orioles|twins|tigers|royals|rangers|"
                    r"brewers|pirates|reds|rockies|marlins|nationals|white sox|guardians|athletics|heat|nets|bucks|suns|mavericks|mavs|nuggets|spurs|rockets|thunder|jazz|"
                    r"clippers|kings|pelicans|grizzlies|hawks|hornets|pistons|pacers|cavaliers|cavs|magic|wizards|raptors|76ers|sixers|timberwolves|wolves|blazers|"
                    r"maple leafs|leafs|canadiens|habs|bruins|oilers|flames|canucks|penguins|flyers|blackhawks|red wings|avalanche|lightning|capitals|islanders|devils|sabres|"
                    r"senators|jets|kraken|predators|stars|blues|wild|ducks|sharks|golden knights|arsenal|chelsea|liverpool|tottenham|spurs|everton|barcelona|real madrid|"
                    r"juventus|bayern|dortmund|psg|ajax|celtic|rangers|milan|inter|napoli|roma|benfica|porto|galatasaray|fenerbahce|boca|river plate)\b")


POSITIVE = re.compile(r"(?i:\bi (?:really |absolutely |just |also |still |honestly |totally |seriously |genuinely |do |personally )?(?:love|loved|adore|adored|enjoy|enjoyed|like|liked|dig|recommend|second|rewatched|replayed)\b|"
                      r"\bi'?m (?:so |really |totally |kinda |completely )?(?:obsessed with|addicted to|into|a (?:huge |big )?fan of|hooked on|in love with)\b|\bcan'?t get enough of\b|"
                      r"\bmy (?:all[- ]time |absolute |personal |current |top )?(?:favou?rites?|faves?|favs?)\b|\bfell in love with\b|"
                      r"\b(?:is|are|was|were) (?:so |really |very |absolutely |just |still |honestly |such an? |pretty |easily |definitely |by far )?(?:good|great|amazing|awesome|excellent|fantastic|"
                      r"underrated|underappreciated|goated|incredible|perfect|beautiful|fun|peak|fire|the goat|the best|my jam|a banger|bangers|a masterpiece|a classic|brilliant|"
                      r"phenomenal|gorgeous|lovely|wonderful|so fun)\b|\b(?:been|currently|finally|started) (?:playing|watching|listening to|reading|bingeing|binging|replaying|rewatching)\b|"
                      r"\bfor me\b|\bmine is\b|\bhands down\b|\bthe goat\b|\bi'?m (?:playing|watching|listening to|reading|replaying|rewatching)\b)")
NEGATIVE = re.compile(r"(?i:\b(?:hate|hated|don'?t like|didn'?t like|not a fan|dislike|overrated|boring|worst|trash|garbage|sucks|terrible|awful|meh|never (?:played|watched|liked))\b)")
CONTEXTS = {
    "video_game": re.compile(r"(?i:\b(?:games?|gaming|gamer|play|played|playing|playthrough|steam|xbox|playstation|ps[1-5]|switch|nintendo|console|dlc|boss|bosses|speedrun|multiplayer|co-?op|rpg|jrpg|mmo|mmorpg|fps|roguelike|patch|grind|raid|quest|controller|remake|remaster|sequel|campaign|achievements?|platinum)\b)"),
    "franchise": re.compile(r"(?i:\b(?:show|shows|series|season|seasons|episode|episodes|anime|manga|movie|movies|film|films|watch|watched|watching|rewatch|rewatching|binge|tv|netflix|hbo|disney|sitcom|cartoon|comic|comics|trilogy|franchise|novel|novels|books?)\b)"),
    "artist": re.compile(r"(?i:\b(?:songs?|albums?|band|bands|music|concerts?|tour|listen|listened|listening|tracks?|singer|rapper|vinyl|ep|lp|spotify|lyrics|discography|gig|setlist|live show|banger|bangers|vocals|guitarist|drummer)\b)"),
    "character": re.compile(r"(?i:\b(?:character|characters|main|maining|mains|waifu|husbando|ship|shipped|arc|villain|protagonist|cosplay|pokemon|pokémon|hero|heroes|champion|skin)\b)"),
    "author": re.compile(r"(?i:\b(?:author|authors|writer|wrote|writes|novels?|books?|read|reading)\b)"),
    "creator": re.compile(r"(?i:\b(?:streamer|streams?|streaming|twitch|youtube|youtuber|channel|videos?|podcast|podcasts|vlogs?|content)\b)"),
}
CANDIDATE = re.compile(r"(?<![\w'])((?:[A-Z][\w'&:.!+-]*|\d+[a-z]*)(?: (?:of|the|and|&|de|la|vs\.?|in|on|a|to|no|[A-Z0-9][\w'&:.!+-]*))*)|[\"“]([^\"”\n]{2,40})[\"”]")
COMMON = frozenset("i i'm im i've i'd i'll it it's its the this that these those my me mine we our you your he she they them his her their a an and but or so if when what why how where who which "
                   "yes no yeah yep nope ok okay lol lmao omg oh hey hi hello thanks thank also just honestly literally well not then there here now today tomorrow yesterday "
                   "love loved great best good amazing awesome edit update tldr tl;dr op reddit google youtube god jesus christmas monday tuesday wednesday thursday friday saturday "
                   "sunday january february march april may june july august september october november december english american nta yta esh nah imo imho idk tbh btw "
                   "definitely probably maybe sure same agreed true right wow damn dude bro man guys please sorry what's that's there's".split())


def fandom(text, found):
    for sentence in re.finditer(r"[^.!?\n]+[.!?]*", text):
        part = sentence.group()
        if not (cue := POSITIVE.search(part)) or NEGATIVE.search(part):
            continue
        if hedged(part.lower(), cue.start(), cue.end(), SELF_HEDGE):
            continue
        first = len(part) - len(part.lstrip())
        lowered_text = text.lower()
        names = []
        for match in CANDIDATE.finditer(part):
            name = (match.group(1) or match.group(2)).strip()
            words = name.lower().split()
            if words and words[0] in COMMON:
                name, words = " ".join(name.split()[1:]), words[1:]
            if not words or not LETTERS.search(name) or re.fullmatch(r"[\d\W]*\w?\d[\w-]*", name):
                continue
            if len(words) == 1 and (words[0] in COMMON or len(name) < 4 or match.start() == first or re.search(rf"(?<![\w'])(?-i:{re.escape(words[0])})(?![\w'])", text)):
                continue
            if cue.start() <= match.start() < cue.end():
                continue
            window = part[max(0, match.start() - 80):match.end() + 80]
            kinds = {kind: 3 * len(pattern.findall(window)) + len(pattern.findall(part)) for kind, pattern in CONTEXTS.items()}
            kind = max(kinds, key=kinds.get)
            if kinds[kind]:
                names.append((abs(match.start() - cue.start()), kind, name))
        for _, kind, name in sorted(names)[:2]:
            named(kind, name, found, sentence.start())


def favorites(text, found):
    for pattern in (FAVORITE, FAVORED):
        for match in pattern.finditer(text):
            name, kind = (match.group(2), match.group(1)) if pattern is FAVORITE else (match.group(1), match.group(2))
            attribute = KINDS.get((kind or "").lower())
            if attribute and not hedged(text.lower(), match.start(), match.end(), SELF_HEDGE):
                named(attribute, name, found, match.start())
    for match in FAN.finditer(text):
        if SPORTS.search(match.group(1)) and not hedged(text.lower(), match.start(), match.end(), SELF_HEDGE):
            named("sports_team", match.group(1), found, match.start())
    for match in MAIN.finditer(text):
        if not hedged(text.lower(), match.start(), match.end(), SELF_HEDGE):
            named("character", match.group(1), found, match.start())


def named(attribute, name, found, position):
    name = TRAILING.sub("", name).strip()
    if 1 < len(name) <= 40 and (value := fan_value(attribute, name.lower())):
        found.setdefault((attribute, value), position)


def places(text, lowered, found):
    for pattern, prefixes in ((RESIDE, ("residence",)), (FROM, ("residence", "origin")), (ORIGIN, ("origin",))):
        for match in re.finditer(pattern, lowered):
            if not hedged(lowered, match.start(), match.end(), SELF_HEDGE):
                for prefix in prefixes:
                    placed(prefix, match.group(1), lowered, match.end(), text, found)
                if pattern is FROM and PLACES[match.group(1)][0] == "country":
                    found.setdefault(("nationality", PLACES[match.group(1)][3]), match.start())
    for match in re.finditer(rf"(?:^|[.!?,;(] *)({'|'.join(map(re.escape, DEMONYMS))}) here\b", lowered):
        found.setdefault(("nationality", DEMONYMS[match.group(1)]), match.start())
    for match in re.finditer(rf"#({PLACE_NAMES})(?![\w-])", lowered):
        placed("residence", match.group(1), lowered, match.end(), text, found)
    first = lowered.split("\n", 1)[0]
    if re.search(FOR, first) or re.search(TAG, first):
        for match in re.finditer(rf"(?<![\w-]){PLACE}", first):
            if text[match.start(1)].isupper() or match.group(1) in ("uk", "usa", "nyc"):
                placed("residence", match.group(1), lowered, match.end(), text, found)
    for match in re.finditer(rf"\b(?:as an? |i'm an? |im an? )({'|'.join(map(re.escape, DEMONYMS))}) living in {PLACE}", lowered):
        placed("residence", match.group(2), lowered, match.end(), text, found)
    for match in re.finditer(rf"(?<!far )(?<!away )(?<!different )(?<!apart )(?<!miles )(?<!flight )(?<!flights )(?<!imported )(?<!shipped )\bfrom (?:the )?{PLACE}", lowered):
        if not hedged(lowered, match.start(), match.end(), SELF_HEDGE):
            placed("residence", match.group(1), lowered, match.end(), text, found)
            if PLACES[match.group(1)][0] == "country":
                placed("origin", match.group(1), lowered, match.end(), text, found)
    for match in re.finditer(rf"{PLACE}[ -]based\b|{PLACE} (?:area|resident|local)\b|\b(?:my city|my town|my country|my state|my hometown)[\s.,:(-]+(?:is |of )?{PLACE}", lowered):
        name = match.group(1) or match.group(2) or match.group(3)
        placed("residence", name, lowered, match.end(), text, found)
    for match in re.finditer(r"\bwe(?:'re| are)? (?:all )?(americans|brits|canadians|aussies|australians|kiwis|germans|irish|indians|filipinos|mexicans)\b|\bwe (americans|brits|canadians|aussies|australians|germans|indians|filipinos)\b", lowered):
        country = DEMONYMS[(match.group(1) or match.group(2)).rstrip("s").replace("filipino", "filipino")] if (match.group(1) or match.group(2)).rstrip("s") in DEMONYMS else DEMONYMS.get((match.group(1) or match.group(2))[:-1])
        if country:
            found.setdefault(("residence_country", country), match.start())
            found.setdefault(("nationality", country), match.start())
    if len(text.strip()) <= 80 and re.fullmatch(r"\W*[^\W\d][\w .'()-]*,\s*[^\W\d][\w .'()-]*\W*", text.strip()):
        for match in re.finditer(rf"(?<![\w-]){PLACE}", lowered):
            if text[match.start(1)].isupper() or match.group(1) in ("uk", "usa", "nyc"):
                placed("residence", match.group(1), lowered, match.end(), text, found)
    for match in re.finditer(r"\b[A-Z][a-z]+(?:[ -][A-Z][a-z]+)*,\s*([A-Z]{2})\b(?![a-z])", text):
        if match.group(1) in CODES and (len(text) <= 200 or match.start() < 80):
            found.setdefault(("residence_region", CODES[match.group(1)]), match.start())
            found.setdefault(("residence_country", "united states"), match.start())


def placed(prefix, name, lowered, end, text, found):
    kind, value, region, country = PLACES[name]
    if kind == "city":
        found.setdefault((f"{prefix}_city", value), end)
        if not region and (code := re.match(r",?\s*([A-Z]{2})\b", text[end:end + 5])) and code.group(1) in CODES:
            region = CODES[code.group(1)]
    if kind in ("city", "region") and region:
        found.setdefault((f"{prefix}_region", region), end)
    found.setdefault((f"{prefix}_country", country), end)


@timed
def extract(texts):
    result = {}
    for index, raw in enumerate(texts):
        text = prepared(raw)
        lowered = text.lower()
        found = {}
        tags(text, lowered, found)
        for attribute, pattern, value, hedge in RULES:
            for match in pattern.finditer(lowered):
                if (stated := value(match)) is not None and not hedged(lowered, match.start(), match.end(), hedge):
                    found.setdefault((attribute, stated), match.start())
        favorites(text, found)
        fandom(text, found)
        places(text, lowered, found)
        stated = {attribute for attribute, _ in found}
        if "occupation" in stated and "employment_status" not in stated:
            found[("employment_status", "employed")] = min(position for (attribute, _), position in found.items() if attribute == "occupation")
        if ("relationship_status", "married") in found and "living_with" not in stated:
            found[("living_with", "partner or family")] = found[("relationship_status", "married")]
        earliest = {}
        for (attribute, value), position in sorted(found.items(), key=lambda item: item[1]):
            if attribute in SINGLE:
                earliest.setdefault(attribute, value)
        if facts := {pair for attribute, value in found if (attribute not in SINGLE or earliest[attribute] == value) and (pair := canonical(attribute, value))}:
            result[index] = facts
    return result
