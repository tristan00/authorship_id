import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

from .common import I, SELF_HEDGE, TAGGED, Gated, clause, fixed, group, needs, question, rule, words

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
OWNER = "self-employed or business owner"
FOUNDER = "founder"

JOBS = table({
    SOFTWARE: "software engineer|software developer|software architect|software dev|developer|programmer|coder|computer programmer|web developer|web dev|app developer|mobile developer|ios developer|"
              "android developer|front end developer|frontend developer|front-end developer|backend developer|back end developer|back-end developer|full stack developer|fullstack developer|"
              "full-stack developer|game developer|game dev|indie dev|dev|swe|sde|data scientist|data engineer|data analyst|data architect|machine learning engineer|ml engineer|ai engineer|"
              "sysadmin|system administrator|systems administrator|network administrator|network engineer|database administrator|dba|devops engineer|site reliability engineer|sre|"
              "cloud engineer|cloud architect|solutions architect|it technician|it tech|it support|it specialist|it consultant|it manager|it guy|it professional|it administrator|it analyst|"
              "systems analyst|help desk technician|helpdesk technician|help desk analyst|desktop support technician|tech support|technical support specialist|support engineer|"
              "qa engineer|qa tester|qa analyst|software tester|game tester|test engineer|cybersecurity analyst|cyber security analyst|security analyst|security engineer|penetration tester|"
              "pentester|ethical hacker|ux engineer|embedded engineer|embedded developer|firmware engineer|computer technician|tech lead|bi developer|"
              "business intelligence analyst|programmer analyst|computer scientist|blockchain developer|it worker|software consultant",
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
              "psychologist|clinical psychologist|veterinarian|vet tech|veterinary technician|veterinary nurse|optometrist|ophthalmologist|"
              "optician|midwife|dental hygienist|hygienist|physician assistant|physician associate|pa-c|gp|general practitioner|family doctor|pediatrician|paediatrician|cardiologist|"
              "dermatologist|oncologist|neurologist|gynecologist|gynaecologist|obgyn|ob-gyn|urologist|gastroenterologist|endocrinologist|pathologist|internist|hospitalist|intensivist|"
              "er doctor|er nurse|icu nurse|nicu nurse|charge nurse|travel nurse|school nurse|psych nurse|labor and delivery nurse|chiropractor|podiatrist|audiologist|dietitian|"
              "dietician|nutritionist|resident physician|medical resident|surgical resident|junior doctor|clinician|medic|combat medic|perfusionist|medical laboratory scientist|"
              "medical lab scientist|medical technologist|acupuncturist|osteopath|naturopath|healthcare professional|health care professional|healthcare worker|health care worker|"
              "nurse midwife|emergency physician|er physician|trauma surgeon|neurosurgeon|orthopedic surgeon|plastic surgeon|oral surgeon|endodontist|periodontist|prosthodontist|"
              "behavioral therapist|art therapist|music therapist|play therapist|marriage and family therapist|mft|lcsw|lpc|lmft",
    CARE: "therapist|psychotherapist|mental health therapist|cna|certified nursing assistant|nursing assistant|nurse aide|nurse's aide|caregiver|care giver|care worker|carer|care assistant|healthcare assistant|health care assistant|"
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
             "billing specialist|collections agent|finance analyst|private banker|relationship manager|credit controller|bank manager|branch manager|bank clerk|bursar|"
             "forensic accountant|enrolled agent|insurance underwriter|investment advisor|investment manager|equity research analyst|fp&a analyst",
    BUSINESS: "manager|consultant|management consultant|business consultant|strategy consultant|ceo|coo|cto|cmo|cio|project manager|program manager|programme manager|product manager|"
              "product owner|scrum master|business analyst|executive|director|managing director|operations manager|general manager|hr manager|hr specialist|hr generalist|"
              "hr business partner|hr coordinator|hr professional|human resources manager|human resources specialist|recruiter|technical recruiter|talent acquisition specialist|headhunter|"
              "supervisor|team lead|team leader|account manager|business development manager|business development representative|operations director|vice president|vp|analyst|"
              "strategist|procurement specialist|procurement manager|purchasing agent|purchasing manager|buyer|supply chain manager|supply chain analyst|logistics manager|"
              "event planner|event coordinator|events manager|wedding planner|project coordinator|program coordinator|executive director|nonprofit director|chief of staff|"
              "operations analyst|operations coordinator|management trainee|middle manager|department manager|area manager|regional manager|district manager|plant manager|"
              "facilities manager|property manager|business manager|program director|managing partner|partner at a firm|corporate trainer|change manager",
    MEDIA: "marketer|marketing manager|marketing specialist|marketing coordinator|marketing director|marketing executive|marketing assistant|digital marketer|seo specialist|seo consultant|"
           "journalist|editor|copy editor|copywriter|reporter|news reporter|correspondent|columnist|broadcaster|news anchor|radio host|radio presenter|tv presenter|presenter|"
           "social media manager|social media specialist|social media coordinator|community manager|pr specialist|pr manager|pr executive|publicist|communications manager|"
           "communications specialist|communications officer|communications director|comms manager|content writer|content strategist|content marketer|content manager|technical writer|"
           "brand manager|brand strategist|advertising executive|ad exec|media buyer|media planner|growth marketer|email marketer|ghostwriter|speechwriter|press officer|"
           "news editor|managing editor|magazine editor|blogger|podcaster|podcast host|photojournalist|news producer|producer at a news station",
    ARTS: "hairdresser|hairstylist|hair stylist|artist|designer|graphic designer|web designer|ux designer|ui designer|ui/ux designer|ux/ui designer|product designer|fashion designer|interior designer|game designer|"
          "level designer|industrial designer|logo designer|motion designer|motion graphics designer|musician|singer|songwriter|singer-songwriter|rapper|drummer|guitarist|bassist|"
          "pianist|violinist|cellist|composer|producer|music producer|record producer|sound engineer|audio engineer|recording engineer|mixing engineer|mastering engineer|sound designer|"
          "audio editor|video editor|film editor|actor|actress|voice actor|voice actress|voice over artist|comedian|stand-up comedian|standup comedian|performer|dancer|choreographer|"
          "photographer|videographer|cinematographer|filmmaker|film maker|film director|writer|author|novelist|poet|screenwriter|playwright|illustrator|animator|3d artist|3d modeler|"
          "concept artist|tattoo artist|tattooist|makeup artist|painter|sculptor|potter|ceramicist|jeweler|jeweller|florist|dj|streamer|content creator|"
          "influencer|model|fashion model|cosplayer|magician|stage manager|stagehand|set designer|costume designer|architect|landscape architect|art director|creative director|"
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
    TRADE: "landscaper|electrician|plumber|carpenter|welder|mechanic|auto mechanic|car mechanic|diesel mechanic|aircraft mechanic|aviation mechanic|motorcycle mechanic|hvac tech|hvac technician|"
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
               "metal fabricator|steelworker|steel worker|mill worker|cnc operator|packaging operator|loader|dock worker|longshoreman|stevedore|production supervisor|"
               "manufacturing technician|production technician|assembly technician|press operator|injection molding operator|sawmill worker|meatpacker|meat packer|cannery worker|"
               "textile worker|seamster|garment worker|printer operator|print technician|shipping and receiving|stock associate|inventory associate|distribution associate",
    TRANSPORT: "truck driver|trucker|delivery driver|bus driver|rideshare driver|taxi driver|cab driver|cabbie|chauffeur|courier|mail carrier|mailman|"
               "postman|postwoman|postal worker|letter carrier|rural carrier|train conductor|train driver|train operator|locomotive engineer|railroad worker|railway worker|conductor on a train|"
               "pilot|airline pilot|commercial pilot|co-pilot|copilot|first officer|flight attendant|air hostess|stewardess|cabin crew|air traffic controller|ship captain|sea captain|"
               "deckhand|boat captain|ferry operator|delivery person|"
               "van driver|hgv driver|lorry driver|cdl driver|owner operator|owner-operator|tow truck driver|ambulance driver|logistics coordinator|freight broker|baggage handler|"
               "ramp agent|airport worker|dispatcher for a trucking company|truck dispatcher|delivery rider|bike courier|bicycle courier|motorcycle courier|tram driver|subway operator|"
               "bus operator|transit operator|school bus driver|limo driver|valet driver|crop duster|helicopter pilot|bush pilot|cargo pilot|merchant mariner|merchant seaman|"
               "tugboat captain|harbor pilot|ship's officer|logistics driver|freight driver|long haul trucker|otr driver|flatbed driver|tanker driver",
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
             "building maintenance worker|groundskeeper|stylist|barber|cosmetologist|nail tech|nail technician|manicurist|esthetician|"
             "aesthetician|beautician|lash tech|lash technician|brow artist|masseuse|masseur|nanny|au pair|babysitter|dog walker|pet sitter|dog groomer|groomer|pet groomer|"
             "dog trainer|personal trainer|fitness instructor|fitness trainer|fitness coach|yoga teacher|yoga instructor|pilates instructor|spin instructor|life coach|butler|valet|"
             "window cleaner|pool cleaner|exterminator|pest control technician|laundry worker|dry cleaner|funeral director|mortician|embalmer|undertaker|chimney sweep|"
             "car wash attendant|detailer|car detailer|professional organizer|home organizer|room attendant|housekeeping attendant|building superintendent|caretaker|"
             "concierge at a building|doorman|porter|cobbler|shoe repairer|key cutter|tanning consultant|spa therapist|beauty therapist|skin therapist|wax specialist|"
             "electrologist|personal stylist|image consultant|wedding officiant|pet care worker|kennel worker|kennel attendant|animal care worker|doggy daycare worker|"
             "house sitter|handyperson|property maintenance worker|custodial worker|sanitation worker|garbage man|garbage collector|bin man|binman|refuse collector|recycling worker",
    OUTDOOR: "farmer|rancher|farmhand|farm hand|farm worker|farm labourer|dairy farmer|cattle rancher|cattleman|gardener|horticulturist|forester|logger|lumberjack|fisherman|"
             "commercial fisherman|arborist|tree surgeon|park ranger|forest ranger|beekeeper|apiarist|shepherd|ranch hand|vineyard worker|grower|hunting guide|fishing guide|"
             "greenhouse worker|nursery worker|zookeeper|animal keeper|horse trainer|stable hand|groom at a stable|wrangler|trail guide|mountain guide|river guide|outdoor educator|"
             "wildlife biologist|conservation officer|conservationist|ecologist in the field|tree planter|orchardist|fruit picker|crop farmer|grain farmer|poultry farmer|"
             "pig farmer|sheep farmer|goat farmer|organic farmer|market gardener|groundsman|greenkeeper|golf course superintendent|landscape gardener|lawn care technician",
    ADULT: "escort|sex worker|cam girl|camgirl|cam model|webcam model|cam boy|camboy|stripper|exotic dancer|porn star|pornstar|adult performer|"
           "adult content creator|adult film actress|adult film actor|porn actress|porn actor|dominatrix|pro domme|prodomme|phone sex operator|sugar baby|nsfw creator|"
           "content seller|camwhore|call girl|courtesan|sex worker and escort|lingerie model|fetish model|findom",
    OTHER: "translator|interpreter|sign language interpreter|courtroom interpreter|gig worker|landlord|auctioneer|appraiser|estate agent assistant|pawnbroker|surveyor of quantities|"
           "quantity surveyor|genealogist|archivist|museum curator|curator|docent|lab animal technician|clockmaker|watchmaker|gunsmith|taxidermist|sommelier trainee|"
           "professional gamer|esports player|pro gamer|professional athlete|athlete|footballer|soccer player|basketball player|baseball player|hockey player|jockey|referee|umpire|"
           "golf pro|tennis pro|professional poker player|poker player|astronaut|domain expert|ai trainer|data annotator|data labeler|freelance translator|proofreader|"
           "scuba instructor|ski instructor|snowboard instructor|surf instructor|climbing instructor|sports coach|cheerleader|mascot|caddie",
    FOUNDER: "founder|co-founder|cofounder|entrepreneur|business owner|small business owner|solopreneur|startup founder|business woman|businesswoman|businessman|business man",
    OWNER: "freelancer|sole trader|sole proprietor|bar owner|restaurant owner|shop owner|store owner|salon owner|contractor|independent contractor|self-employed contractor",
})
SKILL = ("good|great|bad|decent|terrible|awful|amazing|better|best|worse|worst|home|amateur|hobby|hobbyist|aspiring|wannabe|wanna-be|future|former|ex|retired|noob|newbie|"
         "beginner|budding|failed|frustrated|would-be|prospective|fake|pretend|big|huge|massive|total|natural|born|picky|lazy|self-taught|shitty|crappy|mediocre|average|okay|ok|"
         "competent|excellent|fantastic|awesome|horrible|poor|weekend|backyard|armchair|bedroom|closet|student|wanna|sucky|lousy|messy|careful|safe|nervous|confident|avid")
BLOCK = frozenset(SKILL.split("|")) | frozenset("and or but with to of for in at on who that like this my your his her their our the a an not no than as is was".split())
HEADS = frozenset(("engineer|developer|dev|manager|officer|assistant|technician|tech|worker|analyst|specialist|consultant|nurse|scientist|designer|director|architect|administrator|"
                   "operator|supervisor|coordinator|aide|teacher|artist|writer|editor|producer|agent|representative|rep|clerk|student|lead|instructor|therapist|counselor|counsellor|"
                   "attorney|lawyer|driver|mechanic|inspector|owner|practitioner|apprentice|trainee|intern|major|graduate|grad|candidate|friend|fan|school|program|programme|degree|"
                   "course|class|classes|job|position|wife|husband|girlfriend|boyfriend|partner|mom|mum|dad|parent|family|kid|daughter|son|simulator|game|citizen|character|wannabe|"
                   "cosplay|costume|outfit|role|roleplay|rp|fantasy|kink|fetish|uniform|show|movie|series").split("|"))
