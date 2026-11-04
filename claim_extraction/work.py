import re

from .common import I, SELF_HEDGE, fixed, group, rule

CONDITIONAL = re.compile(r"\b(?:if|would|wish|imagine|pretend|unless|whether|might|maybe)\b")


def alternation(words):
    return "|".join(sorted(map(re.escape, words), key=len, reverse=True))


def table(entries):
    return {word: value for value, words in entries.items() for word in words.split("|")}


SOFTWARE, ENGINEERING, SCIENCE, CLINICAL, CARE = "software or IT", "engineering", "science or research", "doctor, nurse or clinical health", "health support or care work"
TEACHING, LAW, FINANCE, BUSINESS, MEDIA = "teaching or education", "law", "finance or accounting", "business, management or consulting", "marketing, media or communications"
ARTS, SALES, FOOD, TRADE, WAREHOUSE = "arts, design or entertainment", "sales or retail", "food service or hospitality", "skilled trade or construction", "manufacturing or warehouse"
TRANSPORT, SAFETY, MILITARY, GOVERNMENT, SOCIAL = "transport or delivery", "police, fire or security", "military", "government or public service", "social work or religious work"
OFFICE, SERVICE, OUTDOOR, ADULT, OTHER = "office or administrative", "cleaning, maintenance or personal service", "farming or outdoor work", "sex work or adult content", "other job"

