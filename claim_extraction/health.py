import re
from pathlib import Path

from .common import HEDGE, SELF_HEDGE, TAGGED, fixed, group, rule


def names(table):
    return "|".join(sorted(map(re.escape, table), key=len, reverse=True))


def spread(groups):
    return {name: value for value, items in groups.items() for name in items}


PEOPLE = (r"mom|mother|mum|mommy|dad|father|daddy|wife|husband|son|daughter|kid|kids|child|children|baby|toddler|friend|friends|bestie|brother|sister|sibling|siblings|grandma|grandpa|"
          r"grandmother|grandfather|granny|nana|aunt|auntie|uncle|cousin|niece|nephew|boyfriend|girlfriend|bf|gf|partner|spouse|fiance|fiancee|fiancé|ex|roommate|coworker|boss|"
          r"he|she|his|her|him|they|their|them|dog|cat|puppy|kitten|pet|patient|client|patients|clients|student|students|parent|parents|family|people|everyone|nobody|someone's|"
          r"guy|girl|lady|man|woman|men|women|teacher|doctor|neighbor|neighbour|grandson|granddaughter|stepdad|stepmom|in-law|sil|bil|mil|fil|dh|dw|ds|dd|op|op's|u|you|your|you're|ur")
OWN_HEDGE = re.compile(SELF_HEDGE.pattern + r"|\b(?:suspect|suspected|probably|possibly|wonder|wondering|could be|could have|do i have|self[- ]diagnosed|test(?:ed)? for|screen(?:ed)? for|rule out|ruled out|i think|i thought|i guess|i feel like|pretty sure|i believe)\b")
OTHERS = re.compile(OWN_HEDGE.pattern + rf"|\b(?:{PEOPLE})\b")
GAP = rf"(?:(?!(?:{PEOPLE}|not|no|never|and|but|or|if|when|because|so|that|who|which|what|where|than|to)\b)[\w'/-]+,?\s+){{0,3}}?"
SUBJECT = r"\bi (?:also |still |do |actually |now |already |too |even |definitely |literally |personally |unfortunately |both |currently |recently |just |really |apparently |obviously |basically |technically |myself |officially |finally |eventually |later |since |unfortunately also )*"
HAVE_NOW = (rf"{SUBJECT}(?:have|got|get|suffer from|suffer with|struggle with|deal with|live with|battle|fight|manage|was born with|developed|contracted|have been diagnosed with|got diagnosed with|"
            r"was (?:also |recently |officially |formally |finally |just |eventually |later |then |initially |first |since )?diagnosed with|have had|have got|am diagnosed with|am being treated for|"
            r"am recovering from|am dealing with|am struggling with|am living with|am suffering from|am suffering with|am battling|am fighting)"
            r"|\b(?:i've|ive|i have) (?:also |always |recently |just |finally |officially |since |now |personally |actually |unfortunately |literally |basically |definitely |still |apparently |technically |long )*(?:had|got|been diagnosed with|been dealing with|been struggling with|been battling|been fighting|been living with|"
            r"been suffering from|been suffering with|been treated for|been recovering from|developed|struggled with|dealt with|suffered from|suffered with|lived with|battled|fought|survived|beaten)"
            r"|\b(?:i'm|im|i am) (?:also |currently |still |now |actually |officially |finally |recently |just |newly |personally |technically |literally |basically |definitely |unfortunately |apparently )*(?:diagnosed with|dealing with|struggling with|living with|suffering from|suffering with|being treated for|recovering from|"
            r"battling|fighting|on meds for|on medication for|in treatment for|in remission from|getting treated for|managing|medicated for|surviving|a survivor of)"
            r"|\bi (?:take|took|need|use|used) (?:meds|medication|medications|medicine|pills|something|treatment|a prescription|an rx) for|\b(?:as |i'm |im |i am )(?:someone|(?:an? )(?:[\w-]+ ){0,2}?(?:person|guy|girl|woman|man|adult|lady|female|male|mom|mum|dad|mother|father|wife|husband|teen|kid|student|individual|dude|gal)) (?:who (?:also |still |too )?(?:has|has had|suffers from|struggles with|lives with|deals with)|living with|with)"
            r"|\bmy (?:diagnosis|diagnoses|dx|dxs) (?:is|are|of|was|were|include|includes)\b|\bdiagnosed me (?:with|as)")
HAVE = HAVE_NOW + rf"|{SUBJECT}(?:had|suffered from|struggled with|dealt with|lived with|battled|fought|beat|survived|overcame|was treated for|was dealing with|went through|got treated for)"
BARE = r"(?:^|[.!?\n|]\s*)(?:recently |newly |just |finally |officially |formally |also |and |got |was |been )*(?:diagnosed|dx'?d) (?:with|w/)"
MODIFIERS = (r"own|severe|mild|moderate|chronic|acute|stupid|damn|damned|fucking|freaking|bloody|bad|untreated|undiagnosed|diagnosed|recent|current|constant|occasional|lifelong|genetic|congenital|"
             r"hereditary|early|late|new|old|primary|secondary|crippling|debilitating|terrible|horrible|awful|pretty bad|really bad|annoying|lovely|wonderful|recurring|recurrent|persistent|ongoing|"
             r"rare|treatment[- ]resistant|clinical|major|severe chronic|medicated|unmedicated|managed|controlled|uncontrolled|diet[- ]controlled|stage \w+|grade \w+|type \w+|level \w+|chronic severe|"
             r"intermittent|episodic|silent|mild case of|bit of|bit of an?|little|minor|slight|full blown|full-blown|high[- ]functioning|combined[- ]type|inattentive[- ]type|hyperactive[- ]type|"
             r"inattentive|combined|hyperactive|textbook|diagnosed severe|late[- ]diagnosed|adult|childhood|postpartum|seasonal|crazy|insane|massive|huge|lingering|residual|newly diagnosed|"
             r"some|a lot of|lots of|serious|really|very|super|extreme|extremely|both|mostly|mainly|also")
MOD = rf"(?:(?:{MODIFIERS})[\s,]+){{0,3}}"
FOLLOWERS = r"(?! (?:friend|friends|kid|kids|son|daughter|brother|sister|partner|husband|wife|mom|dad|mother|father|patient|patients|client|clients|community|people|person|research|awareness|month|day|walk|charity|foundation|society|association|group|subreddit|sub|forum)s?\b)"


