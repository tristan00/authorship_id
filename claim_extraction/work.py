import re

from .common import I, SELF_HEDGE, fixed, group, rule

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
                                        "midwife|dental hygienist|physician assistant|pa-c|doula|nursing student|med student|medical student|gp",
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
                                     "streamer|content creator|youtuber|model|painter|singer|dancer|florist|baker|tailor|seamstress|jeweler|game designer|ux designer|interior designer|comedian|producer|composer|"
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
    "social work or religious work": "social worker|pastor|priest|minister|youth pastor|chaplain|nun|rabbi|imam|case worker|youth worker|counselor|counsellor|substance use counselor|addiction counselor",
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
DEGREES = {"bachelor": "bachelor's degree", "bachelors": "bachelor's degree", "bachelor's": "bachelor's degree", "ba": "bachelor's degree", "bs": "bachelor's degree", "bsc": "bachelor's degree",
           "b.s.": "bachelor's degree", "b.a.": "bachelor's degree", "bcom": "bachelor's degree", "b.com": "bachelor's degree", "btech": "bachelor's degree", "b.tech": "bachelor's degree",
           "beng": "bachelor's degree", "bba": "bachelor's degree", "bfa": "bachelor's degree", "bsn": "bachelor's degree", "undergrad degree": "bachelor's degree", "undergraduate degree": "bachelor's degree",
           "master": "master's degree", "masters": "master's degree", "master's": "master's degree", "ma": "master's degree", "ms": "master's degree", "msc": "master's degree", "m.s.": "master's degree",
           "mba": "master's degree", "msw": "master's degree", "mtech": "master's degree", "m.tech": "master's degree", "mfa": "master's degree", "meng": "master's degree", "mse": "master's degree",
           "phd": "doctorate", "ph.d": "doctorate", "ph.d.": "doctorate", "doctorate": "doctorate", "dphil": "doctorate", "jd": "professional degree such as law or medicine",
           "md": "professional degree such as law or medicine", "mbbs": "professional degree such as law or medicine", "dds": "professional degree such as law or medicine",
           "pharmd": "professional degree such as law or medicine", "dvm": "professional degree such as law or medicine", "llb": "bachelor's degree", "associate's": "trade school or associate degree",
           "associates": "trade school or associate degree", "associate degree": "trade school or associate degree", "ged": "high school diploma", "high school diploma": "high school diploma"}
DEGREE_NAMES = "|".join(sorted(map(re.escape, DEGREES), key=len, reverse=True))
STUDYING = (r"\b(?:last|this|next|my|the) (?:semester|trimester|quarter|term)\b(?= (?:of|at|i|we|was|is|has|my|in|and|,)|[.,!])|\b\d(?:st|nd|rd|th) sem(?:ester)?\b|\b(?:i'm|im|i am) (?:almost |nearly |currently |now |only )?(?:in )?(?:my )?(?:1st|2nd|3rd|4th|5th|first|second|third|fourth|final|last) year\b(?! of (?:high school|marriage|work))"
            r"|\b(?:1st|2nd|3rd|4th|first|second|third|final) year (?:electives|student|courses|exams|project)\b|\b(?:in|at) (?:nursing|engineering|law|med|medical|art|film|business|dental|pharmacy|vet|culinary|trade) school\b(?=[^.!?]*\b(?:i|my|me)\b)|\b(?:i'm|im|i am) (?:currently )?(?:in|at) (?:college|uni|university)\b"
            r"|\b(?:college|university|uni|undergrad|undergraduate|community college|first[- ]generation college|first[- ]gen(?:eration)? college) student\b(?! (?:loans?|debt|visa|athlete|housing|discount)\b)|\bmy (?:freshman|sophomore|junior|senior|first|second|third|final) (?:year|semester) (?:of|in|at) (?:college|uni|university)\b|\bmy (?:major|classes|professors?|lectures?|lecturer|uni|campus|dorm|coursework|semester|gpa|syllabus)\b"
            r"|\b(?:i'm|im|i am) (?:currently )?(?:studying|majoring)\b|\bwhile (?:i'm |im |i am |i )?(?:studying|study)\b|\bi(?:'m| am)? (?:in|doing) (?:the|my) (?:bs|ba|bsc|bachelor'?s?|undergrad) (?:program|degree)\b|\b(?:meu|minha) (?:primeiro|segundo|terceiro|primeira) (?:ano|período|semestre)\b|\bfaço (?:uma )?(?:segunda )?graduação\b|\bich studiere\b|\b\w+ studieren\b|\bestudio (?:en la|en el|una|la)\b|\bje suis (?:étudiant|étudiante)\b")