JOBS = table({
    SOFTWARE: "software engineer|software developer|software architect|software dev|developer|programmer|coder|computer programmer|web developer|web dev|app developer|mobile developer|ios developer|"
              "android developer|front end developer|frontend developer|front-end developer|backend developer|back end developer|back-end developer|full stack developer|fullstack developer|"
              "full-stack developer|game developer|game dev|indie dev|dev|swe|sde|data scientist|data engineer|data analyst|data architect|machine learning engineer|ml engineer|ai engineer|"
              "sysadmin|system administrator|systems administrator|network administrator|network engineer|database administrator|dba|devops engineer|site reliability engineer|sre|"
              "cloud engineer|cloud architect|solutions architect|it technician|it tech|it support|it specialist|it consultant|it manager|it guy|it professional|it administrator|it analyst|"
              "systems analyst|help desk technician|helpdesk technician|help desk analyst|desktop support technician|tech support|technical support specialist|support engineer|"
              "qa engineer|qa tester|qa analyst|software tester|game tester|test engineer|cybersecurity analyst|cyber security analyst|security analyst|security engineer|penetration tester|"
              "pentester|ethical hacker|ux engineer|embedded engineer|embedded developer|firmware engineer|computer technician|salesforce developer|sap consultant|tech lead|bi developer|"
              "business intelligence analyst|programmer analyst|computer scientist|blockchain developer|wordpress developer|shopify developer|it worker|software consultant",
    ENGINEERING: "engineer|mechanical engineer|electrical engineer|civil engineer|chemical engineer|aerospace engineer|aeronautical engineer|structural engineer|process engineer|"
                 "manufacturing engineer|industrial engineer|biomedical engineer|environmental engineer|petroleum engineer|mining engineer|nuclear engineer|materials engineer|"
                 "design engineer|project engineer|quality engineer|reliability engineer|field engineer|systems engineer|controls engineer|automation engineer|electronics engineer|"
                 "hardware engineer|computer engineer|robotics engineer|geotechnical engineer|transportation engineer|mechatronics engineer|engineering technician|drafter|draftsman|"
                 "cad technician|surveyor|land surveyor|telecom engineer|rf engineer|power engineer|marine engineer|naval architect|test pilot engineer",
    SCIENCE: "scientist|research scientist|researcher|biologist|chemist|physicist|lab tech|lab technician|laboratory technician|lab assistant|lab manager|postdoc|post-doc|"
             "postdoctoral researcher|postdoctoral fellow|research assistant|research associate|research fellow|geologist|geophysicist|astronomer|astrophysicist|neuroscientist|"
             "microbiologist|ecologist|statistician|economist|mathematician|epidemiologist|biochemist|geneticist|botanist|zoologist|marine biologist|meteorologist|climatologist|"
             "archaeologist|anthropologist|sociologist|historian|linguist|pharmacologist|toxicologist|virologist|immunologist|physiologist|entomologist|oceanographer|hydrologist|"
             "analytical chemist|food scientist|materials scientist|professor|associate professor|assistant professor|full professor|research professor|academic|research engineer|"
             "principal investigator|clinical researcher|clinical research coordinator|paleontologist|ornithologist|primatologist|volcanologist|seismologist",
    CLINICAL: "doctor|physician|medical doctor|nurse|registered nurse|nurse practitioner|lpn|lvn|surgeon|dentist|orthodontist|pharmacist|paramedic|emt|physical therapist|"
              "physiotherapist|occupational therapist|speech therapist|speech language pathologist|speech-language pathologist|slp|respiratory therapist|radiologist|radiographer|"
              "radiology tech|radiology technician|x-ray tech|sonographer|ultrasound tech|mri tech|anesthesiologist|anaesthetist|anesthetist|crna|nurse anesthetist|psychiatrist|"
              "psychologist|clinical psychologist|therapist|psychotherapist|mental health therapist|veterinarian|vet tech|veterinary technician|veterinary nurse|optometrist|ophthalmologist|"
              "optician|midwife|dental hygienist|hygienist|physician assistant|physician associate|pa-c|gp|general practitioner|family doctor|pediatrician|paediatrician|cardiologist|"
              "dermatologist|oncologist|neurologist|gynecologist|gynaecologist|obgyn|ob-gyn|urologist|gastroenterologist|endocrinologist|pathologist|internist|hospitalist|intensivist|"
              "er doctor|er nurse|icu nurse|nicu nurse|charge nurse|travel nurse|school nurse|psych nurse|labor and delivery nurse|chiropractor|podiatrist|audiologist|dietitian|"
              "dietician|nutritionist|resident physician|medical resident|surgical resident|junior doctor|clinician|medic|combat medic|perfusionist|medical laboratory scientist|"
              "medical lab scientist|medical technologist|acupuncturist|osteopath|naturopath|healthcare professional|health care professional|healthcare worker|health care worker|"
              "nurse midwife|emergency physician|er physician|trauma surgeon|neurosurgeon|orthopedic surgeon|plastic surgeon|oral surgeon|endodontist|periodontist|prosthodontist|"
              "behavioral therapist|art therapist|music therapist|play therapist|marriage and family therapist|mft|lcsw|lpc|lmft",
    CARE: "cna|certified nursing assistant|nursing assistant|nurse aide|nurse's aide|caregiver|care giver|care worker|carer|care assistant|healthcare assistant|health care assistant|"
          "support worker|disability support worker|home health aide|home care worker|personal support worker|psw|medical assistant|pharmacy tech|pharmacy technician|"
          "pharmacy assistant|personal care assistant|phlebotomist|dental assistant|dental nurse|hospice worker|patient care technician|pct|orderly|hospital porter|"
          "sterile processing technician|medical scribe|doula|direct support professional|dsp|behavior technician|behaviour technician|rbt|aba therapist|residential support worker|"
          "care home worker|nursing home worker|hospice aide|home health nurse aide|mental health worker|psych tech|psychiatric technician|ophthalmic technician|optometric technician|"
          "chiropractic assistant|veterinary assistant|vet assistant|massage therapist",
    TEACHING: "teacher|tutor|lecturer|educator|teaching assistant|substitute teacher|sub teacher|supply teacher|kindergarten teacher|preschool teacher|pre-k teacher|elementary teacher|"
              "elementary school teacher|primary teacher|primary school teacher|middle school teacher|high school teacher|secondary teacher|secondary school teacher|math teacher|"
              "maths teacher|english teacher|science teacher|history teacher|music teacher|art teacher|pe teacher|gym teacher|chemistry teacher|biology teacher|physics teacher|"
              "special ed teacher|special education teacher|sped teacher|esl teacher|efl teacher|esl tutor|english tutor|math tutor|librarian|school librarian|principal|vice principal|"
              "assistant principal|headteacher|head teacher|headmaster|headmistress|dean|school counselor|school counsellor|guidance counselor|instructor|adjunct|adjunct professor|"
              "adjunct instructor|coach|swim instructor|swimming instructor|driving instructor|flight instructor|paraprofessional|paraeducator|teacher's aide|teacher aide|daycare worker|"
              "childcare worker|child care worker|early childhood educator|nursery teacher|montessori teacher|academic advisor|school psychologist|music instructor|piano teacher|"
              "guitar teacher|dance teacher|dance instructor|language teacher|french teacher|spanish teacher|german teacher|homeschool teacher|lecturer in|college instructor|"
              "university lecturer|professor of|teaching fellow|instructional designer|curriculum developer|education consultant|school administrator|superintendent of schools",
    LAW: "lawyer|attorney|paralegal|solicitor|barrister|judge|legal assistant|legal secretary|public defender|prosecutor|district attorney|defense attorney|defence lawyer|"
         "criminal defense attorney|criminal defense lawyer|corporate lawyer|immigration lawyer|immigration attorney|family lawyer|divorce lawyer|tax lawyer|tax attorney|litigator|"
         "notary|notary public|legal counsel|general counsel|in-house counsel|law clerk|court clerk|magistrate|patent attorney|patent agent|patent lawyer|mediator|arbitrator|"
         "court reporter|associate attorney|trial lawyer|personal injury lawyer|estate lawyer|real estate attorney|legal analyst|compliance officer|conveyancer|legal executive",
    FINANCE: "accountant|cpa|chartered accountant|financial analyst|banker|investment banker|actuary|auditor|bookkeeper|trader|stock trader|financial advisor|financial adviser|"
             "financial planner|wealth manager|portfolio manager|fund manager|hedge fund manager|bank teller|teller|underwriter|loan officer|mortgage broker|mortgage advisor|"
             "mortgage adviser|insurance broker|claims adjuster|insurance adjuster|tax preparer|tax accountant|tax advisor|payroll specialist|payroll clerk|payroll administrator|"
             "accounts payable clerk|accounts payable specialist|accounts receivable clerk|accounts receivable specialist|credit analyst|risk analyst|quant|quantitative analyst|controller|"
             "financial controller|comptroller|treasurer|cfo|equity analyst|investment analyst|stockbroker|accounting clerk|accounting specialist|accounting manager|finance manager|"
             "billing specialist|collections agent|collector|finance analyst|private banker|relationship manager|credit controller|bank manager|branch manager|bank clerk|bursar|"
             "forensic accountant|enrolled agent|insurance underwriter|investment advisor|investment manager|equity research analyst|fp&a analyst",
    BUSINESS: "manager|consultant|management consultant|business consultant|strategy consultant|ceo|coo|cto|cmo|cio|project manager|program manager|programme manager|product manager|"
              "product owner|scrum master|business analyst|executive|director|managing director|operations manager|general manager|hr manager|hr specialist|hr generalist|"
              "hr business partner|hr coordinator|hr professional|human resources manager|human resources specialist|recruiter|technical recruiter|talent acquisition specialist|headhunter|"
              "supervisor|team lead|team leader|account manager|business development manager|business development representative|operations director|vice president|vp|analyst|"
              "strategist|procurement specialist|procurement manager|purchasing agent|purchasing manager|buyer|supply chain manager|supply chain analyst|logistics manager|"
              "event planner|event coordinator|events manager|wedding planner|project coordinator|program coordinator|executive director|nonprofit director|chief of staff|"
              "operations analyst|operations coordinator|management trainee|middle manager|department manager|area manager|regional manager|district manager|plant manager|"
              "facilities manager|property manager|office administrator|business manager|program director|managing partner|partner at a firm|corporate trainer|change manager",
    MEDIA: "marketer|marketing manager|marketing specialist|marketing coordinator|marketing director|marketing executive|marketing assistant|digital marketer|seo specialist|seo consultant|"
           "journalist|editor|copy editor|copywriter|reporter|news reporter|correspondent|columnist|broadcaster|news anchor|radio host|radio presenter|tv presenter|presenter|"
           "social media manager|social media specialist|social media coordinator|community manager|pr specialist|pr manager|pr executive|publicist|communications manager|"
           "communications specialist|communications officer|communications director|comms manager|content writer|content strategist|content marketer|content manager|technical writer|"
           "brand manager|brand strategist|advertising executive|ad exec|media buyer|media planner|growth marketer|email marketer|ghostwriter|speechwriter|press officer|"
           "news editor|managing editor|magazine editor|blogger|podcaster|podcast host|photojournalist|news producer|producer at a news station",
    ARTS: "artist|designer|graphic designer|web designer|ux designer|ui designer|ui/ux designer|ux/ui designer|product designer|fashion designer|interior designer|game designer|"
          "level designer|industrial designer|logo designer|motion designer|motion graphics designer|musician|singer|songwriter|singer-songwriter|rapper|drummer|guitarist|bassist|"
          "pianist|violinist|cellist|composer|producer|music producer|record producer|sound engineer|audio engineer|recording engineer|mixing engineer|mastering engineer|sound designer|"
          "audio editor|video editor|film editor|actor|actress|voice actor|voice actress|voice over artist|comedian|stand-up comedian|standup comedian|performer|dancer|choreographer|"
          "photographer|videographer|cinematographer|filmmaker|film maker|film director|writer|author|novelist|poet|screenwriter|playwright|illustrator|animator|3d artist|3d modeler|"
          "concept artist|tattoo artist|tattooist|makeup artist|painter|sculptor|potter|ceramicist|jeweler|jeweller|florist|dj|streamer|twitch streamer|content creator|youtuber|"
          "influencer|tiktoker|model|fashion model|cosplayer|magician|stage manager|stagehand|set designer|costume designer|architect|landscape architect|art director|creative director|"
          "cartoonist|comic artist|mangaka|game artist|tailor|seamstress|dressmaker|glassblower|woodcarver|luthier|session musician|orchestra musician|opera singer|conductor|"
          "music teacher and performer|stunt performer|stuntman|circus performer|puppeteer|digital artist|freelance artist|freelance illustrator|freelance photographer|"
          "wedding photographer|portrait photographer|art teacher and artist|visual artist|fine artist|muralist|calligrapher|printmaker|textile artist|set decorator|gaffer|grip|"
          "camera operator|boom operator|colorist|vfx artist|compositor|storyboard artist|character designer|web comic artist|bandleader|dj and producer",
    SALES: "cashier|sales rep|sales representative|salesman|saleswoman|salesperson|sales associate|sales assistant|retail worker|retail associate|retail assistant|shop assistant|"
           "store clerk|shop worker|stocker|shelf stacker|merchandiser|visual merchandiser|store manager|assistant store manager|retail manager|realtor|real estate agent|estate agent|"
           "real estate broker|car salesman|car salesperson|account executive|sales manager|sales engineer|sales consultant|sales executive|sales director|telemarketer|wholesaler|"
           "grocery clerk|insurance agent|insurance salesman|sdr|bdr|retail sales associate|department manager at a store|shopkeeper|pharmacy cashier|sales clerk|checkout operator|"
           "leasing agent|leasing consultant|car dealer|antique dealer|art dealer|vendor|street vendor|market trader|door to door salesman|inside sales rep|outside sales rep|"
           "territory manager|key account manager|personal shopper|beauty advisor|optical sales|parts counter|parts specialist|loan sales",
    FOOD: "chef|head chef|sous chef|pastry chef|executive chef|private chef|line cook|prep cook|short order cook|cook|server|waiter|waitress|bartender|barista|barback|busser|busboy|"
          "dishwasher|host|hostess|baker|pastry cook|butcher|fast food worker|kitchen porter|kitchen manager|kitchen assistant|restaurant manager|bar manager|hotel manager|"
          "front desk agent|front desk clerk|concierge|bellhop|bellman|sommelier|caterer|food runner|pizza maker|deli worker|cafe worker|hotel receptionist|night auditor|innkeeper|"
          "publican|brewer|brewmaster|restaurateur|mixologist|cruise ship worker|tour guide|travel agent|food server|banquet server|cocktail server|catering assistant|"
          "fast food manager|shift manager|crew member|crew trainer|line chef|grill cook|fry cook|pizza chef|sushi chef|cafe manager|hotel worker|front of house|back of house|"
          "food truck owner|chocolatier|cheesemaker|winemaker|distiller|maitre d|maître d|steward",
    TRADE: "electrician|plumber|carpenter|welder|mechanic|auto mechanic|car mechanic|diesel mechanic|aircraft mechanic|aviation mechanic|motorcycle mechanic|hvac tech|hvac technician|"
           "refrigeration technician|roofer|construction worker|laborer|labourer|general contractor|subcontractor|lineman|line worker|tradesman|tradesperson|tradie|mason|bricklayer|"
           "stonemason|machinist|cnc machinist|tool and die maker|handyman|painter and decorator|house painter|drywaller|plasterer|tiler|tile setter|flooring installer|glazier|"
           "ironworker|pipefitter|steamfitter|boilermaker|millwright|sheet metal worker|insulator|concrete finisher|heavy equipment operator|crane operator|excavator operator|"
           "apprentice|apprentice electrician|apprentice plumber|apprentice carpenter|journeyman|journeyman electrician|journeyman plumber|master electrician|master plumber|"
           "locksmith|elevator mechanic|elevator technician|cabinet maker|cabinetmaker|joiner|woodworker|blacksmith|farrier|upholsterer|auto body technician|body shop technician|"
           "panel beater|installer|solar installer|cable technician|telecom technician|appliance repair technician|foreman|site manager|construction manager|project superintendent|"
           "demolition worker|scaffolder|gas fitter|gasfitter|sparky|chippy|miner|coal miner|oil rig worker|roughneck|oilfield worker|lineworker|linesman|wind turbine technician|"
           "field technician|service technician|maintenance electrician|industrial electrician|industrial mechanic|heavy duty mechanic|small engine mechanic|boat builder|shipwright|"
           "shipfitter|pipe welder|fabricator welder|framer|finish carpenter|concrete worker|paver|asphalt worker|road worker|surveyor's assistant|well driller|septic technician|"
           "irrigation technician|pool technician|security system installer|alarm technician|glass installer|window installer|door installer|garage door technician|"
           "electrical contractor|plumbing contractor|roofing contractor|hvac installer|audio installer|car audio installer|auto technician|automotive technician|tire technician",
    WAREHOUSE: "warehouse worker|warehouse associate|factory worker|forklift driver|forklift operator|assembly line worker|assembler|production worker|production operator|machine operator|"
               "line operator|picker|packer|order picker|material handler|shipping clerk|receiving clerk|inventory clerk|inventory specialist|warehouse manager|warehouse supervisor|"
               "fulfillment associate|fulfilment associate|quality inspector|quality control inspector|qc inspector|plant operator|process operator|chemical operator|fabricator|"
               "metal fabricator|steelworker|steel worker|mill worker|cnc operator|packaging operator|loader|dock worker|longshoreman|stevedore|amazon associate|production supervisor|"
               "manufacturing technician|production technician|assembly technician|press operator|injection molding operator|sawmill worker|meatpacker|meat packer|cannery worker|"
               "textile worker|seamster|garment worker|printer operator|print technician|shipping and receiving|stock associate|inventory associate|distribution associate",
    TRANSPORT: "truck driver|trucker|delivery driver|bus driver|uber driver|lyft driver|rideshare driver|taxi driver|cab driver|cabbie|chauffeur|courier|mail carrier|mailman|"
               "postman|postwoman|postal worker|letter carrier|rural carrier|train conductor|train driver|train operator|locomotive engineer|railroad worker|railway worker|conductor on a train|"
               "pilot|airline pilot|commercial pilot|co-pilot|copilot|first officer|flight attendant|air hostess|stewardess|cabin crew|air traffic controller|ship captain|sea captain|"
               "deckhand|boat captain|ferry operator|delivery person|doordash driver|doordasher|dasher|instacart shopper|amazon driver|amazon delivery driver|ups driver|fedex driver|"
               "van driver|hgv driver|lorry driver|cdl driver|owner operator|owner-operator|tow truck driver|ambulance driver|logistics coordinator|freight broker|baggage handler|"
               "ramp agent|airport worker|dispatcher for a trucking company|truck dispatcher|delivery rider|bike courier|bicycle courier|motorcycle courier|tram driver|subway operator|"
               "bus operator|transit operator|school bus driver|limo driver|valet driver|crop duster|helicopter pilot|bush pilot|cargo pilot|merchant mariner|merchant seaman|"
               "tugboat captain|harbor pilot|ship's officer|logistics driver|freight driver|long haul trucker|otr driver|flatbed driver|tanker driver|grubhub driver|ubereats driver",
    SAFETY: "cop|police officer|policeman|policewoman|police detective|detective|firefighter|fireman|firefighter/emt|security guard|security officer|bouncer|correctional officer|"
            "corrections officer|prison guard|prison officer|jailer|sheriff|deputy sheriff|sheriff's deputy|state trooper|trooper|dispatcher|911 dispatcher|emergency dispatcher|"
            "police dispatcher|game warden|border patrol agent|customs officer|fbi agent|federal agent|special agent|private investigator|loss prevention officer|"
            "loss prevention associate|bodyguard|lifeguard|probation officer|parole officer|bailiff|constable|law enforcement officer|peace officer|patrol officer|police sergeant|"
            "police lieutenant|fire captain|fire chief|wildland firefighter|volunteer firefighter|paramedic firefighter|security supervisor|security manager|campus security|"
            "transit police|airport security|tsa agent|tsa officer|immigration officer|cbp officer|secret service agent|us marshal|deputy marshal|crime scene investigator|"
            "forensic investigator|forensic technician|detention officer|juvenile detention officer|animal control officer|code enforcement officer|ems worker",
    MILITARY: "soldier|marine|sailor|airman|infantryman|paratrooper|army officer|naval officer|military officer|service member|servicemember|navy seal|green beret|army ranger|"
              "reservist|national guardsman|guardsman|fighter pilot|military police officer|military pilot|navy pilot|air force pilot|army medic|navy corpsman|corpsman|"
              "submariner|combat engineer|artilleryman|tanker in the army|special forces operator|commissioned officer|nco|non-commissioned officer|enlisted soldier|"
              "army sergeant|drill sergeant|drill instructor|military intelligence officer|intelligence analyst in the army|signal soldier|army reservist|coast guardsman",
    GOVERNMENT: "civil servant|government employee|federal employee|state employee|city employee|county employee|municipal employee|public servant|government worker|diplomat|"
                "foreign service officer|politician|councillor|councilman|councilwoman|city council member|council member|mayor|senator|legislator|policy analyst|policy advisor|"
                "policy adviser|government official|bureaucrat|census worker|tax inspector|irs agent|public sector worker|local government officer|town planner|urban planner|"
                "city planner|government contractor|legislative aide|congressional staffer|political staffer|caseworker for the state|benefits advisor|social security officer|"
                "dmv employee|post office clerk|elections officer|civil service officer|state worker|federal worker|government analyst|program analyst|public health officer|"
                "environmental health officer|building inspector|health inspector|regulatory affairs specialist|park service employee",
    SOCIAL: "social worker|case worker|caseworker|case manager|youth worker|youth pastor|pastor|priest|minister|chaplain|nun|monk|rabbi|imam|cantor|deacon|missionary|reverend|vicar|"
            "preacher|evangelist|clergyman|clergywoman|counselor|counsellor|substance use counselor|substance abuse counselor|addiction counselor|addictions counselor|drug counselor|"
            "drug and alcohol counselor|mental health counselor|mental health counsellor|family support worker|child protective services worker|cps worker|community worker|"
            "outreach worker|peer support worker|peer specialist|nonprofit worker|charity worker|volunteer coordinator|marriage counselor|grief counselor|crisis counselor|"
            "crisis worker|victim advocate|child advocate|family advocate|housing advocate|community organizer|youth leader|youth minister|worship leader|church musician|"
            "church administrator|religious sister|lay minister|deaconess|elder in my church|sunday school teacher|camp counselor|residential counselor|shelter worker|"
            "foster care worker|adoption worker|child welfare worker|community health worker|harm reduction worker|refugee caseworker|immigration caseworker",
    OFFICE: "receptionist|secretary|admin assistant|administrative assistant|admin|office manager|data entry clerk|data entry operator|data entry specialist|clerk|office clerk|"
            "file clerk|customer service rep|customer service representative|customer service agent|customer service advisor|customer service associate|csr|call center agent|"
            "call centre agent|call center worker|call centre worker|call center rep|office worker|executive assistant|personal assistant|virtual assistant|office assistant|"
            "front desk receptionist|medical secretary|medical receptionist|administrative coordinator|scheduler|records clerk|mail clerk|typist|transcriptionist|medical transcriptionist|"
            "medical coder|medical biller|billing clerk|claims processor|insurance clerk|customer support agent|customer support specialist|customer support representative|"
            "support agent|help desk agent|administrator|administrative officer|administration officer|office administrator|team administrator|clerical worker|desk clerk|"
            "front office assistant|patient coordinator|patient access representative|unit secretary|ward clerk|operations assistant|logistics assistant|purchasing assistant|"
            "hr assistant|accounts assistant|admin officer|admin worker|office temp|temp worker|data analyst assistant|document controller|records manager|court administrator|"
            "school secretary|church secretary|legal receptionist|dental receptionist|vet receptionist|chat support agent|email support agent|technical support agent|"
            "call center representative|call centre representative|telephone operator|switchboard operator",
    SERVICE: "janitor|custodian|cleaner|house cleaner|office cleaner|commercial cleaner|housekeeper|maid|maintenance worker|maintenance man|maintenance technician|maintenance tech|"
             "building maintenance worker|groundskeeper|hairdresser|hairstylist|hair stylist|stylist|barber|cosmetologist|nail tech|nail technician|manicurist|esthetician|"
             "aesthetician|beautician|lash tech|lash technician|brow artist|masseuse|masseur|nanny|au pair|babysitter|dog walker|pet sitter|dog groomer|groomer|pet groomer|"
             "dog trainer|personal trainer|fitness instructor|fitness trainer|fitness coach|yoga teacher|yoga instructor|pilates instructor|spin instructor|life coach|butler|valet|"
             "window cleaner|pool cleaner|exterminator|pest control technician|laundry worker|dry cleaner|funeral director|mortician|embalmer|undertaker|chimney sweep|"
             "car wash attendant|detailer|car detailer|professional organizer|home organizer|room attendant|housekeeping attendant|building superintendent|super|caretaker|"
             "concierge at a building|doorman|porter|cobbler|shoe repairer|key cutter|tanning consultant|spa therapist|beauty therapist|skin therapist|wax specialist|"
             "electrologist|personal stylist|image consultant|wedding officiant|pet care worker|kennel worker|kennel attendant|animal care worker|doggy daycare worker|"
             "house sitter|handyperson|property maintenance worker|custodial worker|sanitation worker|garbage man|garbage collector|bin man|binman|refuse collector|recycling worker",
    OUTDOOR: "farmer|rancher|farmhand|farm hand|farm worker|farm labourer|dairy farmer|cattle rancher|cattleman|landscaper|gardener|horticulturist|forester|logger|lumberjack|fisherman|"
             "commercial fisherman|arborist|tree surgeon|park ranger|forest ranger|beekeeper|apiarist|shepherd|ranch hand|vineyard worker|grower|hunting guide|fishing guide|"
             "greenhouse worker|nursery worker|zookeeper|animal keeper|horse trainer|stable hand|groom at a stable|wrangler|trail guide|mountain guide|river guide|outdoor educator|"
             "wildlife biologist|conservation officer|conservationist|ecologist in the field|tree planter|orchardist|fruit picker|crop farmer|grain farmer|poultry farmer|"
             "pig farmer|sheep farmer|goat farmer|organic farmer|market gardener|groundsman|greenkeeper|golf course superintendent|landscape gardener|lawn care technician",
    ADULT: "escort|sex worker|cam girl|camgirl|cam model|webcam model|cam boy|camboy|stripper|exotic dancer|onlyfans creator|onlyfans model|of creator|porn star|pornstar|adult performer|"
           "adult content creator|adult film actress|adult film actor|porn actress|porn actor|dominatrix|pro domme|prodomme|phone sex operator|sugar baby|nsfw creator|"
           "fansly creator|content seller|camwhore|call girl|courtesan|sex worker and escort|lingerie model|fetish model|findom",
    OTHER: "translator|interpreter|sign language interpreter|courtroom interpreter|gig worker|landlord|auctioneer|appraiser|estate agent assistant|pawnbroker|surveyor of quantities|"
           "quantity surveyor|genealogist|archivist|museum curator|curator|docent|lab animal technician|clockmaker|watchmaker|gunsmith|taxidermist|sommelier trainee|"
           "professional gamer|esports player|pro gamer|professional athlete|athlete|footballer|soccer player|basketball player|baseball player|hockey player|jockey|referee|umpire|"
           "golf pro|tennis pro|professional poker player|poker player|astronaut|domain expert|ai trainer|data annotator|data labeler|freelance translator|proofreader|"
           "scuba instructor|ski instructor|snowboard instructor|surf instructor|climbing instructor|sports coach|cheerleader|mascot|caddie",
    None: "founder|co-founder|cofounder|entrepreneur|business owner|small business owner|freelancer|sole trader|sole proprietor|bar owner|restaurant owner|shop owner|store owner|"
          "salon owner|contractor|independent contractor|self-employed contractor|solopreneur|startup founder|business woman|businesswoman|businessman|business man|owner",
})
JOB_TITLES = alternation(JOBS)
OWNERS = frozenset(word for word, value in JOBS.items() if value is None)
SKILL = ("good|great|bad|decent|terrible|awful|amazing|better|best|worse|worst|home|amateur|hobby|hobbyist|aspiring|wannabe|wanna-be|future|former|ex|retired|noob|newbie|"
         "beginner|budding|failed|frustrated|would-be|prospective|fake|pretend|big|huge|massive|total|natural|born|picky|lazy|self-taught|shitty|crappy|mediocre|average|okay|ok|"
         "competent|excellent|fantastic|awesome|horrible|poor|weekend|backyard|armchair|bedroom|closet|student|trainee|wanna|sucky|lousy|messy|careful|safe|nervous|confident|avid")