SOC = {"11": BUSINESS, "11-2": MEDIA, "11-2022": SALES, "11-3021": SOFTWARE, "11-3031": FINANCE, "11-3051": WAREHOUSE, "11-3071": TRANSPORT, "11-9013": OUTDOOR, "11-9021": TRADE,
       "11-903": TEACHING, "11-9041": ENGINEERING, "11-9051": FOOD, "11-9071": FOOD, "11-9081": FOOD, "11-9121": SCIENCE, "11-9131": GOVERNMENT, "11-9151": SOCIAL,
       "11-9161": SAFETY, "11-917": SERVICE, "13": BUSINESS, "13-1031": FINANCE, "13-1032": FINANCE, "13-1161": MEDIA, "13-2": FINANCE, "15": SOFTWARE, "15-2": SCIENCE,
       "15-2011": FINANCE, "15-2051": SOFTWARE, "17": ENGINEERING, "17-1011": ARTS, "17-1012": ARTS, "19": SCIENCE, "19-303": CLINICAL, "19-3051": GOVERNMENT, "21": SOCIAL,
       "23": LAW, "25": TEACHING, "25-401": OTHER, "27": ARTS, "27-3": MEDIA, "27-3043": ARTS, "27-3091": OTHER, "27-2021": OTHER, "27-2022": TEACHING, "27-2023": OTHER,
       "29": CLINICAL, "29-2052": CARE, "29-2053": CARE, "31": CARE, "33": SAFETY, "35": FOOD, "37": SERVICE, "37-3": OUTDOOR, "39": SERVICE, "39-7": FOOD, "39-9011": TEACHING,
       "41": SALES, "41-3031": FINANCE, "43": OFFICE, "43-3031": FINANCE, "43-3071": FINANCE, "43-5021": TRANSPORT, "43-5031": SAFETY, "43-505": TRANSPORT,
       "43-5071": WAREHOUSE, "43-5081": SALES, "45": OUTDOOR, "47": TRADE, "49": TRADE, "51": WAREHOUSE, "51-3011": FOOD, "51-3021": FOOD, "51-6052": ARTS, "51-9071": ARTS,
       "53": TRANSPORT, "53-7": WAREHOUSE, "53-7081": SERVICE, "55": MILITARY}
TOKEN = re.compile(r"[^\W_]+(?:['.&+][^\W_]+)*")
RUN = re.compile(r"[^\W_]+(?:['.&+][^\W_]+)*(?:[ /-]{1,3}[^\W_]+(?:['.&+][^\W_]+)*){0,9}")


def phrase(text):
    return " ".join(TOKEN.findall(text.lower()))


def soc(code):
    return next(SOC[code[:size]] for size in (7, 6, 4, 2) if code[:size] in SOC)


ONET_STOP = frozenset("owner captain player hunter hiker climber comic helper president agent advocate builder breeder boarder guide sewer anchor mixer closer checker dresser "
                      "hanger buffer roller receiver spinner tender filler seater searcher examiner deputy dealer collector trader planner picker sacker scribe messenger "
                      "cowboy caster blender spotter burner chipper bundler runner reader rider starter member observer leader mentor organizer volunteer survivor novice "
                      "delegate resident catcher grader feeder stapler wrapper winder sorter scaler shipper bagger mover pusher".split())


def onet():
    votes = {}
    for line in Path(__file__).with_name("onet_titles.tsv").read_text(encoding="utf-8").splitlines():
        code, source, title = line.split("\t")
        for name in re.split(r"[()]", title):
            if (key := phrase(name)) and (" " in key or source == "R" and len(key) > 4 and key not in ONET_STOP):
                votes.setdefault(key, Counter())[soc(code)] += 1
    return {key: ranked[0][0] for key, counts in votes.items() if len(ranked := counts.most_common(2)) == 1 or ranked[0][1] > ranked[1][1]}


ONET_TITLES = onet()
TITLES = ONET_TITLES | {phrase(word): value for word, value in JOBS.items()}
FOREIGN = {phrase(word): value for word, value in table({
    CLINICAL: "médico|médica|doctor|doctora|enfermero|enfermera|dentista|farmacéutico|farmacéutica|psicólogo|psicóloga|fisioterapeuta|enfermeiro|enfermeira|farmacêutico|farmacêutica|"
              "arzt|ärztin|zahnarzt|zahnärztin|krankenschwester|krankenpfleger|apotheker|apothekerin|psychologe|psychologin|physiotherapeut|physiotherapeutin|hebamme|médecin|"
              "infirmier|infirmière|dentiste|pharmacien|pharmacienne|psychologue|kiné|kinésithérapeute|sage-femme|medico|infermiere|infermiera|farmacista|psicologo|psicologa|"
              "lekarz|lekarzem|lekarką|pielęgniarka|pielęgniarką|pielęgniarz|pielęgniarzem|dentystą|farmaceutą|psychologiem|arts|dokter|verpleegkundige|verpleger|tandarts|psycholoog",
    CARE: "cuidador|cuidadora|altenpfleger|altenpflegerin|pflegekraft|pfleger|pflegerin|pflegehelfer|pflegehelferin|aide-soignant|aide-soignante|badante|opiekunką|opiekunem|"
          "verzorgende|verzorger",
    TEACHING: "profesor|profesora|maestro|maestra|docente|professor|professora|lehrer|lehrerin|erzieher|erzieherin|dozent|dozentin|professeur|prof|enseignant|enseignante|"
              "instituteur|institutrice|insegnante|professore|professoressa|nauczyciel|nauczycielem|nauczycielka|nauczycielką|leraar|lerares|docent|juf",
    SOFTWARE: "programador|programadora|desarrollador|desarrolladora|informático|informática|desenvolvedor|desenvolvedora|programmierer|programmiererin|entwickler|entwicklerin|"
              "softwareentwickler|softwareentwicklerin|informatiker|informatikerin|fachinformatiker|développeur|développeuse|informaticien|informaticienne|programmeur|"
              "programmeuse|programmatore|sviluppatore|sviluppatrice|informatico|programista|programistą|ontwikkelaar",
    ENGINEERING: "ingeniero|ingeniera|engenheiro|engenheira|ingenieur|ingenieurin|ingénieur|ingénieure|ingegnere|inżynier|inżynierem",
    LAW: "abogado|abogada|advogado|advogada|anwalt|anwältin|rechtsanwalt|rechtsanwältin|jurist|juristin|avocat|avocate|avvocato|avvocata|prawnik|prawnikiem|adwokat|adwokatem|"
         "advocaat",
    FINANCE: "contador|contadora|contable|buchhalter|buchhalterin|steuerberater|steuerberaterin|comptable|commercialista|contabile|księgowy|księgowym|księgowa|księgową|boekhouder",
    GOVERNMENT: "funcionario público|funcionaria pública|funcionário público|funcionária pública|servidor público|servidora pública|beamter|beamtin|fonctionnaire|"
                "funzionario pubblico|dipendente pubblico|urzędnik|urzędnikiem|urzędniczką|ambtenaar",
    SAFETY: "policía|policial|polizist|polizistin|policier|policière|poliziotto|poliziotta|policjant|policjantem|politieagent|bombero|bombera|bombeiro|bombeira|feuerwehrmann|"
            "pompier|pompière|vigile del fuoco|strażak|strażakiem|brandweerman",
    MILITARY: "soldado|militar|soldat|soldatin|soldato|żołnierz|żołnierzem|soldaat",
    TRADE: "electricista|eletricista|elektriker|électricien|elettricista|elektryk|elektrykiem|elektricien|fontanero|encanador|klempner|installateur|plombier|idraulico|hydraulik|"
           "hydraulikiem|loodgieter|carpintero|carpinteiro|tischler|schreiner|menuisier|falegname|stolarz|stolarzem|timmerman|mecánico|mecânico|mechaniker|kfz-mechatroniker|"
           "mécanicien|meccanico|mechanik|mechanikiem|monteur|albañil|pedreiro|maurer|maçon|muratore|murarz|murarzem|metselaar|handwerker|soldador|schweißer|soudeur|saldatore|"
           "spawacz|spawaczem|lasser",
    FOOD: "cocinero|cocinera|cozinheiro|cozinheira|koch|köchin|cuisinier|cuisinière|cuoco|cuoca|kucharz|kucharzem|kok|camarero|camarera|mesero|mesera|garçom|garçonete|kellner|"
          "kellnerin|serveur|serveuse|cameriere|cameriera|kelner|kelnerem|kelnerką|ober|serveerster|barista|panadero|padeiro|bäcker|boulanger|fornaio|piekarz|bakker",
    SALES: "vendedor|vendedora|verkäufer|verkäuferin|vendeur|vendeuse|commesso|commessa|sprzedawca|sprzedawcą|sprzedawczynią|verkoper|verkoopster|cajero|cajera|kassierer|"
           "kassiererin|caissier|caissière|cassiere|cassiera|kasjer|kasjerem|kasjerką",
    TRANSPORT: "camionero|camionera|caminhoneiro|motorista|fahrer|fahrerin|lkw-fahrer|busfahrer|berufskraftfahrer|chauffeur|routier|camionista|kierowca|kierowcą|"
               "vrachtwagenchauffeur|piloto|pilot|pilotin|pilote|pilota|pilotem|piloot|repartidor|entregador|zusteller|livreur",
    ARTS: "artista|künstler|künstlerin|artiste|artysta|artystą|artystką|kunstenaar|diseñador|diseñadora|designer|designerin|grafiker|grafikerin|graphiste|grafik|grafikiem|"
          "músico|música|musiker|musikerin|musicien|musicienne|musicista|muzyk|muzykiem|muzikant|fotógrafo|fotógrafa|fotograf|fotografin|photographe|fotografo|fotografa|"
          "fotografem|fotograaf|escritor|escritora|schriftsteller|schriftstellerin|écrivain|écrivaine|scrittore|scrittrice|pisarz|pisarzem|schrijver|actor|actriz|ator|atriz|"
          "schauspieler|schauspielerin|acteur|actrice|attore|attrice|aktor|aktorem|aktorką|ilustrador|ilustradora|illustrator|illustratorin|illustrateur|illustratrice|"
          "illustratore|ilustratorem|arquitecto|arquiteto|arquitecta|arquiteta|architekt|architektin|architecte|architetto|architektem",
    SCIENCE: "investigador|investigadora|pesquisador|pesquisadora|forscher|forscherin|wissenschaftler|wissenschaftlerin|chercheur|chercheuse|ricercatore|ricercatrice|"
             "naukowiec|naukowcem|onderzoeker|wetenschapper|científico|científica|cientista|doktorand|doktorandin|doctorant|doctorante|dottorando|doktorantem",
    OFFICE: "secretario|secretaria|secretária|sekretär|sekretärin|secrétaire|segretario|segretaria|sekretarka|sekretarką|secretaresse|recepcionista|rezeptionist|"
            "rezeptionistin|réceptionniste|receptionist|receptionista|recepcjonistką|bürokaufmann|bürokauffrau|administrativo|administrativa",
    SERVICE: "peluquero|peluquera|cabeleireiro|cabeleireira|friseur|friseurin|friseuse|coiffeur|coiffeuse|parrucchiere|parrucchiera|fryzjer|fryzjerem|fryzjerką|kapper|"
             "kapster|limpiador|limpiadora|reinigungskraft|niñera|babá|kindermädchen|nounou|niania|nianią",
    SOCIAL: "trabajador social|trabajadora social|assistente social|sozialarbeiter|sozialarbeiterin|sozialpädagoge|sozialpädagogin|assistant social|assistante sociale|"
            "assistente sociale|sacerdote|pfarrer|pfarrerin|prêtre|prete|ksiądz|księdzem|priester|pastor|pastora|pastoor|dominee",
    OUTDOOR: "agricultor|agricultora|campesino|campesina|fazendeiro|fazendeira|landwirt|landwirtin|bauer|bäuerin|agriculteur|agricultrice|agricoltore|rolnik|rolnikiem|boer|"
             "jardinero|jardinera|jardineiro|gärtner|gärtnerin|jardinier|giardiniere|ogrodnik|hovenier|tuinman",
    BUSINESS: "gerente|gestor|gestora|manager|managerin|geschäftsführer|geschäftsführerin|consultor|consultora|berater|beraterin|unternehmensberater|consultant|consultante|"
              "consulente|konsultant|konsultantem|adviseur|kierownik|kierownikiem|bedrijfsleider",
    WAREHOUSE: "operario|operaria|operário|operária|lagerarbeiter|lagerist|lageristin|fabrikarbeiter|magasinier|magasinière|operaio|operaia|magazynier|magazynierem|"
               "magazijnmedewerker|produktionsmitarbeiter",
    OWNER: "autónomo|autónoma|autônomo|autônoma|selbstständig|selbständig|freiberufler|freiberuflerin|unternehmer|unternehmerin|empresario|empresaria|empresário|empresária|"
           "emprendedor|emprendedora|empreendedor|empreendedora|entrepreneur|entrepreneuse|indépendant|indépendante|imprenditore|imprenditrice|libero professionista|"
           "freelancer|freelance|ondernemer|zzp'er|zelfstandige|przedsiębiorcą|przedsiębiorca",
}).items()}
FOREIGN_BLOCK = frozenset("kein keine keiner geen pas nie não no non nicht plus ex".split())
SCOPE = re.compile(r"\b(?:because|cause|cuz|since|and|but|so|as|although|though|after|before|while|until)\b")
FORMER = re.compile(r"\s*\(?\s*(?:retired|ret\.|former|ex)\b")
PRETEND = re.compile(r"\b(?:like|as if|as though|pretend|pretending|imagine)\s*$")
MARKS = re.compile(r"[\W_]*")
YOU = re.compile(r"\s*,?\s*(?:you|u|your|yourself)\b")
SELF = re.compile(r"\b(?:i|i'm|im|i've|ive|my|me|myself)\b")
ELIDED = r"(?:^|[.!?\n]\s*)(?:also |currently |still |now |unfortunately |sadly |just |recently |happily )?"
STATED = r"(?=\s*(?:$|[.,!;:)(\n-]|\b(?:for|since|and|now|right|currently|again|atm|rn|lol|but|so|too|myself|here|with|as|in|at)\b))"
ADVERB = r"(?:(?:also|now|currently|still|actually|literally|basically|just|only|really|officially|finally|myself|technically|already|proudly|both|happily|full[- ]?time|part[- ]?time) )*"