PHYSICAL = spread({
    "diabetes": ["diabetes", "type 1 diabetes", "type 2 diabetes", "type one diabetes", "type two diabetes", "type i diabetes", "type ii diabetes", "t1d", "t2d", "t1dm", "t2dm", "prediabetes", "pre-diabetes",
                 "gestational diabetes", "insulin resistance", "hypoglycemia", "reactive hypoglycemia", "diabetic neuropathy", "diabetic retinopathy", "diabetic ketoacidosis",
                 "juvenile diabetes", "sugar diabetes", "type 1.5 diabetes", "insulin dependent diabetes", "hypoglycemic", "diabetic"],
    "autoimmune disease": ["lupus", "sle", "systemic lupus", "rheumatoid arthritis", "multiple sclerosis", "relapsing remitting ms", "rrms", "hashimoto's", "hashimotos", "hashimoto", "hashimoto's thyroiditis",
                           "hashimoto's disease", "graves disease", "graves' disease", "grave's disease", "graves", "psoriatic arthritis", "ankylosing spondylitis", "axial spondyloarthritis",
                           "spondyloarthritis", "sjogren's", "sjogrens", "sjögren's", "sjogren's syndrome", "sjögren's syndrome", "scleroderma", "systemic sclerosis", "vasculitis", "myasthenia gravis",
                           "addison's disease", "addison's", "addisons", "autoimmune hepatitis", "an autoimmune disease", "an autoimmune disorder", "autoimmune disease", "autoimmune disorder",
                           "an autoimmune condition", "autoimmune condition", "autoimmune issues", "autoimmune diseases", "autoimmune disorders", "sarcoidosis", "sarcoid", "behcet's", "behcets", "dermatomyositis", "polymyositis",
                           "guillain-barre", "guillain barre", "guillain-barré", "mixed connective tissue disease", "undifferentiated connective tissue disease", "uctd", "mctd", "antiphospholipid syndrome",
                           "pernicious anemia", "juvenile arthritis", "juvenile idiopathic arthritis", "polymyalgia rheumatica", "rheumatoid disease", "autoimmune", "primary biliary cholangitis", "psc",
                           "primary sclerosing cholangitis", "autoimmune thyroiditis", "autoimmune thyroid disease", "nmosd", "neuromyelitis optica", "cidp", "stiff person syndrome", "still's disease",
                           "connective tissue disease", "a connective tissue disorder", "connective tissue disorder"],
    "chronic pain or fibromyalgia": ["chronic pain", "fibromyalgia", "fibro", "chronic back pain", "back pain", "chronic back problems", "back problems", "back issues", "chronic neck pain", "neck pain",
                                     "joint pain", "chronic joint pain", "sciatica", "herniated disc", "herniated discs", "bulging disc", "bulging discs", "slipped disc", "a slipped disc", "degenerative disc disease",
                                     "crps", "complex regional pain syndrome", "costochondritis", "tmj", "tmd", "chronic pelvic pain", "pelvic pain", "vulvodynia", "chronic headaches",
                                     "daily headaches", "nerve pain", "spinal stenosis", "myofascial pain syndrome", "chronic knee pain", "knee pain", "hip pain", "chronic hip pain", "shoulder pain",
                                     "lower back pain", "chronic lower back pain", "a herniated disc", "a bulging disc", "a ruptured disc", "ruptured disc", "chronic pain syndrome", "central sensitization",
                                     "pudendal neuralgia", "chronic muscle pain", "widespread pain", "constant pain", "chronic pain condition", "a chronic pain condition"],
    "cancer": ["cancer", "breast cancer", "prostate cancer", "lung cancer", "colon cancer", "colorectal cancer", "rectal cancer", "skin cancer", "thyroid cancer", "ovarian cancer", "cervical cancer",
               "uterine cancer", "endometrial cancer", "pancreatic cancer", "liver cancer", "kidney cancer", "bladder cancer", "stomach cancer", "esophageal cancer", "testicular cancer", "brain cancer",
               "bone cancer", "blood cancer", "throat cancer", "oral cancer", "tongue cancer", "head and neck cancer", "bowel cancer", "anal cancer", "gallbladder cancer", "bile duct cancer", "leukemia",
               "leukaemia", "aml", "cll", "cml", "lymphoma", "hodgkin's lymphoma", "hodgkins lymphoma", "hodgkin lymphoma", "hodgkin's", "hodgkins", "non-hodgkin's lymphoma", "non-hodgkin lymphoma",
               "melanoma", "carcinoma", "basal cell carcinoma", "squamous cell carcinoma", "ductal carcinoma", "sarcoma", "osteosarcoma", "ewing's sarcoma", "ewing sarcoma", "myeloma",
               "multiple myeloma", "glioblastoma", "glioma", "astrocytoma", "oligodendroglioma", "a brain tumor", "brain tumor", "a brain tumour", "brain tumour", "a tumor", "a tumour", "tumor", "tumour",
               "mesothelioma", "neuroblastoma", "metastatic cancer", "metastatic breast cancer", "stage 4 cancer", "stage iv cancer", "dcis", "tnbc", "triple negative breast cancer", "cholangiocarcinoma",
               "a malignant tumor", "malignancy", "a malignancy", "a rare cancer", "terminal cancer", "hpv positive cancer", "seminoma", "a seminoma",
               "myelodysplastic syndrome", "thymoma", "medulloblastoma", "retinoblastoma", "wilms tumor", "kaposi sarcoma", "a cancer diagnosis"],
    "heart or blood condition": ["a heart condition", "heart condition", "heart disease", "heart problems", "heart issues", "heart failure", "congestive heart failure", "chf", "arrhythmia", "an arrhythmia",
                                 "arrhythmias", "afib", "a-fib", "atrial fibrillation", "atrial flutter", "tachycardia", "svt", "bradycardia", "long qt",
                                 "long qt syndrome", "wpw", "wolff-parkinson-white", "hypertension", "high blood pressure", "low blood pressure", "hypotension", "orthostatic hypotension", "high cholesterol",
                                 "hyperlipidemia", "familial hypercholesterolemia", "a heart murmur", "heart murmur", "mitral valve prolapse", "cardiomyopathy", "hypertrophic cardiomyopathy", "hcm",
                                 "coronary artery disease", "a heart attack", "heart attack", "heart attacks", "angina", "anemia", "anaemia", "iron deficiency anemia", "iron deficiency anaemia", "iron deficiency",
                                 "sickle cell", "sickle cell disease", "sickle cell anemia", "hemophilia", "haemophilia", "thalassemia", "thalassaemia", "von willebrand", "von willebrand disease",
                                 "a blood clotting disorder", "blood clotting disorder", "a clotting disorder", "clotting disorder", "blood clots", "a blood clot", "dvt", "a dvt", "pulmonary embolism",
                                 "a pulmonary embolism", "pulmonary embolisms", "factor v leiden", "a pacemaker", "palpitations", "heart palpitations", "an aneurysm", "aneurysm", "an aortic aneurysm",
                                 "raynaud's", "raynauds", "raynaud's syndrome", "raynaud's disease", "itp", "hemochromatosis", "haemochromatosis", "polycythemia", "polycythemia vera", "a bleeding disorder",
                                 "bleeding disorder", "congenital heart defect", "a congenital heart defect", "a congenital heart disease", "congenital heart disease", "a hole in my heart", "peripheral artery disease",
                                 "vasovagal syncope", "inappropriate sinus tachycardia", "heart arrhythmia", "an irregular heartbeat", "irregular heartbeat", "low iron", "a heart defect", "heart defect",
                                 "pulmonary hypertension", "an enlarged heart", "enlarged heart", "a leaky valve", "a bicuspid aortic valve", "bicuspid aortic valve", "aortic stenosis", "endocarditis",
                                 "myocarditis", "pericarditis", "a stent", "stents", "a triple bypass", "heart surgery", "open heart surgery", "a heart transplant", "heart valve disease", "mthfr",
                                 "a heart block", "heart block", "ectopic beats", "a blood disorder", "blood disorder", "neutropenia", "thrombocytopenia", "low platelets", "leukopenia",
                                 "a low white blood cell count", "atherosclerosis", "vascular disease", "varicose veins", "a stroke risk", "high bp", "low bp", "elevated blood pressure"],
    "digestive condition": ["ibs", "ibs-c", "ibs-d", "ibs-m", "irritable bowel syndrome", "ibd", "inflammatory bowel disease", "crohn's", "crohns", "crohn's disease", "crohns disease", "crohn", "ulcerative colitis",
                            "colitis", "microscopic colitis", "celiac", "celiac disease", "coeliac", "coeliac disease", "celiacs", "celiac's", "gastritis", "chronic gastritis", "gerd", "acid reflux", "reflux",
                            "silent reflux", "gastroparesis", "diverticulitis", "diverticulosis", "sibo", "sifo", "a hiatal hernia", "hiatal hernia", "hiatus hernia", "a hiatus hernia", "an ulcer",
                            "ulcers", "stomach ulcer", "stomach ulcers", "a stomach ulcer", "peptic ulcer", "a peptic ulcer", "pancreatitis", "chronic pancreatitis", "exocrine pancreatic insufficiency",
                            "gallstones", "gallbladder issues", "gallbladder disease", "gallbladder problems", "fatty liver", "fatty liver disease", "nafld", "nash", "masld", "cirrhosis", "liver disease",
                            "hepatitis", "hepatitis b", "hepatitis c", "hep c", "hep b", "lactose intolerance", "gluten intolerance", "gluten sensitivity", "non-celiac gluten sensitivity", "eoe",
                            "eosinophilic esophagitis", "esophagitis", "barrett's esophagus", "barretts esophagus", "hemorrhoids", "haemorrhoids", "piles", "chronic constipation", "anal fissure",
                            "an anal fissure", "a fissure", "fissures", "a fistula", "an anal fistula", "ostomy", "an ostomy", "ileostomy", "an ileostomy", "j-pouch", "a j-pouch", "short bowel syndrome",
                            "digestive issues", "stomach issues", "stomach problems", "gut issues", "gut problems", "digestive problems", "bile acid malabsorption", "pancreatic insufficiency",
                            "cyclic vomiting syndrome", "chronic nausea", "achalasia", "food intolerances", "a food intolerance", "histamine intolerance", "fructose malabsorption", "fructose intolerance",
                            "h. pylori", "h pylori", "dumping syndrome", "functional dyspepsia", "dyspepsia", "bowel issues", "bowel problems", "a sensitive stomach", "sensitive stomach", "a weak stomach",
                            "chronic diarrhea", "leaky gut", "candida overgrowth", "gastric issues", "digestive disorder", "a digestive disorder", "pelvic floor dysfunction", "a colostomy", "lactose malabsorption",
                            "biliary colic", "no gallbladder", "a liver condition", "gilbert's syndrome", "gilberts syndrome", "gilbert's", "hirschsprung's", "a bowel obstruction", "hiatal hernias"],
    "hormonal or reproductive condition": ["pcos", "polycystic ovary syndrome", "polycystic ovarian syndrome", "polycystic ovaries", "endometriosis", "adenomyosis", "fibroids", "uterine fibroids", "a fibroid",
                                           "ovarian cysts", "an ovarian cyst", "hypothyroidism", "hyperthyroidism", "hypothyroid", "hyperthyroid", "thyroid disease", "a thyroid condition", "thyroid condition",
                                           "thyroid issues", "thyroid problems", "an underactive thyroid", "underactive thyroid", "an overactive thyroid", "overactive thyroid", "thyroid nodules", "a thyroid nodule",
                                           "goiter", "a goiter", "menopause", "perimenopause", "peri-menopause", "peri menopause", "early menopause", "surgical menopause", "premature menopause",
                                           "premature ovarian failure", "premature ovarian insufficiency", "pmdd", "infertility", "infertility issues", "fertility issues", "fertility problems", "low testosterone",
                                           "low t", "hypogonadism", "klinefelter", "klinefelter syndrome", "klinefelter's", "turner syndrome", "turner's syndrome", "hormone imbalance", "a hormone imbalance",
                                           "hormonal imbalance", "a hormonal imbalance", "hormonal imbalances", "adrenal insufficiency", "adrenal fatigue", "cushing's", "cushings", "cushing's syndrome", "cushing's disease",
                                           "hyperprolactinemia", "a prolactinoma", "prolactinoma", "a pituitary tumor", "pituitary tumor", "a pituitary adenoma", "erectile dysfunction", "bph", "an enlarged prostate",
                                           "enlarged prostate", "prostatitis", "vaginismus", "recurrent miscarriages", "recurrent pregnancy loss", "secondary infertility", "male infertility", "low sperm count",
                                           "a low sperm count", "irregular periods", "heavy periods", "amenorrhea", "hypothalamic amenorrhea", "my hormones", "diabetes insipidus", "hypoparathyroidism",
                                           "an endocrine disorder", "endocrine disorder", "hashimoto's hypothyroidism", "a thyroidectomy", "no thyroid", "thyroid cancer survivor", "estrogen dominance", "low estrogen",
                                           "high prolactin", "high testosterone", "hirsutism", "pcod", "uterine polyps", "endometrial hyperplasia", "a septate uterus", "a bicornuate uterus", "an incompetent cervix",
                                           "low progesterone", "luteal phase defect", "hyperemesis", "hyperemesis gravidarum", "preeclampsia", "pre-eclampsia", "gestational hypertension", "a hysterectomy",
                                           "ovarian failure", "acromegaly", "growth hormone deficiency", "congenital adrenal hyperplasia", "intersex condition", "a hormonal disorder", "hormonal disorder",
                                           "hormonal issues", "hormone issues", "hormone problems", "low libido", "peyronie's", "peyronies", "peyronie's disease", "varicocele", "a varicocele", "hypospadias",
                                           "an undescended testicle", "phimosis", "endometrioma", "an endometrioma", "chocolate cysts", "a retroverted uterus", "a tilted uterus", "pelvic inflammatory disease"],
    "neurological condition": ["epilepsy", "seizures", "seizure disorder", "a seizure disorder", "migraines", "migraine", "chronic migraines", "chronic migraine", "migraine with aura", "migraines with aura",
                               "ocular migraines", "vestibular migraines", "vestibular migraine", "hemiplegic migraines", "cluster headaches", "parkinson's", "parkinsons", "parkinson's disease", "parkinsons disease",
                               "als", "huntington's", "huntingtons", "huntington's disease", "neuropathy", "peripheral neuropathy", "small fiber neuropathy", "narcolepsy", "idiopathic hypersomnia", "hypersomnia",
                               "essential tremor", "a tremor", "tremors", "a stroke", "strokes", "a mini stroke", "a tia", "tbi", "a tbi", "traumatic brain injury", "a traumatic brain injury", "a brain injury",
                               "brain injury", "brain damage", "a concussion", "concussions", "multiple concussions", "post-concussion syndrome", "post concussion syndrome", "vertigo", "chronic vertigo", "bppv",
                               "bell's palsy", "bells palsy", "dystonia", "trigeminal neuralgia", "restless leg syndrome", "restless legs syndrome", "restless legs", "rls", "hydrocephalus", "chiari",
                               "chiari malformation", "dementia", "alzheimer's", "alzheimers", "early onset alzheimer's", "early onset dementia", "fnd", "functional neurological disorder", "neuralgia",
                               "occipital neuralgia", "iih", "idiopathic intracranial hypertension", "intracranial hypertension", "pseudotumor cerebri", "a neurological disorder", "neurological disorder",
                               "a neurological condition", "neurological condition", "neurological issues", "neurological problems", "ataxia", "charcot-marie-tooth", "myoclonus", "nerve damage",
                               "transverse myelitis", "syringomyelia", "a brain aneurysm", "tethered cord", "tethered cord syndrome", "migraine headaches", "tension headaches", "dysautonomia", "pots", "postural orthostatic tachycardia syndrome",
                               "absence seizures", "grand mal seizures", "tonic clonic seizures", "focal seizures", "temporal lobe epilepsy", "juvenile myoclonic epilepsy", "a brain bleed",
                               "brain lesions", "a brain lesion", "white matter lesions", "a cavernoma", "moyamoya", "neurofibromatosis", "nf1", "tuberous sclerosis", "carpal tunnel syndrome",
                               "cubital tunnel", "cubital tunnel syndrome", "a pinched nerve", "pinched nerve", "ulnar neuropathy", "spasticity", "a movement disorder", "movement disorder", "headaches",
                               "chronic daily headache", "new daily persistent headache", "ndph", "pnes", "non-epileptic seizures", "nonepileptic seizures", "a seizure", "febrile seizures", "brain fog",
                               "migraine disorder", "abdominal migraines", "silent migraines", "occipital neuralgia", "a neuromuscular disease", "neuromuscular disease", "mild cognitive impairment"],
    "skin condition": ["eczema", "psoriasis", "acne", "cystic acne", "hormonal acne", "adult acne", "severe acne", "rosacea", "dermatitis", "atopic dermatitis", "contact dermatitis", "seborrheic dermatitis",
                       "perioral dermatitis", "hives", "chronic hives", "urticaria", "chronic urticaria", "chronic idiopathic urticaria", "cold urticaria", "vitiligo",
                       "hidradenitis suppurativa", "hidradenitis", "keratosis pilaris", "melasma", "dry skin", "sensitive skin", "very dry skin", "extremely dry skin", "alopecia", "alopecia areata",
                       "androgenic alopecia", "androgenetic alopecia", "traction alopecia", "lichen planus", "lichen sclerosus", "ichthyosis",
                       "hyperhidrosis", "folliculitis", "dyshidrotic eczema", "pemphigus", "pemphigoid", "bullous pemphigoid", "epidermolysis bullosa", "a skin condition", "skin condition", "a skin disease",
                       "skin disease", "skin issues", "skin problems", "fungal acne", "milia", "scalp psoriasis", "plaque psoriasis", "guttate psoriasis", "inverse psoriasis", "tinea versicolor",
                       "dermatographia", "dermatographism", "chronic itch", "prurigo nodularis", "hyperpigmentation", "acne scars", "acne scarring", "back acne", "bacne", "body acne", "chest acne",
                       "a skin disorder", "skin disorder", "nummular eczema", "seborrheic keratosis", "seb derm", "seborrheic eczema", "dandruff", "severe dandruff", "chronic dandruff", "keloids",
                       "a keloid", "keloid scars", "cold sores", "pityriasis rosea", "molluscum", "warts", "plantar warts", "a fungal infection", "ringworm", "athlete's foot", "jock itch",
                       "eczema herpeticum", "papulopustular rosacea", "ocular rosacea", "pseudofolliculitis barbae", "razor bumps", "ingrown hairs",
                       "keratosis", "actinic keratosis", "photosensitivity", "sun allergy", "polymorphous light eruption", "skin allergies", "a skin allergy", "dermatitis herpetiformis", "morphea",
                       "telogen effluvium", "hair loss", "thinning hair", "male pattern baldness", "a receding hairline", "oily skin", "acne-prone skin", "acne prone skin", "breakouts"],
    "respiratory condition or allergy": ["asthma", "severe asthma", "allergies", "allergy", "an allergy", "severe allergies", "food allergies", "a food allergy", "food allergy", "seasonal allergies",
                                         "hay fever", "hayfever", "copd", "emphysema", "chronic bronchitis", "bronchiectasis", "cystic fibrosis", "pulmonary fibrosis", "ipf", "interstitial lung disease",
                                         "lung disease", "sinusitis", "chronic sinusitis", "chronic sinus infections", "sinus issues", "sinus problems", "nasal polyps", "a deviated septum", "deviated septum",
                                         "a peanut allergy", "peanut allergy", "peanut allergies", "nut allergy", "a nut allergy", "nut allergies", "tree nut allergy", "a tree nut allergy", "shellfish allergy",
                                         "a shellfish allergy", "a gluten allergy", "anaphylaxis", "mcas", "mast cell activation syndrome", "mast cell activation", "alpha-gal", "alpha gal", "alpha-gal syndrome",
                                         "a collapsed lung", "chronic cough", "allergic rhinitis", "rhinitis", "non-allergic rhinitis", "dust allergy", "dust allergies", "a dust allergy", "pollen allergy", "pollen allergies",
                                         "cat allergy", "a cat allergy", "cat allergies", "dog allergy", "a dog allergy", "dog allergies", "pet allergies", "eosinophilic asthma", "exercise induced asthma",
                                         "exercise-induced asthma", "allergic asthma", "reactive airway disease", "vocal cord dysfunction", "lung issues", "lung problems", "breathing problems", "breathing issues",
                                         "a penicillin allergy", "penicillin allergy", "latex allergy", "a latex allergy", "an egg allergy", "egg allergy", "a dairy allergy", "dairy allergy", "a milk allergy",
                                         "milk allergy", "a wheat allergy", "wheat allergy", "a soy allergy", "soy allergy", "a fish allergy", "fish allergy", "a sesame allergy", "sesame allergy", "a bee allergy",
                                         "bee allergy", "a sulfa allergy", "sulfa allergy", "drug allergies", "a drug allergy", "multiple allergies", "environmental allergies", "a lung condition", "lung condition",
                                         "a respiratory condition", "respiratory condition", "respiratory issues", "respiratory problems", "weak lungs", "bad lungs", "sarcoidosis of the lungs", "a1at deficiency",
                                         "alpha-1 antitrypsin deficiency", "alpha-1", "a mold allergy", "mold allergy", "mold allergies", "fragrance allergy", "a fragrance allergy", "a nickel allergy", "nickel allergy",
                                         "eosinophilic", "chronic rhinosinusitis", "sinus infections", "post nasal drip", "tuberculosis", "pleurisy", "aspergillosis", "chronic asthma", "mild asthma", "childhood asthma",
                                         "a pneumothorax", "pneumothorax", "spontaneous pneumothorax", "allergic reactions", "severe allergic reactions", "oral allergy syndrome", "an anaphylactic allergy"],
    "vision or hearing impairment": ["tinnitus", "hearing loss", "deafness", "partial hearing loss", "hearing impairment", "a hearing impairment", "hearing problems", "hearing issues", "single sided deafness",
                                     "single-sided deafness", "glaucoma", "cataracts", "a cataract", "macular degeneration", "retinitis pigmentosa", "keratoconus", "astigmatism", "myopia", "high myopia",
                                     "nearsightedness", "farsightedness", "hyperopia", "color blindness", "colour blindness", "colorblindness", "a lazy eye", "lazy eye", "amblyopia", "strabismus", "nystagmus",
                                     "dry eye", "dry eyes", "dry eye syndrome", "chronic dry eye", "low vision", "vision loss", "vision impairment", "a vision impairment", "a visual impairment", "visual impairment",
                                     "poor eyesight", "bad eyesight", "terrible eyesight", "horrible eyesight", "shit eyesight", "bad vision", "poor vision", "terrible vision", "blindness", "partial blindness",
                                     "a detached retina", "retinal detachment", "uveitis", "iritis", "optic neuritis", "meniere's", "meniere's disease", "menieres", "menieres disease", "hyperacusis",
                                     "auditory processing disorder", "an eye disease", "eye disease", "an eye condition", "eye condition", "eye problems", "eye issues",
                                     "visual snow", "visual snow syndrome", "otosclerosis", "eustachian tube dysfunction", "hearing aids", "a hearing aid", "a cochlear implant", "cochlear implants",
                                     "night blindness", "monocular vision", "one eye", "a prosthetic eye", "a glass eye", "a retinal tear", "diabetic retinopathy", "ptosis", "a droopy eyelid",
                                     "photophobia", "light sensitivity", "presbyopia", "ear damage", "noise induced hearing loss", "high frequency hearing loss", "sensorineural hearing loss", "conductive hearing loss",
                                     "deaf in one ear", "blind in one eye", "a perforated eardrum", "chronic ear infections", "an ear condition", "fuchs dystrophy", "fuchs' dystrophy", "corneal dystrophy", "stargardt",
                                     "stargardt disease", "achromatopsia", "coloboma", "aniridia", "a hearing loss", "hearing damage", "prosopagnosia"],
    "physical disability": ["cerebral palsy", "spina bifida", "muscular dystrophy", "duchenne", "duchenne muscular dystrophy", "spinal muscular atrophy", "dwarfism", "achondroplasia", "a spinal cord injury",
                            "spinal cord injury", "paralysis", "paraplegia", "quadriplegia", "tetraplegia", "a physical disability", "physical disability", "physical disabilities", "a mobility impairment",
                            "mobility issues", "mobility problems", "a limb difference", "limb difference", "an amputation", "amputation", "osteogenesis imperfecta", "brittle bone disease", "arthrogryposis",
                            "clubfoot", "a club foot", "club foot", "hemiplegia", "hemiparesis", "polio", "post-polio syndrome", "a missing limb", "a prosthetic leg", "a prosthetic arm", "a prosthetic",
                            "a prosthesis", "one arm", "one leg", "one hand", "a mobility disability", "a disability", "disabilities", "a physical handicap", "limited mobility", "a wheelchair", "a mobility aid",
                            "mobility aids", "a walker", "a cane", "crutches", "an amputated leg", "an amputated arm", "phocomelia", "a birth defect", "a congenital limb deficiency", "erb's palsy", "brachial plexus injury",
                            "a brachial plexus injury", "a spinal injury", "spinal injury", "a broken back", "a broken neck"],
    "other physical condition": ["eds", "heds", "ehlers-danlos", "ehlers danlos", "ehlers-danlos syndrome", "ehlers danlos syndrome", "hypermobile eds", "hypermobility", "hypermobility syndrome",
                                 "hypermobility spectrum disorder", "joint hypermobility", "marfan", "marfan syndrome", "marfans", "me/cfs", "cfs", "chronic fatigue syndrome", "chronic fatigue",
                                 "myalgic encephalomyelitis", "long covid", "post covid", "post-covid", "arthritis", "osteoarthritis", "osteoporosis", "osteopenia", "gout", "sleep apnea", "sleep apnoea",
                                 "obstructive sleep apnea", "central sleep apnea", "kidney disease", "chronic kidney disease", "ckd", "kidney stones", "a kidney stone", "kidney failure", "renal failure", "pkd",
                                 "polycystic kidney disease", "a kidney transplant", "a liver transplant", "a transplant", "a lung transplant", "dialysis", "scoliosis", "kyphosis", "a hernia", "hernia", "hernias",
                                 "an inguinal hernia", "inguinal hernia", "an umbilical hernia", "umbilical hernia", "a torn acl", "torn acl", "a torn meniscus", "torn meniscus", "a torn rotator cuff",
                                 "torn rotator cuff", "plantar fasciitis", "carpal tunnel", "tendonitis", "tendinitis", "bursitis", "frozen shoulder", "tennis elbow", "golfer's elbow", "lyme disease", "lyme",
                                 "chronic lyme", "hiv", "herpes", "hsv", "hsv-2", "hsv2", "hsv-1", "hsv1", "hpv", "shingles", "epstein-barr", "ebv", "vitamin d deficiency", "b12 deficiency",
                                 "vitamin b12 deficiency", "a vitamin deficiency", "vitamin deficiencies", "interstitial cystitis", "overactive bladder", "incontinence", "urinary incontinence", "a chronic illness",
                                 "chronic illness", "chronic illnesses", "a chronic condition", "chronic conditions", "chronic health issues", "chronic health problems", "health issues", "health problems",
                                 "medical issues", "medical problems", "a medical condition", "medical conditions", "a health condition", "health conditions", "a genetic disorder", "genetic disorder",
                                 "a genetic condition", "a rare disease", "a rare genetic disorder", "a rare condition", "lymphedema", "lipedema", "lipoedema", "hyperparathyroidism", "primary hyperparathyroidism",
                                 "a bad knee", "bad knees", "a bad hip", "bad hips", "a bad back", "bad back", "a bad shoulder", "bad shoulders", "a bad ankle", "bad ankles", "flat feet", "bunions", "a bunion",
                                 "a broken ankle", "broken ankle", "a broken leg", "a broken arm", "a broken wrist", "a broken foot", "broken ribs", "a broken rib",
                                 "a broken hand", "a broken finger", "a broken toe", "a broken collarbone", "a broken nose", "a fractured", "a stress fracture", "stress fractures", "a sprained ankle",
                                 "immunodeficiency", "cvid", "an immune deficiency", "a weak immune system", "a compromised immune system", "a weakened immune system", "degenerative joint disease",
                                 "a joint replacement", "a hip replacement", "a knee replacement", "two hip replacements", "two knee replacements", "pectus excavatum", "kidney issues", "kidney problems",
                                 "bladder issues", "bladder problems", "spondylolisthesis", "spondylosis", "a pilonidal cyst", "pilonidal cyst", "a cyst", "cysts", "a baker's cyst", "a ganglion cyst",
                                 "colostomy", "an ostomy bag", "obesity", "morbid obesity", "lipoma", "lipomas", "a lipoma", "hydronephrosis", "a single kidney", "one kidney",
                                 "nephrotic syndrome", "glomerulonephritis", "iga nephropathy", "kidney damage", "fatty tumors", "a degenerative condition", "a degenerative disease", "muscle weakness",
                                 "costochondritis", "chronic infections", "recurring utis", "recurrent utis", "chronic utis", "frequent utis", "utis", "a uti", "bladder infections", "kidney infections",
                                 "a torn labrum", "torn labrum", "a labral tear", "hip dysplasia", "patellar tendonitis", "runner's knee", "shin splints", "achilles tendonitis", "a torn achilles",
                                 "an achilles rupture", "a ruptured achilles", "osteomyelitis", "a bone disease", "bone disease", "pagets disease", "paget's disease", "fused vertebrae", "a spinal fusion",
                                 "spinal fusion", "rods in my back", "a rod in my back", "metal in my", "a metal plate", "plates and screws", "an autoimmune-like", "mitochondrial disease", "a mitochondrial disorder",
                                 "fabry disease", "gaucher disease", "pompe disease", "wilson's disease", "porphyria", "cystinosis", "a metabolic disorder", "metabolic disorder", "pku", "phenylketonuria",
                                 "g6pd deficiency", "g6pd", "hereditary angioedema", "angioedema"]})