MOD = rf"(?:(?!(?:{SKILL}|and|or|but|with|to|of|for|in|at|on|who|that|like|this|my|your|his|her|their|our|the|a|an|not|no|than|as|is|was)\b)[\w'./&+-]+ ){{0,3}}?"
HEADS = ("engineer|developer|dev|manager|officer|assistant|technician|tech|worker|analyst|specialist|consultant|nurse|scientist|designer|director|architect|administrator|operator|"
         "supervisor|coordinator|aide|teacher|artist|writer|editor|producer|agent|representative|rep|clerk|student|lead|instructor|therapist|counselor|counsellor|attorney|lawyer|"
         "driver|mechanic|inspector|owner|practitioner|apprentice|trainee|intern|major|graduate|grad|candidate|friend|fan|school|program|programme|degree|course|class|classes|job|"
         "position|wife|husband|girlfriend|boyfriend|partner|mom|mum|dad|parent|family|kid|daughter|son|simulator|game|citizen|character|wannabe|cosplay|costume|outfit|role|"
         "roleplay|rp|fantasy|kink|fetish|uniform|show|movie|series")
JOB = rf"({JOB_TITLES})(?![\w'&/-])(?! (?:{HEADS})s?\b)"
FIRST = r"(?=[^.!?\n]{0,80}\b(?:i|i'm|im|i've|ive|my|me|myself)\b)"
ADVERB = r"(?:(?:also|now|currently|still|actually|literally|basically|just|only|really|officially|finally|myself|technically|already|proudly|both|happily|full[- ]time|part[- ]time) )*"
BUSINESSES = table({
    FOOD: "bar|pub|restaurant|cafe|café|coffee shop|bakery|pizza shop|pizzeria|pizza place|food truck|diner|brewery|hotel|motel|b&b|bed and breakfast|catering business|catering company|"
          "taqueria|food stall|food cart|deli|bistro|sandwich shop|ice cream shop|donut shop|tea shop|bubble tea shop|burger joint|food business|restaurant business",
    SERVICE: "salon|hair salon|nail salon|barbershop|barber shop|spa|cleaning business|cleaning company|grooming business|dog grooming business|pet sitting business|dog walking business|"
             "daycare for dogs|laundromat|car wash|detailing business",
    ARTS: "tattoo shop|tattoo studio|tattoo parlor|tattoo parlour|photography business|photography studio|art studio|recording studio|design studio|design agency|dance studio|"
          "music studio|production company|record label|etsy shop|pottery studio|gallery",
    OUTDOOR: "farm|ranch|landscaping business|landscaping company|lawn care business|lawn care company|orchard|vineyard|nursery|tree service",
    SALES: "boutique|gas station|dealership|bookstore|book shop|bookshop|convenience store|liquor store|grocery store|corner shop|flower shop|gift shop|thrift store|thrift shop|"
           "clothing store|clothing brand|clothing line|pawn shop|vape shop|smoke shop|bike shop|record store|game store|comic shop|online store|online shop|ecommerce store|"
           "e-commerce store|shopify store|retail store|retail business|furniture store|jewelry store|pet store",
    TRADE: "construction company|construction business|construction firm|plumbing business|plumbing company|electrical business|electrical company|roofing company|roofing business|"
           "hvac company|hvac business|auto shop|repair shop|body shop|mechanic shop|handyman business|painting business|painting company|remodeling company|"
           "renovation business|carpentry business|welding shop|machine shop|fabrication shop|woodworking shop",
    TRANSPORT: "trucking company|trucking business|moving company|courier business|delivery business|logistics company|taxi company",
    FINANCE: "accounting firm|accounting practice|bookkeeping business|tax business|tax practice|financial advisory firm|insurance agency",
    LAW: "law firm|law practice|legal practice",
    CLINICAL: "dental practice|medical practice|vet practice|veterinary practice|veterinary clinic|clinic|private practice|therapy practice|chiropractic practice|physiotherapy clinic|pharmacy",
    TEACHING: "daycare|tutoring business|tutoring company|preschool|music school|dance school|driving school|language school",
    BUSINESS: "consulting firm|consulting business|consulting company|consultancy|staffing agency|recruitment agency|recruiting firm",
    MEDIA: "marketing agency|ad agency|advertising agency|digital agency|pr firm|pr agency|seo agency|media company|publishing company",
    SOFTWARE: "software company|software business|tech company|tech startup|saas company|web development agency|web design business|it company|it business|dev shop|game studio",
    None: "business|company|startup|small business|firm|agency|llc|shop|store|practice|own business|own company|side business|online business|franchise",
})
BUSINESS_NAMES = alternation(BUSINESSES)
MY_BUSINESS_NAMES = alternation(name for name in BUSINESSES if " " in name or name in {"business", "startup", "bakery", "boutique", "pizzeria", "brewery", "restaurant", "cafe", "café", "llc", "consultancy"})
BMOD = r"(?:(?!(?:local|favorite|favourite|usual|nearest|go-to|regular|closest|neighborhood|neighbourhood|nearby|preferred|dad's|mom's|mum's|parents'|family's|friend's|old)\b)[\w'&-]+ ){0,2}?"
FIELDS = table({
    SOFTWARE: "tech|software|cybersecurity|cyber security|data science|web development|game development|gamedev|game dev|saas|fintech|devops|it industry|it field|information technology",
    CLINICAL: "healthcare|health care|nursing|medicine|the medical field|medical field|dentistry|veterinary medicine|mental health|emergency medicine|pharma|pharmaceuticals",
    TRADE: "construction|the trades|trades|plumbing|electrical|hvac|roofing|welding|oil and gas|oilfield|the oilfield|mining|the mines|the mine",
    SALES: "retail|sales|real estate|car sales",
    FINANCE: "finance|banking|insurance|accounting|investment banking|private equity|wealth management|asset management|audit|tax|payroll|big four|big 4",
    MEDIA: "marketing|advertising|media|journalism|public relations|pr|publishing|digital marketing|social media marketing|communications|comms|broadcasting",
    FOOD: "hospitality|food service|the restaurant industry|restaurants|kitchens|fast food|the service industry|service industry|catering|the hotel industry|hotels|tourism",
    GOVERNMENT: "government|the government|local government|public service|the public sector|public sector|civil service|the civil service|politics|policy",
    MILITARY: "the military|military|the army|the navy|the air force|the marines|the marine corps|the coast guard|the national guard|the reserves|the army reserve|the armed forces",
    SAFETY: "law enforcement|policing|corrections|security|private security|the fire service|fire service|ems|emergency services",
    SCIENCE: "research|academia|science|a lab|biotech",
    TEACHING: "education|teaching|higher education|higher ed|early childhood education|childcare|child care|special education|special ed|edtech",
    BUSINESS: "consulting|management consulting|management|hr|human resources|recruiting|recruitment|operations|project management|product management|supply chain|procurement|"
              "business development|corporate|strategy",
    TRANSPORT: "logistics|trucking|transportation|aviation|shipping|delivery|freight|the airline industry|airlines|rail|railroads",
    WAREHOUSE: "manufacturing|a factory|a warehouse|warehousing|production|fulfillment|distribution",
    SOCIAL: "social work|social services|ministry|nonprofits|the nonprofit sector|non-profits|harm reduction|child welfare|addiction treatment|youth work",
    OFFICE: "customer service|customer support|admin|administration|a call center|a call centre|call centers|data entry|reception",
    ARTS: "film|entertainment|the film industry|music|the music industry|fashion|design|graphic design|animation|game design|theater|theatre|photography|tv|television|vfx|art",
    LAW: "law|legal|big law|biglaw",
    SERVICE: "beauty|the beauty industry|cosmetology|hairdressing|cleaning|janitorial|fitness|pest control|funeral services",
    OUTDOOR: "agriculture|farming|landscaping|forestry|fishing|conservation|horticulture",
    ADULT: "sex work|the adult industry|adult entertainment|porn",
})
FIELD_NAMES = alternation(FIELDS)
PLACES = table({
    CLINICAL: "hospital|clinic|medical clinic|dental office|dentist office|dentist's office|doctor's office|vet clinic|vet office|veterinary clinic|animal hospital|er|icu|nicu|"
              "emergency room|urgent care|pharmacy|surgery center|rehab center|psych ward|psychiatric hospital|mental hospital|medical center|health center|optometrist office",
    CARE: "nursing home|care home|assisted living facility|assisted living|group home|hospice|retirement home|memory care facility|home care agency",
    FOOD: "restaurant|bar|pub|hotel|motel|kitchen|cafe|café|coffee shop|bakery|pizza place|pizza shop|fast food restaurant|fast food place|diner|brewery|casino|resort|catering company|"
          "starbucks|mcdonalds|mcdonald's|burger king|wendy's|taco bell|chipotle|subway restaurant|dunkin|tim hortons|chick-fil-a|kfc|pizza hut|domino's|dominos|olive garden|"
          "applebee's|steakhouse|sushi restaurant|deli|cafeteria|food truck|cruise ship|country club|golf club|night club|nightclub|club",
    SALES: "store|grocery store|supermarket|gas station|retail store|department store|mall|car dealership|dealership|walmart|target store|costco|home depot|lowe's|lowes|best buy|"
           "ikea|tesco|aldi|lidl|kroger|publix|safeway|walgreens|cvs|sephora|ulta|bookstore|clothing store|shoe store|thrift store|furniture store|jewelry store|pet store|"
           "convenience store|liquor store|shop|boutique|phone store|electronics store|hardware store|big box store|retailer",
    WAREHOUSE: "warehouse|factory|distribution center|distribution centre|fulfillment center|fulfilment centre|amazon warehouse|plant|manufacturing plant|mill|sawmill|"
               "processing plant|meat plant|meatpacking plant|cannery|print shop|assembly plant|steel mill|paper mill|refinery",
    TEACHING: "school|elementary school|middle school|high school|primary school|secondary school|preschool|kindergarten|daycare|nursery|university|college|community college|"
              "tutoring center|learning center|library|academy|charter school|private school|public school|montessori school|boarding school|language school",
    FINANCE: "bank|credit union|accounting firm|insurance company|investment bank|hedge fund|brokerage|tax firm|big four firm|financial firm",
    LAW: "law firm|courthouse|court|public defender's office|da's office|prosecutor's office|legal aid office|legal clinic",
    OFFICE: "call center|call centre|front desk|reception desk|office|corporate office|head office",
    TRADE: "construction site|construction company|auto shop|body shop|mechanic shop|garage|machine shop|repair shop|oil rig|mine|coal mine|shipyard|power plant|car shop|tire shop",
    TRANSPORT: "airport|airline|trucking company|post office|ups|fedex|usps|royal mail|train station|bus depot|shipping company|logistics company|moving company|port",
    SAFETY: "police department|police station|fire department|fire station|prison|jail|correctional facility|detention center|sheriff's office|sheriff's department|security company",
    GOVERNMENT: "city hall|government agency|federal agency|state agency|council|dmv|social security office|embassy|consulate|town hall|county office",
    SOCIAL: "church|nonprofit|non-profit|charity|shelter|homeless shelter|women's shelter|food bank|community center|mosque|synagogue|temple|youth center|treatment center|rehab|"
            "detox center|halfway house",
    SOFTWARE: "tech company|software company|startup|tech startup|it company|game studio|data center|saas company|faang|big tech",
    MEDIA: "newspaper|magazine|news station|tv station|radio station|ad agency|advertising agency|marketing agency|pr firm|publishing house|publisher|media company",
    ARTS: "studio|recording studio|design studio|museum|gallery|theater|theatre|cinema|movie theater|film studio|animation studio|tattoo shop|tattoo studio|photography studio",
    SCIENCE: "lab|laboratory|research lab|research institute|research center|observatory|biotech company|pharma company|pharmaceutical company",
    SERVICE: "salon|hair salon|nail salon|barbershop|barber shop|spa|gym|fitness center|car wash|funeral home|dry cleaners|laundromat|kennel|doggy daycare|grooming salon",
    OUTDOOR: "farm|ranch|nursery|garden center|greenhouse|vineyard|orchard|zoo|aquarium|park|national park|golf course|stable|stables|dairy farm",
    BUSINESS: "consulting firm|consultancy|staffing agency|recruitment agency|big four",
    None: "company|firm|agency|business|corporation|small business|family business|organization|organisation|nonprofit organization|place",
})
PLACE_NAMES = alternation(PLACES)
SAID = r"(?:(?!\b(?:if|would|wish|never|not|didn't|don't|can't|won't|wouldn't|couldn't|shouldn't|used to|want|wanted|hope|should|could|might|gonna|maybe|probably|when i was)\b)[^.!?\n]){0,40}?"
OCCUPATION = [
    rf"\b{I} {ADVERB}(?:an?|the) {MOD}{JOB}",
    rf"\b(?:i|i'm|im|i am|i've been|ive been|i have been|currently|now)(?: (?:also|now|currently|still|actually|mostly|mainly|primarily|full[- ]time|part[- ]time|employed))* "
    rf"(?:work|working|employed|hired|serving|trained|qualified|certified|licensed|practicing|practising|moonlighting|freelancing|contracting) as (?:an? |the )?{MOD}{JOB}",
    rf"\bi (?:just |recently |finally |eventually )?(?:became|got hired as|was hired as|started (?:work(?:ing)? )?as|got a job as|landed a job as|got promoted to|was promoted to|"
    rf"got a position as|accepted a (?:job|position|role) as|took a job as|started a (?:new )?job as|now work as) (?:an? |the )?{MOD}{JOB}",
    rf"\bmy (?:(?!(?:previous|old|former|last|first|dream|ideal|future|next|dad's|mom's|mum's|husband's|wife's)\b)\w+ )?(?:job|career|work|role|position|title|day job|gig|profession) "
    rf"(?:as|is) (?:an? |the )?{MOD}{JOB}",
    rf"(?:^|[.!?\n:(]\s*|\b(?:hi|hey|hello|hiya|yo|hey all|hi all|hello all)\b[ ,!.]*)(?:an? |fellow |another |a fellow |also an? |as an? |just an? )?{MOD}({JOB_TITLES})s?"
    rf"(?: by (?:trade|profession|training))? here\b(?=\s*(?:[.,!:;)(\-–—]|\band\b|\bwith\b|\bwho\b|\bso\b|\bbut\b|$))",
    rf"(?:^|[.!?\n;:]\s*|\b(?:and|but|so|because|cause|cuz|since|being)\s+)as an? {MOD}{JOB}{FIRST}",    rf"\A\s*[^\n]{{0,40}}?[\[(](?:m|f|t|nb|mtf|ftm)4(?:m|f|a|r|t|nb|mf|fm|mm|ff)\w*[\])](?:(?!\b(?:for|seeking|looking|want|wanting|wants|need|needs|needing|into|craving|your|you|my|a|an|the)\b)[^\n]){{0,50}}?\b"
    rf"({JOB_TITLES})(?![\w'&/-])(?![^\n]*\b(?:rp|roleplay|role ?play|role-play|scenario|fantasy|kink|fetish|cosplay)\b)",
]
WORKPLACE = [
    rf"\b{I} {ADVERB}in (?:the )?({FIELD_NAMES})(?: industry| field| sector| department| dept| business| world| trade)?\b(?! (?:class|classes|school|course|program|degree|student|game|movie|show)\b)",
    rf"\bi(?:'ve| have)? (?:been )?(?:currently |now |also |still |mostly |mainly |just started |started |actually )?(?:work|working) (?:in|for) (?:the )?({FIELD_NAMES})"
    rf"(?: industry| field| sector| department| dept| business| world| trade)?\b(?! (?:class|classes|school|course|program|degree|student|home|homes|facility|facilities)\b)",
    rf"\bi(?:'ve| have)? (?:been )?(?:currently |now |also |still |mostly |mainly |just started |started |actually )?(?:work|working) (?:at|in|for) (?:a |an |the |my local |our local |this |our |one of the )?"
    rf"(?:(?!(?:same|this|that|my|your|his|her)\b)[\w'-]+ ){{0,2}}?({PLACE_NAMES})s?\b",
    rf"\b{I} (?:currently |now |also |still )?(?:working|employed) (?:at|in|for) (?:a |an |the )?(?:(?!(?:same|this|that|my|your)\b)[\w'-]+ ){{0,2}}?({PLACE_NAMES})s?\b",
]
OWNERSHIP = [
    rf"(?:\bi(?:'ve| have)? (?:also |now |still |currently |actually |just |recently )?(?:own|run|co-?own|opened|started|founded|operate|launched)|(?:^|[.!?\n]\s*)(?:own|run|co-?own)) "
    rf"(?:a|an|my own|my|two|three|four|several|a few|\d+|our|our own|a small|a little) {BMOD}({BUSINESS_NAMES})(?:es|s)?\b"
    rf"(?! (?:card|account|class|classes|school|trip|degree|plan|idea|name|loan|license|partner|tab|game|simulator|course|major|student)\b)",
    rf"(?<!of )(?<!mind )(?<!minding )\bmy (?:own )?(?:small |little |tiny |online |family |new )?({MY_BUSINESS_NAMES})\b"
    rf"(?! (?:card|account|class|classes|school|trip|degree|plan|idea|name|loan|license|partner|apartment|flat|tab|game|simulator|course|major|student|friends?)\b)",
]