def free(text, start, hedge=SELF_HEDGE):
    start = MARKS.match(text, start).end()
    if PRETEND.search(text, max(0, start - 16), start):
        return False
    left = max(clause(text, start), start - 40)
    cut = max((found.end() for found in SCOPE.finditer(text, left, start)), default=left)
    return not hedge.search(text, cut, start)


def spot(text, start, skip, block, titles):
    if not (run := RUN.match(text, start)):
        return None
    tokens = [(token.group(), token.end()) for token in TOKEN.finditer(text, start, run.end())]
    names = [name for name, _ in tokens]
    for offset in range(len(names) if skip is None else min(skip + 1, len(names))):
        if names[offset] in block:
            return None
        for size in range(min(6, len(names) - offset), 0, -1):
            if (key := " ".join(names[offset:offset + size])) in titles:
                after = offset + size
                end = tokens[after - 1][1]
                return None if after < len(names) and names[after] in HEADS or FORMER.match(text, end) else (key, end)
    return None


@lru_cache(maxsize=1024)
def spotted(text, start, skip):
    return spot(text, start, skip, BLOCK, TITLES)


def title(text, start, skip=None, titles=TITLES):
    found = spotted(text, start, skip)
    return found and (titles[found[0]], found[1])


@lru_cache(maxsize=1024)
def ended(text, start, end):
    names = TOKEN.findall(text, start, end)
    if names and names[-1] not in TITLES and names[-1].endswith("s"):
        names[-1] = names[-1][:-1]
    for offset in range(max(0, len(names) - 6), len(names)):
        if (key := " ".join(names[offset:])) in TITLES:
            return None if BLOCK & set(names[:offset]) else key
    return None


def ending(text, start, end, titles=TITLES):
    key = ended(text, start, end)
    return key and titles[key]


def after(match, titles=TITLES):
    found = free(match.string, match.start()) and title(match.string, match.end(), titles=titles)
    return found[0] if found else None


def opener(match, titles=TITLES):
    found = title(match.string, match.end(), titles=titles)
    return found[0] if found and not YOU.match(match.string, found[1]) else None


OPENED = re.compile(r"(?:^|[.!?\n,]|\b(?:but|so|because|also))\s*$")


def opened(match, titles=TITLES):
    return opener(match, titles) if OPENED.search(match.string, max(0, match.start() - 20), match.start()) else None


def here(match, titles=TITLES):
    return ending(match.string, *match.span(1), titles)


def hired(match, titles=TITLES):
    found = title(match.string, match.end(), titles=titles)
    return found[0] if found else None


def abroad(match):
    found = spot(match.string, match.end(), 1, FOREIGN_BLOCK, FOREIGN)
    return FOREIGN[found[0]] if found else None


BUSINESSES = table({
    FOOD: "bar|pub|restaurant|cafe|café|coffee shop|bakery|pizza shop|pizzeria|pizza place|food truck|diner|brewery|hotel|motel|b&b|bed and breakfast|catering business|catering company|"
          "taqueria|food stall|food cart|deli|bistro|sandwich shop|ice cream shop|donut shop|tea shop|bubble tea shop|burger joint|food business|restaurant business",
    SERVICE: "salon|hair salon|nail salon|barbershop|barber shop|spa|cleaning business|cleaning company|grooming business|dog grooming business|pet sitting business|dog walking business|"
             "daycare for dogs|laundromat|car wash|detailing business",
    ARTS: "tattoo shop|tattoo studio|tattoo parlor|tattoo parlour|photography business|photography studio|art studio|recording studio|design studio|design agency|dance studio|"
          "music studio|production company|record label|pottery studio|gallery",
    OUTDOOR: "farm|ranch|landscaping business|landscaping company|lawn care business|lawn care company|orchard|vineyard|nursery|tree service",
    TRADE: "construction company|construction business|construction firm|plumbing business|plumbing company|electrical business|electrical company|roofing company|roofing business|"
           "hvac company|hvac business|auto shop|repair shop|body shop|mechanic shop|handyman business|painting business|painting company|remodeling company|"
           "renovation business|carpentry business|welding shop|machine shop|fabrication shop|woodworking shop",
    TRANSPORT: "trucking company|trucking business|moving company|courier business|delivery business|logistics company|taxi company",
    FINANCE: "accounting firm|accounting practice|bookkeeping business|tax business|tax practice|financial advisory firm|insurance agency",
    LAW: "law firm|law practice|legal practice",
    CLINICAL: "dental practice|medical practice|vet practice|veterinary practice|veterinary clinic|clinic|private practice|therapy practice|chiropractic practice|physiotherapy clinic|pharmacy",
    TEACHING: "daycare|tutoring business|tutoring company|preschool|music school|dance school|driving school|language school",
    MEDIA: "marketing agency|ad agency|advertising agency|digital agency|pr firm|pr agency|seo agency|media company|publishing company",
    SOFTWARE: "software company|software business|tech company|tech startup|saas company|web development agency|web design business|it company|it business|dev shop|game studio",
    BUSINESS: "business|company|startup|small business|firm|agency|llc|own business|own company|online business|franchise",
    SALES: "shop|store",
    None: "practice|side business",
})
BUSINESS_NAMES = alternation(BUSINESSES)
MY_BUSINESS_NAMES = alternation(name for name in BUSINESSES if " " in name or name in {"business", "startup", "bakery", "pizzeria", "brewery", "restaurant", "cafe", "café", "llc"})
BMOD = r"(?:(?!(?:local|favorite|favourite|usual|nearest|go-to|regular|closest|neighborhood|neighbourhood|nearby|preferred|dad's|mom's|mum's|parents'|family's|friend's|old)\b)[\w'&-]+ ){0,2}?"
FIELDS = table({
    CARE: "aged care|elder care|eldercare|elderly care|disability services|disability support|home care|home health|home health care|social care|residential care|dementia care|behavioral health|behavioural health",
    SOFTWARE: "tech|technology|ai|software|cybersecurity|cyber security|data science|web development|game development|gamedev|game dev|saas|fintech|devops|it industry|it field|information technology",
    CLINICAL: "healthcare|health care|nursing|medicine|the medical field|medical field|dentistry|veterinary medicine|mental health|emergency medicine|pharma|pharmaceuticals",
    ENGINEERING: "engineering",
    TRADE: "construction|the trades|trades|plumbing|electrical|hvac|roofing|welding|oil and gas|oilfield|the oilfield|mining|the mines|the mine",
    SALES: "retail|sales|real estate|car sales",
    FINANCE: "finance|banking|insurance|accounting|investment banking|private equity|wealth management|asset management|audit|tax|payroll",
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
    CARE: "nursing home|care home|assisted living facility|assisted living|group home|hospice|retirement home|memory care facility|home care agency",
    FOOD: "restaurant|bar|pub|hotel|motel|kitchen|cafe|café|coffee shop|bakery|pizza place|pizza shop|fast food restaurant|fast food place|diner|brewery|casino|resort|catering company|"
          "steakhouse|sushi restaurant|deli|cafeteria|food truck|cruise ship|country club|golf club|night club|nightclub|club",
    SALES: "store|grocery store|supermarket|gas station|retail store|department store|mall|car dealership|dealership|bookstore|clothing store|shoe store|thrift store|furniture store|jewelry store|pet store|"
           "convenience store|liquor store|shop|boutique|phone store|electronics store|hardware store|big box store|retailer",
    WAREHOUSE: "warehouse|factory|distribution center|distribution centre|fulfillment center|fulfilment centre|plant|manufacturing plant|mill|sawmill|"
               "processing plant|meat plant|meatpacking plant|cannery|print shop|assembly plant|steel mill|paper mill|refinery",
    TEACHING: "school|elementary school|middle school|high school|primary school|secondary school|preschool|kindergarten|daycare|university|college|community college|"
              "tutoring center|learning center|library|academy|charter school|private school|public school|montessori school|boarding school|language school",
    FINANCE: "bank|credit union|accounting firm|insurance company|investment bank|hedge fund|brokerage|tax firm|financial firm",
    LAW: "law firm|courthouse|court|public defender's office|da's office|prosecutor's office|legal aid office|legal clinic",
    OFFICE: "call center|call centre|front desk|reception desk|office|corporate office|head office",
    TRADE: "construction site|construction company|auto shop|body shop|mechanic shop|garage|machine shop|repair shop|oil rig|mine|coal mine|shipyard|power plant|car shop|tire shop",
    TRANSPORT: "airport|airline|trucking company|post office|train station|bus depot|shipping company|logistics company|moving company|port",
    SAFETY: "police department|police station|fire department|fire station|prison|jail|correctional facility|detention center|sheriff's office|sheriff's department|security company",
    GOVERNMENT: "city hall|government agency|federal agency|state agency|council|dmv|social security office|embassy|consulate|town hall|county office",
    SOCIAL: "church|nonprofit|non-profit|charity|shelter|homeless shelter|women's shelter|food bank|community center|mosque|synagogue|temple|youth center|treatment center|rehab|"
            "detox center|halfway house",
    SOFTWARE: "tech company|software company|startup|tech startup|it company|game studio|data center|saas company|big tech",
    MEDIA: "newspaper|magazine|news station|tv station|radio station|ad agency|advertising agency|marketing agency|pr firm|publishing house|publisher|media company",
    ARTS: "studio|recording studio|design studio|museum|gallery|theater|theatre|cinema|movie theater|film studio|animation studio|tattoo shop|tattoo studio|photography studio",
    SCIENCE: "lab|laboratory|research lab|research institute|research center|observatory|biotech company|pharma company|pharmaceutical company",
    SERVICE: "salon|hair salon|nail salon|barbershop|barber shop|spa|gym|fitness center|car wash|funeral home|dry cleaners|laundromat|kennel|doggy daycare|grooming salon",
    OUTDOOR: "farm|ranch|nursery|garden center|greenhouse|vineyard|orchard|zoo|aquarium|park|national park|golf course|stable|stables|dairy farm",
    BUSINESS: "consulting firm|consultancy|staffing agency|recruitment agency",
    None: "company|firm|agency|business|corporation|small business|family business|organization|organisation|nonprofit organization|place|"
          "hospital|clinic|medical clinic|dental office|dentist office|dentist's office|doctor's office|vet clinic|vet office|veterinary clinic|animal hospital|er|icu|nicu|"
          "emergency room|urgent care|pharmacy|surgery center|rehab center|psych ward|psychiatric hospital|mental hospital|medical center|health center|optometrist office",
})
PLACE_NAMES = alternation(PLACES)
IN_IT = r"\bi(?:'m| am|'ve been| have been)? (?:also |currently |now |still |actually )?work(?:ing)? in it\b(?=\s*(?:[,.;!)]|$|\b(?:and|for|as|support|now|myself|too|so|but)\b))"
WORKING_IN = (rf"(?:^|[.,;!\n]\s*|\band )(?:also |currently |now |still )?(?:work|working) in (?:the )?({FIELD_NAMES})(?: industry| field| sector| department| dept| business| world| trade)?\b"
              r"(?! (?:class|classes|school|course|program|degree|student|home|homes|facility|facilities)\b)")
OCCUPATION = [
    (rf"\b(?:{I}|and am) {ADVERB}(?:an?|the) ", after),
    (rf"\b(?:i|i'm|im|i am|i've been|ive been|i have been|currently|now)(?: (?:also|now|currently|still|actually|mostly|mainly|primarily|full[- ]?time|part[- ]?time|employed))* "
     rf"(?:work|working|employed|hired|serving|trained|qualified|certified|licensed|practicing|practising|moonlighting|freelancing|contracting)"
     rf"(?: (?:there|here|remotely|full[- ]?time|part[- ]?time)| (?:at|for|in|with)(?: [^\s.!?,;()]+){{1,5}}?)? as (?:an? |the )?", after),
    (rf"\bi (?:just |recently |finally |eventually )?(?:became|got hired as|was hired as|started (?:work(?:ing)? )?as|got a job as|landed a job as|got promoted to|was promoted to|"
     rf"got a position as|accepted a (?:job|position|role) as|took a job as|started a (?:new )?(?:job|role|position) as|now work as) (?:an? |the )?", after),
    (rf"\bmy (?:(?!(?:previous|old|former|last|first|dream|ideal|future|next|dad's|mom's|mum's|husband's|wife's)\b)\w+ )?(?:job|career|work|role|position|title|day job|gig|profession) "
     rf"(?:as|is) (?:an? |the )?", after),
    (r"\b(?<!no )(?<!não )(?<!non )(?<!nie )(?:yo soy|soy|sou|eu sou|ich bin|bin ich|je suis|sono|jestem|ik ben|ben ik)\s+(?:von beruf\s+)?(?:(?:un|una|um|uma|ein|eine|une|een)\s+)?", abroad),
    (r"\b(?:trabajo|trabajando|trabalho|trabalhando|arbeite|travaille|lavoro|pracuję|pracuje|werk|werkzaam)\s+(?:como|als|comme|come|jako)\s+(?:(?:un|una|um|uma|ein|eine|une|een)\s+)?", abroad),
]
OPENER = r"(?:^|[.!?\n]\s*)(?:as|being|speaking as) an? "
GERUND = r"\bworking as (?:an? |the )?"
NAMED_REST = (r"\s+(?!(?:not|so|very|sorry|sure|afraid|guessing|confused|curious|glad|happy|tired|just|also|like|really|honestly|currently|still|okay|ok|fine|good|here|back|done|new|old|aware|thinking|wondering|asking|saying|going|trying|looking|getting|being|talking|actually|always|never|now|single|married|alone|well|but|and|or)\b)"
              r"\**[a-z][\w.'-]*(?: [a-z][\w.'-]*)?\**\s?,\s*(?:an? |the )")