PHYSICAL_STATES = spread({
    "diabetes": ["diabetic", "a diabetic", "type 1", "type 2", "a type 1 diabetic", "a type 2 diabetic", "type 1 diabetic", "type 2 diabetic", "prediabetic", "pre-diabetic", "insulin resistant",
                 "insulin dependent", "t1d", "t2d", "a t1d", "a t1", "a t2", "hypoglycemic"],
    "neurological condition": ["epileptic", "an epileptic", "a migraineur", "a migraine sufferer", "a stroke survivor", "narcoleptic", "a narcoleptic", "concussed"],
    "respiratory condition or allergy": ["asthmatic", "an asthmatic", "allergic", "highly allergic", "severely allergic", "deathly allergic", "very allergic", "an allergy sufferer", "a hay fever sufferer"],
    "vision or hearing impairment": ["deaf", "hard of hearing", "blind", "legally blind", "visually impaired", "hearing impaired", "partially deaf", "partially blind", "colorblind", "color blind",
                                     "colourblind", "colour blind", "nearsighted", "near sighted", "short sighted", "shortsighted", "farsighted", "far sighted", "long sighted", "half deaf", "half blind",
                                     "blind as a bat", "deaf in one ear", "blind in one eye", "red green colorblind", "red-green colorblind", "a deaf person", "a blind person", "hoh", "a cochlear implant user",
                                     "a hearing aid user", "severely nearsighted", "extremely nearsighted", "very nearsighted"],
    "physical disability": ["disabled", "physically disabled", "a wheelchair user", "in a wheelchair", "wheelchair bound", "wheelchair-bound", "an amputee", "a double amputee", "a paraplegic", "paraplegic",
                            "quadriplegic", "a quadriplegic", "tetraplegic", "paralyzed", "paralysed", "paralyzed from the waist down", "a little person", "an ambulatory wheelchair user", "a cane user",
                            "a below knee amputee", "an above knee amputee"],
    "digestive condition": ["celiac", "a celiac", "coeliac", "a coeliac", "lactose intolerant", "gluten intolerant", "gluten sensitive", "a crohnie", "a crohn's patient"],
    "heart or blood condition": ["anemic", "anaemic", "hypertensive", "a heart patient", "a heart attack survivor", "a hemophiliac"],
    "hormonal or reproductive condition": ["hypothyroid", "hyperthyroid", "menopausal", "perimenopausal", "post menopausal", "postmenopausal", "post-menopausal", "infertile", "sterile",
                                           "in menopause", "in perimenopause", "going through menopause", "going through perimenopause"],
    "cancer": ["a cancer survivor", "a breast cancer survivor", "a cancer patient", "a survivor of cancer", "a two time cancer survivor", "a leukemia survivor",
               "a lymphoma survivor"],
    "other physical condition": ["immunocompromised", "immunosuppressed", "immuno-compromised", "hypermobile", "chronically ill", "a spoonie", "hiv positive", "hsv positive", "herpes positive", "obese", "morbidly obese", "a transplant recipient",
                                 "a kidney transplant recipient", "on dialysis", "a dwarf", "arthritic", "chronically sick"]})