def job_status(match):
    return "self-employed or business owner" if match.group(1) in OWNERS else "employed"


TEACH = (r"\bi (?:currently |now |also |still |actually )?teach (?:high school|middle school|elementary|kindergarten|preschool|pre-k|\w+ grade|\d+(?:st|nd|rd|th) grade|grade \d+|year \d+|"
         r"math|maths|english|science|history|art|music|pe|biology|chemistry|physics|special ed|sped|esl|efl|college|university|uni|at|in|for|classes|courses|a class|students|"
         r"undergrads|freshmen|ap|french|spanish|german|reading|kids|children|teens)\b|\bi(?:'ve| have) been teaching (?:for|since|\d|at|in)\b|\bmy (?:students|pupils|classroom|"
         r"lesson plans?|class of|kindergarteners|kinders|first graders|second graders|third graders|fourth graders|fifth graders|\d+(?:st|nd|rd|th) graders|homeroom)\b")
CARE_TERMS = r"\bmy (?:patients|patient load|caseload|case load|charge nurse|unit manager|nurse manager)\b"
DOING = {"teaching": TEACHING, "tutoring": TEACHING, "nursing": CLINICAL, "accounting": FINANCE, "bookkeeping": FINANCE, "bartending": FOOD, "serving": FOOD, "waitressing": FOOD,
         "cleaning": SERVICE, "delivery": TRANSPORT, "deliveries": TRANSPORT, "doordash": TRANSPORT, "uber": TRANSPORT, "construction": TRADE, "plumbing": TRADE, "welding": TRADE,
         "electrical": TRADE, "roofing": TRADE, "landscaping": OUTDOOR, "modeling": ARTS, "modelling": ARTS, "camming": ADULT, "photography": ARTS, "videography": ARTS,
         "freelance design": ARTS, "web design": ARTS, "graphic design": ARTS, "web development": SOFTWARE, "software development": SOFTWARE, "translation": OTHER,
         "translating": OTHER, "security": SAFETY, "retail": SALES, "sales": SALES, "consulting": BUSINESS, "marketing": MEDIA, "copywriting": MEDIA, "freelance writing": MEDIA,
         "content writing": MEDIA, "video editing": ARTS, "data entry": OFFICE, "customer service": OFFICE, "it support": SOFTWARE, "tech support": SOFTWARE, "hair": SERVICE,
         "nails": SERVICE, "makeup": ARTS, "tattooing": ARTS, "dog walking": SERVICE, "pet sitting": SERVICE, "babysitting": SERVICE, "nannying": SERVICE, "caregiving": CARE,
         "home care": CARE, "farming": OUTDOOR, "trucking": TRANSPORT, "driving": TRANSPORT, "research": SCIENCE, "social work": SOCIAL, "warehouse": WAREHOUSE}