EDUCATION = [
    rule("education", STUDYING, fixed("college student"), SELF_HEDGE),
    rule("education", rf"\b(?:grad|graduate|phd|ph\.d\.?|doctoral|masters?|master's|msc|mba|msw|ma|ms|mfa) (?:student|candidate|program|programme)\b(?! (?:loans?|debt|visa|housing)\b)|\bgrad school\b|\bgraduate school\b|\bmy (?:thesis|dissertation|advisor|supervisor|phd|doctorate|lab)\b|\bfinishing (?:my )?(?:grad|graduate|masters?|master's|phd) (?:program|degree)?\b|\bi study an? (?:jd|ma|ms|msc|masters|phd|llm)\b|\bmeiner dissertation\b|\bmi (?:tesis|doctorado|maestría)\b",
         fixed("graduate student"), SELF_HEDGE),
    rule("education", r"\b(?:law|med|medical|dental|vet|pharmacy) school\b|\bmy residency\b|\b(?:in|doing|finishing|starting) (?:my )?residency\b|\b(?:law|med|medical) student\b", fixed("professional degree such as law or medicine"), SELF_HEDGE),
    rule("education", rf"\b(?:i have|i've got|i got|i hold|i earned|i finished|i completed|i've done|i have done|i did|got|just got|have|with) (?:a |an |my |both |two )?({DEGREE_NAMES})(?: degree| degrees| hons| in| from)?\b(?! (?:student|program|programme|candidate|course|class)\b)|\b({DEGREE_NAMES}) (?:&|and|->|→|,|then) (?:[\w.' ]{{0,12}})\b|\b({DEGREE_NAMES}) hons\b|(?:->|→|&) (?:[\w.' ]{{0,12}} )?({DEGREE_NAMES})\b",
         lambda match: DEGREES[next(filter(None, match.groups()))], SELF_HEDGE),
    rule("education", r"\bi (?:graduated|have graduated|just graduated) (?:from )?(?:college|university|uni|with (?:a|my|honors))\b|\b(?:college|university) graduate\b|\b(?:as an? |i'm an? |im an? |i am an? )(?:\w+ )?(?:graduate|grad)\b(?! (?:student|program|school)\b)|\b\w+ (?:and \w+ )?grad\b(?= (?:having|here|with|who|and|looking)\b)|\bme formei\b|\bi went back to school for\b|\bmy (?:bachelor'?s|bachelors|undergrad|degree) (?:is|was) in\b",
         fixed("bachelor's degree"), SELF_HEDGE),
    rule("education", r"\b(?:i )?(?:graduated|finished) (?:from )?high ?school\b|\bhigh ?school (?:graduate|diploma)\b|\bcompleted (?:my )?12th\b|\bpassed (?:my )?12th\b|\bi have (?:a|my) ged\b", fixed("high school diploma"), SELF_HEDGE),
    rule("education", r"\b(?:i'm|im|i am) (?:still |currently )?in (?:high ?school|hs|(?:9th|10th|11th|12th) grade|year (?:9|10|11|12))\b|\b(?:high ?school|hs) (?:student|senior|junior|sophomore|freshman)\b|\b(?:i'm|im|i am) (?:a )?(?:senior|junior|sophomore|freshman) in (?:high ?school|hs)\b|\bgraduating (?:in |from )?high ?school\b|\bmy (?:high school|highschool) (?:teacher|classes|graduation|exams)\b", fixed("high school student"), SELF_HEDGE),
    rule("education", r"\bi dropped out of (?:college|uni|university)\b|\bi have some college\b|\bi never finished (?:college|my degree)\b|\btransferred (?:to \w+ )?from a community college\b|\bput myself back in college\b|\bacademic(?:ally)? (?:dismissed|suspended|probation)\b", fixed("some college, no degree"), re.compile(r"\b(?:if|would|wish)\b")),
    rule("education", r"\bi dropped out of high ?school\b|\bi never finished high ?school\b|\bi didn't finish high ?school\b", fixed("no high school diploma"), re.compile(r"\b(?:if|would|wish)\b")),
    rule("education", r"\bi (?:have|got|earned) (?:an? )?associate'?s(?: degree)?\b|\bi went to (?:a )?trade school\b|\bi(?:'m| am) a (?:journeyman|licensed electrician|licensed plumber)\b", fixed("trade school or associate degree"), SELF_HEDGE),
]
RULES = [
    rule("employment_status", r"\bi work (?:as|at|for|in|from home|remotely|part[- ]time|full[- ]time|nights|weekends|\d+ hours|retail|construction|the same|two|2|three|long|12|10|8|overtime|doubles|every)\b|\bmy (?:employer|paycheck|paychecks|salary|wage|wages|commute to work|work day|workday|work week|shift|shifts|day job|full[- ]time job|part[- ]time job|job)\b(?! (?:hunt|search|application|interview|offer)\b)|\bi'?m at work\b|\bon my lunch break\b|\bfor a living\b|\bi get paid\b|\bi(?:'ve| have) been teaching\b|\b(?:i'm|im|i am) (?:currently )?(?:doing an? (?:\w+ )?internship|employed|interning|working (?:as|at|in|for|full|part|from))\b|\bi'm on shift\b|\b(?:day|days|hours) of work\b", fixed("employed")),
    rule("employment_status", r"\b(?:i'm|im|i am) (?:a |an )?(?:old |now )?retired\b|\b\(retired\)|\bretired (?:now|since|for)\b|\bmy retirement\b(?! (?:account|fund|savings|plan|age))", fixed("retired")),
    rule("employment_status", r"\b(?:i'm|im|i am) (?:a |an )?(?:solo |serial |first[- ]time |startup )?(?:founder|co-?founder|entrepreneur|freelancer|contractor|business owner|small business owner)\b|(?<!minding )(?<!mind )\bmy (?:own )?(?:business|company|agency|startup|salon|studio|practice)\b(?! (?:card|account|class|school|trip))|\bi (?:have |just )?started (?:a|an|my own|my) (?:business|company|agency|startup)\b|\bi'm self employed\b|\bi freelance\b", fixed("self-employed or business owner")),
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
    rule("income", r"(?:\b(?:i|me) (?:make|made|earn|earned|bring in|bring home|gross|net|take home|clear|pull|pulled)|\bmy (?:salary|income|pay) is)\s+(?:about |around |roughly |over |like |~|almost |just under |just over |close to |nearly |an? )?\$?(\d[\d,]*(?:\.\d+)?)\s*(k|thousand)?\s*(?:(?:a|per|/|an?|each)\s*(year|yr|annum|month|mo|hour|hr|week|wk)\b|(annually|yearly|monthly|hourly|weekly)\b|(?=\s*(?:$|[.,!;)])))",
         lambda match: (lambda amount: str(int(amount)) if 1000 <= amount <= 100_000_000 else None)(float(match.group(1).replace(",", "")) * (1000 if match.group(2) else 1) * {"year": 1, "yr": 1, "annum": 1, "annually": 1, "yearly": 1, "month": 12, "mo": 12, "monthly": 12, "hour": 2080, "hr": 2080, "hourly": 2080, "week": 52, "wk": 52, "weekly": 52, None: 1}[match.group(3) or match.group(4)]), SELF_HEDGE),
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
    rule("occupation", r"\bi (?:sell|teach|tutor|clean|drive|cook|bartend|code|program|nurse|deliver|repair|fix|build|install|cut hair|do hair|do nails|tattoo|farm|trade|edit|photograph|film|stream|cam|dance|model|dj|translate|design|write) (?:\w+ ){0,3}?(?:for a living|for work|professionally|as a job|for my job|full[- ]time|part[- ]time|things to|cars|houses|homes|kids|students|online|on twitch|for clients)\b|\b(?:doing|do) (?:\w+ )?(teaching|nursing|accounting|tutoring|bartending|cleaning|delivery|deliveries|construction|plumbing|welding|modeling|camming|photography|freelance design|web design|graphic design|translation|security|retail|sales) (?:work |jobs? )?(?:right now|now|currently|for a living|full[- ]time|part[- ]time|these days)\b",
         lambda match: {"teaching": "teaching or education", "tutoring": "teaching or education", "nursing": "doctor, nurse or clinical health", "accounting": "finance or accounting", "bartending": "food service or hospitality",
                        "cleaning": "cleaning, maintenance or personal service", "delivery": "transport or delivery", "deliveries": "transport or delivery", "construction": "skilled trade or construction",
                        "plumbing": "skilled trade or construction", "welding": "skilled trade or construction", "modeling": "arts, design or entertainment", "camming": "sex work or adult content",
                        "photography": "arts, design or entertainment", "freelance design": "arts, design or entertainment", "web design": "arts, design or entertainment", "graphic design": "arts, design or entertainment",
                        "translation": "other job", "security": "police, fire or security", "retail": "sales or retail", "sales": "sales or retail"}.get(match.group(1)) or {
                        "sell": "sales or retail", "teach": "teaching or education", "tutor": "teaching or education", "clean": "cleaning, maintenance or personal service", "drive": "transport or delivery",
                        "cook": "food service or hospitality", "bartend": "food service or hospitality", "code": "software or IT", "program": "software or IT", "nurse": "doctor, nurse or clinical health",
                        "deliver": "transport or delivery", "repair": "skilled trade or construction", "fix": "skilled trade or construction", "build": "skilled trade or construction", "install": "skilled trade or construction",
                        "cut": "cleaning, maintenance or personal service", "do": "cleaning, maintenance or personal service", "tattoo": "arts, design or entertainment", "farm": "farming or outdoor work",
                        "trade": "finance or accounting", "edit": "arts, design or entertainment", "photograph": "arts, design or entertainment", "film": "arts, design or entertainment",
                        "stream": "arts, design or entertainment", "cam": "sex work or adult content", "dance": "arts, design or entertainment", "model": "arts, design or entertainment",
                        "dj": "arts, design or entertainment", "translate": "other job", "design": "arts, design or entertainment", "write": "arts, design or entertainment"}[match.group().split()[1]], SELF_HEDGE),
    rule("occupation", r"\b(?:doing|started|got|landed|have|finished|completed|in) (?:a|an|my) (?:\w+ )?(banking|finance|accounting|marketing|engineering|software|it|law|legal|nursing|teaching|research|design|consulting|sales|hr|government|journalism) (?:internship|apprenticeship|placement|residency|co-?op)\b|\b(?:camming|cam model|cam girl|onlyfans|only fans|of creator|selling content|custom (?:content|videos|vids))\b",
         lambda match: {"banking": "finance or accounting", "finance": "finance or accounting", "accounting": "finance or accounting", "marketing": "marketing, media or communications", "engineering": "engineering",
                        "software": "software or IT", "it": "software or IT", "law": "law", "legal": "law", "nursing": "doctor, nurse or clinical health", "teaching": "teaching or education", "research": "science or research",
                        "design": "arts, design or entertainment", "consulting": "business, management or consulting", "sales": "sales or retail", "hr": "business, management or consulting",
                        "government": "government or public service", "journalism": "marketing, media or communications"}.get(match.group(1), "sex work or adult content"), SELF_HEDGE),
    rule("occupation", r"\bmy (patients|students|pupils|clients|customers|classroom|lesson plans?|caseload|shift at the hospital|charge nurse|clinic)\b",
         group({"patients": "doctor, nurse or clinical health", "students": "teaching or education", "pupils": "teaching or education", "clients": "business, management or consulting",
                "customers": "sales or retail", "classroom": "teaching or education", "lesson plan": "teaching or education", "lesson plans": "teaching or education", "caseload": "social work or religious work",
                "shift at the hospital": "doctor, nurse or clinical health", "unit": "doctor, nurse or clinical health", "charge nurse": "doctor, nurse or clinical health", "clinic": "doctor, nurse or clinical health"}), SELF_HEDGE),
    *EDUCATION,
    rule("field_of_study", rf"\bi (?:study|studied|majored in|major in|am majoring in|'m majoring in|m majoring in|have a degree in|got my degree in|have a (?:bachelor'?s|bachelors|master'?s|masters|phd|ba|bs|bsc|ms|msc) in|graduated in|did my degree in|am studying|'m studying|m studying)\s+({SUBJECT_NAMES})\b", group(SUBJECTS)),
    rule("field_of_study", rf"\b{I} (?:a |an )?({SUBJECT_NAMES}) (?:major|student|graduate|grad)\b|\bmy ({SUBJECT_NAMES}) (?:degree|major)\b", lambda match: SUBJECTS[match.group(1) or match.group(2)]),
    rule("field_of_study", rf"\b(?:degree|degrees|bachelors?|bachelor's|masters?|master's|phd|bsc|ba|bs|ms|msc|major|majoring|majored|graduate|student|year|diploma|course|studies|studying|study|studied) in ({SUBJECT_NAMES}|electronics(?: and communication)?(?: engineering)?|data analytics|it management|physical therapy|accountancy|ultrasound|nursing|chem)\b",
         lambda match: SUBJECTS.get(match.group(1)) or {"data analytics": "computer science or IT", "it management": "computer science or IT", "physical therapy": "medicine or health", "accountancy": "business or finance",
                                                       "ultrasound": "medicine or health", "chem": "natural sciences"}.get(match.group(1)) or "engineering", SELF_HEDGE),
    rule("field_of_study", rf"\b(?:as an? |i'm an? |im an? |i am an? )({SUBJECT_NAMES}) (?:graduate|grad|student|major)\b|\b(bcom|b\.com|bba|mba|cse|ece|eee|btech in cs|mbbs|llb|bsn|bscn|beng|bfa)\b",
         lambda match: SUBJECTS.get(match.group(1)) if match.group(1) else {"bcom": "business or finance", "b.com": "business or finance", "bba": "business or finance", "mba": "business or finance", "cse": "computer science or IT",
                                                                         "ece": "engineering", "eee": "engineering", "btech in cs": "computer science or IT", "mbbs": "medicine or health", "llb": "law", "bsn": "medicine or health",
                                                                         "bscn": "medicine or health", "beng": "engineering", "bfa": "arts or design"}[match.group(2)], SELF_HEDGE),
]