PHYSICAL_TOOLS = spread({
    "respiratory condition or allergy": ["inhaler", "inhalers", "rescue inhaler", "nebulizer", "allergist", "pulmonologist", "allergy meds", "allergy medication",
                                         "allergy shots", "allergy pills", "antihistamines",
                                         "asthma meds", "asthma medication", "asthma", "allergies", "allergy", "allergic reactions", "allergic reaction",
                                         "peanut allergy", "nut allergy", "food allergies", "seasonal allergies", "sinuses"],
    "diabetes": ["insulin", "insulin pump", "pump", "cgm", "glucose monitor", "blood sugar", "blood sugars", "a1c",
                 "basal insulin", "bolus", "diabetes", "diabetic supplies", "test strips", "diabetes meds",
                 "glucose levels", "sugar levels", "endocrinologist"],
    "cancer": ["chemo", "chemotherapy", "radiation", "radiation therapy", "radiation treatments", "radiotherapy", "oncologist", "oncology team", "tumor", "tumour", "tumors", "tumours", "mastectomy",
               "double mastectomy", "lumpectomy", "port", "immunotherapy",
               "biopsy results", "cancer", "breast cancer", "prostate cancer", "cancer diagnosis", "cancer treatment", "cancer treatments", "scans", "pet scan", "remission", "metastasis", "mets",
               "lymph nodes", "proton therapy", "brachytherapy", "stem cell transplant", "bone marrow transplant", "infusions",
               "leukemia", "lymphoma", "melanoma", "cancer journey", "cancer battle", "tumor markers", "ct scans", "ostomy"],
    "hormonal or reproductive condition": ["thyroid", "thyroid meds", "thyroid medication", "thyroid levels",
                                           "tsh", "thyroid doctor", "endo", "periods", "period", "cycle", "cycles", "hormones", "hormone levels", "testosterone levels", "estrogen levels", "trt", "testosterone therapy",
                                           "hrt", "ivf", "ivf journey", "ttc journey", "fertility journey", "fertility doctor", "reproductive endocrinologist",
                                           "gynecologist", "gyno", "obgyn", "ob-gyn", "ob", "midwife", "hysterectomy", "endometriosis", "pcos", "fibroids", "adenomyosis", "menopause", "perimenopause",
                                           "hot flashes", "hot flushes", "night sweats", "iud", "birth control", "the pill",
                                           "hypothyroidism", "hyperthyroidism", "thyroid issues", "thyroid problems", "low t", "pmdd"],
    "neurological condition": ["migraine", "migraines", "migraine meds", "migraine medication", "seizure", "seizures", "seizure meds", "neurologist", "epilepsy", "epilepsy meds",
                               "triptans",
                               "neuropathy", "tremor", "tremors", "parkinson's", "ms", "multiple sclerosis", "tbi", "brain injury", "concussion", "vertigo", "headaches", "chronic migraines",
                               "headache", "cluster headaches", "dementia", "narcolepsy", "nerve damage", "vns", "aura", "auras", "eeg", "mri results"],
    "heart or blood condition": ["cardiologist", "heart doctor", "heart meds", "heart medication", "blood pressure", "blood pressure meds", "blood pressure medication", "bp meds", "pacemaker", "defibrillator",
                                 "icd",
                                 "statins", "statin", "blood thinners", "blood thinner",
                                 "iron infusions", "iron infusion", "iron levels", "ferritin",
                                 "hematologist", "heart condition", "heart", "heart rate", "resting heart rate", "afib", "pots", "anemia", "cholesterol", "high blood pressure", "hypertension", "arrhythmia",
                                 "tachycardia", "palpitations", "heart murmur", "heart failure", "heart attack", "stent", "stents", "bypass", "heart surgery", "valve replacement", "ablation", "blood clots",
                                 "blood clot", "dvt", "factor v", "sickle cell", "hemophilia", "b12 shots", "b12 injections"],
    "digestive condition": ["gastroenterologist", "gi doctor", "gi", "ibs", "gerd", "reflux", "acid reflux", "crohn's", "crohns", "colitis", "uc", "celiac", "celiac disease", "gut", "stomach", "digestion",
                            "digestive system", "bowels", "bowel movements", "colonoscopy", "endoscopy",
                            "ppi", "ppis", "colostomy", "ileostomy",
                            "stoma", "j-pouch", "gallbladder removal", "gallbladder surgery", "liver", "liver enzymes", "flare", "flares", "flare ups", "flare-ups", "trigger foods", "fodmap", "low fodmap",
                            "elimination diet", "sibo", "gastroparesis", "ulcer", "ulcers", "hiatal hernia", "eoe", "diverticulitis", "hemorrhoids", "fissure", "fistula", "lactose intolerance",
                            "gluten intolerance", "ibd", "pancreatitis", "pancreas", "fatty liver", "cirrhosis", "hepatitis", "gastritis", "digestive issues", "stomach issues", "stomach problems", "gut issues",
                            "gut health"],
    "skin condition": ["dermatologist", "derm", "eczema", "psoriasis", "acne", "rosacea", "dermatitis", "hives", "skin", "skin condition", "skin issues", "skin problems", "flare ups", "breakouts",
                       "steroid cream", "steroid creams", "topical steroids",
                       "hs", "vitiligo", "alopecia", "hair loss", "scalp", "keratosis pilaris", "melasma", "hyperpigmentation",
                       "dry skin", "sensitive skin", "oily skin", "acne scars", "cystic acne", "hormonal acne", "skin type", "combination skin", "moisture barrier", "skin barrier", "pores", "spots", "scars"],
    "vision or hearing impairment": ["hearing aid", "hearing aids", "cochlear implant", "cochlear implants", "audiologist", "glasses", "contacts", "contact lenses", "scleral lenses",
                                     "prescription", "eye doctor", "ophthalmologist", "optometrist", "retina specialist", "eyes", "eyesight", "vision", "hearing", "tinnitus", "ears", "lasik", "prk",
                                     "cataract surgery", "glaucoma", "eye drops", "eye pressure", "retinas", "retina", "corneas", "cornea", "white cane", "guide dog", "seeing eye dog", "screen reader",
                                     "braille", "magnifier", "dry eye", "dry eyes", "iol", "lenses", "keratoconus", "astigmatism", "myopia", "lazy eye", "colorblindness", "color blindness", "hearing loss",
                                     "deafness", "blindness", "vision loss", "low vision"],
    "physical disability": ["wheelchair", "power chair", "powerchair", "manual chair", "mobility scooter", "scooter", "walker", "rollator", "cane", "canes", "forearm crutches", "crutches", "prosthetic",
                            "prosthetics", "prosthetic leg", "prosthetic arm", "prosthesis", "leg brace", "afos", "afo", "disability", "disabilities", "physical disability", "disability benefits",
                            "disability check", "disability payments", "ssdi", "ssi", "pip", "blue badge", "disabled parking", "handicap placard", "handicap sticker", "disabled badge", "stump", "residual limb",
                            "amputation", "paralysis", "spinal cord injury", "sci", "cp", "cerebral palsy", "spina bifida", "muscular dystrophy", "mobility", "mobility aid", "mobility aids", "service dog",
                            "carer", "caregiver", "pca", "home health aide"],
    "chronic pain or fibromyalgia": ["back pain", "chronic pain", "pain", "pain levels", "pain meds", "pain medication", "pain management", "pain doctor", "pain clinic", "pain specialist", "fibro", "fibromyalgia",
                                     "sciatica", "herniated disc", "herniated discs", "bulging disc", "discs", "spine", "lower back", "neck pain", "joint pain", "nerve pain", "tmj", "jaw pain", "crps",
                                     "nerve blocks", "nerve block", "epidurals", "epidural injections",
                                     "cortisone shots", "cortisone injections", "steroid injections", "spinal cord stimulator", "ablations", "radiofrequency ablation", "flare", "flares", "bad days", "spoons",
                                     "pain flares", "pain days", "physical therapy", "pt", "physio", "physiotherapy", "chiropractor", "chiro"],
    "autoimmune disease": ["rheumatologist", "rheumy", "lupus", "ra", "ms", "ms meds",
                           "steroids", "biologic", "biologics", "immunosuppressants", "immune system", "autoimmune disease", "autoimmune", "ana", "inflammation", "inflammation markers", "crp", "esr",
                           "hashimoto's", "hashimotos", "graves", "sjogren's", "psoriatic arthritis", "rheumatoid arthritis", "ankylosing spondylitis", "as", "flare", "flares", "lesions", "relapses",
                           "relapse", "mri", "infusions", "infusion"],
    "other physical condition": ["dialysis", "kidneys", "kidney", "kidney function", "kidney doctor", "nephrologist", "transplant", "cpap", "cpap machine", "sleep apnea", "knee", "knees",
                                 "bad knee", "bad knees", "hip", "hips", "shoulder", "shoulders", "ankle", "ankles", "wrist", "wrists", "acl", "mcl", "meniscus", "rotator cuff", "achilles", "joints",
                                 "arthritis", "osteoarthritis", "osteoporosis", "gout", "eds", "hypermobility", "me/cfs", "chronic fatigue", "long covid", "chronic illness",
                                 "chronic illnesses", "chronic condition", "chronic conditions", "condition", "conditions", "health condition", "health conditions", "health issues", "health problems",
                                 "medical condition", "medical conditions", "medical issues", "medical history", "illness", "illnesses", "disease", "diseases", "disorder", "diagnosis", "diagnoses",
                                 "symptoms", "symptom", "surgery", "surgeries", "operation", "procedure", "recovery", "injury", "injuries", "scar", "scoliosis", "spinal fusion", "rods", "hardware",
                                 "plates", "screws", "ostomy bag", "catheter", "bladder", "uti", "utis", "lyme", "hiv", "herpes", "hsv", "hpv", "shingles", "immune system", "white blood cells",
                                 "bloodwork", "blood work", "labs", "lab results", "test results", "doctor", "doctors", "specialist", "specialists", "gp", "pcp", "primary care", "primary care doctor",
                                 "primary care physician", "physician", "nurse", "medication", "medications", "meds", "prescriptions", "pills", "supplements", "treatment", "treatments", "therapy", "therapies",
                                 "hospital stay", "hospitalization", "er visit", "er visits", "health", "body", "bones", "muscles", "tendons", "ligaments", "nerves", "lungs", "chest", "fatigue"]})
PHYSICAL_TOOL_STRICT = {name: value for name, value in PHYSICAL_TOOLS.items() if value != "other physical condition" or name in {
    "dialysis", "nephrologist", "cpap", "cpap machine", "sleep apnea", "bad knee", "bad knees", "arthritis", "osteoarthritis", "osteoporosis", "gout", "eds",
    "hypermobility", "me/cfs", "chronic fatigue", "long covid", "chronic illness", "chronic illnesses", "chronic condition", "chronic conditions", "scoliosis", "spinal fusion",
    "ostomy bag", "catheter", "lyme", "hiv", "herpes", "hsv", "hpv"}}
PHYSICAL_TOOL_STRICT = {name: value for name, value in PHYSICAL_TOOL_STRICT.items() if name not in {
    "pump", "port", "scans", "pet scan", "infusions", "infusion", "lymph nodes", "ct scans", "headache", "headaches", "aura", "auras", "eeg", "mri results", "ms", "heart", "heart rate",
    "resting heart rate", "blood pressure", "cholesterol", "iron levels", "ferritin", "stent", "stents", "bypass", "ablation", "b12 shots", "b12 injections", "gut", "stomach", "digestion",
    "digestive system", "bowels", "bowel movements", "liver", "flare", "flares", "flare ups", "flare-ups", "pancreas", "gut health", "derm", "skin", "scalp", "dry skin", "sensitive skin",
    "oily skin", "skin type", "combination skin", "moisture barrier", "skin barrier", "pores", "spots", "scars", "hs", "breakouts", "hair loss",
    "glasses", "contacts", "contact lenses", "prescription", "eye doctor", "ophthalmologist", "optometrist", "eyes", "eyesight", "vision", "hearing", "ears", "lasik", "prk", "eye drops", "lenses",
    "retinas", "retina", "corneas", "cornea", "scooter", "mobility", "carer", "caregiver", "pca", "pip", "ssi", "sci", "cp", "service dog", "pain", "pain levels", "spine", "lower back", "flare",
    "bad days", "spoons", "pt", "physio", "physiotherapy", "physical therapy", "chiropractor", "chiro", "ra", "as", "ana", "crp", "esr", "inflammation", "inflammation markers", "mri", "lesions",
    "relapse", "relapses", "steroids", "immune system", "biologic", "sinuses", "endocrinologist", "endo", "a1c", "blood sugar", "blood sugars", "bolus", "glucose levels",
    "sugar levels", "remission", "metastasis", "tumor markers", "ostomy",
    "epidurals", "ablations", "pain meds", "pain medication", "allergy meds", "allergy medication", "allergy pills",
    "antihistamines", "allergies", "allergy", "allergic reactions", "allergic reaction", "acne", "pots", "birth control", "the pill", "iud", "hrt", "uc", "discs", "ob", "period", "periods", "cycle", "cycles", "gynecologist", "gyno", "obgyn", "ob-gyn", "midwife"}}
PHYSICAL_TOOL_STRICT |= dict.fromkeys(("surgery", "surgeries", "operation", "injury", "injuries", "diagnosis", "diagnoses", "illness", "illnesses", "disease",
                                      "diseases", "disorder", "condition", "conditions", "health condition", "health conditions", "medical condition", "medical conditions", "health issues",
                                      "health problems", "medical issues", "hospitalization", "hospital stay", "uti", "utis", "bladder", "kidneys", "kidney", "fatigue"), "unspecified")


def physical_tool(match):
    mental = MENTAL_TAIL.search(match.string, match.start(), match.end())
    return None if mental and mental.start() < match.start(1) else PHYSICAL_TOOL_STRICT.get(match.group(1))


