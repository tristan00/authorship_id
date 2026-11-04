import re

from .common import HEDGE, SELF_HEDGE, TAGGED, fixed, group, rule

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
RULES = [
    rule("automated_account", r"^(?![\s\S]*\b(?:removed|remove|approv\w*|karma|title|session id)\b)[\s\S]*?(?:\bi am a bot\b|\bi'm a bot\b|\bthis is a bot\b|\bthis action was performed automatically\b|\bsou um bot\b|\bsoy un bot\b|\bbeep boop\b)", fixed("bot"), TAGGED),
    rule("mental_condition", rf"\b(?:i have|i've had|i was diagnosed with|i got diagnosed with|i've been diagnosed with|i'm diagnosed with|i suffer from|i struggle with|i deal with|i live with|i've got|i got|as someone with|as a person with|diagnosed with|i'm on meds for|i take meds for|i was recently diagnosed with)\s+(?:(?:severe|mild|moderate|chronic|clinical|major|diagnosed|combined[- ]type|inattentive[- ]type|crippling|bad|really bad|pretty bad|terrible|high[- ]functioning|level \d|untreated|unmedicated|both|some|a lot of|serious|horrible|debilitating) )*({'|'.join(map(re.escape, MENTAL))})\b", group(MENTAL)),
    rule("mental_condition", rf"\bmy (?:own )?({'|'.join(map(re.escape, MENTAL))})(?! (?:friend|kid|son|daughter|brother|sister|partner|husband|wife|mom|dad)\b)\b", group(MENTAL)),
    rule("mental_condition", rf"(?:^|[.!?,;(] *)(?:an? )?(?:fellow )?({'|'.join(map(re.escape, MENTAL))}) (?:here|person here|haver here|sufferer here)\b", group(MENTAL), SELF_HEDGE),
    rule("physical_condition", rf"\b(?:i have|i've had|i was diagnosed with|i got diagnosed with|i've been diagnosed with|i'm diagnosed with|i suffer from|i struggle with|i deal with|i live with|i've got|as someone with|as a person with|i was recently diagnosed with|i'm being treated for)\s+(?:(?:severe|mild|moderate|chronic|stage \w+|diagnosed|really bad|pretty bad|bad|terrible|crazy|debilitating|a mild|a severe|an autoimmune disease called) )*({'|'.join(map(re.escape, PHYSICAL))})\b", group(PHYSICAL)),
    rule("physical_condition", rf"\bmy (?:own )?({'|'.join(map(re.escape, PHYSICAL))})(?! (?:friend|kid|son|daughter|brother|sister|partner|husband|wife|mom|dad|medication)\b)\b", group(PHYSICAL)),
    rule("physical_condition", rf"(?:^|[.!?,;(] *)(?:an? )?(?:fellow )?({'|'.join(map(re.escape, PHYSICAL))}) (?:here|sufferer here|patient here)\b", group(PHYSICAL), SELF_HEDGE),
    rule("mental_condition", rf"\bi (?:have|had|got|suffer from|struggle with|deal with|live with|was diagnosed with|got diagnosed with|have been diagnosed with|'ve been diagnosed with|'ve been dealing with|'ve been struggling with|am dealing with|'m dealing with|battle|fight|manage)\s+(?:\w+\s+){{0,3}}?({'|'.join(map(re.escape, MENTAL))})\b", group(MENTAL)),
    rule("mental_condition", r"\b(?:i'm|im|i am|i get|i got|i feel) (?:so |really |very |pretty |super |kinda |a (?:rather |very |really )?)?(anxious|depressed|suicidal|manic|psychotic|paranoid)(?: person)?\b",
         group({"anxious": "anxiety", "depressed": "depression", "suicidal": "depression", "manic": "bipolar disorder", "psychotic": "schizophrenia or psychosis", "paranoid": "anxiety"}), SELF_HEDGE),
    rule("mental_condition", r"\b(?:my|i take|i'm on|i am on|i started|on|gave me|prescribed me|i need) (?:\w+ )?(sertraline|zoloft|lexapro|escitalopram|ecsitalopram|citalopram|prozac|fluoxetine|wellbutrin|bupropion|effexor|venlafaxine|cymbalta|duloxetine|paxil|buspirone|buspar|lithium|lamictal|lamotrigine|seroquel|quetiapine|abilify|risperidone|adderall|vyvanse|vyvance|ritalin|concerta|methylphenidate|strattera|xanax|klonopin|ativan|antidepressants|ssris?|stimulants|antipsychotics|mood stabilizers?)\b",
         group({"sertraline": "depression", "zoloft": "depression", "lexapro": "anxiety", "escitalopram": "anxiety", "ecsitalopram": "anxiety", "citalopram": "depression", "prozac": "depression", "fluoxetine": "depression",
                "wellbutrin": "depression", "bupropion": "depression", "effexor": "depression", "venlafaxine": "depression", "cymbalta": "depression", "duloxetine": "depression", "paxil": "anxiety",
                "buspirone": "anxiety", "buspar": "anxiety", "lithium": "bipolar disorder", "lamictal": "bipolar disorder", "lamotrigine": "bipolar disorder", "seroquel": "bipolar disorder",
                "quetiapine": "bipolar disorder", "abilify": "schizophrenia or psychosis", "risperidone": "schizophrenia or psychosis", "adderall": "adhd", "vyvanse": "adhd", "ritalin": "adhd",
                "concerta": "adhd", "vyvance": "adhd", "methylphenidate": "adhd", "strattera": "adhd", "xanax": "anxiety", "klonopin": "anxiety", "ativan": "anxiety", "antidepressants": "depression",
                "ssri": "depression", "ssris": "depression", "stimulants": "adhd", "antipsychotics": "schizophrenia or psychosis", "mood stabilizer": "bipolar disorder", "mood stabilizers": "bipolar disorder"}), SELF_HEDGE),
    rule("mental_condition", rf"(?:^|[\s,(])(adhd|autism|autistic|ocd|ptsd|bpd|anxiety|depression|bipolar)(?:er)? (?:here|brain|person here|gang|squad|club)\b|\bas (?:an? )?(?:fellow )?(adhd|autistic|ocd|ptsd|bpd|bipolar|anxious|depressed) (?:person|woman|man|adult|guy|girl|individual|sufferer|haver)\b",
         lambda match: MENTAL.get(match.group(1) or match.group(2)) or {"anxious": "anxiety", "depressed": "depression"}.get(match.group(1) or match.group(2)), SELF_HEDGE),
    rule("physical_condition", rf"\bi (?:have|had|got|suffer from|struggle with|deal with|live with|was diagnosed with|got diagnosed with|have been diagnosed with|'ve been diagnosed with|'ve been dealing with|am dealing with|'m dealing with|was born with|battle|fight|manage)\s+(?:\w+\s+){{0,3}}?({'|'.join(map(re.escape, PHYSICAL))})\b", group(PHYSICAL)),
    rule("physical_condition", rf"\b(?:i'm|im|i am) (?:\w+ )?({'|'.join(map(re.escape, (name for name, (field, _) in STATES_OF.items() if field == 'physical_condition')))})\b(?! (?:people|person|friend|community|rights)\b)", lambda match: STATES_OF[match.group(1)][1], SELF_HEDGE),
    rule("mental_condition", rf"\b(?:i'm|im|i am) (?:\w+ )?({'|'.join(map(re.escape, (name for name, (field, _) in STATES_OF.items() if field == 'mental_condition')))})\b(?! (?:people|person|friend|community|rights|kids?|son|daughter)\b)", lambda match: STATES_OF[match.group(1)][1], SELF_HEDGE),
    rule("physical_condition", r"\bmy (?:\w+ )?(inhaler|epipen|insulin|metformin|chemo|chemotherapy|radiation|dialysis|levothyroxine|thyroid|hearing aids?|wheelchair|cane|crutches|migraines?|seizures?|back pain|arthritis|ibs|gerd|reflux|tumor|tumour)\b",
         group({"inhaler": "respiratory condition or allergy", "epipen": "respiratory condition or allergy", "insulin": "diabetes", "metformin": "diabetes", "chemo": "cancer", "chemotherapy": "cancer",
                "radiation": "cancer", "dialysis": "other physical condition", "levothyroxine": "hormonal or reproductive condition", "thyroid": "hormonal or reproductive condition",
                "period": "hormonal or reproductive condition", "periods": "hormonal or reproductive condition", "cycle": "hormonal or reproductive condition", "hearing aid": "vision or hearing impairment",
                "hearing aids": "vision or hearing impairment", "wheelchair": "physical disability", "cane": "physical disability", "crutches": "other physical condition", "migraine": "neurological condition",
                "migraines": "neurological condition", "seizure": "neurological condition", "seizures": "neurological condition", "knee": "other physical condition", "back pain": "chronic pain or fibromyalgia",
                "arthritis": "other physical condition", "endo": "hormonal or reproductive condition", "ibs": "digestive condition", "gerd": "digestive condition", "reflux": "digestive condition",
                "tumor": "cancer", "tumour": "cancer"}), SELF_HEDGE),
    rule("physical_condition", r"\bi (?:also |still |now |have to )?(?:wear|need|use) (?:hearing aids?|a wheelchair|a cane|an inhaler)\b|\bi'?m (?:legally )?(?:deaf|blind|hard of hearing)\b|\bi (?:was )?born without\b",
         lambda match: "physical disability" if "wheelchair" in match.group() or "cane" in match.group() or "without" in match.group() else "respiratory condition or allergy" if "inhaler" in match.group() else "vision or hearing impairment", SELF_HEDGE),
    rule("physical_condition", rf"(?:^|[\s,(])(t1d|t2d|t1|t2|type 1|type 2|diabetic|pcos|endo|celiac|coeliac|ibs|crohnie|spoonie|fibro|eds|pots|me/cfs) (?:here|warrior|gang|squad|life)\b", group({"t1d": "diabetes", "t2d": "diabetes", "t1": "diabetes", "t2": "diabetes", "type 1": "diabetes", "type 2": "diabetes", "diabetic": "diabetes", "pcos": "hormonal or reproductive condition", "endo": "hormonal or reproductive condition", "celiac": "digestive condition", "coeliac": "digestive condition", "ibs": "digestive condition", "crohnie": "digestive condition", "spoonie": "chronic pain or fibromyalgia", "fibro": "chronic pain or fibromyalgia", "eds": "other physical condition", "pots": "heart or blood condition", "me/cfs": "other physical condition"}), SELF_HEDGE),
    rule("mental_condition", r"\b(audhd|au/dhd)\b", fixed("both adhd and autism"), SELF_HEDGE),
    rule("mental_condition", rf"\bmy (?:\w+ ){{0,2}}?({'|'.join(map(re.escape, MENTAL))})\b(?! (?:friend|kid|son|daughter|brother|sister|partner|husband|wife|mom|dad|medication|meds)\b)|\b(?:recovering|recovered) from (?:my )?({'|'.join(map(re.escape, MENTAL))})\b|\b(?:undiagnosed|unmedicated|untreated|diagnosed|severe|crippling|chronic) (?:but severe )?({'|'.join(map(re.escape, MENTAL))})\b(?=[^.!?]*\b(?:i|my|me)\b)|^\W*(?:yep\W+|yeah\W+|also\W+)?({'|'.join(map(re.escape, MENTAL))})\W*$|\balso,? ({'|'.join(map(re.escape, MENTAL))})\b",
         lambda match: MENTAL[next(filter(None, match.groups()))], SELF_HEDGE),
    rule("mental_condition", r"\b(?:made|makes|making|left) me (?:really |so |very |super )?(depressed|anxious|suicidal)\b|\bi(?:'m| am) (?:feeling|getting) (?:really |so |very )?(anxious|depressed|suicidal)\b|\b(?:becoming|became|become) an (alcoholic|addict)\b|\bi(?:'m| am) (?:a |an )?(?:recovering |former )?(alcoholic|addict)\b|\bas a (suicidal)\b|\b(?:i have|i've got|i struggle with|someone who (?:also )?has) (body dysmorphia|bdd|insomnia|bulimia|anorexia|binge eating)\b",
         lambda match: {"depressed": "depression", "anxious": "anxiety", "suicidal": "other mental health condition", "alcoholic": "addiction", "addict": "addiction", "body dysmorphia": "other mental health condition",
                        "bdd": "other mental health condition", "insomnia": "other mental health condition", "bulimia": "eating disorder", "anorexia": "eating disorder", "binge eating": "eating disorder"}[next(filter(None, match.groups()))], SELF_HEDGE),
    rule("mental_condition", r"\b(adhd|autism|autistic|asd) (?:brain|makes my|affects my|ruins my|means i)\b|\bmy (?:adhd|autism) (?:brain|meds|medication|diagnosis)\b|\bfor my (adhd|autism|anxiety|depression|ocd|ptsd)\b",
         lambda match: MENTAL[next(filter(None, match.groups()), "adhd") if (match.group(1) or match.group(2)) else re.search(r"adhd|autism|anxiety|depression|ocd|ptsd", match.group()).group()], SELF_HEDGE),
    rule("mental_condition", r"\b(?:i'm|im|i am|i m) (?:literally |also |very |severely |pretty )?(dyslexic|dyspraxic|neurodivergent|neurodiverse|nd|on the spectrum)\b", lambda match: "autism" if "spectrum" in match.group() else "neurodivergent, unspecified", SELF_HEDGE),
]
FIRST_PERSON = re.compile(r"\b(?:i|i'm|im|i've|i'd|my|me|mine|we|our|us)\b")
AILMENTS = {**PHYSICAL, "crohn's disease": "digestive condition", "celiacs": "digestive condition", "hiatal hernia": "digestive condition", "fibroids": "hormonal or reproductive condition",
            "adenomyosis": "hormonal or reproductive condition", "perimenopause": "hormonal or reproductive condition", "pmos": "hormonal or reproductive condition", "my hormones": "hormonal or reproductive condition",
            "osteoarthritis": "other physical condition", "rheumatoid disease": "autoimmune disease", "hyperparathyroidism": "other physical condition", "chronic fatigue": "other physical condition",
            "dry skin": "skin condition", "sensitive skin": "skin condition", "cystic acne": "skin condition", "iritis": "vision or hearing impairment", "dry eye": "vision or hearing impairment",
            "sensitive ears": "vision or hearing impairment", "hearing aids": "vision or hearing impairment", "dialysis": "other physical condition", "colostomy": "other physical condition",
            "scoliosis": "other physical condition", "sciatica": "chronic pain or fibromyalgia", "herniated disc": "chronic pain or fibromyalgia", "kidney stones": "other physical condition",
            "hypoglycemic": "diabetes", "diabetic": "diabetes", "shattered ankle": "other physical condition", "broken ankle": "other physical condition", "torn acl": "other physical condition",
            "genetic eye disease": "vision or hearing impairment", "eye disease": "vision or hearing impairment", "migraine": "neurological condition"}
AILMENT_NAMES = re.compile(r"\b(" + "|".join(sorted(map(re.escape, AILMENTS), key=len, reverse=True)) + r")\b")
OTHER_PEOPLE = re.compile(r"\b(?:mom|mother|dad|father|wife|husband|son|daughter|friend|brother|sister|grandma|grandpa|grandmother|grandfather|aunt|uncle|cousin|boyfriend|girlfriend|partner|he|she|his|her|him|they|their|dog|cat|patient|client)\b")


def ailments(lowered, found):
    for sentence in re.finditer(r"[^.!?\n]+", lowered):
        part = sentence.group()
        if not FIRST_PERSON.search(part) or OTHER_PEOPLE.search(part) or HEDGE.search(part):
            continue
        for match in AILMENT_NAMES.finditer(part):
            found.setdefault(("physical_condition", AILMENTS[match.group(1)]), sentence.start() + match.start())