NAMED = [r"i(?<!\wi)(?:'m|m| am)" + NAMED_REST, r"my(?<!\wmy) name(?: is|'s)" + NAMED_REST]
MENTIONS = [
    (r"(?:^|[.!?\n:(,]\s*|\s[-–—]\s+|\b(?:hi|hey|hello|hiya|yo|greetings)\b[ ,!.]*)(?:an? |fellow |another |a fellow |also an? |as an? |just an? )?((?:[\w'&/.+-]+ ){1,6}?)"
     r"(?:by (?:trade|profession|training) )?here\b(?=\s*(?:[^\w\s]|\b(?:and|with|who|so|but|in|from|too|lol|haha|for)\b|$))", here),
    (r"\b(?:as|being|speaking as) an? ", opened),
    (r"\[\s*(?:for hire|hire me)\s*\][\W_]*", hired),
    (r"(?:^|\n)[^\w\n]*(?:occupation|profession|job|work|career|job title|current job|current role)[^\w\n]{0,4}?[:=][^\w\n]*", hired),
    (r"(?:^|[.!?\n]\s*)currently (?:working as )?an? ", opener),
    (r"(?:^|[.!?\n]\s*)((?:[\w'&/.+-]+ ){1,6}?)by (?:trade|profession)\b", here),
    (r"\b(?:we(?:'re| are)|and i are|and me are|and myself are) both ((?:[\w'&/.+-]+ ){0,3}?[\w'&/.+-]+s)\b", here),
]
LEAD = (r"(?:^|\n)[ \t>*#\\-]*(?:(?:\d{2}\s?(?:yo|y/o|yrs? old|years? old)|\d{2}\s?[mf]?|[mf]\s?\d{2}|[\[(][\w /+-]{1,12}[\])]|#[\w/-]+|[-–—|,]+)[ \t]*)*+(?:(?:also|just|another|fellow|a|an) )*"
        r"(?:(?:married|professional|licensed|certified|registered|senior|junior|qualified|experienced|freelance|hung|single|divorced|tired|exhausted) )*")
PERSONA = re.compile(r"\d{2}\s?[mf]\b|\b[mf]\s?\d{2}\b|\b[mf]4[a-z]+\b|\d{2}\s?(?:yo|y/o|yrs? old|years? old)\b")
STRICT_END = re.compile(r"[ \t]*(?:$|[.,!;|(\n]|(?:and|by trade|by profession|here)\b)")
PERSONA_END = re.compile(r"[ \t]*(?:$|[.,!;|(\n-]|(?:and|by trade|by profession|here|who|with|getting|looking|seeking|available|from|in)\b)")


def fragment(match, titles=TITLES):
    text, lead = match.string, match.group()
    persona = PERSONA.search(lead)
    if "hir" in lead or not (found := title(text, match.end(), 2 if persona else 0, titles=titles)) or question(text, found[1]):
        return None
    if persona:
        return found[0] if PERSONA_END.match(text, found[1]) else None
    return found[0] if STRICT_END.match(text, found[1]) and (SELF.search(text, found[1], found[1] + 120) or len(text) < 60) else None


CELL = r"[,|][ \t]*(?:an? )?"
WANTED = re.compile(r"\b(?:you|your|you're|u|ur|looking|seeking|want|wanted|wanting|prefer|preferably|ideally|bonus|like|into|for)\b")


@lru_cache(maxsize=256)
def marks(text, line):
    end = len(text) if (stop := text.find("\n", line)) < 0 else stop
    persona, wanted = PERSONA.search(text, line, end), WANTED.search(text, line, end)
    return persona.end() if persona else end + 1, wanted.start() if wanted else end


def celled(match, titles=TITLES):
    text, start = match.string, match.start()
    persona, wanted = marks(text, text.rfind("\n", 0, start) + 1)
    if persona > start or wanted < start:
        return None
    found = title(text, match.end(), 0, titles=titles)
    return found[0] if found and STRICT_END.match(text, found[1]) else None


WORKPLACE = [
    rf"(?:\bi(?:(?:(?:'ve| have) (?:been )?(?:currently |now |also |still |mostly |mainly |actually )?(?:work|working|worked)|(?:'m| am)? (?:currently |now |also |still |mostly |mainly |just started |started |actually )?(?:work|working|employed)) (?:(?:in|for) )?(?:the |an? )?(?:(?!(?:same|this|that|my|your|his|her|their|our|other|different|any|every|no)\b)[\w-]+ ){{0,2}}?|(?:'m| am|m|'ve been| have been) (?:currently |now |also |still |actually |mostly |mainly )?in (?:the )?)|\bas (?:someone|somebody) (?:who (?:also |currently |now |still |actually )?(?:works|has worked) |working )?in (?:the )?)({FIELD_NAMES})"
    rf"(?: industry| field| sector| department| dept| business| world| trade)?\b(?! (?:class|classes|school|course|program|degree|student|home|homes|facility|facilities)\b)",
    rf"\bi(?:'ve| have)? (?:been )?(?:currently |now |also |still |mostly |mainly |just started |started |actually )?(?:work|working) (?:at|in|for) (?:a |an |the |my local |our local |this |our |one of the )?"
    rf"(?:(?!(?:same|this|that|my|your|his|her)\b)[\w'-]+ ){{0,2}}?({PLACE_NAMES})s?\b",
    rf"\b{I} (?:currently |now |also |still )?(?:working|employed) (?:at|in|for) (?:a |an |the )?(?:(?!(?:same|this|that|my|your)\b)[\w'-]+ ){{0,2}}?({PLACE_NAMES})s?\b",
]
OWNERSHIP = [
    rf"(?:\b(?:i|we)(?:'ve| have)? (?:also |now |still |currently |actually |just |recently )?(?:own and run|own and operate|run and own|own|run|co-?own|opened|started|founded|operate|launched)|(?:^|[.!?\n,]\s*)(?:own and run|own|run|co-?own)) "
    rf"(?:a|an|my own|my|two|three|four|several|a few|\d+|our|our own|a small|a little) {BMOD}({BUSINESS_NAMES})(?:es|s)?\b"
    rf"(?! (?:card|account|class|classes|school|trip|degree|plan|idea|name|loan|license|partner|tab|game|simulator|course|major|student)\b)",
    rf"(?=my )(?<!of )(?<!mind )(?<!minding )\bmy (?:own )?(?:small |little |tiny |online |family |new )?({MY_BUSINESS_NAMES})\b"
    rf"(?! (?:card|account|class|classes|school|trip|degree|plan|idea|name|loan|license|partner|apartment|flat|tab|game|simulator|course|major|student|friends?)\b)",
]


def occupied(find):
    return lambda match: BUSINESS if (value := find(match)) == FOUNDER else None if value == OWNER else value


def employed(find):
    return lambda match: None if (value := find(match)) is None else OWNER if value in (OWNER, FOUNDER) else "employed"


ROLEPLAY = re.compile(r"\b(?:rp|roleplay|role play|role-play|roleplaying|role playing)\b")


@lru_cache(maxsize=64)
def roleplay(text):
    return bool(ROLEPLAY.search(text))


def scoped(value, hedge=SELF_HEDGE, played=False):
    return lambda match: value(match) if free(match.string, match.start(), hedge) and (played or not roleplay(match.string)) else None


def said(attribute, pattern, value, hedge=SELF_HEDGE):
    return rule(attribute, pattern, scoped(value, hedge), TAGGED)


TEACH = (r"\bi(?:'ve| have)? (?:currently |now |also |still |actually )?(?:teach|taught) (?:both )?(?:high school|middle school|elementary|kindergarten|preschool|pre-k|\w+ grade(?:rs)?|\d+(?:st|nd|rd|th) grade(?:rs)?|grade \d+|year \d+|"
         r"math|maths|english|science|history|art|music|pe|biology|chemistry|physics|special ed|sped|esl|efl|college|university|uni|at|in|for|classes|courses|a class|students|"
         r"undergrads|freshmen|ap|french|spanish|german|reading|kids|children|teens)\b|\bi(?:'ve| have) been teaching (?:for|since|\d|at|in)\b|"
         r"\bi(?:'m| am|'ve been| have been)? (?:currently |now |also |still |actually |mostly |mainly )?(?:teach|teaching) (?!(?:me|you|him|her|them|myself|yourself|themselves|it|that|this|us|"
         r"my (?:\w+ )*?(?:kids?|son|daughter|children|baby|girl|boy|dog|cat|puppy|wife|husband|partner|friends?))\b)[a-z]|\bmy (?:students|pupils|classroom|"
         r"lesson plans?|class of|kindergarteners|kinders|first graders|second graders|third graders|fourth graders|fifth graders|\d+(?:st|nd|rd|th) graders|homeroom)\b")
CARE_TERMS = r"\bmy (?:patients|patient load|caseload|case load|charge nurse|unit manager|nurse manager)\b"
VERBS = {"sell": SALES, "teach": TEACHING, "tutor": TEACHING, "clean": SERVICE, "drive": TRANSPORT, "cook": FOOD, "bartend": FOOD, "code": SOFTWARE, "program": SOFTWARE,
         "nurse": CLINICAL, "deliver": TRANSPORT, "repair": TRADE, "fix": TRADE, "build": TRADE, "install": TRADE, "cut": SERVICE, "tattoo": ARTS, "farm": OUTDOOR,
         "trade": FINANCE, "edit": ARTS, "photograph": ARTS, "film": ARTS, "stream": ARTS, "cam": ADULT, "dance": ARTS, "model": ARTS, "dj": ARTS, "translate": OTHER, "design": ARTS,
         "write": ARTS, "develop": SOFTWARE, "groom": SERVICE, "paint": ARTS, "sing": ARTS, "act": ARTS, "illustrate": ARTS, "animate": ARTS, "audit": FINANCE, "manage": BUSINESS,
         "consult": BUSINESS, "recruit": BUSINESS, "plumb": TRADE, "weld": TRADE, "wait": FOOD, "serve": FOOD, "bake": FOOD, "landscape": OUTDOOR}
VERB_NAMES = alternation(VERBS)
ACTIVITY = [
    (rf"\bi ({VERB_NAMES}) (?:\w+ ){{0,3}}?(?:for a living|for work|professionally|as a job|as my job|for my job|for a job|full[- ]?time|part[- ]?time|for clients|on the side|as a side hustle|"
     rf"cars|houses|homes|real estate|insurance)\b",
     lambda match: VERBS[match.group(1)]),
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
    (r"\b(?:i'm|im|i am|i've been) an rn\b", fixed(CLINICAL)),
    (r"(?:^|[.!?\n]\s*)(?:an? )?(?:\w+ )?rn here\b", fixed(CLINICAL)),
]
ROLE_TERMS = [
    (r"\bi(?:'ve| have)? (?:see|saw|treat|treated|have|had|'ve had|have had) (?:\w+ )?patients\b|\ba patient of mine\b|\bour patients\b(?=[^.!?\n]*\b(?:i|i'm|i've|my|me)\b)", fixed(CLINICAL)),
    (r"\bmy (?:(?!(?:fellow|former|old|future|international|college|own)\b)[\w-]+ ){1,3}?students\b|\ba student of mine\b", fixed(TEACHING)),
]
CODING = (r"\bi(?:'ve| have)?(?: been)? (?:writing|write|wrote|ship|shipping) (?:code|software)\b|\b\d+\+? yoe\b|\bi(?:'m| am)? (?:a |an )?(?:software|computer|tech) (?:guy|person|nerd by trade)\b")