RULES = [
    rule("physical_condition", rf"\bmy (?:own |new |old |daily |current |rescue |emergency |stupid |damn |trusty |first |second |last |next |latest |recent |regular |usual |monthly |weekly |yearly |annual |"
         rf"\w+ (?:and )?)?({names(PHYSICAL_TOOL_STRICT)})\b(?! (?:friend|kid|son|daughter|brother|sister|partner|husband|wife|mom|dad)s?\b)", physical_tool, OWN_HEDGE),
    rule("physical_condition", rf"\b(?:i (?:also |still |now |have to |had to |need to |always |usually |currently |sometimes |must )?(?:wear|need|use|carry|have|got|take|took|started|start|am on|was on|was put on|got put on|was prescribed|got prescribed|inject|do|did|go to|see|saw|visit)|i'm (?:also |still |now |currently )?(?:on|taking|using)|i've (?:been on|been taking|been using|started)) (?:a |an |my |the |two |both |prescription |daily )?({names({name for name in PHYSICAL_TOOL_STRICT if name not in {'cancer', 'diabetes', 'asthma', 'hypertension', 'migraines', 'migraine', 'seizures', 'seizure', 'heart condition', 'eczema', 'psoriasis', 'rosacea', 'dermatitis', 'hives', 'tinnitus', 'glaucoma', 'ibs', 'gerd', 'reflux', 'acid reflux', 'colitis', 'celiac', 'celiac disease', 'endometriosis', 'pcos', 'fibroids', 'adenomyosis', 'menopause', 'perimenopause', 'hypothyroidism', 'hyperthyroidism', 'arthritis', 'osteoarthritis', 'gout', 'lupus', 'autoimmune disease'}})})\b",
         group(PHYSICAL_TOOL_STRICT), OWN_HEDGE),
    rule("physical_condition", r"\bi'?m (?:legally |completely |totally |profoundly |partially |mostly )?(?:deaf|blind|hard of hearing)\b|\bi (?:was )?born (?:without|with(?:out)? (?:a |an |one )?(?:missing|no) )|\bi (?:was )?born with (?:one|only one|half an?|a missing|no) (?:arm|leg|hand|foot|kidney|eye|ear|lung)\b|\bi (?:lost|had amputated|had to have amputated) (?:my |both |one of my |part of my )(?:\w+ )?(?:arm|leg|hand|foot|feet|legs|arms|fingers|toes|eye|sight|vision|hearing)\b",
         lambda match: "vision or hearing impairment" if re.search(r"deaf|blind|hearing|eye|sight|vision|ear\b", match.group()) else "physical disability", SELF_HEDGE),
    rule("physical_condition", r"\bmy (?:face|skin|scalp|face skin|facial skin) (?:is|has been|gets|get|keeps|is always|is still|is getting|has gotten|tends to be|is naturally|is super|is very|is so|is really|is extremely|is quite|is pretty|is kinda|is a bit|always gets)* ?"
         r"(?:so |very |really |super |extremely |quite |pretty |kinda |a bit |naturally )?(?:dry|oily|sensitive|acne[- ]prone|prone to (?:acne|breakouts|redness|irritation)|breaking out|broken out|flaky|flaking|peeling|"
         r"itchy|irritated|inflamed|congested|dehydrated|reactive|combination)\b", fixed("skin condition"), OWN_HEDGE)]

MENTAL = spread({
    "adhd": ["adhd", "adhd-pi", "adhd-c", "adhd-i", "adhd-h", "inattentive adhd", "combined adhd", "combined type adhd", "inattentive type adhd", "hyperactive adhd", "attention deficit disorder",
             "attention deficit hyperactivity disorder", "adult adhd", "severe adhd", "adhd combined type", "adhd inattentive type", "adhd-combined", "adhd-inattentive"],
    "autism": ["autism", "asd", "asperger's", "aspergers", "asperger", "asperger syndrome", "asperger's syndrome", "aspergers syndrome", "autism spectrum disorder", "level 1 autism", "level 2 autism",
               "level 3 autism", "high functioning autism", "hfa", "autism level 1", "autism level 2", "autism spectrum condition", "asc"],
    "both adhd and autism": ["audhd", "au/dhd", "autism and adhd", "adhd and autism", "asd and adhd", "adhd and asd", "adhd + autism", "autism + adhd", "adhd/autism", "autism/adhd", "asd/adhd", "adhd/asd",
                             "adhd & autism", "autism & adhd", "adhd and aspergers", "adhd and asperger's"],
    "depression": ["depression", "major depressive disorder", "mdd", "clinical depression", "major depression", "severe depression", "chronic depression", "persistent depressive disorder", "dysthymia",
                   "postpartum depression", "post-partum depression", "post partum depression", "postnatal depression", "seasonal affective disorder", "seasonal depression", "treatment resistant depression",
                   "treatment-resistant depression", "trd", "depressive disorder", "a depressive disorder", "perinatal depression", "atypical depression", "depressive episodes", "a depressive episode",
                   "psychotic depression", "recurrent depression", "melancholic depression", "double depression", "high functioning depression"],
    "anxiety": ["anxiety", "an anxiety disorder", "anxiety disorder", "anxiety disorders", "generalized anxiety disorder", "generalised anxiety disorder", "gad", "panic disorder", "panic attacks",
                "a panic disorder", "social anxiety", "social anxiety disorder", "agoraphobia", "health anxiety", "severe anxiety", "anxiety attacks", "emetophobia", "separation anxiety",
                "illness anxiety disorder", "anxiety issues", "anxiety problems", "chronic anxiety", "crippling anxiety", "generalized anxiety", "generalised anxiety", "social phobia", "claustrophobia",
                "a phobia of", "driving anxiety", "performance anxiety", "panic attack disorder", "an anxiety problem", "nervous breakdowns"],
    "bipolar disorder": ["bipolar", "bipolar disorder", "bipolar 1", "bipolar 2", "bipolar i", "bipolar ii", "bipolar type 1", "bipolar type 2", "bipolar one", "bipolar two", "bp1", "bp2", "bpd2", "bp ii",
                         "cyclothymia", "cyclothymic disorder", "manic depression", "bipolar affective disorder", "bipolar 1 disorder", "bipolar 2 disorder", "manic episodes", "a manic episode",
                         "hypomanic episodes", "hypomania", "mania"],
    "ptsd": ["ptsd", "cptsd", "c-ptsd", "c ptsd", "complex ptsd", "post traumatic stress disorder", "post-traumatic stress disorder", "posttraumatic stress disorder", "post traumatic stress",
             "complex post traumatic stress disorder", "complex post-traumatic stress disorder", "combat ptsd", "medical ptsd", "birth trauma"],
    "ocd": ["ocd", "obsessive compulsive disorder", "obsessive-compulsive disorder", "pure o", "pure-o", "rocd", "harm ocd", "contamination ocd", "relationship ocd", "religious ocd", "scrupulosity",
            "health ocd", "sexual orientation ocd", "pocd", "hocd", "real event ocd", "checking ocd", "obsessive compulsive"],
    "eating disorder": ["anorexia", "anorexia nervosa", "bulimia", "bulimia nervosa", "binge eating disorder", "arfid", "an eating disorder", "eating disorder", "eating disorders", "ednos", "osfed",
                        "orthorexia", "atypical anorexia", "compulsive overeating", "binge eating", "bed", "disordered eating", "an ed", "my ed", "anorexic tendencies", "food issues", "rumination disorder",
                        "pica", "a restrictive eating disorder", "restrictive eating"],
    "personality disorder": ["bpd", "borderline personality disorder", "borderline", "npd", "narcissistic personality disorder", "avpd", "avoidant personality disorder", "aspd", "antisocial personality disorder",
                             "histrionic personality disorder", "schizoid personality disorder", "schizotypal personality disorder", "a personality disorder", "personality disorder", "personality disorders",
                             "dependent personality disorder", "ocpd", "obsessive compulsive personality disorder", "paranoid personality disorder", "quiet bpd", "eupd", "emotionally unstable personality disorder",
                             "cluster b", "cluster b personality disorder", "a cluster b personality disorder", "cluster b traits", "spd", "stpd", "hpd"],
    "schizophrenia or psychosis": ["schizophrenia", "paranoid schizophrenia", "schizoaffective", "schizoaffective disorder", "psychosis", "psychotic disorder", "a psychotic disorder", "psychotic episodes",
                                   "a psychotic episode", "psychotic breaks", "a psychotic break", "delusional disorder", "brief psychotic disorder", "schizophreniform", "schizophreniform disorder",
                                   "drug induced psychosis", "drug-induced psychosis", "postpartum psychosis", "hallucinations", "auditory hallucinations", "paranoid delusions", "delusions", "first episode psychosis"],
    "addiction": ["an addiction", "addiction", "addictions", "addiction issues", "addiction problems", "alcoholism", "alcohol addiction", "alcohol use disorder", "a drinking problem", "drinking problem",
                  "a drug problem", "drug problem", "drug addiction", "a drug addiction", "substance abuse", "substance abuse issues", "substance use disorder", "a substance use disorder", "sud",
                  "opioid addiction", "an opioid addiction", "opiate addiction", "an opiate addiction", "opioid use disorder", "oud", "heroin addiction", "a heroin addiction", "meth addiction",
                  "a meth addiction", "cocaine addiction", "a cocaine addiction", "crack addiction", "a gambling problem", "gambling addiction", "a gambling addiction", "gambling problem", "porn addiction",
                  "a porn addiction", "sex addiction", "a sex addiction", "nicotine addiction", "a nicotine addiction", "weed addiction", "a weed addiction", "cannabis addiction", "cannabis use disorder",
                  "an alcohol problem", "alcohol problem", "alcohol issues", "kratom addiction", "a kratom addiction", "benzo addiction", "a benzo addiction", "pill addiction", "a pill addiction",
                  "a pill problem", "video game addiction", "a video game addiction", "gaming addiction", "a gaming addiction", "food addiction", "a food addiction", "shopping addiction",
                  "a shopping addiction", "an alcohol addiction", "a drinking addiction", "a vaping addiction", "vape addiction", "phone addiction", "social media addiction", "a phone addiction",
                  "a fentanyl addiction", "fentanyl addiction", "pain pill addiction", "a pain pill addiction", "a caffeine addiction", "caffeine addiction",
                  "a sugar addiction", "sugar addiction", "dependency", "a dependency", "chemical dependency", "alcohol dependence", "alcohol dependency", "drug dependency", "codependency"],
    "neurodivergent, unspecified": ["neurodivergent", "neurodivergence", "neurodivergency", "neurodiversity", "dyslexia", "dyspraxia", "dyscalculia", "dysgraphia", "dyslexic tendencies"],
    "other mental health condition": ["tourette's", "tourettes", "tourette syndrome", "tourette's syndrome", "tourettes syndrome", "dissociative identity disorder",
                                      "osdd", "a dissociative disorder", "dissociative disorder", "dpdr", "depersonalization", "derealization", "depersonalisation", "derealisation", "depersonalization disorder",
                                      "depersonalization-derealization disorder", "insomnia", "chronic insomnia", "severe insomnia", "body dysmorphia", "body dysmorphic disorder", "bdd", "trichotillomania", "trich",
                                      "dermatillomania", "skin picking disorder", "excoriation disorder", "misophonia", "a tic disorder", "tic disorder", "tics", "motor tics", "vocal tics", "selective mutism",
                                      "adjustment disorder", "an adjustment disorder", "a mental illness", "mental illness", "mental illnesses", "mental health issues", "mental health problems", "mental health struggles",
                                      "a mental health condition", "mental health conditions", "a mental disorder", "mental disorders", "a mental health disorder", "a mood disorder", "mood disorder",
                                      "mood disorders", "intrusive thoughts", "suicidal ideation", "suicidal thoughts", "self harm", "self-harm", "self harm issues", "a learning disability", "learning disability",
                                      "learning disabilities", "an intellectual disability", "intellectual disability", "sensory processing disorder", "sensory processing issues", "sensory issues",
                                      "rejection sensitive dysphoria", "hoarding disorder", "kleptomania", "pyromania", "conversion disorder", "somatic symptom disorder", "sleep paralysis", "night terrors",
                                      "nightmare disorder", "dissociation", "dissociative episodes", "emotional dysregulation", "executive dysfunction", "a processing disorder", "a nonverbal learning disability",
                                      "nvld", "a stutter", "stuttering", "a speech impediment", "speech impediment", "a lisp", "apraxia", "complex trauma", "trauma", "religious trauma",
                                      "childhood trauma", "attachment issues", "an attachment disorder", "attachment disorder", "reactive attachment disorder", "abandonment issues", "trust issues", "anger issues",
                                      "anger problems", "an anger problem", "impulse control disorder", "intermittent explosive disorder", "ied", "odd", "oppositional defiant disorder", "conduct disorder",
                                      "burnout", "autistic burnout", "chronic stress", "grief", "complicated grief", "prolonged grief disorder", "maladaptive daydreaming", "pmdd", "gender dysphoria", "body image issues",
                                      "low self esteem", "low self-esteem", "an inferiority complex", "agoraphobic tendencies", "hypochondria", "psychological issues", "emotional issues", "mental issues",
                                      "mental problems", "a breakdown", "a nervous breakdown", "a mental breakdown", "mental breakdowns", "did"]})