VERBS = {"sell": SALES, "teach": TEACHING, "tutor": TEACHING, "clean": SERVICE, "drive": TRANSPORT, "cook": FOOD, "bartend": FOOD, "code": SOFTWARE, "program": SOFTWARE,
         "nurse": CLINICAL, "deliver": TRANSPORT, "repair": TRADE, "fix": TRADE, "build": TRADE, "install": TRADE, "cut": SERVICE, "tattoo": ARTS, "farm": OUTDOOR,
         "trade": FINANCE, "edit": ARTS, "photograph": ARTS, "film": ARTS, "stream": ARTS, "cam": ADULT, "dance": ARTS, "model": ARTS, "dj": ARTS, "translate": OTHER, "design": ARTS,
         "write": ARTS, "develop": SOFTWARE, "groom": SERVICE, "paint": ARTS, "sing": ARTS, "act": ARTS, "illustrate": ARTS, "animate": ARTS, "audit": FINANCE, "manage": BUSINESS,
         "consult": BUSINESS, "recruit": BUSINESS, "plumb": TRADE, "weld": TRADE, "wait": FOOD, "serve": FOOD, "bake": FOOD, "landscape": OUTDOOR}
DOING_NAMES, VERB_NAMES = alternation(DOING), alternation(VERBS)
ACTIVITY = [
    (rf"\bi ({VERB_NAMES}) (?:\w+ ){{0,3}}?(?:for a living|for work|professionally|as a job|as my job|for my job|for a job|full[- ]time|part[- ]time|for clients|on the side|as a side hustle|"
     rf"cars|houses|homes|real estate|insurance)\b",
     lambda match: VERBS[match.group(1)]),
    (rf"\b(?:i(?:'m| am)?|im|i've been|ive been) (?:currently |now |still |also )?(?:doing|do|working in|working) (?:some |freelance )?({DOING_NAMES}) (?:work |jobs? |gigs? )?"
     rf"(?:right now|now|currently|for a living|full[- ]time|part[- ]time|these days|on the side|as a side hustle|professionally|for work|for money)\b", lambda match: DOING[match.group(1)]),
    (rf"\b(?:doing|started|got|landed|have|finished|completed|in|on|accepted|start) (?:a|an|my) (?:\w+ )?(banking|finance|accounting|marketing|engineering|software|it|law|legal|nursing|"
     rf"teaching|research|design|consulting|sales|hr|government|journalism|data|audit|tax|clinical|pharmacy|medical|hospital|retail|hotel|media|tech|coding|developer|"
     rf"electrical|plumbing|carpentry|welding|mechanic|hvac) (?:internship|apprenticeship|placement|residency|co-?op|traineeship|rotation)\b",
     group({"banking": FINANCE, "finance": FINANCE, "accounting": FINANCE, "audit": FINANCE, "tax": FINANCE, "marketing": MEDIA, "journalism": MEDIA, "media": MEDIA,
            "engineering": ENGINEERING, "software": SOFTWARE, "it": SOFTWARE, "data": SOFTWARE, "tech": SOFTWARE, "coding": SOFTWARE, "developer": SOFTWARE, "law": LAW, "legal": LAW,
            "nursing": CLINICAL, "clinical": CLINICAL, "pharmacy": CLINICAL, "medical": CLINICAL, "hospital": CLINICAL, "teaching": TEACHING, "research": SCIENCE, "design": ARTS,
            "consulting": BUSINESS, "hr": BUSINESS, "sales": SALES, "retail": SALES, "hotel": FOOD, "government": GOVERNMENT, "electrical": TRADE, "plumbing": TRADE,
            "carpentry": TRADE, "welding": TRADE, "mechanic": TRADE, "hvac": TRADE})),
    (TEACH, fixed(TEACHING)),
    (CARE_TERMS, fixed(CLINICAL)),
    (r"\b(?:i'm|im|i am|i've been) an rn\b|(?:^|[.!?\n]\s*)(?:an? )?(?:\w+ )?rn here\b", fixed(CLINICAL)),
    (r"\b(?:i (?:sell|post|make|create) (?:my )?(?:own )?(?:content|nudes|custom content|customs|lewds|videos) (?:on|through|via) (?:onlyfans|fansly|my of|my onlyfans)|"
     r"(?:subscribe to|sub to|check out|join) my (?:onlyfans|fansly)|my (?:onlyfans|fansly) (?:page|account|link|subscribers|fans|is))\b", fixed(ADULT)),
]