EMPLOYED = [
    r"\bi (?:currently |now |also |still |only |mostly |usually |just |actually |normally |typically |literally |basically |both )?work (?:as|at|for|in|from home|remotely|remote|"
    r"hybrid|part[- ]?time|full[- ]?time|ft|pt|nights|night shift|nightshift|days|day shift|evenings|mornings|weekends|weekdays|overnights?|graveyard|swing|doubles|overtime|"
    r"\d|one|two|three|four|five|six|seven|long|every|monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tues|retail|construction|the same|on (?:a|the) (?:\w+ )?(?:team|floor|unit|ward|site|line)|"
    r"an? \d+|a few|a couple|several|odd|crazy|irregular|rotating|split|shifts|alone|by myself|nine|forty|40|full|part|till|until|late|early|weekend|on call|12s|10s|three 12s|close|opening|the closing|the opening|closing|opening|retail|"
    r"with (?:kids|children|patients|clients|students|customers|people with|adults with|families|veterans|seniors|the elderly)|under|directly|closely|alongside|next to|"
    r"near|around (?:\d|forty|40|50|60)|about (?:\d|forty|40|50|60)|like (?:\d|forty|40|50|60)|nearly|over (?:\d|forty|40)|more than|less than|so much|too much|a lot)\b",
    r"(?=my )(?<!quit )(?<!lost )(?<!left )(?<!leave )(?<!leaving )(?<!quitting )(?<!losing )\bmy (?:day job|full[- ]?time job|part[- ]?time job|current job|new job|job)\b"
    r"(?! (?:hunt|hunting|search|application|applications|interview|offer|is to|to|of|from)\b)",
    r"\b(?:i have|i've got|i have got|i got|i landed|i accepted|i took|i started|i hold|i work|i now have|i currently have|i also have|i just got|i finally got|i recently got) "
    r"(?:an? |two |2 |three |3 |multiple |several )(?:[\w-]+ ){0,3}?(?:job|jobs|position|career)\b"
    r"(?! (?:interview|offer|application|hunt|search|fair|posting|listing)\b)",
    r"\bi (?:[\w'-]+ ){1,4}?for a living\b|\b(?:i'?m at work|i get paid|i got paid|i'm getting paid|i'm paid|i am paid|i got hired|i just got hired|i was hired|i'm on shift|i got promoted|i was promoted|my first day at work|"
    r"my first week at|my new employer|my employment|i clock in|i clocked in|i clock out|i clocked out|i'm salaried|i am salaried|i'm hourly|i'm full[- ]?time|i'm part[- ]?time|"
    r"i'm a full[- ]?time employee|i'm an employee|i'm staff|i'm on salary|i'm on the payroll|i'm unionized|i'm in a union|my union|i'm a union member|"
    r"i'm (?:a )?(?:salaried|hourly) (?:worker|employee)|i(?:'ve| have) been teaching|i(?:'ve| have) been nursing)\b",
    r"\b(?:i|i'm|im|me|my|while|and)\b[^.!?\n]{0,60}?\b(?:working from home|work from home|wfh|working remotely)\b",
    r"\b(?:i'm|im|i am) (?:currently |now |still |gainfully |fully )?employed\b(?! (?:as|by|at|in)\b)|"
    r"\b(?:i'm|im|i am) (?:currently |now )?on (?:maternity|paternity|parental|mat) leave\b|\bmy (?:maternity|paternity|parental|mat) leave\b|\bmy (?:9 ?(?:-|to) ?5|nine to five)\b|"
    r"\bi(?:'ve| have) been working (?:at|for|in|as|there|here|full[- ]?time|part[- ]?time|nights|from home|remotely|\d|since)\b|"
    r"\bi(?:'m| am) (?:currently |now |still )?working (?:full[- ]?time|part[- ]?time|nights|days|weekends|from home|remotely|remote|two jobs|\d+ hours|overtime|doubles|tonight|tomorrow|this weekend|a double)\b|"
    r"\b(?:i|i'm|im|me|my|while)\b[^.!?\n]{0,40}?\bworking (?:a |the |my )?(?:night|day|graveyard|overnight|double|evening|morning|closing|opening|swing|\d+[- ]hour|twelve[- ]hour) shifts?\b|"
    r"\bmy work (?:pays|offers|gives|provides|covers|requires|makes me|schedule|load|week|day|place)\b",
    r"\bi (?:also |currently |now |still |mainly |mostly |actually |professionally )?work (?:with|on) (?!(?:you|him|her|them|my|me|myself|it|this|that|what|whatever|anything|everything|something|someone|somebody|people who|a therapist|the assumption)\b)[a-z]",
    r"\b(?:i|me) (?:just )?(?:started|start|starting) (?:a |my )?(?:new )?(?:job|position|role|work)\b(?! (?:hunt|search|application|interview)\b)|\bmy (?:first|second) (?:day|week|month) at (?:my|the) (?:new )?(?:job|work|office)\b",
    r"\bi (?:also |currently |still |now )?work(?: there| here)?\b(?=\s*(?:[.,!;)]|$|\b(?:and|but|so|too|as well|now)\b))",
    r"\b(?<!no )(?:yo trabajo|trabajo en (?:un|una|el|la)|trabalho (?:em|na|no|numa|num)|je travaille (?:dans|chez|à|au|en|pour)|ich arbeite (?:bei|in|im|als|für)|"
    r"lavoro (?:in|presso|come|per)|ik werk (?:bij|in|als|voor)|pracuję (?:w|jako|na|dla)|jeg (?:arbejder|jobber|arbeider) (?:som|i|på|hos|for)|jag (?:jobbar|arbetar) (?:som|i|på|hos|med)|"
    r"lucrez (?:la|ca|în|in|pentru)|pracuji (?:v|ve|jako|na|pro)|työskentelen|я работаю|çalışıyorum)\b",
    r"\b(?:mi|meu|minha|mein|meine|meinem|meinen|mon|il mio|la mia|mia|mój|moja|mojej|mijn|mitt) (?:trabajo|trabalho|emprego|empleo|job|jobb|arbeit|arbeitsplatz|travail|boulot|lavoro|praca|pracy|werk|baan|jefe|jefa|chefe|chefa|chef|chefin|gerente|capo)\b",
]
GOT_JOB = r"\b(?:got|landed|accepted|offered) the job\b"
EMPLOYED += [
    r"\b(?:we|and i) (?:both|each|all) (?:work|have jobs|have full[- ]?time jobs|are employed|wfh|work from home|work remotely|work full[- ]?time|work part[- ]?time)\b",
    GOT_JOB,
]
WORKING_ROLE = r"working (?:mom|mum|mother|dad|father|parent|professional|adult|woman|man)\b(?! (?:to|on|in|at|for)\b)"
WORKING_LINES = [
    r"i(?<!\wi)(?:'m|m| am)(?: also| now| currently| just)? (?:an? )?(?:[\w-]+ ){0,2}?" + WORKING_ROLE,
    r"(?:(?m:^)[ \t>*#\\-]*|,[ \t]*)(?:(?:\d{2}\s?[mf]?|[mf]4[a-z]+|[mf]\s?\d{2}|[\[(][\w /+-]{1,12}[\])])[ \t,|-]*)*+(?:an? )?(?:[\w-]+ ){0,2}?" + WORKING_ROLE,
]
EMPLOYED += WORKING_LINES
SELF_EMPLOYED = [
    ELIDED + r"(?:self[- ]employed|freelancer|sole trader)\b" + STATED,
    r"\b(?:i|i'm|im|i am|i've|ive|me|myself)\b[^.!?\n]{0,40}?\b(?:self[- ]employed|work for myself|working for myself|freelance work|freelance gigs|freelancing|freelancer)\b|"
    r"\bi (?:also |currently |now |mostly )?(?:freelance|do freelance)\b",
    r"\b(?:solo|indie) (?:game )?dev(?:eloper)?\b|\bsolo developing\b|\b1099 (?:worker|contractor|employee|income|job)\b",
    r"\b(?:i'm|im|i am|i've been|ive been|i have been) (?:currently |now |also |still |fully |technically )?(?:self[- ]employed|freelancing|a freelancer|freelance|my own boss|"
    r"an independent contractor|a contractor|a sole trader|a sole proprietor|a solopreneur|an entrepreneur|a business owner|a small business owner|a (?:solo |serial |first[- ]time |startup |tech )?(?:co-?)?founder)\b",
]
UNEMPLOYED = [
    ELIDED + r"(?:unemployed|jobless|out of work|between jobs)\b" + STATED,
    rf"\b{I} (?:currently |now |still |officially |technically |basically |just |recently |unfortunately |sadly )?(?:unemployed|jobless|between jobs|out of work|out of a job|without (?:a )?(?:job|work)|"
    r"on unemployment|on the dole|on jobseeker'?s|job hunting|job searching|laid off|furloughed|redundant|looking for (?:a |another |any )?(?:job|work)|searching for (?:a )?(?:job|work)|"
    r"applying (?:for|to) jobs|in between jobs|on ei)\b",
    r"\bi (?:just |recently |unfortunately |finally )?(?:lost my job|got laid off|was laid off|got let go|was let go|got fired|was fired|got made redundant|was made redundant|got terminated|"
    r"was terminated)\b",
    r"\bi(?:'ve| have) been (?:unemployed|out of work|jobless|job hunting|job searching|looking for (?:a )?(?:job|work)|"
    r"searching for (?:a )?(?:job|work)|applying (?:for|to) jobs)\b|\bmy (?:unemployment|job search|job hunt|job applications)\b|\b(?:being|as an?) unemployed\b(?=[^.!?\n]{0,40}\b(?:i|my|me)\b)",
    r"\bi (?:can't|cannot|can not|couldn't) (?:find|get) (?:a |any )?(?:job|work)\b|\bno one (?:will|wants to) hire me\b|\bnobody (?:will|wants to) hire me\b|\bcan't get hired\b|"
    r"\b(?:\d+|hundreds of|dozens of) (?:job )?applications\b(?=[^.!?\n]{0,60}\b(?:no|not|zero|none|nothing|haven't|still)\b)",
    r"\b(?:cerco lavoro|busco trabajo|busco empleo|procuro emprego|estou desempregad[oa]|estoy desemplead[oa]|soy desemplead[oa]|je cherche du travail|je suis au chômage|"
    r"ich bin arbeitslos|ich suche arbeit|jestem bezrobotn[ya]|ik ben werkloos|sono disoccupat[oa])\b",
]
RETIRED = [
    ELIDED + r"(?:semi[- ])?retired(?=\s*(?:$|[.,!;\n]|\b(?:now|last|since|in \d|and)\b))",
    rf"\b{I}\s+(?:(?:an?|now|happily|semi|recently|newly|fully|medically|early|proudly|officially|also|old|finally|just|basically|technically|long|partially)[- ]?\s*)*retired\b"
    r"(?! (?:gamer|player|from (?:the |this )?(?:game|gaming|league|sport|competitive|scene)|streamer|lurker|redditor|account|from (?:reddit|twitter|social media)))",
    r"(?:^|[.!?\n]\s*)(?:a )?(?:\w+ ){0,1}retired (?:\w+ ){0,2}here\b",
    r"\bas an? (?:\w+ )?retiree\b|\b(?:since|after|when|now that|until|before) i (?:retired|am retired)\b|"
    r"\bi (?:just |recently |finally )?retired (?:in|last|a few|from|at|early|after|two|three|four|five|\d|this|back|recently|young|on)\b|\bi(?:'ve| have) been retired\b|"
    r"\b(?:in|since|during|enjoying|into|throughout|after|before) my retirement\b(?! (?:account|fund|savings|plan|age|goals?|portfolio))|\bi(?:'m| am) a retiree\b|\b(?:retired|retiree) (?:myself|too)\b",
    r"\(\s*retired\s*\)|\b(?:since|after|when|now that|until|before) we (?:retired|'re retired|are retired)\b|\A[^\n]{0,60}?[\[(][mf]4[a-z]+[\])][^\n]{0,40}?\bretired\b",
    r"\b(?:i'm|im|i am) (?:on|living on|drawing) (?:my |a )?(?:pension|social security|state pension|retirement income)\b|\bi (?:draw|collect|get) (?:my )?(?:pension|social security)\b|\b(?:i'm|im|i am) (?:\d{2}) and retired\b",
]
HOMEMAKER = [
    rf"\b{I} {ADVERB}(?:an? )?(?:full[- ]?time |proud |happy |exhausted |tired )?(?:stay[- ]at[- ]home (?:mom|mum|dad|parent|wife|mother|father|husband)|sahm|sahd|sahp|homemaker|housewife|"
    r"househusband|home ?maker|home ?keeper|domestic engineer|work[- ]at[- ]home mom)\b",
    r"(?:^|[.!?\n]\s*)(?:\d{2}\s?[mf]?\s+)?(?:sahm|sahd|stay[- ]at[- ]home (?:mom|mum|dad|parent)|homemaker|housewife)\b|(?:^|[.!?\n]\s*)(?:a |fellow |another )?(?:sahm|sahd|stay[- ]at[- ]home (?:mom|mum|dad|parent)|homemaker|housewife) here\b",
    r"\bas an? (?:sahm|sahd|stay[- ]at[- ]home (?:mom|mum|dad|parent)|"
    r"homemaker|housewife)\b(?=[^.!?\n]{0,60}\b(?:i|my|me)\b)|\bi stay (?:at )?home (?:full[- ]?time )?(?:with|to raise|to take care of) (?:my|the|our) (?:kids|son|daughter|baby|children|toddler|twins|boys|girls)\b|"
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
    r"\b(?:i'm|im|i am) (?:almost |nearly |currently |now )?(?:in )?(?:my )?(?:1st|2nd|3rd|4th|first|second|third|fourth|final|last) year (?:of|in|at)\b|\bmy (?:bs|ba|bsc|major|course|courses|uni|thesis|dissertation|lecturer|lectures|semester|finals|coursework|midterms?|syllabus|campus|student id|student visa|transcript|academic advisor|class schedule)\b(?! (?:was|were) (?:great|fun|hard)\b)|"
    r"\b(?:i'?m|i am)(?: currently| still| also| now| actually)? (?:studying|in school|in college|in uni|at uni|at college|at university|in university|back in school|back at school)\b|\bwhile (?:i'm |im |i am )?studying\b|\bi study\b(?! (?:the|it|this|that|them|him|her|how|why|what)\b)",
    r"\b(?:i'm|im|i am|i'm currently|im currently|i am currently) (?:a |an )?(?:(?!(?:former|ex|old|past|of|the|my|his|her|their|to|with|for|and|that|who|not)\b)[\w'-]+ ){0,4}?(?:student|undergrad|undergraduate|freshman|sophomore|fresher|postgrad|uni student|phd student|"
    r"grad student|masters student|med student|law student|nursing student)\b|\bmy (?:semester|finals|midterm|midterms)\b",
    r"(?:^|[.!?\n,]\s*)(?:a |an )?(?:\w+ )?student (?:from|at|of|here)\b",
    r"\bas an? (?:(?!(?:former|ex|old|past|of|the|my)\b)[\w'-]+ ){0,3}?student\b(?=[^.!?\n]{0,60}\b(?:i|my|me)\b)|"
    r"\b(?:mein(?:em)? studium|ins studium|im studium|ich studiere|studiere ich|ich bin student(?:in)?|je suis (?:étudiant|étudiante|en (?:licence|master|fac))|soy estudiante|"
    r"sou estudante|estudo (?:na|no|em)|faço faculdade|estoy estudiando|jestem student(?:em|ką)|studiuję|sono (?:uno |una )?(?:studente|studentessa)|ik studeer|ik ben student|"
    r"estoy en la (?:universidad|facultad|uni)|estou na (?:faculdade|universidade|facul)|estudio en|je suis à la fac|je fais (?:une licence|un master|des études))\b",
]
STUDYING = (r"\b\d(?:st|nd|rd|th) sem(?:ester)?\b|\b(?:i'm|im|i am) (?:almost |nearly |currently |now |only )?(?:in |a )?(?:my )?(?:(?:1st|2nd|3rd|4th|5th|first|second|third|fourth|final|last)[- ]year|year [1-5])\b(?! of (?:high school|marriage|work))"
            r"|\b(?:1st|2nd|3rd|4th|first|second|third|final) year (?:electives|student|courses|exams|project)\b|\b(?:i'm|im|i am) (?:currently |also |still |now )?(?:in|at) (?:an? (?:[\w'-]+ ){0,3}?)?(?:college|uni|university)\b"
            r"|\b(?:college|university|uni|undergrad|undergraduate|community college|first[- ]generation college|first[- ]gen(?:eration)? college) student\b(?! (?:loans?|debt|visa|athlete|housing|discount)\b)|\bmy (?:freshman|sophomore|junior|senior|first|second|third|final) (?:year|semester) (?:of|in|at) (?:college|uni|university)\b|\bmy (?:major|lectures?|lecturer|uni|campus|coursework|semester|syllabus|midterms?)\b"
            r"|\b(?:i'm|im|i am) (?:currently )?(?:studying|majoring)\b|\bwhile (?:i'm |im |i am |i )?(?:studying|study)\b|\bi(?:'m| am)? (?:in|doing) (?:the|my) (?:bs|ba|bsc|bachelor'?s?|undergrad) (?:program|degree)\b|\b(?:meu|minha) (?:primeiro|segundo|terceiro|primeira) (?:ano|período|semestre)\b|\bfaço (?:uma )?(?:segunda )?graduação\b|\bich studiere\b|\b\w+ studieren\b|\bestudio (?:en la|en el|una|la)\b|\bje suis (?:étudiant|étudiante|à la fac)\b|\b(?:faço faculdade|estoy en la (?:universidad|facultad)|estou na (?:faculdade|universidade|facul)|jestem student(?:em|ką)|studiuję|sono (?:uno |una )?(?:studente|studentessa)|ik studeer|estoy estudiando|sou estudante|soy estudiante|estudo (?:na|no|em))\b"
            r"|\bi have (?:a |my )?(?:midterm|midterms|final exam|finals) (?:coming up|tomorrow|next week|this week|today)\b|\bmy (?:college|university|uni) (?:classes|courses|professor|campus|dorm|roommate|application)\b|\b(?:mein(?:em)? studium|ins studium|im studium)\b|\bstudent (?:from|at) (?:the )?(?:main campus|\w+ (?:university|college|campus))\b")