MENTAL_LOOSE = {name: value for name, value in MENTAL.items() if name not in {"did", "bed", "trauma", "grief", "burnout", "tics", "trich", "hfa", "asc", "spd", "stpd", "hpd", "odd", "ied", "sud",
                                                                               "oud", "trd", "osdd", "pica", "mania", "delusions", "hallucinations", "dependency", "a dependency", "codependency", "dissociation",
                                                                               "trust issues", "anger issues", "low self esteem", "low self-esteem", "chronic stress", "a lisp", "an ed", "my ed", "borderline",
                                                                               "sensory issues", "executive dysfunction", "emotional dysregulation", "intrusive thoughts", "food issues", "attachment issues",
                                                                               "abandonment issues", "childhood trauma", "religious trauma", "complex trauma", "birth trauma", "a breakdown", "mental issues",
                                                                               "mental problems", "emotional issues", "body image issues", "an inferiority complex", "hypochondria", "sleep paralysis", "night terrors",
                                                                               "stuttering", "a stutter", "a speech impediment", "speech impediment", "apraxia", "nervous breakdowns", "a nervous breakdown",
                                                                               "a mental breakdown", "mental breakdowns", "gender dysphoria", "claustrophobia", "a phobia of", "performance anxiety", "driving anxiety",
                                                                               "separation anxiety", "disordered eating", "restrictive eating", "binge eating", "insomnia", "hypomania", "panic attacks", "anxiety attacks",
                                                                               "suicidal thoughts", "self harm", "self-harm", "burnout", "autistic burnout", "grief", "complicated grief", "dyslexic tendencies",
                                                                               "anorexic tendencies", "cluster b traits", "depressive episodes", "a depressive episode", "manic episodes", "a manic episode",
                                                                               "hypomanic episodes", "psychotic episodes", "a psychotic episode", "psychotic breaks", "a psychotic break", "paranoid delusions",
                                                                               "auditory hallucinations", "dissociative episodes", "maladaptive daydreaming", "phone addiction", "social media addiction",
                                                                               "a phone addiction", "a caffeine addiction", "caffeine addiction", "a sugar addiction", "sugar addiction", "food addiction",
                                                                               "a food addiction", "shopping addiction", "a shopping addiction", "gaming addiction", "a gaming addiction", "video game addiction",
                                                                               "a video game addiction", "add", "pmdd"}}
MENTAL_STATES = spread({
    "autism": ["autistic", "an autistic", "on the spectrum", "on the autism spectrum", "an aspie", "aspie", "aspergian", "somewhere on the spectrum", "level 1 autistic", "level 2 autistic", "an autist",
               "autistic af", "very autistic", "high functioning autistic", "low support needs autistic"],
    "adhd": ["adhd", "an adhder", "adhder", "an adhd person", "an adhd adult", "adhd af", "an adhd haver", "adhd myself", "add"],
    "both adhd and autism": ["audhd", "autistic and adhd", "adhd and autistic", "autistic with adhd", "autistic + adhd", "adhd + autistic", "autistic/adhd", "adhd/autistic", "autistic & adhd", "adhd & autistic"],
    "bipolar disorder": ["bipolar", "bipolar 1", "bipolar 2", "bipolar ii", "bipolar i", "a manic depressive", "manic depressive", "cyclothymic"],
    "schizophrenia or psychosis": ["schizophrenic", "a schizophrenic", "schizoaffective", "psychotic", "a psychotic"],
    "eating disorder": ["anorexic", "an anorexic", "bulimic", "a bulimic", "a recovering anorexic", "a recovered anorexic", "a binge eater", "a compulsive eater"],
    "addiction": ["an alcoholic", "a recovering alcoholic", "a recovered alcoholic", "a sober alcoholic", "an addict", "a recovering addict", "a recovered addict", "a former addict", "a drug addict",
                  "a heroin addict", "a meth addict", "a crack addict", "a gambling addict", "a porn addict", "a sex addict", "a recovering drug addict", "an ex addict", "an ex-addict", "an ex alcoholic",
                  "an ex-alcoholic", "a functioning alcoholic", "a high functioning alcoholic", "a recovering heroin addict", "a pill addict", "an opiate addict", "an opioid addict", "a junkie",
                  "a recovering junkie", "an addict in recovery", "an alcoholic in recovery", "in recovery", "in recovery from", "sober", "clean and sober", "a sober", "x days sober", "years sober",
                  "months sober", "days sober", "an alcoholic myself", "an addict myself", "a nicotine addict", "a kratom addict", "a benzo addict", "a cocaine addict", "a coke addict"],
    "neurodivergent, unspecified": ["neurodivergent", "neurodiverse", "nd", "dyslexic", "dyspraxic", "dyscalculic", "neuro divergent", "neuro-divergent", "a neurodivergent", "neurospicy", "neurodivergent myself"],
    "depression": ["clinically depressed", "chronically depressed", "severely depressed", "a depressive", "manic"],
    "anxiety": ["agoraphobic", "an anxious person", "a very anxious person", "an anxious wreck", "chronically anxious", "clinically anxious", "a nervous wreck"],
    "other mental health condition": ["an insomniac", "insomniac", "mentally ill", "a mentally ill", "suicidal", "a hoarder", "a plural system", "a system",
                                      "learning disabled", "intellectually disabled", "an empath", "hypersensitive", "a highly sensitive person", "an hsp", "hsp", "mentally unwell", "a stutterer", "a cutter",
                                      "a self harmer", "a survivor of suicide", "a suicide survivor", "dissociative", "a trauma survivor", "traumatized", "traumatised"]})
MENTAL_STATE_STRICT = {name: value for name, value in MENTAL_STATES.items() if name not in {"in recovery", "in recovery from", "sober", "a sober", "nd", "manic", "psychotic", "a psychotic", "a system",
                                                                                         "an empath", "hypersensitive", "a highly sensitive person", "an hsp", "hsp", "traumatized", "traumatised",
                                                                                         "a trauma survivor", "a hoarder", "suicidal", "dissociative", "mentally unwell", "clean and sober",
                                                                                         "x days sober", "years sober", "months sober", "days sober", "a junkie", "add", "a depressive",
                                                                                         "a nervous wreck", "an anxious wreck", "a cutter"}}
MENTAL_TAIL = re.compile(rf"\b(?:{names(MENTAL)})$")
MENTAL_WORDS = {name: value for name, value in MENTAL.items() if name not in {"did", "add", "odd", "bed", "ed"}}
ADHD_DRUGS_WIKIDATA = dict.fromkeys(Path(__file__).with_name("adhd_drugs.txt").read_text(encoding="utf-8").splitlines(), "adhd")

RULES += [
    rule("mental_condition", rf"(?:{HAVE})\s+{MOD}(?:an? )?{GAP}({names(MENTAL_LOOSE)})\b{FOLLOWERS}", group(MENTAL_LOOSE), OWN_HEDGE),
    rule("mental_condition", rf"{BARE}\s+{MOD}(?:an? )?{GAP}({names(MENTAL_LOOSE)})\b{FOLLOWERS}", group(MENTAL_LOOSE), OTHERS),
    rule("mental_condition", r"\bas an? (suicidal|depressed|anxious|paranoid|psychotic)\b", group({"suicidal": "other mental health condition", "depressed": "depression", "anxious": "anxiety", "paranoid": "anxiety", "psychotic": "schizophrenia or psychosis"}), SELF_HEDGE),
    rule("mental_condition", rf"\b(?:i have|i've had|i was diagnosed with|i got diagnosed with|i've been diagnosed with|i'm diagnosed with|i'm on meds for|i take meds for|i was recently diagnosed with|diagnosed with|i also have|i do have|i have had) (?:(?:severe|mild|moderate|chronic|clinical|diagnosed|combined[- ]type|inattentive[- ]type|bad|really bad|pretty bad|terrible|untreated|unmedicated|adult|both|some|serious) )*(add|did|ied|odd|osdd|trich|tics|insomnia|pmdd|hypomania|mania|panic attacks|anxiety attacks|binge eating|disordered eating|intrusive thoughts|suicidal thoughts|self harm|self-harm|childhood trauma|complex trauma|trauma|burnout|autistic burnout|executive dysfunction|sensory issues|gender dysphoria|separation anxiety|claustrophobia|dissociation|sleep paralysis|night terrors|a stutter|a speech impediment|stuttering|apraxia|a nervous breakdown|a mental breakdown|nervous breakdowns|emotional dysregulation)\b",
         group({**MENTAL, "add": "adhd", "bed": "eating disorder", "ied": "other mental health condition", "odd": "other mental health condition"}), OWN_HEDGE),
    rule("mental_condition", rf"\bmy {MOD}({names(MENTAL_LOOSE)})\b{FOLLOWERS}(?! (?:medication|meds)\b)", group(MENTAL_LOOSE), OWN_HEDGE),
    rule("mental_condition", rf"\bmy (?:own )?(adhd|autism|audhd|ocd|bpd|ptsd|cptsd|anxiety|depression|bipolar|ed|eating disorder|addiction|insomnia|tics|trich|did) (?:brain|meds|medication|diagnosis|symptoms|is|was|has|makes|gets|kicks|flares|got|took|and|so)\b",
         group({**MENTAL, "bipolar": "bipolar disorder", "ed": "eating disorder", "insomnia": "other mental health condition", "tics": "other mental health condition",
                "trich": "other mental health condition", "did": "other mental health condition"}), OWN_HEDGE),
    rule("mental_condition", rf"\b(?:as an?|being an?|me, an?|as a fellow|as someone who is|as a person who is|as somebody with|as a person with|as someone with|as one with) (?:fellow |diagnosed |late[- ]diagnosed |recovering |recovered |formerly )?({names(MENTAL_LOOSE)}|{names(MENTAL_STATE_STRICT)}) ?(?:person|woman|man|adult|guy|girl|individual|sufferer|patient|survivor|haver|myself|lady|dude|mom|dad|mother|father|parent|teen|kid|student|female|male|human|being)?\b",
         group({**MENTAL_LOOSE, **MENTAL_STATE_STRICT}), SELF_HEDGE),
    rule("mental_condition", rf"\b(?:i'm|im|i am|i m|i've been|ive been|i was|i became|i'm now|i'm also|i'm actually) (?:also |now |currently |technically |actually |literally |officially |still |pretty |very |severely |extremely |mildly |pretty much |basically |definitely |diagnosed |clinically |formally |medically |probably not |a diagnosed |a |an |self[- ]diagnosed |late[- ]diagnosed )*({names(MENTAL_STATE_STRICT)})\b(?! (?:people|person|friend|friends|community|rights|folks|kids?|son|daughter|family|patients?|to (?:the|this|that|your|my|his|her|their|it|them|what|how|whether|any)|about|of|for|from|by|over|with)\b)",
         group(MENTAL_STATE_STRICT), OWN_HEDGE),
    rule("mental_condition", rf"\b(?:my|i take|i'm on|i am on|i've been on|i started|i'm taking|i am taking|i've been taking|i was put on|i got put on|i was prescribed|i got prescribed|i was given|prescribed me|gave me|put me on|i switched to|switched me to|i take my|i forgot my|i forgot to take my|i ran out of|i'm out of) (?:\w+ )?(?:\d+\s?mg (?:of )?)?({names(ADHD_DRUGS_WIKIDATA)})\b",
         group(ADHD_DRUGS_WIKIDATA), SELF_HEDGE),
    rule("mental_condition", r"\b(audhd|au/dhd)\b", fixed("both adhd and autism"), SELF_HEDGE),
    rule("mental_condition", r"\b(?:i'm|im|i am|i m) (?:literally |also |very |severely |pretty )?nd\b", fixed("neurodivergent, unspecified"), SELF_HEDGE),
    rule("mental_condition", r"\b(adhd|autism|audhd|asd|ocd|ptsd|cptsd|bpd|anxiety|depression|bipolar|insomnia) (?:brain|makes my|affects my|ruins my|means i|makes me|makes it|has made my|messes with my|fucks with my|controls my|took over my|runs my|got the better of me)\b",
         group({**MENTAL, "bipolar": "bipolar disorder", "insomnia": "other mental health condition"}), SELF_HEDGE),
    *(rule("mental_condition", pattern, group(MENTAL_LOOSE), OWN_HEDGE) for pattern in (
        rf"\b(?:recovering|recovered|in recovery) from (?:my |an? )?({names(MENTAL_LOOSE)})\b",
        rf"\b(?:undiagnosed|unmedicated|untreated|diagnosed|crippling|lifelong|late[- ]diagnosed) (?:but severe )?({names(MENTAL_LOOSE)})\b(?=[^.!?\n]*\b(?:i|my|me)\b)",
        rf"^\W*(?:yep\W+|yeah\W+|also\W+|same\W+|me too\W+)?({names(MENTAL_LOOSE)})\W*$", rf"(?:^|[.!?\n]\s*)also,? ({names(MENTAL_LOOSE)})\b(?=\W*(?:$|[.!?\n]))")),
    rule("mental_condition", r"\b(?:made|makes|making|left|leaving|gave) me (?:really |so |very |super |severely |clinically |chronically )?(depressed|anxious|suicidal|depression|anxiety|ptsd|an eating disorder|agoraphobic)\b(?= *(?:$|[.!\n,;]|and\b|for (?:years|months|a long time)))|\b(?:becoming|became|become) an (alcoholic|addict)\b",
         lambda match: {"depressed": "depression", "anxious": "anxiety", "suicidal": "other mental health condition", "depression": "depression", "anxiety": "anxiety", "ptsd": "ptsd",
                        "an eating disorder": "eating disorder", "agoraphobic": "anxiety", "alcoholic": "addiction", "addict": "addiction"}[next(filter(None, match.groups()))], OWN_HEDGE),
    rule("mental_condition", r"\bfor my (adhd|autism|anxiety|depression|ocd|ptsd|cptsd|bipolar|bpd|insomnia|panic attacks|panic disorder|social anxiety|mdd|gad|ed|eating disorder|addiction|alcoholism)\b",
         group({**MENTAL, "bipolar": "bipolar disorder", "ed": "eating disorder", "insomnia": "other mental health condition", "panic attacks": "anxiety"}), OWN_HEDGE),
    rule("mental_condition", r"\bi (?:was|got) (?:\w+ )?(?:hospitalized|hospitalised|admitted|committed|sectioned|baker acted|5150'?d|put on a 5150|put in a psych ward|in a psych ward|in the psych ward|inpatient) (?:for|after|because of) (?:my |an? )?(depression|suicidal thoughts|a suicide attempt|suicide attempt|an overdose|psychosis|a psychotic episode|mania|a manic episode|an eating disorder|anorexia|bulimia|self harm|self-harm)\b",
         group({"depression": "depression", "suicidal thoughts": "depression", "a suicide attempt": "depression", "suicide attempt": "depression", "an overdose": "addiction", "psychosis": "schizophrenia or psychosis",
                "a psychotic episode": "schizophrenia or psychosis", "mania": "bipolar disorder", "a manic episode": "bipolar disorder", "an eating disorder": "eating disorder", "anorexia": "eating disorder",
                "bulimia": "eating disorder", "self harm": "other mental health condition", "self-harm": "other mental health condition"}), OWN_HEDGE),
    rule("mental_condition", r"\b(?:i'm|im|i am|i've been|i have been) (?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|a few|several|many|over \d+|almost \d+|nearly \d+) (?:days?|weeks?|months?|years?|yrs?) (?:sober|clean|off (?:drugs|alcohol|heroin|meth|opiates|opioids|pills|booze|the booze|the drink|drinking))\b",
         fixed("addiction"), SELF_HEDGE)]