EMPLOYED = [
    r"\bi (?:currently |now |also |still |only |mostly |usually |just |actually |normally |typically |literally |basically |both )?work (?:as|at|for|in|from home|remotely|remote|"
    r"hybrid|part[- ]time|full[- ]time|ft|pt|nights|night shift|nightshift|days|day shift|evenings|mornings|weekends|weekdays|overnights?|graveyard|swing|doubles|overtime|"
    r"\d|one|two|three|four|five|six|seven|long|every|monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tues|retail|construction|the same|on (?:a|the) (?:\w+ )?(?:team|floor|unit|ward|site|line)|"
    r"an? \d+|alone|by myself|nine|forty|40|full|part|till|until|late|early|weekend|on call|12s|10s|three 12s|close|opening|the closing|the opening|closing|opening|retail|"
    r"with (?:kids|children|patients|clients|students|customers|people with|adults with|families|veterans|seniors|the elderly)|under|directly|closely|alongside|next to|"
    r"near|around (?:\d|forty|40|50|60)|about (?:\d|forty|40|50|60)|like (?:\d|forty|40|50|60)|nearly|over (?:\d|forty|40)|more than|less than|so much|too much|a lot)\b",
    r"(?<!quit )(?<!lost )(?<!left )(?<!leave )(?<!leaving )(?<!quitting )(?<!losing )\bmy (?:boss|bosses|manager|supervisor|coworkers?|co-workers?|colleagues?|employer|company|paycheck|paychecks|pay check|paystub|pay stub|salary|wages?|weekly wage|hourly wage|hourly rate|"
    r"work hours|working hours|work schedule|work week|workweek|work day|workday|work shift|work shifts|commute|day job|full[- ]time job|part[- ]time job|current job|new job|job|"
    r"workplace|office|shift|shifts|lunch break|break room|work laptop|work phone|work computer|work email|work uniform|work friends|team lead|line manager|direct reports?|union rep|"
    r"pto|vacation days|sick days|performance review|annual review|raise|overtime|night shift|day shift|(?:\d+|ten|twelve|eight)[- ]hour (?:shifts?|workdays?|work days?|days?)|"
    r"team at work|work bestie|cubicle|desk at work|employment contract|work contract|probation period|probationary period|notice period|place of work|line of work|field of work|"
    r"clients at work|job title|work badge|work truck|work van|shift lead|shift supervisor)\b(?! (?:hunt|hunting|search|application|applications|interview|offer|is to|to|of|from)\b)",
    rf"\b(?:i|i'm|im|i am|i've|ive|me|my)\b{SAID}\b(?:at|from|after|before|off|for|leave|leaving|left|skip|miss|missed|late for|back to|home from|way to|drive to|commute to|"
    rf"walk to|headed to|heading to|go to|get to|got to|clock in at|clocked in at|busy at|stressed at|tired from|exhausted from|bored at|break at|ride to) work\b(?! (?:out|on|it)\b)",
    r"\b(?:i'm|im|i am|i've been|ive been|i have been) (?:currently |now |still |also |just |literally |actually )?(?:employed|interning|on shift|on call|on the clock|clocked in|at work|"
    r"at my job|on my break|on break|on my lunch|on lunch break|in the office today|on the night shift|on nights|working (?:as|at|in|for|full|part|from|nights|days|weekends|two|2|three|"
    r"\d|overtime|doubles|long|a lot|so much|too much|remotely|remote|hybrid|retail|construction|the night|the day|night|day|again|today|tonight|tomorrow|this weekend|right now|rn|now|"
    r"every|all|an|a))\b",
    r"\b(?:i have|i've got|i have got|i got|i landed|i accepted|i took|i started|i hold|i work|i now have|i currently have|i also have|i just got|i finally got|i recently got) "
    r"(?:an? |two |2 |three |3 |multiple |several )(?:[\w-]+ ){0,3}?(?:job|jobs|position|career)\b"
    r"(?! (?:interview|offer|application|hunt|search|fair|posting|listing)\b)",
    r"\b(?:i'?m at work|on my lunch break|for a living|i get paid|i got paid|i'm getting paid|i'm paid|i am paid|i got hired|i just got hired|i was hired|i'm on shift|i got promoted|i was promoted|my first day at work|"
    r"my first week at|my new employer|my employment|i clock in|i clocked in|i clock out|i clocked out|i'm salaried|i am salaried|i'm hourly|i'm full[- ]time|i'm part[- ]time|"
    r"i'm a full[- ]time employee|i'm an employee|as an employee|i'm staff|i'm on salary|i'm on the payroll|i'm unionized|i'm in a union|my union|i'm a union member|"
    r"i'm (?:a )?(?:salaried|hourly) (?:worker|employee)|i(?:'ve| have) been teaching|i(?:'ve| have) been nursing)\b",
    r"\b(?:i|i'm|im|me|my|while|and)\b[^.!?\n]{0,60}?\b(?:working from home|work from home|wfh|working remotely)\b",
    r"\b(?:i(?:'ve| have) been|i've|i have) (?:working|employed) (?:at|for|in|as|there|here|full|part|\d|since|the past|the last|over)\b",
    r"\b(?:after|in|with|over|for) (?:\d+|two|three|four|five|six|seven|eight|nine|ten|fifteen|twenty) years? (?:in|of) (?:the|this) (?:industry|field|business|profession|job|trade|role)\b",
    r"\b(?:ich arbeite|arbeite ich|je travaille|trabajo (?:en|como|de)|eu trabalho|trabalho (?:como|em|na|no)|lavoro (?:come|in|presso)|ik werk)\b",
    r"\b(?:i|me) (?:just )?(?:started|start|starting) (?:a |my )?(?:new )?(?:job|position|role|work)\b(?! (?:hunt|search|application|interview)\b)|\bmy (?:first|second) (?:day|week|month) at (?:my|the) (?:new )?(?:job|work|office)\b",
]
SELF_EMPLOYED = [
    r"\b(?:i'm|im|i am|i've been|ive been|i have been) (?:currently |now |also |still |fully |technically )?(?:self[- ]employed|freelancing|a freelancer|freelance|my own boss|"
    r"an independent contractor|a contractor|a sole trader|a sole proprietor|a solopreneur|an entrepreneur|a business owner|a small business owner|a (?:solo |serial |first[- ]time |startup |tech )?(?:co-?)?founder)\b",
    r"\bi (?:freelance|work for myself|run my own|own my own|am my own boss|contract for|consult for|do freelance|do contract work|take commissions|take on clients)\b",
    r"\b(?:self[- ]employed|freelancer|business owner|small business owner|founder|entrepreneur) here\b|\b(?:selbstständig|selbständig|freiberufler|freiberuflich|autônomo|autónomo|autonomo|"
    r"emprendedor|entrepreneur indépendant|auto-entrepreneur|travailleur indépendant)\b",
    r"\bmy (?:own )?(?:clients|customers) (?:pay|book|hire|commission)\b|\bmy (?:freelance|consulting|contracting|small business|side business|etsy|online) (?:business|clients|work|income|career|shop|store)\b",
]
UNEMPLOYED = [
    rf"\b{I} (?:currently |now |still |officially |technically |basically |just |recently |unfortunately |sadly )?(?:unemployed|jobless|between jobs|out of work|out of a job|without (?:a )?(?:job|work)|"
    r"on unemployment|on the dole|on jobseeker'?s|job hunting|job searching|laid off|furloughed|redundant|looking for (?:a |another |any )?(?:job|work)|searching for (?:a )?(?:job|work)|"
    r"applying (?:for|to) jobs|in between jobs|on ei)\b",
    r"\bi (?:just |recently |unfortunately |finally )?(?:lost my job|got laid off|was laid off|got let go|was let go|got fired|was fired|got made redundant|was made redundant|got terminated|"
    r"was terminated)\b",
    r"\bsince i (?:lost my job|got laid off|was laid off|was let go|got fired|was fired|quit)\b|\bi(?:'ve| have) been (?:unemployed|out of work|jobless|job hunting|job searching|looking for (?:a )?(?:job|work)|"
    r"searching for (?:a )?(?:job|work)|applying (?:for|to) jobs)\b|\bmy (?:unemployment|job search|job hunt|job applications)\b|\bunemployed (?:for|since)\b|\b(?:being|as an?) unemployed\b(?=[^.!?\n]{0,40}\b(?:i|my|me)\b)",
    r"\bi (?:can't|cannot|can not|couldn't) (?:find|get) (?:a |any )?(?:job|work)\b|\bno one (?:will|wants to) hire me\b|\bnobody (?:will|wants to) hire me\b|\bcan't get hired\b|"
    r"\b(?:\d+|hundreds of|dozens of) (?:job )?applications\b(?=[^.!?\n]{0,60}\b(?:no|not|zero|none|nothing|haven't|still)\b)",
]
RETIRED = [
    rf"\b{I}\s+(?:(?:an?|now|happily|semi|recently|newly|fully|medically|early|proudly|officially|also|old|finally|just|basically|technically|long|partially)[- ]?\s*)*retired\b"
    r"(?! (?:gamer|player|from (?:the |this )?(?:game|gaming|league|sport|competitive|scene)|streamer|lurker|redditor|account|from (?:reddit|twitter|social media)))",
    r"(?:^|[.!?\n]\s*)(?:a )?(?:\w+ ){0,1}retired (?:\w+ ){0,2}here\b|\bas an? (?:\w+ )?retiree\b|\b(?:since|after|when|now that|until|before) i (?:retired|am retired|'m retired)\b|"
    r"\bi (?:just |recently |finally )?retired (?:in|last|a few|from|at|early|after|two|three|four|five|\d|this|back|recently|young|on)\b|\bi(?:'ve| have) been retired\b|"
    r"\b(?:in|since|during|enjoying|into|throughout|after|before) my retirement\b(?! (?:account|fund|savings|plan|age|goals?|portfolio))|\bi(?:'m| am) a retiree\b|\b(?:retired|retiree) (?:myself|too)\b",
    r"\b(?:i'm|im|i am) (?:on|living on|drawing) (?:my |a )?(?:pension|social security|state pension|retirement income)\b|\bi (?:draw|collect|get) (?:my )?(?:pension|social security)\b|\b(?:i'm|im|i am) (?:\d{2}) and retired\b",
]
HOMEMAKER = [
    rf"\b{I} {ADVERB}(?:an? )?(?:full[- ]time |proud |happy |exhausted |tired )?(?:stay[- ]at[- ]home (?:mom|mum|dad|parent|wife|mother|father|husband)|sahm|sahd|sahp|homemaker|housewife|"
    r"househusband|home ?maker|home ?keeper|domestic engineer|work[- ]at[- ]home mom)\b",
    r"(?:^|[.!?\n]\s*)(?:a |fellow |another )?(?:sahm|sahd|stay[- ]at[- ]home (?:mom|mum|dad|parent)|homemaker|housewife) here\b|\bas an? (?:sahm|sahd|stay[- ]at[- ]home (?:mom|mum|dad|parent)|"
    r"homemaker|housewife)\b(?=[^.!?\n]{0,60}\b(?:i|my|me)\b)|\bi stay (?:at )?home (?:full[- ]time )?(?:with|to raise|to take care of) (?:my|the|our) (?:kids|son|daughter|baby|children|toddler|twins|boys|girls)\b|"
    r"\bi (?:quit|left|gave up) (?:my job|work|my career) to (?:stay home|raise|be a (?:sahm|stay at home))\b",
]
UNABLE = [
    rf"\b{I} {ADVERB}(?:permanently |medically |totally |partially )?(?:on disability|on ssdi|on ssi|on pip|on esa|on dsp|on odsp|on aish|on pwd|unable to work|too sick to work|too ill to work|"
    r"on long[- ]term disability|on ltd|on short[- ]term disability|on medical leave|on sick leave|on workers'? comp|on workman'?s comp|disabled and (?:can't|cannot|unable to) work|"
    r"medically retired|retired on disability|unfit (?:for|to) work)\b",
    r"\bi (?:can't|cannot|can no longer|am unable to|couldn't) (?:work|hold (?:down )?a job|keep a job)(?: anymore| any more)? (?:because|due|since|anymore|any more|with|after)\b|"
    r"\bi (?:get|receive|collect|was granted|got approved for|was approved for|finally got|won my|got awarded|was awarded|live on|survive on) (?:my )?(?:ssdi|ssi|disability|pip|esa|"
    r"disability benefits|disability payments|dsp|odsp|aish)\b|\b(?:i was |i got |was |been )?granted (?:ssdi|ssi|disability|pip)\b|\bmy (?:ssdi|ssi|disability|pip|esa|odsp|aish) "
    r"(?:check|checks|payments?|benefits|income|claim|award|hearing|case|application)\b",
]
STUDENT = [
    r"\b(?:i'm|im|i am) (?:almost |nearly |currently |now )?(?:in )?(?:my )?(?:1st|2nd|3rd|4th|first|second|third|fourth|final|last) year (?:of|in|at)\b|\bmy (?:bs|ba|bsc|major|course|courses|uni|thesis|dissertation|lecturer|lectures|semester|classes|professor|exams?|finals|coursework|midterms?|syllabus|gpa|campus|dorm|tuition|student id|student visa|transcript|academic advisor|class schedule)\b(?! (?:was|were) (?:great|fun|hard)\b)|"
    r"\bi'?m (?:studying|in school|in college|in uni|at uni|at college|at university|in university|back in school|back at school)\b|\bwhile (?:i'm |im |i am )?studying\b|\bi study\b(?! (?:the|it|this|that|them|him|her|how|why|what)\b)",
    r"\b(?:i'm|im|i am|i'm currently|im currently|i am currently) (?:a |an )?(?:(?!(?:former|ex|old|past)\b)\w+ )?(?:student|undergrad|undergraduate|freshman|sophomore|fresher|postgrad|uni student|phd student|"
    r"grad student|masters student|med student|law student|nursing student)\b|\bmy (?:classes|professor|semester|exams|finals|midterm|midterms)\b",
    r"(?:^|[.!?\n,]\s*)(?:a |an )?(?:\w+ )?student (?:from|at|of|here)\b|\bas an? (?:\w+ )?(?:college |university |uni |grad |graduate |international |phd |broke )?student\b(?=[^.!?\n]{0,60}\b(?:i|my|me)\b)|"
    r"\b(?:mein(?:em)? studium|ins studium|im studium|ich studiere|studiere ich|ich bin student(?:in)?|je suis (?:étudiant|étudiante|en (?:licence|master|fac))|soy estudiante|"
    r"sou estudante|estudo (?:na|no|em)|faço faculdade|estoy estudiando)\b",
]
STUDYING = (r"\b(?:last|this|next|my) (?:semester|trimester|quarter)\b(?= (?:of|at|i|we|was|is|has|my|in|and)\b|[.,!])|\b\d(?:st|nd|rd|th) sem(?:ester)?\b|\b(?:i'm|im|i am) (?:almost |nearly |currently |now |only )?(?:in )?(?:my )?(?:1st|2nd|3rd|4th|5th|first|second|third|fourth|final|last) year\b(?! of (?:high school|marriage|work))"
            r"|\b(?:1st|2nd|3rd|4th|first|second|third|final) year (?:electives|student|courses|exams|project)\b|\b(?:in|at) (?:nursing|engineering|law|med|medical|art|film|business|dental|pharmacy|vet|culinary|trade) school\b(?=[^.!?]*\b(?:i|my|me)\b)|\b(?:i'm|im|i am) (?:currently )?(?:in|at) (?:college|uni|university)\b"
            r"|\b(?:college|university|uni|undergrad|undergraduate|community college|first[- ]generation college|first[- ]gen(?:eration)? college) student\b(?! (?:loans?|debt|visa|athlete|housing|discount)\b)|\bmy (?:freshman|sophomore|junior|senior|first|second|third|final) (?:year|semester) (?:of|in|at) (?:college|uni|university)\b|\bmy (?:major|classes|professors?|lectures?|lecturer|uni|campus|dorm|coursework|semester|gpa|syllabus|midterms?)\b"
            r"|\b(?:i'm|im|i am) (?:currently )?(?:studying|majoring)\b|\bwhile (?:i'm |im |i am |i )?(?:studying|study)\b|\bi(?:'m| am)? (?:in|doing) (?:the|my) (?:bs|ba|bsc|bachelor'?s?|undergrad) (?:program|degree)\b|\b(?:meu|minha) (?:primeiro|segundo|terceiro|primeira) (?:ano|período|semestre)\b|\bfaço (?:uma )?(?:segunda )?graduação\b|\bich studiere\b|\b\w+ studieren\b|\bestudio (?:en la|en el|una|la)\b|\bje suis (?:étudiant|étudiante)\b"
            r"|\bi have (?:a |my )?(?:midterm|midterms|final exam|finals) (?:coming up|tomorrow|next week|this week|today)\b|\bmy (?:college|university|uni) (?:classes|courses|professor|campus|dorm|roommate|application)\b|\b(?:mein(?:em)? studium|ins studium|im studium)\b|\bstudent (?:from|at) (?:the )?(?:main campus|\w+ (?:university|college|campus))\b")