GRADUATE = rf"\b(?:grad|graduate|phd|ph\.d\.?|doctoral|masters?|master's|msc|mba|msw|ma|ms|mfa) (?:student|candidate|program|programme)\b(?! (?:loans?|debt|visa|housing)\b)|\bmy (?:thesis|dissertation|phd|doctorate)\b|\bfinishing (?:my )?(?:grad|graduate|masters?|master's|phd) (?:program|degree)?\b|\bi study an? (?:jd|ma|ms|msc|masters|phd|llm)\b|\bmeiner dissertation\b|\bmi (?:tesis|doctorado|maestría)\b|\b(?:accepted|admitted) (?:in)?to (?:the |a )?(?:\w+ ){{0,3}}?(?:masters?|master's|phd|graduate|msw|mba|doctoral) program\b"
PRO_SCHOOL = r"(?:law|med|medical|dental|vet|veterinary|pharmacy|grad|graduate)"
PRO_STUDENT = (rf"\b(?:{I}|i'm currently|currently) (?:still |now )?(?:in|at|attending|finishing) (?:my (?:\w+ )?(?:year|semester) (?:of|in|at) )?{PRO_SCHOOL} school\b|"
               rf"\b(?:{I}|as) (?:an? |the )?(?:current |first[- ]year |second[- ]year |third[- ]year |fourth[- ]year |final[- ]year |\d(?:st|nd|rd|th)[- ]year )?{PRO_SCHOOL} student\b|"
               rf"\bmy (?:\w+ )?(?:year|semester) (?:of|in|at) {PRO_SCHOOL} school\b|\bi (?:go to|attend|started|start) {PRO_SCHOOL} school\b")
HIGH_SCHOOL = r"\b(?:i'm|im|i am|just) (?:an? )?(?:[\w-]+ )?(?:high ?schooler|high-schooler|(?:\d+th|seventh|eighth|ninth|tenth|eleventh|twelfth) grader)\b|\b(?:i'm|im|i am) (?:still |currently )?in (?:high ?school|hs|(?:9th|10th|11th|12th) grade|year (?:9|10|11|12))\b|\b(?:high ?school|hs) (?:student|senior|junior|sophomore|freshman)\b|\b(?:i'm|im|i am) (?:a )?(?:senior|junior|sophomore|freshman) in (?:high ?school|hs)\b|\bmy (?:high school|highschool) (?:teacher|classes|graduation|exams)\b"
COLLEGE = (r"\b(?:i'm|im|i am|this|just an?|\d{2}\s?[mf]?) (?:(?!(?:former|ex|retired)\b)[\w-]+ ){0,2}?college (?:boy|girl|guy|dude|bro|kid|twink|jock|athlete|lad|stud)s?\b|\bstudent,? here\b|\bjust an? (?:\w+ )?student\b|"
           r"\b(?:my|next|this) (?:\w+ )?year (?:of|at|in) (?:uni|college|university)\b|\bi (?:take|am taking|'m taking|m taking) (?:\w+ )?(?:classes|courses|units|credits)\b")
CAMPUS = (r"\bi (?:currently |now |still |also )?(?:go to|attend|am attending|'m attending|transferred to) (?:a |an |the )?(?:[\w'&.-]+ ){0,3}?(?:college|university|uni|community college|polytechnic)\b|"
          r"\b(?!(?:any|a|the|every|no|some)\b)(?:undergrad|undergraduate|fresher|freshman|sophomore|[\w'-]+ (?:major|student)) here\b|"
          r"\bmy (?:college|uni|university|class|course|semester|final[- ]year|capstone|group) (?:project|assignment|exams?|presentation|essay|paper|lectures?)\b|"
          r"\b(?:i'm|im|i am) (?:now |currently |almost |nearly )?(?:in|into|starting) (?:my )?(?:\d(?:st|nd|rd|th)|first|second|third|fourth|fifth|final|last) (?:year|semester|sem) (?:of|in|at) (?:college|uni|university|my degree|my bachelor'?s|undergrad)\b|"
          r"\b(?:i'm|im|i am) (?:about to |almost |nearly |currently |finally )?(?:finishing|graduating from|graduating|done with) (?:college|uni|university|my degree|my bachelor'?s|my undergrad)\b|"
          r"\b(?:\d+|one|two|three|four|a) (?:more )?(?:semesters?|years?|terms?|quarters?) (?:away from|left (?:of|in|until|before)) (?:graduation|graduating|my degree|college|uni)\b|"
          r"\b(?:i'm|im|i am) (?:an? )?(?:[\w'-]+ ){0,2}?major\b(?! (?:issue|problem|concern|fan|reason|part|key|league|player|city|brand|company)\b)")
CAMPUS_STARTED = (r"\bi(?:'m| am|m)? (?:currently |now |still |also |just |finally |recently |about to )?(?:attending|enrolled in|enrolled at|got into|gotten into|starting|start|going to|heading to|heading into|joining|entering) "
                  r"(?:a |an |the )?(?:[\w'&.-]+ ){0,3}?(?:college|university|uni|community college|polytechnic)\b|"
                  r"\b(?:i'm|im|i am) (?:about to graduate from|about to graduate|about to finish) (?:college|uni|university|my degree|my bachelor'?s|my undergrad)\b")
ANY_STUDENT = (r"\b(?:i'm|im|i am)(?: currently| still| just| also| now)? (?:an? )?(?:(?!(?:former|ex|old|past|of|the|my|his|her|their|to|with|for|and|that|who|not|high|school|grad|graduate|phd|masters?|master's|doctoral|level)\b)"
              r"[\w'-]+ ){0,4}?student\b(?! (?:loans?|visa|athlete|housing|discount|of|pilot|nurse|teacher|driver|worker|union)\b)|"
              r"\b(?:already|still) a student\b|"
              r"\bas an? (?:(?!(?:former|ex|old|past|of|the|my|high|school|grad|graduate|phd|masters?|doctoral|level)\b)[\w'-]+ ){0,3}?student\b(?=[^.!?\n]{0,60}\b(?:i|my|me)\b)")
STUDENT_HERE = r"(?:^|[.!?\n,]\s*)(?:a |an )?(?:college |uni |university )?student here\b"
STUDENT_LINE = (r"(?:(?m:^)[ \t>*#\\-]*|,[ \t]*)(?:(?:\d{2}\s?[mf]?|[mf]4[a-z]+|[mf]\s?\d{2}|[\[(][\w /+-]{1,12}[\])])[ \t,|-]*)*+(?:an? )?"
                r"(?:(?!(?:the|this|that|these|those|my|your|his|her|their|our|every|each|any|some|no|one|which|what|why|how|when|is|are|was|were|do|does|did|former|ex|old|future|fellow)\b)[\w'-]+ ){0,3}?"
                r"(?:student|college (?:girl|boy|guy|student|kid))\b(?! (?:loans?|visa|athlete|housing|discount|debt|union|card|id|council|account|accommodation|life|government|body|aid|finance)\b)"
                r"(?=\s*(?:$|[.,!;|(\n-]|\d|\b(?:here|looking|seeking|from|in|at|with|who|and)\b))")
GRADUATE_LEVEL = re.compile(r"\b(?:grad|graduate|phd|masters?|master's|doctoral|med|law|medical)\b")
SCHOOL_LEVEL = re.compile(r"\b(?:high school|highschool|hs)\b")
LEVELED = re.compile(r"\b(?:high|school|hs|grad|graduate|phd|masters?|master's|doctoral|med|law|medical|nursing|international|foreign|exchange|overseas)\b")


def leveled(match):
    span = match.group()
    return "graduate student" if GRADUATE_LEVEL.search(span) else "high school student" if SCHOOL_LEVEL.search(span) else None if LEVELED.search(span) else "college student"


STUDENT_TWINS = [STUDYING, PRO_STUDENT, ANY_STUDENT, STUDENT_HERE, STUDENT_LINE]
KIN = "he|she|they|his|her|their|him|them|husband|wife|boyfriend|girlfriend|partner|friend|friends|brother|sister|son|daughter|mom|mum|dad|mother|father|cousin|roommate"
OTHERS = re.compile(rf"\b(?:{KIN}|you|your|u|someone|anyone|everyone|everybody|nobody|people)\b")


def mine(value):
    return lambda match: value(match) if not OTHERS.search(match.string, clause(match.string, match.start()), match.start()) else None


def sentence(text, start):
    return max(text.rfind(mark, 0, start) for mark in ".!?\n") + 1


def near(value):
    return lambda match: value(match) if FIRST_NEAR.search(match.string, sentence(match.string, match.start()), match.start()) else None


WORKLIFE = [
    r"\b(?:at|after|before|outside of|outside|during) work\b(?! (?:on|out)\b)",
    r"\b(?:walk|walking|walked|commute|commuting|head|heading|headed|late|ride|riding|bike|biking|leave|leaving|left|ready|got|came|come|coming) "
    r"(?:to|for) work\b(?! (?:on|out|for|with|it|this|that|together|well|better|properly|again)\b)",
    r"\bmy (?:boss|bosses|supervisor|coworkers|co-workers|employer|place of work|line manager|shift|shifts|work schedule|work hours|"
    r"working hours|work day|workday|work week|workweek|work friends|break room|paycheck|paychecks|payslip|pay stub|paystub|work laptop|work phone|work email|work computer|"
    r"work uniform|work clothes|work boots)\b(?! (?:fired|let me go|laid me off)\b)",
    r"\b(?:i|i'm|im|i've|ive)\b[^.!?\n]{0,25}?\b(?:a|long|night|day|double|late|early|morning|evening|closing|opening|graveyard|overnight|\d+ ?(?:hr|hour)|\d+-hour|twelve[- ]hour) shifts?\b|"
    r"\b(?:got|get|getting|coming|came|home) off (?:a |my |the )?(?:\w+ )?shift\b|\bbusy with work\b",
]
SELF_WORK = [r"\b(?:off|from) work\b", r"(?=for work)(?<!looking )(?<!look )(?<!searching )(?<!search )(?<!apply )(?<!applying )(?<!ready )(?<!late )(?<!hunting )\bfor work\b(?! (?:to|that|in|at|on|online)\b)", r"\b(?:work|working) (?:full[- ]?time|part[- ]?time|\d+ days a week|\d+ hours a week|\d+ ?hrs a week)\b"]
SELLING = [
    r"\b(?:i'm |im |i am |i )?(?:selling|sell) (?:my )?(?:[\w-]+ ){0,2}?(?:nudes|pics|pictures|videos|vids|content|premades|pre-mades|pre mades|sex tapes|gfe|customs|sexting)\b|"
    r"\boffering (?:[\w-]+,? ){0,3}?(?:sexting|customs?|content|gfe|video calls|facetime)\b",
]
OWNERS = [
    r"\b(?:(?:commissions|comms) (?:are )?(?:open|opened)|open(?:ing)? (?:my )?(?:commissions|comms)|open (?:for|to) (?:commissions|comms)|(?:taking|accepting|doing|started taking) (?:commissions|comms)|working (?:on|with) commissions)\b",
    r"\[\s*for hire\s*\]",
]
INDEPENDENT = rf"\b{I}(?: [a-z]+(?:[ -][a-z]+)?,)? {ADVERB}an? (?:independent|freelance|freelancing|self[- ]employed) "
LEVELLESS = re.compile(r"\b(?:international|foreign|exchange|overseas)\b")
RULES = [
    *(rule("occupation", pattern, occupied(find), TAGGED) for pattern, find in (*OCCUPATION, *MENTIONS, (LEAD, fragment))),
    *(rule("employment_status", pattern, employed(find), TAGGED) for pattern, find in (*OCCUPATION[:2], *OCCUPATION[3:], *MENTIONS[:2], MENTIONS[3], (LEAD, fragment))),
    rule("occupation", GERUND, scoped(mine(occupied(after))), TAGGED),
    *(rule("occupation", pattern, occupied(after), TAGGED) for pattern in NAMED),
    *(rule("employment_status", pattern, employed(after), TAGGED) for pattern in NAMED),
    rule("occupation", CELL, occupied(celled), TAGGED),
    *(rule("occupation", pattern, scoped(group(FIELDS if index == 0 else PLACES)), TAGGED) for index, pattern in enumerate(WORKPLACE)),
    *(rule("employment_status", pattern, scoped(fixed("employed")), TAGGED) for pattern in WORKPLACE),
    rule("occupation", WORKING_IN, scoped(group(FIELDS)), TAGGED),
    rule("occupation", IN_IT, scoped(fixed(SOFTWARE)), TAGGED),
    *(rule("occupation", pattern, scoped(lambda match: None if match.group() == "my business" else BUSINESSES.get(match.group(1))), TAGGED) for pattern in OWNERSHIP),
    *(rule("employment_status", pattern, scoped(fixed(OWNER)), TAGGED) for pattern in OWNERSHIP),
    *(rule("occupation", pattern, scoped(value), TAGGED) for pattern, value in ACTIVITY),
    *(rule("employment_status", pattern, scoped(fixed("employed")), TAGGED) for pattern, _ in ACTIVITY),
    *(rule("occupation", pattern, scoped(value), TAGGED) for pattern, value in ROLE_TERMS),
    rule("occupation", CODING, scoped(fixed(SOFTWARE)), TAGGED),
    rule("employment_status", CODING, scoped(fixed("employed")), TAGGED),
    *(rule("employment_status", pattern, scoped(fixed("employed")), TAGGED) for pattern in EMPLOYED),
    *(rule("employment_status", pattern, scoped(fixed(OWNER)), TAGGED) for pattern in SELF_EMPLOYED),
    rule("employment_status", INDEPENDENT, scoped(lambda match: OWNER if title(match.string, match.end()) else None), TAGGED),
    *(rule("employment_status", pattern, scoped(fixed("unemployed"), CONDITIONAL), TAGGED) for pattern in UNEMPLOYED),
    *(rule("employment_status", pattern, scoped(fixed("retired")), TAGGED) for pattern in RETIRED),
    *(rule("employment_status", pattern, scoped(fixed("homemaker")), TAGGED) for pattern in HOMEMAKER),
    *(rule("employment_status", pattern, scoped(fixed("unable to work"), CONDITIONAL), TAGGED) for pattern in UNABLE),
    *(rule("employment_status", pattern, scoped(fixed("student")), TAGGED) for pattern in (*STUDENT, *STUDENT_TWINS)),
    rule("employment_status", CAMPUS, scoped(fixed("student")), SELF_HEDGE),
    *(rule("employment_status", pattern, scoped(mine(fixed("employed"))), TAGGED) for pattern in WORKLIFE),
    *(rule("employment_status", pattern, scoped(mine(near(fixed("employed")))), TAGGED) for pattern in SELF_WORK),
    *(rule("employment_status", pattern, scoped(fixed(OWNER), played=True), TAGGED) for pattern in SELLING),
    *(rule("occupation", pattern, scoped(fixed(ADULT), played=True), TAGGED) for pattern in SELLING),
    *(rule("employment_status", pattern, scoped(fixed(OWNER)), TAGGED) for pattern in OWNERS),
]