FOREIGN_AM = r"(?<![\w'])(?:soy|sou|je suis|ich bin|sono|jestem|ik ben)\s+(?:(?:un|una|um|uma|une|ein|eine|einen|un'|een|tambien|también|também|aussi|auch|anche|też|ook)\s+)*"
FOREIGN_MIND_STATES = spread({"autism": ["autista", "autiste", "autist", "autistin", "autistisch", "autistico", "autistica", "autystą", "autystyczny", "autystyczna"],
                              "bipolar disorder": ["bipolar", "bipolaire", "bipolare"], "depression": ["depresivo", "depresiva", "deprimido", "deprimida", "depressivo", "depressiva", "dépressif", "dépressive",
                                                                                                     "depressiv", "depresso", "depressa", "w depresji", "depressief"],
                              "adhd": ["tdah", "adhs", "adhd", "adhdowcem"], "addiction": ["alcohólico", "alcohólica", "alcoólatra", "alcoolique", "alkoholiker", "alkoholikerin", "alcolizzato", "alkoholikiem", "verslaafd"]})
RULES += [
    rule("mental_condition", rf"{FOREIGN_AM}({names(FOREIGN_MIND_STATES)})(?![\w'])", group(FOREIGN_MIND_STATES), SELF_HEDGE),
    rule("mental_condition", r"\b(?:we|us)\W+(?:fellow |other )?(autistic|adhd|adhders|neurodivergent|nd|audhd|bipolar|ocd|anxious|depressed|dyslexic) (?:people|folks|adults|women|men|girls|guys|ones|kids|types|individuals|humans)\b",
         group({"autistic": "autism", "adhd": "adhd", "adhders": "adhd", "neurodivergent": "neurodivergent, unspecified", "nd": "neurodivergent, unspecified", "audhd": "both adhd and autism",
                "bipolar": "bipolar disorder", "ocd": "ocd", "anxious": "anxiety", "depressed": "depression", "dyslexic": "neurodivergent, unspecified"}), SELF_HEDGE),
    rule("mental_condition", rf"\b(?:i was|i've been|i got|i am|i'm|got|was|been|they|doctor|psychiatrist|therapist) (?:\w+ )?(?:diagnosed|dx'?d) (?:me )?(?:with|as)(?: an?)? ({names(MENTAL)})\b",
         group(MENTAL), OTHERS),
    rule("mental_condition", rf"\bi (?:also |still |do )?(?:have|have had|struggle with|deal with|live with)(?: an?)? ({names(MENTAL_WORDS)})\b(?! (?:to|with|of|that|for|in)\b)", group(MENTAL), OTHERS)]

BOT_SELF = (r"(?:\bi(?:'m| am)[\s^]+a[\s^]+bot\b|\bthis is a bot\b|\bperformed[\s^]+automatically\b|\bsou um bot\b|\bsoy un bot\b|\bbeep boop\b|\bbleep bloop\b|"
            r"\bthis is an? (?:automated|automatic) (?:message|response|reply|comment|process)\b|\bthis message is an automat\w+ response\b)")
MODERATION = r"removed|remove|approv\w*|karma|locked|not allowed|bans?|bannable|banned|comments are disabled|filtered|blocked|block you|copy of (?:the|this|your) (?:original )?(?:post|submission)|post's original text|copia del post|salvo qui una copia"
RULES += [
    rule("automated_account", rf"^(?=[\s\S]*?(?:bot|automat|beep|bleep))(?![\s\S]*\b(?:{MODERATION})\b)(?![\s\S]*(?:\bu/\w|\bop\b))[\s\S]*?{BOT_SELF}", fixed("bot"), TAGGED)]

def quoted(text, start):
    line = text[text.rfind("\n", 0, start) + 1:start]
    return line.count('"') % 2 == 1 or line.count("“") > line.count("”")


def unquoted(value):
    return lambda match: None if quoted(match.string, match.start()) else value(match)


RULES = [(attribute, pattern, value if attribute == "automated_account" else unquoted(value), hedge) for attribute, pattern, value, hedge in RULES]

COMMON = ("diabetes", "type 1 diabetes", "type 2 diabetes", "t1d", "t2d", "diabetic", "hypoglycemic", "lupus", "rheumatoid arthritis", "rheumatoid disease", "multiple sclerosis", "hashimoto's",
          "hashimotos", "an autoimmune disease", "graves disease", "graves' disease", "psoriatic arthritis", "chronic pain", "fibromyalgia", "fibro", "sciatica", "herniated disc", "breast cancer",
          "leukemia", "lymphoma", "a heart condition", "heart disease", "high blood pressure", "hypertension", "afib", "anemia", "ibs", "crohn's", "crohns", "crohn's disease", "ulcerative colitis",
          "colitis", "celiac", "celiac disease", "celiacs", "gastritis", "gerd", "acid reflux", "hiatal hernia", "pcos", "endometriosis", "fibroids", "adenomyosis", "hypothyroidism", "hyperthyroidism",
          "menopause", "perimenopause", "my hormones", "epilepsy", "migraine", "migraines", "chronic migraines", "parkinson's", "seizures", "eczema", "psoriasis", "acne", "cystic acne", "rosacea",
          "dermatitis", "dry skin", "sensitive skin", "asthma", "allergies", "copd", "tinnitus", "hearing loss", "hearing aids", "iritis", "dry eye", "eye disease", "cerebral palsy", "eds",
          "ehlers-danlos", "me/cfs", "chronic fatigue", "long covid", "arthritis", "osteoarthritis", "sleep apnea", "kidney disease", "kidney stones", "dialysis", "colostomy", "scoliosis",
          "hyperparathyroidism", "broken ankle", "torn acl", "gastroparesis", "ibd", "hidradenitis suppurativa", "ankylosing spondylitis", "sjogren's", "high cholesterol", "diverticulitis", "gout",
          "plantar fasciitis", "carpal tunnel", "tendonitis", "osteoporosis", "b12 deficiency", "insulin resistance", "prediabetes", "narcolepsy", "lyme disease", "hypermobility", "mcas",
          "tachycardia", "hypothyroid", "heds", "vertigo", "neuropathy", "peripheral neuropathy", "gallstones", "herpes", "lymphedema", "lipedema", "vitiligo", "alopecia", "glaucoma", "cataracts",
          "keratoconus", "chronic sinusitis", "hay fever", "food allergies", "emphysema", "cystic fibrosis", "spina bifida", "muscular dystrophy", "osteopenia", "tmj", "trigeminal neuralgia",
          "restless leg syndrome", "dysautonomia", "interstitial cystitis", "lichen sclerosus", "polycystic kidney disease", "chronic kidney disease", "degenerative disc disease", "spinal stenosis",
          "bulging discs", "herniated discs", "costochondritis", "frozen shoulder", "bursitis", "tendinitis")
AILMENTS = {name: PHYSICAL[name] for name in COMMON}
OTHER_PEOPLE = re.compile(r"\b(?:mom|mother|dad|father|wife|husband|son|daughter|friend|brother|sister|grandma|grandpa|grandmother|grandfather|aunt|uncle|cousin|boyfriend|girlfriend|partner|he|she|his|her|him|they|their|dog|cat|patients?|clients?|family|families|relatives)\b")
MOODS = {"anxiety": "anxiety", "depression": "depression", "ocd": "ocd", "ptsd": "ptsd", "cptsd": "ptsd", "bpd": "personality disorder", "bipolar": "bipolar disorder", "an eating disorder": "eating disorder",
         "anorexia": "eating disorder", "bulimia": "eating disorder", "schizophrenia": "schizophrenia or psychosis", "psychosis": "schizophrenia or psychosis", "insomnia": "other mental health condition",
         "body dysmorphia": "other mental health condition", "adhd": "adhd", "autism": "autism", "audhd": "both adhd and autism", "autistic": "autism", "asd": "autism",
         "addiction": "addiction", "an addiction": "addiction", "alcoholism": "addiction"}
MOOD_NAMES = re.compile(r"\b(" + names(MOODS) + r")\b")
NEURO = ("adhd", "autism", "both adhd and autism")
ASSESSED = re.compile(r"\s*(?:assessments?|evaluations?|diagnosis|diagnoses|traits|testing|tests?)\b")
POSSESSOR = re.compile(rf"\b(?:{PEOPLE}|someone|anyone|somebody|anybody) (?:has|have|had|having|with|gets|got)(?: \w+){{0,2}} $")
ADDRESSED = re.compile(r"\b(?:you|your|you're|u|ur)\b")
GENERIC = re.compile(r"\s+(?:is|are|isn't|aren't|makes|make|causes|cause|can|could|does|doesn't|means|affects|tends|presents|manifests)\b")
ATTRIBUTIVE = re.compile(r" +(?!(?:and|or|af|asf|myself|too|as|but|so|lol)\b)[a-z]")
ASKING = re.compile(r"\b(?:do|does|did|could|can|might|may|am|would|should|will|have) i\b")
CAUSED = re.compile(r"\b(?:give|gives|giving|gave|given) (?:me|us) (?:[\w-]+ ){0,3}$")
FIRST_PERSON = re.compile(r"\b(?:i|i'm|im|i've|ive|i'd|i'll|my|me|myself|mine)\b")
CROWD = re.compile(r"\b(?:people|person|those|anyone|someone|somebody|everyone|many|most|some|others|patients|women|men|kids|children|americans|studies|research|risk|causes?|symptoms?)\b")

ORGANS = {"heart": "heart or blood condition", "cardiac": "heart or blood condition", "blood pressure": "heart or blood condition", "circulation": "heart or blood condition",
          "stomach": "digestive condition", "gut": "digestive condition", "bowel": "digestive condition", "digestive": "digestive condition", "gi": "digestive condition", "tummy": "digestive condition",
          "skin": "skin condition", "eye": "vision or hearing impairment", "vision": "vision or hearing impairment", "eyesight": "vision or hearing impairment", "hearing": "vision or hearing impairment",
          "ear": "vision or hearing impairment", "thyroid": "hormonal or reproductive condition", "hormone": "hormonal or reproductive condition", "hormonal": "hormonal or reproductive condition",
          "fertility": "hormonal or reproductive condition", "breathing": "respiratory condition or allergy", "lung": "respiratory condition or allergy", "sinus": "respiratory condition or allergy",
          "respiratory": "respiratory condition or allergy", "back": "other physical condition", "knee": "other physical condition", "hip": "other physical condition", "joint": "other physical condition",
          "kidney": "other physical condition", "liver": "other physical condition", "bladder": "other physical condition", "health": "other physical condition", "medical": "other physical condition",
          "dental": "other physical condition", "teeth": "other physical condition", "sleep": "other physical condition"}
TROUBLES = ("problems", "issues", "trouble", "condition", "conditions", "imbalance")
GENERAL = spread({"autoimmune disease": ["ms"], "other physical condition": ["motion sickness", "car sickness", "parkinsonism", "drug induced parkinsonism", "a chronic illness", "a medical condition", "a health condition"],
                  "digestive condition": ["constipation", "chronic constipation"],
                  "hormonal or reproductive condition": ["miscarriages", "a miscarriage", "recurrent miscarriages", "recurrent pregnancy loss", "a hormonal imbalance"],
                  "skin condition": ["keratosis pilaris"]})


def inflected(table):
    grown = dict(table)
    for name, value in table.items():
        if name.startswith(("a ", "an ")) and " " in name.split(" ", 1)[1]:
            grown.setdefault(name.split(" ", 1)[1], value)
        if len(name) >= 5 and name[-1].isalpha() and not name.endswith(("s", "x", "y", "sh", "ch")):
            grown.setdefault(name + "s", value)
        elif len(name) >= 5 and name.endswith("y") and name[-2] not in "aeiou":
            grown.setdefault(name[:-1] + "ies", value)
    return grown