GRADUATE = rf"\b(?:grad|graduate|phd|ph\.d\.?|doctoral|masters?|master's|msc|mba|msw|ma|ms|mfa) (?:student|candidate|program|programme)\b(?! (?:loans?|debt|visa|housing)\b)|\bgrad school\b|\bgraduate school\b|\bmy (?:thesis|dissertation|advisor|supervisor|phd|doctorate|lab)\b|\bfinishing (?:my )?(?:grad|graduate|masters?|master's|phd) (?:program|degree)?\b|\bi study an? (?:jd|ma|ms|msc|masters|phd|llm)\b|\bmeiner dissertation\b|\bmi (?:tesis|doctorado|maestría)\b|\b(?:accepted|admitted) (?:in)?to (?:the |a )?(?:\w+ ){{0,3}}?(?:masters?|master's|phd|graduate|msw|mba|doctoral) program\b"
HIGH_SCHOOL = r"\b(?:i'm|im|i am) (?:still |currently )?in (?:high ?school|hs|(?:9th|10th|11th|12th) grade|year (?:9|10|11|12))\b|\b(?:high ?school|hs) (?:student|senior|junior|sophomore|freshman)\b|\b(?:i'm|im|i am) (?:a )?(?:senior|junior|sophomore|freshman) in (?:high ?school|hs)\b|\bgraduating (?:in |from )?high ?school\b|\bmy (?:high school|highschool) (?:teacher|classes|graduation|exams)\b"
STUDENT_TWINS = [STUDYING, GRADUATE, HIGH_SCHOOL]
RULES = [
    *(rule("occupation", pattern, group(JOBS), SELF_HEDGE) for pattern in OCCUPATION),
    *(rule("employment_status", pattern, job_status, SELF_HEDGE) for pattern in OCCUPATION),
    *(rule("occupation", pattern, group(FIELDS if index < 2 else PLACES), SELF_HEDGE) for index, pattern in enumerate(WORKPLACE)),
    *(rule("employment_status", pattern, fixed("employed"), SELF_HEDGE) for pattern in WORKPLACE),
    *(rule("occupation", pattern, group(BUSINESSES), SELF_HEDGE) for pattern in OWNERSHIP),
    *(rule("employment_status", pattern, fixed("self-employed or business owner"), SELF_HEDGE) for pattern in OWNERSHIP),
    *(rule("occupation", pattern, value, SELF_HEDGE) for pattern, value in ACTIVITY),
    *(rule("employment_status", pattern, fixed("employed"), SELF_HEDGE) for pattern, _ in ACTIVITY),
    *(rule("employment_status", pattern, fixed("employed"), SELF_HEDGE) for pattern in EMPLOYED),
    *(rule("employment_status", pattern, fixed("self-employed or business owner"), SELF_HEDGE) for pattern in SELF_EMPLOYED),
    *(rule("employment_status", pattern, fixed("unemployed"), CONDITIONAL) for pattern in UNEMPLOYED),
    *(rule("employment_status", pattern, fixed("retired"), SELF_HEDGE) for pattern in RETIRED),
    *(rule("employment_status", pattern, fixed("homemaker"), SELF_HEDGE) for pattern in HOMEMAKER),
    *(rule("employment_status", pattern, fixed("unable to work"), CONDITIONAL) for pattern in UNABLE),
    *(rule("employment_status", pattern, fixed("student"), SELF_HEDGE) for pattern in (*STUDENT, *STUDENT_TWINS)),
]

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
CLASSES = (r"\b(?:last|this|next|my|the) (?:semester|trimester|quarter|term)\b(?= (?:of|at|i|we|was|is|has|my|in|and|,)|[.,!])|\b\d(?:st|nd|rd|th) sem(?:ester)?\b|\b(?:i'm|im|i am) (?:almost |nearly |currently |now |only )?(?:in )?(?:my )?(?:1st|2nd|3rd|4th|5th|first|second|third|fourth|final|last) year\b(?! of (?:high school|marriage|work))"
            r"|\b(?:1st|2nd|3rd|4th|first|second|third|final) year (?:electives|student|courses|exams|project)\b|\b(?:in|at) (?:nursing|engineering|law|med|medical|art|film|business|dental|pharmacy|vet|culinary|trade) school\b(?=[^.!?]*\b(?:i|my|me)\b)|\b(?:i'm|im|i am) (?:currently )?(?:in|at) (?:college|uni|university)\b"
            r"|\b(?:college|university|uni|undergrad|undergraduate|community college|first[- ]generation college|first[- ]gen(?:eration)? college) student\b(?! (?:loans?|debt|visa|athlete|housing|discount)\b)|\bmy (?:freshman|sophomore|junior|senior|first|second|third|final) (?:year|semester) (?:of|in|at) (?:college|uni|university)\b|\bmy (?:major|classes|professors?|lectures?|lecturer|uni|campus|dorm|coursework|semester|gpa|syllabus)\b"
            r"|\b(?:i'm|im|i am) (?:currently )?(?:studying|majoring)\b|\bwhile (?:i'm |im |i am |i )?(?:studying|study)\b|\bi(?:'m| am)? (?:in|doing) (?:the|my) (?:bs|ba|bsc|bachelor'?s?|undergrad) (?:program|degree)\b|\b(?:meu|minha) (?:primeiro|segundo|terceiro|primeira) (?:ano|período|semestre)\b|\bfaço (?:uma )?(?:segunda )?graduação\b|\bich studiere\b|\b\w+ studieren\b|\bestudio (?:en la|en el|una|la)\b|\bje suis (?:étudiant|étudiante)\b")