SUBJECTS = {"computer systems": "computer science or IT", "information systems": "computer science or IT", "infosys": "computer science or IT", "informatics": "computer science or IT",
            "social science": "social sciences", "social sciences": "social sciences", "chem": "natural sciences", "bio": "natural sciences", "econ": "social sciences", "psych": "psychology", "poli sci": "social sciences", "polisci": "social sciences",
            "computer science": "computer science or IT", "cs": "computer science or IT", "comp sci": "computer science or IT", "software engineering": "computer science or IT",
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
            "architecture": "arts or design", "design": "arts or design", "journalism": "humanities", "communications": "social sciences",
            "cse": "computer science or IT", "ai": "computer science or IT", "med": "medicine or health", "vet": "medicine or health", "mech": "engineering", "ece": "engineering",
            "eee": "engineering", "life sci": "natural sciences", "life science": "natural sciences"}
SUBJECTS |= table({
    "computer science or IT": "computer engineering|software development|web development|information security|game development|data analytics|artificial intelligence|machine learning",
    "engineering": "biomedical engineering|industrial engineering|environmental engineering|materials engineering|petroleum engineering|nuclear engineering|mechatronics|"
                   "electronics engineering|nanotechnology|robotics|engineering physics|computer and electrical engineering",
    "mathematics or statistics": "applied math|applied mathematics|actuarial science|stats",
    "natural sciences": "biochem|microbiology|molecular biology|cell biology|genetics|zoology|botany|ecology|marine biology|astrophysics|earth science|materials science|physiology|"
                        "biotechnology|forensic science|life sciences|biological sciences|natural sciences",
    "medicine or health": "dentistry|veterinary medicine|nutrition|dietetics|occupational therapy|speech pathology|radiography|midwifery|paramedicine|health science|health sciences|"
                          "exercise science|pharmacology|biomedical science|premed|pre-med|optometry|physiotherapy|nuclear medicine",
    "social sciences": "social work|criminal justice|public policy|public administration|urban planning|homeland security|gender studies",
    "business or finance": "human resources|supply chain management|hospitality management|entrepreneurship|international business|commerce|business management|economics and finance",
    "humanities": "art history|english literature|comparative literature|creative writing|religion|archaeology",
    "arts or design": "game design|fashion design|interior design|animation|photography|film studies|music production|music theory|dance|drama|illustration|industrial design",
    "education": "early childhood education|special education|elementary education|secondary education",
    "law": "legal studies|pre-law|prelaw",
    "psychology": "clinical psychology|counseling psychology",
})
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
SHORT_DEGREES = frozenset({"ba", "bs", "ma", "ms", "md", "jd", "b.s.", "b.a.", "m.s.", "mse", "dds", "dvm", "mfa", "ged", "associates", "associate's"})
LONG_DEGREE_NAMES = alternation(name for name in DEGREES if name not in SHORT_DEGREES)
SHORT_DEGREE_NAMES = alternation(SHORT_DEGREES & set(DEGREES))
FIRST_NEAR = re.compile(r"\b(?:i|i'm|im|i've|ive|my|me)\b")
PEERS = re.compile(rf"\b(?:{KIN}|batchmates?|classmates?|colleagues?|coworkers?)\b")


def owned(text, start, reach=50):
    left = max(clause(text, start), start - reach)
    return bool(FIRST_NEAR.search(text, left, start)) and not PEERS.search(text, left, start)


LEVELS = {name.rstrip("."): level for name, level in DEGREES.items()} | {"msn": "master's degree"}
DEGREE_IN = (r"\b(bachelor's|bachelors|master's|masters|phd|ph\.d|bsc|msc|b\.s|m\.s|ba|bs|ma|ms|mba|bfa|mfa|llb|jd|md|btech|b\.tech|mtech|m\.tech|bcom|b\.com|bba|bsn|msn|"
             r"meng|beng)\.? (?:degree |hons |honours |honors )?(?:in|of) ([a-z]+(?: [a-z]+)?)")
ASPIRING = re.compile(r"\b(?:goal|goals|pursue|pursuing|planning|plan|plans|apply|applying|application|considering|thinking|soch|want|wanted|wanting|hoping|dream|future|next|aspiring|"
                      r"get|getting|start|starting|consider|choose|choosing|need|needs|require|requires|required|offer|offers)\b")


def degree_in(match):
    text, start = match.string, match.start()
    level = LEVELS.get(match.group(1))
    if not level or match.group(1) in SHORT_DEGREES and match.group(2) not in SUBJECTS and match.group(2).split()[0] not in SUBJECTS:
        return None
    left = max(clause(text, start), start - 60)
    if ASPIRING.search(text, left, start) or not (FIRST_NEAR.search(text, max(0, start - 80), start) or text.rfind("\n", 0, start) + 1 == start):
        return None
    return level


PURSUING = (r"\b(?:i'm|im|i am|i'm currently|im currently|i am currently|currently) (?:still |now |also )?(?:doing|pursuing|finishing|completing|working on|working towards|in the middle of|halfway through) "
            r"(?:a |an |my )(?:(masters?|master's|phd|ph\.d|doctorate|msc|mba|msw|mfa|ma|ms|grad school)|(bachelor'?s|bachelors|undergrad|undergraduate degree|degree|bsc|ba|bs|bba|bcom|btech))\b")
EDUCATION_RULES = [
    said("education", DEGREE_IN, degree_in, SELF_HEDGE),
    said("education", PURSUING, lambda match: "graduate student" if match.group(1) else "college student", SELF_HEDGE),
    said("education", STUDYING, fixed("college student")),
    said("education", COLLEGE, fixed("college student")),
    rule("education", CAMPUS, scoped(fixed("college student")), SELF_HEDGE),
    rule("education", CAMPUS_STARTED, scoped(fixed("college student")), SELF_HEDGE),
    said("education", STUDENT[0], fixed("college student")),
    said("education", r"\b(?:my|a) (?:master'?s|masters|master|msc|mba) (?:thesis|dissertation|gpa|coursework)\b|\bfinishing (?:a|my) (?:master'?s|masters)\b|\bi did my (?:ms|msc|ma|mba|masters|master's)\b",
         fixed("master's degree")),
    said("education", r"\b(?:i'm|im|i am) (?:still |currently |now )?(?:finishing|in|attending) (?:high ?school|class 1[012](?:th)?|1[012]th class|class (?:xi|xii))\b|\ban? a[- ]levels? student\b",
         fixed("high school student")),
    said("education", ANY_STUDENT, lambda match: None if LEVELLESS.search(match.group()) else "college student", SELF_HEDGE),
    said("education", STUDENT_HERE, fixed("college student"), SELF_HEDGE),
    said("education", STUDENT_LINE, leveled, SELF_HEDGE),
    said("education", r"\b(?:i'm|im|i am|as|just finished|finished|i was|during|after|since) (?:an? |my )?[123]l\b", fixed("professional degree such as law or medicine"), SELF_HEDGE),
    said("education", GRADUATE, fixed("graduate student"), SELF_HEDGE),
    said("education", PRO_STUDENT, fixed("graduate student"), SELF_HEDGE),
    said("education", r"\bmy residency\b|\b(?:i'm|im|i am) (?:in|doing|finishing|starting) (?:my )?residency\b", fixed("professional degree such as law or medicine"), SELF_HEDGE),
    said("education", rf"\b(?:i have|i've got|i got|i hold|i earned|i finished|i completed|i've done|i have done|i did|got|just got|have|with) (?:a |an |my |both |two )?(?:({LONG_DEGREE_NAMES})(?: degree| degrees| hons| in| from)?|({SHORT_DEGREE_NAMES}) (?:degree|degrees|in|from))\b(?! (?:student|program|programme|candidate|course|class)\b)|\b({LONG_DEGREE_NAMES}) hons\b",
         lambda match: DEGREES[next(filter(None, match.groups()))] if match.group().startswith("i") or owned(match.string, match.start()) else None, SELF_HEDGE),
    said("education", r"\b(?:i have|i've got|i hold|i earned|i got|i completed|i finished|i do have|i also have) (?:a |an |my |both |two )?"
         r"(?:(?!(?:associate'?s?|masters?|master's|phd|doctoral|online|honorary|useless|worthless|second|new)\b)[\w'-]+ ){0,3}?degrees?\b(?! (?:program|programme|course|apprenticeship)\b)|\b(?:college|university|uni)[- ]educated\b",
         fixed("bachelor's degree"), SELF_HEDGE),
    rule("education", rf"(?:^|\n)[^\w\n]*(?:education|degree|qualifications?|highest degree)[^\w\n]{{0,4}}?[:=][^\w\n]*(?:an? )?({LONG_DEGREE_NAMES}|{SHORT_DEGREE_NAMES})\b", group(DEGREES), SELF_HEDGE),
    said("education", r"\b(?:masters?|master's)[- ]educated\b", fixed("master's degree"), SELF_HEDGE),
    needs(said("education", r"\b(?:i (?:graduated|have graduated|just graduated|recently graduated|finally graduated|just finished|recently finished|finished)|(?:^|[.!?\n]\s*)(?:just |recently |finally )?(?:graduated|finished)|(?:since|after|when|once) (?:i )?graduat(?:ed|ing)) (?:from )?(?:college|university|uni|undergrad|with (?:a|my|honors))\b|\b(?:college|university) graduate\b|\b(?:as an? |i'm an? |im an? |i am an? )(?!(?:\w+ )?high ?school)(?:\w+ ){0,3}?(?:graduate|grad)\b(?! (?:student|program|school)\b)|\b\w+ (?:and \w+ )?grad\b(?= (?:having|here|with|who|and|looking)\b)|\bme formei\b|\bi went back to school for\b|\bmy (?:bachelor'?s|bachelors|undergrad|degree) (?:is|was) in\b",
         fixed("bachelor's degree"), SELF_HEDGE), "grad", "finished", "formei", "went back to school", "bachelor", "undergrad", "degree"),
    said("education", r"\b(?:i )?(?:graduated|finished) (?:from )?high ?school\b|\bhigh ?school (?:graduate|diploma)\b|\bcompleted (?:my )?12th\b|\bpassed (?:my )?12th\b|\bi have (?:a|my) ged\b", fixed("high school diploma"), SELF_HEDGE),
    said("education", HIGH_SCHOOL, fixed("high school student"), SELF_HEDGE),
    said("education", r"\bi dropped out of (?:college|uni|university)\b|\bi have some college\b|\bi never finished (?:college|my degree)\b|\btransferred (?:to \w+ )?from a community college\b|\bput myself back in college\b|\bacademic(?:ally)? (?:dismissed|suspended|probation)\b", fixed("some college, no degree"), re.compile(r"\b(?:if|would|wish)\b")),
    said("education", r"\bi dropped out of high ?school\b|\bi never finished high ?school\b|\bi didn't finish high ?school\b", fixed("no high school diploma"), re.compile(r"\b(?:if|would|wish)\b")),
    said("education", r"\bi (?:have|got|earned) (?:an? )?associate'?s(?: degree)?\b|\bi went to (?:a )?trade school\b|\bi(?:'m| am) a (?:journeyman|licensed electrician|licensed plumber)\b", fixed("trade school or associate degree"), SELF_HEDGE),
]
SCHOOLS = {"law": "law", "l": "law", "med": "medicine or health", "medical": "medicine or health", "pharmacy": "medicine or health", "nursing": "medicine or health", "dental": "medicine or health",
           "vet": "medicine or health", "veterinary": "medicine or health", "residency": "medicine or health", "engineering": "engineering",
           "business": "business or finance", "b": "business or finance", "art": "arts or design", "film": "arts or design", "architecture": "arts or design"}