MIND_EXTRA = spread({"anxiety": ["panic attacks", "anxiety attacks", "a panic disorder", "separation anxiety", "performance anxiety", "test anxiety"], "depression": ["depressive episodes", "a depressive episode"],
                     "bipolar disorder": ["manic episodes", "a manic episode"], "eating disorder": ["binge eating"],
                     "other mental health condition": ["suicidal thoughts", "intrusive thoughts", "executive dysfunction", "insomnia"]})
KNOWN = {*PHYSICAL, *PHYSICAL_STATES, *PHYSICAL_TOOLS, *MENTAL, *MENTAL_STATES, *MIND_EXTRA, *GENERAL}
WORDNET_CONDITIONS = {name: value for name, value in (line.split("\t") for line in Path(__file__).with_name("wordnet_conditions.tsv").read_text(encoding="utf-8").splitlines()) if name not in KNOWN}
CONDITIONS = inflected({**WORDNET_CONDITIONS, **{f"{organ} {trouble}": value for organ, value in ORGANS.items() for trouble in TROUBLES}, **GENERAL, **PHYSICAL,
                        **dict.fromkeys(("surgery", "surgeries", "a surgery", "an operation", "an injury", "injuries", "an illness", "illness", "a disease", "an infection", "infection", "infections"), "unspecified")})
STATES = {name: value for name, value in inflected(PHYSICAL_STATES).items() if name not in CONDITIONS}
MIND = inflected({**MIND_EXTRA, **MENTAL_LOOSE})
MIND_STATES = {name: value for name, value in inflected(MENTAL_STATE_STRICT).items() if name not in MIND}
WORD = re.compile(r"[\w'/+-]+(?:\.\d+)?")
STOP = rf"{PEOPLE}|not|no|never|and|but|or|if|when|because|so|that|who|which|what|where|why|how|whether|than|to|in|on|about|like|for|from|at|by|into|of|with|without|is|was|are|were|be|it|this"
FREE = rf"(?:(?!(?:{STOP})\b)(?![\w'-]*(?:ed|en)\b)[\w'/-]+,?\s+)"
LEAD = rf"(?:[\s,]+(?:(?:{MODIFIERS})\b|an?\b|the\b))*[\s,]*"
def owning(have, mine):
    return (rf"(?:{have}){LEAD}{FREE}{{0,2}}|{mine}|\b(?:i've|ive|i have got){LEAD}|\b(?:a |as a |from a )?fellow{LEAD}|\b(?:i'm|i am|im) (?:on|taking) [\w-]+ for(?: my| the)?{LEAD}|"
            rf"\b(?:put|got|have) me on [\w-]+ for(?: my| the)?{LEAD}|\bi (?:take|took|use|need) [\w-]+(?: [\w-]+)? for(?: my| the)?{LEAD}|"
            rf"\bi (?:talked|spoke|talk|speak|went) to (?:my|a) (?:doctor|therapist|psychiatrist|psych|gp|pcp|counselor|counsellor|specialist|neurologist|doc) (?:about|for)(?: my)?{LEAD}")


NOUN_CUE = re.compile(rf"(?:{owning(HAVE_NOW, rf'\bmy{LEAD}{FREE}{{0,2}}')})$")
MIND_CUE = re.compile(rf"(?:{owning(HAVE, rf'\bmy{LEAD}')}|\b(?:must|could|might|may|probably|just|it's|its|that's|thats|blame it on|blame)(?: just| probably| definitely)?(?: be)? the{LEAD})$")
DROPPED = re.compile(rf"\W*(?:also |and |but |still |now |recently |just |newly |finally |officially |got |was |been )*(?:have|got|having|suffer from|suffer with|suffering from|suffering with|struggle with|struggling with|deal with|dealing with|live with|living with|recovering from|battling|diagnosed with|dx'?d with){LEAD}{FREE}?")
DIAGNOSED = re.compile(rf"\W*(?:recently |just |also |finally |newly |officially |formally )?(?:got |was |been )?(?:diagnosed|dx'?d)(?: as)?{LEAD}")
CANDIDATE = re.compile(r"\b(?:i|i'm|im|i've|ive|my|me|fellow|have|having|got|suffer|suffering|struggle|struggling|deal|dealing|live|living|recovering|battling|diagnosed|dx'?d|the|here|warrior|gang|squad|life|club|crew|fam)\b")
HERE_BEFORE = re.compile(r"(?:^|[,;(|]\s*)(?:an? )?(?:fellow |another |also |also an? |proud |former |recovering |recovered )?$")
HERE_AFTER = {"physical_condition": re.compile(r" (?:here|sufferer here|patient here|survivor here|warrior here|warrior|gang|squad|life|haver here|person here|club|crew|fam)\b"),
              "mental_condition": re.compile(r" (?:here|person here|haver here|sufferer here|survivor here|gal here|guy here|girl here|woman here|man here|mom here|mama here|dad here|adult here|"
                                             r"patient here|warrior|gang|squad|club|crew|fam)\b")}
def stating(being):
    return re.compile(rf"(?:\b(?:i'm|im|i am|i've been|ive been|i was born|i became|as(?: an?)?|{being}|me,?(?: an?)?|(?:a |as a |from a )?fellow)(?: (?:also|now|currently|still|technically|actually|literally|officially|"
                      rf"basically|completely|totally|profoundly|severely|mostly|partially|fully|medically|legally|kind of|kinda|just|really|recently|newly|permanently|chronically|clinically|"
                      rf"unfortunately|apparently|obviously|functionally|genetically|naturally|definitely))*{LEAD}{FREE}{{0,2}})$")


STATE_CUE = stating("being an?")
MIND_STATE_CUE = stating("being(?: an?)?|of us")
LINK = re.compile(rf"\s*(?:,|&|/|\+|\band\b|\bor\b|\bplus\b|\bas well as\b|\balong with\b|\bw/)(?:\s*(?:and|&)\b)?{LEAD}")
TRAIL = re.compile(rf"\s*(?:{PEOPLE}|community|person|research|awareness|month|day|walk|"
                   r"charity|foundation|society|association|group|subreddit|sub|forum|nurse|doctor|unit|ward|center|centre|clinic|risk|test|testing|screening)s?\b|'s\b")
MS_PREV = re.compile(r"\b(?:have|had|with|my|i've|ive|got|and|&)\s*$")
MS_NEXT = re.compile(r"\s*(?:$|[^\w\s]|(?:and|is|was|has|had|diagnosis|symptoms|flare|relapse|meds|medication|fatigue|brain|lesions)\b)")
SCOPE = re.compile(r"[,;:(.!?\n]|\b(?:and|but|because|cause|cuz|bc|since|so|though|although|while|whereas)\b")
ASTROLOGY = re.compile(r"\b(?:aries|taurus|gemini|geminis|leo|leos|virgo|virgos|libra|libras|scorpio|scorpios|sagittarius|capricorn|capricorns|aquarius|pisces|zodiac|horoscope|astrology)\b|\b(?:in|into) cancer\b|\bcancer (?:sun|moon|rising|venus|mars|mercury|jupiter|saturn|placement|season|sign)\b|\b(?:sun|moon|rising|saturn|jupiter|venus|mars|mercury) (?:in|sign)\b")


def spans(names):
    longest = {}
    for name in names:
        first, size = name.split(" ", 1)[0], name.count(" ") + 1
        longest[first] = max(longest.get(first, 0), size)
    return longest


FAMILIES = tuple((attribute, nouns, states, known, cue, state_cue, suffix, spans(known))
                 for attribute, nouns, states, cue, state_cue, suffix in (("physical_condition", CONDITIONS, STATES, NOUN_CUE, STATE_CUE, ("itis", "other physical condition")),
                                                                          ("mental_condition", MIND, MIND_STATES, MIND_CUE, MIND_STATE_CUE, ("phobia", "other mental health condition")))
                 for known in [{**nouns, **states}])


def lookup(words, table, longest, suffix=""):
    tokens = [word for _, _, word in words]
    after = 0
    for index in [index for index, token in enumerate(tokens) if token in longest or suffix and token.endswith(suffix)]:
        if index < after:
            continue
        token = tokens[index]
        if token not in longest:
            if len(token) > len(suffix) + 3:
                yield words[index][0], words[index][1], token
            continue
        for size in range(min(longest[token], len(tokens) - index), 0, -1):
            if (name := " ".join(tokens[index:index + size])) in table:
                yield words[index][0], words[index + size - 1][1], name
                after = index + size
                break


TOKEN = re.compile(r"\w+(?:'\w+)*")
SPOTS = re.compile(r"\w+(?:'\w+)*|[.!?\n]")
AILMENT_KEYS = {" ".join(TOKEN.findall(name)): value for name, value in AILMENTS.items()}
AILMENT_SPANS = spans(AILMENT_KEYS)


POSSESSIVE_HEDGE = re.compile(r"\b(?:if|whether|unless|imagine|pretend|wish|hope)\b")


def unhedged(lowered, start):
    window = lowered[max(0, start - 40):start]
    cut = max((match.end() for match in SCOPE.finditer(window)), default=0)
    return not (POSSESSIVE_HEDGE if lowered.startswith("my", start) else OWN_HEDGE).search(window, cut)


def owned(lowered, sentence, found, families):
    part = sentence.group()
    if not CANDIDATE.search(part):
        return
    words = [(match.start(), match.end(), match.group()) for match in WORD.finditer(part)]
    for attribute, nouns, states, known, noun_cue, state_cue, suffix, longest in families:
        previous = None
        for start, end, name in lookup(words, known, longest, suffix[0]):
            noun = name not in states
            if attribute == "physical_condition" and (mental := MENTAL_TAIL.search(part, max(0, start - 40), end)) and mental.start() < start:
                previous = None
                continue
            left = part[max(0, start - 90):start]
            here = HERE_AFTER[attribute].match(part, end) and HERE_BEFORE.search(left)
            cue = (noun_cue if noun else state_cue).search(left) or here
            begin = start - len(cue.group()) if cue else 0 if (DROPPED if noun else DIAGNOSED).fullmatch(part, 0, start) else None
            chained = previous is not None and LINK.fullmatch(part, previous, start)
            if ((begin is not None or chained) and (here or not TRAIL.match(part, end)) and (name != "ms" or MS_NEXT.match(part, end) and MS_PREV.search(part, 0, start))
                    and (chained or unhedged(lowered, sentence.start() + begin)) and not quoted(lowered, sentence.start() + start)):
                found.setdefault((attribute, nouns.get(name) or states.get(name) or suffix[1]), sentence.start() + start)
                previous = end
            else:
                previous = None


def ailments(lowered, found):
    speaker = FIRST_PERSON.search(lowered)
    moody = speaker and MOOD_NAMES.search(lowered)
    spotted = lookup([(match.start(), match.end(), match.group()) for match in SPOTS.finditer(lowered)], AILMENT_KEYS, AILMENT_SPANS) if speaker else iter(())
    upcoming = next(spotted, None)
    for sentence in re.finditer(r"[^.!?\n]+", lowered):
        part = sentence.group()
        here = []
        while upcoming and upcoming[0] < sentence.end():
            here.append((upcoming[0] - sentence.start(), upcoming[1] - sentence.start(), upcoming[2]))
            upcoming = next(spotted, None)
        asked = lowered[sentence.end():sentence.end() + 1] == "?"
        if not asked or not ASKING.search(part):
            owned(lowered, sentence, found, FAMILIES[1:] if asked else FAMILIES)
        if asked:
            continue
        first = FIRST_PERSON.search(part)
        mood = first or moody and MOOD_NAMES.search(part)
        if not (mood or here) or OTHER_PEOPLE.search(part) or not first and CROWD.search(part):
            continue
        hedge = HEDGE.search(part)
        addressed = ADDRESSED.search(part)
        for start, end, name in here:
            if addressed or hedge and hedge.end() <= start:
                break
            if quoted(lowered, sentence.start() + start) or POSSESSOR.search(part, max(0, start - 50), start) or GENERIC.match(part, end):
                continue
            found.setdefault(("physical_condition", AILMENT_KEYS[name]), sentence.start() + start)
        if hedge or not mood:
            continue
        for match in MOOD_NAMES.finditer(part):
            value, after = MOODS[match.group(1)], match.end()
            if quoted(lowered, sentence.start() + match.start()) or POSSESSOR.search(part, max(0, match.start() - 50), match.start()) or TRAIL.match(part, after) or ASSESSED.match(part, after) or CAUSED.search(part, max(0, match.start() - 40), match.start()) or not first and value not in NEURO:
                continue
            if value in NEURO and (OWN_HEDGE.search(part) or GENERIC.match(part, after) or match.group(1) == "autistic" and ATTRIBUTIVE.match(part, after)):
                continue
            found.setdefault(("mental_condition", value), sentence.start() + match.start())
    if ASTROLOGY.search(lowered):
        found.pop(("physical_condition", "cancer"), None)
    if (key := ("physical_condition", "neurological condition")) in found:
        found.setdefault(("physical_condition", "other physical condition"), found.pop(key))
    if (key := ("physical_condition", "unspecified")) in found:
        position = found.pop(key)
        if not any(attribute == "physical_condition" for attribute, _ in found):
            found[("physical_condition", "other physical condition")] = position