EDUCATION_RULES = [
    rule("education", CLASSES, fixed("college student"), SELF_HEDGE),
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
FIELD_RULES = [
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

PERIODS = {"year": 1, "yr": 1, "annum": 1, "annually": 1, "yearly": 1, "month": 12, "mo": 12, "monthly": 12, "hour": 2080, "hr": 2080, "hourly": 2080, "week": 52, "wk": 52,
           "weekly": 52, None: 1}
SCALES = {"k": 1000, "thousand": 1000, "grand": 1000, "mil": 1_000_000, "million": 1_000_000, None: 1}


def income(match):
    amount = float(match.group(1).replace(",", "")) * SCALES[match.group(2)] * PERIODS[match.group(3) or match.group(4)]
    return str(int(amount)) if 1000 <= amount <= 100_000_000 else None


AMOUNT = (r"(?:about |around |roughly |over |like |~|almost |just under |just over |close to |nearly |an? |approximately |approx |more than |barely |only |just )?\$?(\d[\d,]*(?:\.\d+)?)\s*(k|thousand|grand|mil|million)?"
          r"\s*(?:(?:usd|cad|aud|eur|gbp|dollars|pounds|euros)\s*)?(?:(?:a|per|/|an?|each)\s*(year|yr|annum|month|mo|hour|hr|week|wk)\b|(annually|yearly|monthly|hourly|weekly)\b|(?=\s*(?:$|[.,!;)]|before|after|pre|post|gross|net|base|salary|total|tc|as)))")
INCOME = [
    rf"(?:\b(?:i|me) (?:currently |now |only |just |still )?(?:make|made|earn|earned|bring in|bring home|gross|grossed|net|netted|take home|clear|cleared|pull|pulled|pull in|am making|'m making|m making|"
    rf"am earning|'m earning|m earning|get paid|got paid|am paid|'m paid|am on|'m on|passed|hit|crossed|topped)|\bmy (?:salary|income|pay|base|base salary|base pay|tc|total comp|total compensation|"
    rf"take home|take-home|take home pay|comp|annual salary|gross income|net income|household income|paycheck|wage|hourly rate|rate) (?:is|was|went up to|of|:|=|is now|just hit|is around|is about|is like)|"
    rf"(?:^|[.!?\n]\s*)(?:passed|cleared|hit|crossed|made|make|earn|earning|making|grossed|netted|took home|take home))\s+{AMOUNT}",
]
RULES += [
    *EDUCATION_RULES,
    *FIELD_RULES,
    *(rule("income", pattern, income, SELF_HEDGE) for pattern in INCOME),
]