FOREIGN_SUBJECTS = table({
    "engineering": "engenharia|ingeniería|ingenieria|ingegneria|ingénierie|ingenieurwesen|maschinenbau|elektrotechnik",
    "medicine or health": "medicina|médecine|medizin|enfermagem|enfermería|enfermeria|farmácia|farmacia|pharmacie|odontologia|odontología|fisioterapia|pflege",
    "law": "direito|derecho|droit|jura|jus|giurisprudenza|rechten|rechtswissenschaft|prawo",
    "computer science or IT": "informática|informatica|informatique|informatik|computação|computacion|computación|wirtschaftsinformatik",
    "psychology": "psicologia|psicología|psychologie|psychologia",
    "arts or design": "arquitetura|arquitectura|architettura|architecture|architektur|design|diseño|artes|arte|kunst",
    "business or finance": "administração|administración|administracion|contabilidade|contabilidad|economia|economía|économie|bwl|betriebswirtschaft|gestion|finanzas|finanças",
    "natural sciences": "biologia|biología|biologie|bio|química|quimica|chimie|chemie|física|fisica|physique|physik|geologia|geología",
    "mathematics or statistics": "matemática|matemáticas|matematica|mathématiques|mathe|mathematik|estatística|estadística|statistik",
    "social sciences": "sociologia|sociología|sociologie|soziologie|ciência política|ciencias políticas|politikwissenschaft|antropologia",
    "education": "pedagogia|pedagogía|pédagogie|pädagogik|lehramt|magisterio",
    "humanities": "história|historia|geschichte|letras|filosofia|filosofía|philosophie|literatura|germanistik|anglistik",
})
DEGREE_SUBJECTS = SUBJECTS | {"it management": "computer science or IT", "accountancy": "business or finance", "ultrasound": "medicine or health", "electronics": "engineering",
                              "electronics and communication": "engineering", "electronics and communication engineering": "engineering"}
WORDS = re.compile(r"[\w'-]+")


def subject_before(text, start):
    words = WORDS.findall(text, max(0, start - 60), start)
    return next((SUBJECTS[key] for size in (4, 3, 2, 1) if len(words) >= size and (key := " ".join(words[-size:])) in SUBJECTS), None)


SUBJECT_LINE = r"(?:(?m:^)\W*|,[ \t]*)(?:(?:\d{2}\s?[mf]?|[mf]4[a-z]+|[mf]\s?\d{2}|[\[(][\w /+-]{1,12}[\])])[ \t,|-]*)*+(?:an? )?([\w'-]+(?: [\w'-]+){0,3}?) (?:student|major)\b"
STUDYING_SUBJECT = rf"(?:^|[.,;!\n]\s*|\band )(?:currently |also |still |now )?(?:studying|majoring in) ({SUBJECT_NAMES})\b"
FIELD_RULES = [
    rule("field_of_study", STUDYING_SUBJECT, group(SUBJECTS)),
    rule("field_of_study", rf"\bmy (?:\w+ )?({SUBJECT_NAMES}) (?:class|classes|course|courses|module|modules|lab|labs|lecture|lectures|lecturer|professor|professors|prof|exam|exams|"
         rf"final|finals|midterm|midterms|coursework|assignment|assignments|thesis|dissertation|program|programme|department|dept|cohort|classmates|seminar|studies)\b|"
         rf"\bmy (?:thesis|dissertation|capstone|research|phd|ph\.d|masters|master's) (?:is |was )?(?:on|about|in) (?:the )?({SUBJECT_NAMES})\b|"
         rf"\b(?:i'm|im|i am) (?:currently |also )?(?:taking|in|doing) (?:a |an |my |two |some )?({SUBJECT_NAMES}) (?:class|classes|course|courses|module|modules|degree|program|programme)\b",
         lambda match: SUBJECTS[next(filter(None, match.groups()))], SELF_HEDGE),
    rule("field_of_study", rf"(?:\bi(?:'m| am|m)? (?:currently |now |also |still |actually )?|\bcurrently )(?:study|studied|studying|majored in|major in|majoring in|have a degree in|got my degree in|"
         rf"have a (?:bachelor'?s|bachelors|master'?s|masters|phd|ba|bs|bsc|ms|msc) in|graduated in|did my degree in)\s+({SUBJECT_NAMES})\b", group(SUBJECTS)),
    rule("field_of_study", rf"\b{I} (?:a |an )?(?:(?:first|second|third|fourth|final|\d(?:st|nd|rd|th))[- ]year )?({SUBJECT_NAMES}) (?:major|student|graduate|grad|undergrad|undergraduate)\b|\bmy ({SUBJECT_NAMES}) (?:degree|major)\b", lambda match: SUBJECTS[match.group(1) or match.group(2)]),
    rule("field_of_study", rf"\b(?:a|an|my) ({SUBJECT_NAMES}) (?:degree|diploma|bachelor'?s|bachelors|masters?|master's|phd|major)\b",
         lambda match: SUBJECTS[match.group(1)] if match.group().startswith("my") or owned(match.string, match.start()) else None, SELF_HEDGE),
    rule("field_of_study", r"\b(?:student|major|grad) here\b", lambda match: subject_before(match.string, match.start()), SELF_HEDGE),
    rule("field_of_study", STUDENT_LINE, scoped(lambda match: subject_before(match.string, match.start() + k) if (k := match.group().rfind("student")) > 0 else None), TAGGED),
    rule("field_of_study", SUBJECT_LINE, lambda match: SUBJECTS.get(match.group(1)), SELF_HEDGE),
    rule("field_of_study", rf"\b(?:degree|degrees|bachelors?|bachelor's|masters?|master's|phd|bsc|ba|bs|ms|msc|ma|major|majoring|majored|graduate|student|year|diploma|course|studies|studying|study|studied|undergrad|undergraduate|graduation|schooling|background)(?: is| was)? in (?:(?!(?:the|a|an|my|this|that|their|his|her|which|what)b)[a-z]+ )??({alternation(DEGREE_SUBJECTS)})\b",
         group(DEGREE_SUBJECTS), SELF_HEDGE),
    rule("field_of_study", rf"\bi(?:'m| am|m)? (?:currently |now |also |still )?(?:going (?:back )?to|go to|in|back in|attending) (?:school|college|uni|university|grad school) for ({SUBJECT_NAMES})\b", group(SUBJECTS), SELF_HEDGE),
    rule("field_of_study", rf"\b(?:as an? |i'm an? |im an? |i am an? )(?:[\w-]+ ){{0,2}}({SUBJECT_NAMES}) (?:graduate|grad|student|major)\b", group(SUBJECTS), SELF_HEDGE),
    rule("field_of_study", r"\b(law|med|medical|pharmacy|nursing|dental|vet|veterinary|engineering|business|art|film|architecture|b) (?:school|college)\b|\b(?:i'm|im|i am|i was|as) (?:a |an )?[123](l)\b|"
         r"\b(?:my|in|doing|finishing|starting|out of) (?:my )?(residency)\b", lambda match: SCHOOLS[next(filter(None, match.groups()))] if owned(match.string, match.start(), 60) else None, SELF_HEDGE),
    needs(rule("field_of_study", r"\b(?:estudante|estudiante|étudiante?|studente(?:ssa)?|studentin?|student) (?:de |d'|di |en |der )(?:la |el |a |o )?(\w+)|\b(?:faço|estudo|estudio|curso|cursando|studiere|studio|j'étudie|étudie|studeer) "
         r"(?:de |la |el |a |o |in )?(\w+)|\b(?:facoltà|faculdade|facultad|faculté|fakultät) (?:di |de |d'|für )(?:la |el |a |o )?(\w+)|\b(\w+) (?:zu )?studieren\b",
         lambda match: FOREIGN_SUBJECTS.get(next(filter(None, match.groups()))), SELF_HEDGE), "estud", "étud", "studen", "studi", "studeer", "faço", "curs", "facolt", "faculdade", "facultad", "faculté", "fakultät"),
]
TRAINED = {CLINICAL: "medicine or health", ENGINEERING: "engineering"}
TITLE_FIELDS = {key: "psychology" if "psycholog" in key else TRAINED.get(value) for key, value in TITLES.items()}
DEGREE_FIELDS = table({"business or finance": "mba|bba|bcom|b.com|mcom|m.com", "medicine or health": "mbbs|bsn|msn|pharmd|dvm|bds", "law": "llb",
                       "arts or design": "bfa|mfa", "social sciences": "msw|bsw", "engineering": "btech|b.tech|mtech|m.tech|beng|meng"})
DEGREE_FIELD_NAMES = alternation(DEGREE_FIELDS)
FIELD_RULES += [
    *(rule("field_of_study", pattern, lambda match, find=find: find(match, TITLE_FIELDS), TAGGED) for pattern, find in (OCCUPATION[0], OCCUPATION[1], OCCUPATION[3], (OPENER, opener))),
    rule("field_of_study", rf"\b(?:have|got|hold|earned|finished|completed|did|doing|pursuing|my|an?) (?:an? |my )?({DEGREE_FIELD_NAMES})\b|\b({DEGREE_FIELD_NAMES}) (?:student|graduate|grad|holder|hons)\b",
         lambda match: DEGREE_FIELDS[match.group(1) or match.group(2)] if match.group().startswith("my") or owned(match.string, match.start()) else None, SELF_HEDGE),
]

ANNUAL = frozenset({"year", "yr", "annum", "annually", "yearly", None})
SCALES = {"k": 1000, "thousand": 1000, "grand": 1000, "mil": 1_000_000, "million": 1_000_000, None: 1}


def income(match):
    amount = float(match.group(1).replace(",", "")) * SCALES[match.group(2)]
    return str(int(amount)) if (match.group(3) or match.group(4)) in ANNUAL and 1000 <= amount <= 100_000_000 else None


AMOUNT = (r"(?:about |around |roughly |over |like |~|almost |just under |just over |close to |nearly |an? |approximately |approx |more than |barely |only |just |(?:a bit|a little|slightly) (?:over|under|more than|less than) |just shy of |upwards of |north of )?"
          r"\$?(\d[\d,]*(?:\.\d+)?)\s*(k|thousand|grand|mil|million)?"
          r"\s*(?:(?:usd|cad|aud|eur|gbp|dollars|pounds|euros)\s*)?(?:(?:a|per|/|an?|each)\s*(year|yr|annum|month|mo|hour|hr|week|wk)\b|(annually|yearly|monthly|hourly|weekly)\b|"
          r"(?=\s*(?:$|[.,!;)+]|before|after|pre|post|gross|net|base|salary|total|tc|as|currently|now|right now|working|plus|and|but|so|with|which)))")
INCOME = [
    rf"(?:\b(?:i|me) (?:currently |now |only |just |still )?(?:make|made|earn|earned|bring in|bring home|gross|grossed|net|netted|take home|clear|cleared|pull|pulled|pull in|get paid|got paid|passed|hit|crossed|topped)|"
    rf"\b(?:i'm|im|i am) (?:currently |now |only |just |still )?(?:making|earning|paid|getting paid|bringing in|bringing home|pulling in|clearing|netting|grossing|taking home|(?:on|at)(?=\s+(?:about |around |like |~)?\$|\s+\d[\d,.]*\s*k\b))|\bmy (?:salary|income|pay|base|base salary|base pay|tc|total comp|total compensation|"
    rf"take home|take-home|take home pay|comp|annual salary|gross income|net income|household income|paycheck|wage|hourly rate|rate) (?:is|was|went up to|of|:|=|is now|just hit|is around|is about|is like))\s+{AMOUNT}",
    rf"(?:^|[.!?\n]\s*)(?:passed|cleared|hit|crossed|made|make|earn|earning|making|grossed|netted|took home|take home)\s+{AMOUNT}",
]
RULES += [
    *EDUCATION_RULES,
    said("employment_status", PURSUING, fixed("student"), SELF_HEDGE),
    said("employment_status", GRADUATE, fixed("student"), SELF_HEDGE),
    said("employment_status", HIGH_SCHOOL, fixed("student"), SELF_HEDGE),
    *FIELD_RULES,
    *(rule("income", pattern, income, SELF_HEDGE) for pattern in INCOME),
    *(rule("employment_status", pattern, lambda match: "employed" if income(match) else None, SELF_HEDGE) for pattern in INCOME),
]
TERM = r"\b(?:this|next) (?:semester|quarter|sem)\b|\bcurrently (?:studying|pursuing|enrolled|doing (?:my|a|an) (?:degree|bachelor'?s|masters?|master's|bsc|ba|bs|btech|undergrad))\b"
RULES += [
    said("employment_status", TERM, near(fixed("student"))),
    said("education", TERM, near(fixed("college student"))),
]


NAMED_GATE = re.compile(r",\s*(?:an? |the )")


GATES = {STUDENT_LINE: words("student", "college"), SUBJECT_LINE: words("student", "major"), CELL: PERSONA.search, NAMED[0]: NAMED_GATE.search, NAMED[1]: words("my name"),
         GERUND: words("working as"), WORKING_IN: words("working in", "work in"), IN_IT: words("work in it", "working in it"), STUDYING_SUBJECT: words("studying", "majoring"), ROLE_TERMS[0][0]: words("patient"), ROLE_TERMS[1][0]: words("student"), GOT_JOB: words("the job"), MENTIONS[0][0]: words("here"), MENTIONS[3][0]: words("occupation", "profession", "job", "work", "career", "current role"), MENTIONS[4][0]: words("currently"), MENTIONS[5][0]: words("by trade", "by profession"), MENTIONS[6][0]: words("both"), HOMEMAKER[1]: words("sahm", "sahd", "stay", "homemaker", "housewife"),
         **{pattern: words("retire") for pattern in RETIRED[:5]}, UNEMPLOYED[0]: words("unemployed", "jobless", "out of work", "between jobs"), CAMPUS_STARTED: words("college", "uni"), SELF_EMPLOYED[0]: words("employed", "freelancer", "sole trader"), **{line: words("working") for line in WORKING_LINES}}
RULES = [(attribute, Gated(pattern, GATES[pattern.pattern]) if pattern.pattern in GATES else pattern, value, hedge) for attribute, pattern, value, hedge in RULES]

