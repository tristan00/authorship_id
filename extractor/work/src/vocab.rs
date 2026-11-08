use std::collections::HashMap;

pub const SOFTWARE: &str = "software or IT";
pub const ENGINEERING: &str = "engineering";
pub const SCIENCE: &str = "science or research";
pub const CLINICAL: &str = "doctor, nurse or clinical health";
pub const CARE: &str = "health support or care work";
pub const TEACHING: &str = "teaching or education";
pub const LAW: &str = "law";
pub const FINANCE: &str = "finance or accounting";
pub const BUSINESS: &str = "business, management or consulting";
pub const MEDIA: &str = "marketing, media or communications";
pub const ARTS: &str = "arts, design or entertainment";
pub const SALES: &str = "sales or retail";
pub const FOOD: &str = "food service or hospitality";
pub const TRADE: &str = "skilled trade or construction";
pub const WAREHOUSE: &str = "manufacturing or warehouse";
pub const TRANSPORT: &str = "transport or delivery";
pub const SAFETY: &str = "police, fire or security";
pub const MILITARY: &str = "military";
pub const GOVERNMENT: &str = "government or public service";
pub const SOCIAL: &str = "social work or religious work";
pub const OFFICE: &str = "office or administrative";
pub const SERVICE: &str = "cleaning, maintenance or personal service";
pub const OUTDOOR: &str = "farming or outdoor work";
pub const ADULT: &str = "sex work or adult content";
pub const OTHER: &str = "other job";
pub const OWNER: &str = "self-employed or business owner";
pub const FOUNDER: &str = "founder";

pub type Map = HashMap<String, Option<&'static str>>;

pub fn listed(entries: &[(&'static str, &str)]) -> Map {
    let mut out = Map::new();
    for (value, words) in entries {
        for word in words.split('|') {
            out.insert(word.to_string(), if value.is_empty() { None } else { Some(*value) });
        }
    }
    out
}

pub fn pairs(entries: &[(&str, &'static str)]) -> Map {
    entries.iter().map(|(k, v)| (k.to_string(), Some(*v))).collect()
}

pub const JOBS: &[(&str, &str)] = &[
    (SOFTWARE, concat!("software engineer|software developer|software architect|software dev|developer|programmer|coder|computer programmer|web developer|web dev|app developer|mobile developer|ios developer|",
        "android developer|front end developer|frontend developer|front-end developer|backend developer|back end developer|back-end developer|full stack developer|fullstack developer|",
        "full-stack developer|game developer|game dev|indie dev|dev|swe|sde|data scientist|data engineer|data analyst|data architect|machine learning engineer|ml engineer|ai engineer|",
        "sysadmin|system administrator|systems administrator|network administrator|network engineer|database administrator|dba|devops engineer|site reliability engineer|sre|",
        "cloud engineer|cloud architect|solutions architect|it technician|it tech|it support|it specialist|it consultant|it manager|it director|it admin|it guy|it professional|it administrator|it analyst|",
        "systems analyst|help desk technician|helpdesk technician|help desk analyst|desktop support technician|tech support|technical support specialist|support engineer|",
        "qa engineer|qa tester|qa analyst|software tester|game tester|test engineer|cybersecurity analyst|cyber security analyst|security analyst|security engineer|penetration tester|",
        "pentester|ethical hacker|ux engineer|embedded engineer|embedded developer|firmware engineer|computer technician|tech lead|bi developer|",
        "business intelligence analyst|programmer analyst|computer scientist|blockchain developer|it worker|software consultant")),
    (ENGINEERING, concat!("engineer|mechanical engineer|electrical engineer|civil engineer|chemical engineer|aerospace engineer|aeronautical engineer|structural engineer|process engineer|",
        "manufacturing engineer|industrial engineer|biomedical engineer|environmental engineer|petroleum engineer|mining engineer|nuclear engineer|materials engineer|",
        "design engineer|project engineer|quality engineer|reliability engineer|field engineer|systems engineer|controls engineer|automation engineer|electronics engineer|",
        "hardware engineer|computer engineer|robotics engineer|geotechnical engineer|transportation engineer|mechatronics engineer|engineering technician|drafter|draftsman|",
        "cad technician|surveyor|land surveyor|telecom engineer|rf engineer|power engineer|marine engineer|naval architect|test pilot engineer")),
    (SCIENCE, concat!("scientist|research scientist|researcher|biologist|chemist|physicist|lab tech|lab technician|laboratory technician|lab assistant|lab manager|postdoc|post-doc|",
        "postdoctoral researcher|postdoctoral fellow|research assistant|research associate|research fellow|geologist|geophysicist|astronomer|astrophysicist|neuroscientist|",
        "microbiologist|ecologist|statistician|economist|mathematician|epidemiologist|biochemist|geneticist|botanist|zoologist|marine biologist|meteorologist|climatologist|",
        "archaeologist|anthropologist|sociologist|historian|linguist|pharmacologist|toxicologist|virologist|immunologist|physiologist|entomologist|oceanographer|hydrologist|",
        "analytical chemist|food scientist|materials scientist|professor|associate professor|assistant professor|full professor|research professor|academic|research engineer|",
        "principal investigator|clinical researcher|clinical research coordinator|paleontologist|ornithologist|primatologist|volcanologist|seismologist")),
    (CLINICAL, concat!("doctor|physician|medical doctor|nurse|registered nurse|nurse practitioner|lpn|lvn|surgeon|dentist|orthodontist|pharmacist|paramedic|emt|physical therapist|",
        "physiotherapist|occupational therapist|speech therapist|speech language pathologist|speech-language pathologist|slp|respiratory therapist|radiologist|radiographer|",
        "radiology tech|radiology technician|x-ray tech|sonographer|ultrasound tech|mri tech|anesthesiologist|anaesthetist|anesthetist|crna|nurse anesthetist|psychiatrist|",
        "psychologist|clinical psychologist|veterinarian|vet tech|veterinary technician|veterinary nurse|optometrist|ophthalmologist|",
        "optician|midwife|dental hygienist|hygienist|physician assistant|physician associate|pa-c|gp|general practitioner|family doctor|pediatrician|paediatrician|cardiologist|",
        "dermatologist|oncologist|neurologist|gynecologist|gynaecologist|obgyn|ob-gyn|urologist|gastroenterologist|endocrinologist|pathologist|internist|hospitalist|intensivist|",
        "er doctor|er nurse|icu nurse|nicu nurse|charge nurse|travel nurse|school nurse|psych nurse|labor and delivery nurse|chiropractor|podiatrist|audiologist|dietitian|",
        "dietician|nutritionist|resident physician|medical resident|surgical resident|junior doctor|clinician|medic|combat medic|perfusionist|medical laboratory scientist|",
        "medical lab scientist|medical technologist|acupuncturist|osteopath|naturopath|healthcare professional|health care professional|healthcare worker|health care worker|",
        "nurse midwife|emergency physician|er physician|trauma surgeon|neurosurgeon|orthopedic surgeon|plastic surgeon|oral surgeon|endodontist|periodontist|prosthodontist|",
        "behavioral therapist|art therapist|music therapist|play therapist|marriage and family therapist|mft|lcsw|lpc|lmft")),
    (CARE, concat!("therapist|psychotherapist|mental health therapist|cna|certified nursing assistant|nursing assistant|nurse aide|nurse's aide|caregiver|care giver|care worker|carer|care assistant|healthcare assistant|health care assistant|",
        "support worker|disability support worker|home health aide|home care worker|personal support worker|psw|medical assistant|pharmacy tech|pharmacy technician|",
        "pharmacy assistant|personal care assistant|phlebotomist|dental assistant|dental nurse|hospice worker|patient care technician|pct|orderly|hospital porter|",
        "sterile processing technician|medical scribe|doula|direct support professional|dsp|behavior technician|behaviour technician|rbt|aba therapist|residential support worker|",
        "care home worker|nursing home worker|hospice aide|home health nurse aide|mental health worker|psych tech|psychiatric technician|ophthalmic technician|optometric technician|",
        "chiropractic assistant|veterinary assistant|vet assistant|massage therapist")),
    (TEACHING, concat!("teacher|tutor|lecturer|educator|teaching assistant|substitute teacher|sub teacher|supply teacher|kindergarten teacher|preschool teacher|pre-k teacher|elementary teacher|",
        "elementary school teacher|primary teacher|primary school teacher|middle school teacher|high school teacher|secondary teacher|secondary school teacher|math teacher|",
        "maths teacher|english teacher|science teacher|history teacher|music teacher|art teacher|pe teacher|gym teacher|chemistry teacher|biology teacher|physics teacher|",
        "special ed teacher|special education teacher|sped teacher|esl teacher|efl teacher|esl tutor|english tutor|math tutor|librarian|school librarian|principal|vice principal|",
        "assistant principal|headteacher|head teacher|headmaster|headmistress|dean|school counselor|school counsellor|guidance counselor|instructor|adjunct|adjunct professor|",
        "adjunct instructor|coach|swim instructor|swimming instructor|driving instructor|flight instructor|paraprofessional|paraeducator|teacher's aide|teacher aide|daycare worker|",
        "childcare worker|child care worker|early childhood educator|nursery teacher|montessori teacher|academic advisor|school psychologist|music instructor|piano teacher|",
        "guitar teacher|dance teacher|dance instructor|language teacher|french teacher|spanish teacher|german teacher|homeschool teacher|lecturer in|college instructor|",
        "university lecturer|professor of|teaching fellow|instructional designer|curriculum developer|education consultant|school administrator|superintendent of schools")),
    (LAW, concat!("lawyer|attorney|paralegal|solicitor|barrister|judge|legal assistant|legal secretary|public defender|prosecutor|district attorney|defense attorney|defence lawyer|",
        "criminal defense attorney|criminal defense lawyer|corporate lawyer|immigration lawyer|immigration attorney|family lawyer|divorce lawyer|tax lawyer|tax attorney|litigator|",
        "notary|notary public|legal counsel|general counsel|in-house counsel|law clerk|court clerk|magistrate|patent attorney|patent agent|patent lawyer|mediator|arbitrator|",
        "court reporter|associate attorney|trial lawyer|personal injury lawyer|estate lawyer|real estate attorney|legal analyst|compliance officer|conveyancer|legal executive")),
    (FINANCE, concat!("accountant|cpa|chartered accountant|financial analyst|banker|investment banker|actuary|auditor|bookkeeper|trader|stock trader|financial advisor|financial adviser|",
        "financial planner|wealth manager|portfolio manager|fund manager|hedge fund manager|bank teller|teller|underwriter|loan officer|mortgage broker|mortgage advisor|",
        "mortgage adviser|insurance broker|claims adjuster|insurance adjuster|tax preparer|tax accountant|tax advisor|payroll specialist|payroll clerk|payroll administrator|",
        "accounts payable clerk|accounts payable specialist|accounts receivable clerk|accounts receivable specialist|credit analyst|risk analyst|quant|quantitative analyst|controller|",
        "financial controller|comptroller|treasurer|cfo|equity analyst|investment analyst|stockbroker|accounting clerk|accounting specialist|accounting manager|finance manager|",
        "billing specialist|collections agent|finance analyst|private banker|relationship manager|credit controller|bank manager|branch manager|bank clerk|bursar|",
        "forensic accountant|enrolled agent|insurance underwriter|investment advisor|investment manager|equity research analyst|fp&a analyst")),
    (BUSINESS, concat!("manager|consultant|management consultant|business consultant|strategy consultant|ceo|coo|cto|cmo|cio|project manager|program manager|programme manager|product manager|",
        "product owner|scrum master|business analyst|executive|director|managing director|operations manager|general manager|hr manager|hr specialist|hr generalist|",
        "hr business partner|hr coordinator|hr professional|human resources manager|human resources specialist|recruiter|technical recruiter|talent acquisition specialist|headhunter|",
        "supervisor|team lead|team leader|account manager|business development manager|business development representative|operations director|vice president|vp|analyst|",
        "strategist|procurement specialist|procurement manager|purchasing agent|purchasing manager|buyer|supply chain manager|supply chain analyst|logistics manager|",
        "event planner|event coordinator|events manager|wedding planner|project coordinator|program coordinator|executive director|nonprofit director|chief of staff|",
        "operations analyst|operations coordinator|management trainee|middle manager|department manager|area manager|regional manager|district manager|plant manager|",
        "facilities manager|property manager|business manager|program director|managing partner|partner at a firm|corporate trainer|change manager")),
    (MEDIA, concat!("marketer|marketing manager|marketing specialist|marketing coordinator|marketing director|marketing executive|marketing assistant|digital marketer|seo specialist|seo consultant|",
        "journalist|editor|copy editor|copywriter|reporter|news reporter|correspondent|columnist|broadcaster|news anchor|radio host|radio presenter|tv presenter|presenter|",
        "social media manager|social media specialist|social media coordinator|community manager|pr specialist|pr manager|pr executive|publicist|communications manager|",
        "communications specialist|communications officer|communications director|comms manager|content writer|content strategist|content marketer|content manager|technical writer|",
        "brand manager|brand strategist|advertising executive|ad exec|media buyer|media planner|growth marketer|email marketer|ghostwriter|speechwriter|press officer|",
        "news editor|managing editor|magazine editor|blogger|podcaster|podcast host|photojournalist|news producer|producer at a news station")),
    (ARTS, concat!("hairdresser|hairstylist|hair stylist|artist|designer|graphic designer|web designer|ux designer|ui designer|ui/ux designer|ux/ui designer|product designer|fashion designer|interior designer|game designer|",
        "level designer|industrial designer|logo designer|motion designer|motion graphics designer|musician|singer|songwriter|singer-songwriter|rapper|drummer|guitarist|bassist|",
        "pianist|violinist|cellist|composer|producer|music producer|record producer|sound engineer|audio engineer|recording engineer|mixing engineer|mastering engineer|sound designer|",
        "audio editor|video editor|film editor|actor|actress|voice actor|voice actress|voice over artist|comedian|stand-up comedian|standup comedian|performer|dancer|choreographer|",
        "photographer|videographer|cinematographer|filmmaker|film maker|film director|writer|author|novelist|poet|screenwriter|playwright|illustrator|animator|3d artist|3d modeler|",
        "concept artist|tattoo artist|tattooist|makeup artist|painter|sculptor|potter|ceramicist|jeweler|jeweller|florist|dj|streamer|content creator|",
        "influencer|model|fashion model|cosplayer|magician|stage manager|stagehand|set designer|costume designer|architect|landscape architect|art director|creative director|",
        "cartoonist|comic artist|mangaka|game artist|tailor|seamstress|dressmaker|glassblower|woodcarver|luthier|session musician|orchestra musician|opera singer|conductor|",
        "music teacher and performer|stunt performer|stuntman|circus performer|puppeteer|digital artist|freelance artist|freelance illustrator|freelance photographer|",
        "wedding photographer|portrait photographer|art teacher and artist|visual artist|fine artist|muralist|calligrapher|printmaker|textile artist|set decorator|gaffer|grip|",
        "camera operator|boom operator|colorist|vfx artist|compositor|storyboard artist|character designer|web comic artist|bandleader|dj and producer")),
    (SALES, concat!("cashier|sales rep|sales representative|salesman|saleswoman|salesperson|sales associate|sales assistant|retail worker|retail associate|retail assistant|shop assistant|",
        "store clerk|shop worker|stocker|shelf stacker|merchandiser|visual merchandiser|store manager|assistant store manager|retail manager|realtor|real estate agent|estate agent|",
        "real estate broker|car salesman|car salesperson|account executive|sales manager|sales engineer|sales consultant|sales executive|sales director|telemarketer|wholesaler|",
        "grocery clerk|insurance agent|insurance salesman|sdr|bdr|retail sales associate|department manager at a store|shopkeeper|pharmacy cashier|sales clerk|checkout operator|",
        "leasing agent|leasing consultant|car dealer|antique dealer|art dealer|vendor|street vendor|market trader|door to door salesman|inside sales rep|outside sales rep|",
        "territory manager|key account manager|personal shopper|beauty advisor|optical sales|parts counter|parts specialist|loan sales")),
    (FOOD, concat!("chef|head chef|sous chef|pastry chef|executive chef|private chef|line cook|prep cook|short order cook|cook|server|waiter|waitress|bartender|barista|barback|busser|busboy|",
        "dishwasher|host|hostess|baker|pastry cook|butcher|fast food worker|kitchen porter|kitchen manager|kitchen assistant|restaurant manager|bar manager|hotel manager|",
        "front desk agent|front desk clerk|concierge|bellhop|bellman|sommelier|caterer|food runner|pizza maker|deli worker|cafe worker|hotel receptionist|night auditor|innkeeper|",
        "publican|brewer|brewmaster|restaurateur|mixologist|cruise ship worker|tour guide|travel agent|food server|banquet server|cocktail server|catering assistant|",
        "fast food manager|shift manager|crew member|crew trainer|line chef|grill cook|fry cook|pizza chef|sushi chef|cafe manager|hotel worker|front of house|back of house|",
        "food truck owner|chocolatier|cheesemaker|winemaker|distiller|maitre d|maître d|steward")),
    (TRADE, concat!("landscaper|electrician|plumber|carpenter|welder|mechanic|auto mechanic|car mechanic|diesel mechanic|aircraft mechanic|aviation mechanic|motorcycle mechanic|hvac tech|hvac technician|",
        "refrigeration technician|roofer|construction worker|laborer|labourer|general contractor|subcontractor|lineman|line worker|tradesman|tradesperson|tradie|mason|bricklayer|",
        "stonemason|machinist|cnc machinist|tool and die maker|handyman|painter and decorator|house painter|drywaller|plasterer|tiler|tile setter|flooring installer|glazier|",
        "ironworker|pipefitter|steamfitter|boilermaker|millwright|sheet metal worker|insulator|concrete finisher|heavy equipment operator|crane operator|excavator operator|",
        "apprentice|apprentice electrician|apprentice plumber|apprentice carpenter|journeyman|journeyman electrician|journeyman plumber|master electrician|master plumber|",
        "locksmith|elevator mechanic|elevator technician|cabinet maker|cabinetmaker|joiner|woodworker|blacksmith|farrier|upholsterer|auto body technician|body shop technician|",
        "panel beater|installer|solar installer|cable technician|telecom technician|appliance repair technician|foreman|site manager|construction manager|project superintendent|",
        "demolition worker|scaffolder|gas fitter|gasfitter|sparky|chippy|miner|coal miner|oil rig worker|roughneck|oilfield worker|lineworker|linesman|wind turbine technician|",
        "field technician|service technician|maintenance electrician|industrial electrician|industrial mechanic|heavy duty mechanic|small engine mechanic|boat builder|shipwright|",
        "shipfitter|pipe welder|fabricator welder|framer|finish carpenter|concrete worker|paver|asphalt worker|road worker|surveyor's assistant|well driller|septic technician|",
        "irrigation technician|pool technician|security system installer|alarm technician|glass installer|window installer|door installer|garage door technician|",
        "electrical contractor|plumbing contractor|roofing contractor|hvac installer|audio installer|car audio installer|auto technician|automotive technician|tire technician")),
    (WAREHOUSE, concat!("warehouse worker|warehouse associate|factory worker|forklift driver|forklift operator|assembly line worker|assembler|production worker|production operator|machine operator|",
        "line operator|picker|packer|order picker|material handler|shipping clerk|receiving clerk|inventory clerk|inventory specialist|warehouse manager|warehouse supervisor|",
        "fulfillment associate|fulfilment associate|quality inspector|quality control inspector|qc inspector|plant operator|process operator|chemical operator|fabricator|",
        "metal fabricator|steelworker|steel worker|mill worker|cnc operator|packaging operator|loader|dock worker|longshoreman|stevedore|production supervisor|",
        "manufacturing technician|production technician|assembly technician|press operator|injection molding operator|sawmill worker|meatpacker|meat packer|cannery worker|",
        "textile worker|seamster|garment worker|printer operator|print technician|shipping and receiving|stock associate|inventory associate|distribution associate")),
    (TRANSPORT, concat!("truck driver|trucker|delivery driver|bus driver|rideshare driver|taxi driver|cab driver|cabbie|chauffeur|courier|mail carrier|mailman|",
        "postman|postwoman|postal worker|letter carrier|rural carrier|train conductor|train driver|train operator|locomotive engineer|railroad worker|railway worker|conductor on a train|",
        "pilot|airline pilot|commercial pilot|co-pilot|copilot|first officer|flight attendant|air hostess|stewardess|cabin crew|air traffic controller|ship captain|sea captain|",
        "deckhand|boat captain|ferry operator|delivery person|",
        "van driver|hgv driver|lorry driver|cdl driver|owner operator|owner-operator|tow truck driver|ambulance driver|logistics coordinator|freight broker|baggage handler|",
        "ramp agent|airport worker|dispatcher for a trucking company|truck dispatcher|delivery rider|bike courier|bicycle courier|motorcycle courier|tram driver|subway operator|",
        "bus operator|transit operator|school bus driver|limo driver|valet driver|crop duster|helicopter pilot|bush pilot|cargo pilot|merchant mariner|merchant seaman|",
        "tugboat captain|harbor pilot|ship's officer|logistics driver|freight driver|long haul trucker|otr driver|flatbed driver|tanker driver")),
    (SAFETY, concat!("cop|police officer|policeman|policewoman|police detective|detective|firefighter|fireman|firefighter/emt|security guard|security officer|bouncer|correctional officer|",
        "corrections officer|prison guard|prison officer|jailer|sheriff|deputy sheriff|sheriff's deputy|state trooper|trooper|dispatcher|911 dispatcher|emergency dispatcher|",
        "police dispatcher|game warden|border patrol agent|customs officer|fbi agent|federal agent|special agent|private investigator|loss prevention officer|",
        "loss prevention associate|bodyguard|lifeguard|probation officer|parole officer|bailiff|constable|law enforcement officer|peace officer|patrol officer|police sergeant|",
        "police lieutenant|fire captain|fire chief|wildland firefighter|volunteer firefighter|paramedic firefighter|security supervisor|security manager|campus security|",
        "transit police|airport security|tsa agent|tsa officer|immigration officer|cbp officer|secret service agent|us marshal|deputy marshal|crime scene investigator|",
        "forensic investigator|forensic technician|detention officer|juvenile detention officer|animal control officer|code enforcement officer|ems worker")),
    (MILITARY, concat!("soldier|marine|sailor|airman|infantryman|paratrooper|army officer|naval officer|military officer|service member|servicemember|navy seal|green beret|army ranger|",
        "reservist|national guardsman|guardsman|fighter pilot|military police officer|military pilot|navy pilot|air force pilot|army medic|navy corpsman|corpsman|",
        "submariner|combat engineer|artilleryman|tanker in the army|special forces operator|commissioned officer|nco|non-commissioned officer|enlisted soldier|",
        "army sergeant|drill sergeant|drill instructor|military intelligence officer|intelligence analyst in the army|signal soldier|army reservist|coast guardsman")),
    (GOVERNMENT, concat!("civil servant|government employee|federal employee|state employee|city employee|county employee|municipal employee|public servant|government worker|diplomat|",
        "foreign service officer|politician|councillor|councilman|councilwoman|city council member|council member|mayor|senator|legislator|policy analyst|policy advisor|",
        "policy adviser|government official|bureaucrat|census worker|tax inspector|irs agent|public sector worker|local government officer|town planner|urban planner|",
        "city planner|government contractor|legislative aide|congressional staffer|political staffer|caseworker for the state|benefits advisor|social security officer|",
        "dmv employee|post office clerk|elections officer|civil service officer|state worker|federal worker|government analyst|program analyst|public health officer|",
        "environmental health officer|building inspector|health inspector|regulatory affairs specialist|park service employee")),
    (SOCIAL, concat!("social worker|case worker|caseworker|case manager|youth worker|youth pastor|pastor|priest|minister|chaplain|nun|monk|rabbi|imam|cantor|deacon|missionary|reverend|vicar|",
        "preacher|evangelist|clergyman|clergywoman|counselor|counsellor|substance use counselor|substance abuse counselor|addiction counselor|addictions counselor|drug counselor|",
        "drug and alcohol counselor|mental health counselor|mental health counsellor|family support worker|child protective services worker|cps worker|community worker|",
        "outreach worker|peer support worker|peer specialist|nonprofit worker|charity worker|volunteer coordinator|marriage counselor|grief counselor|crisis counselor|",
        "crisis worker|victim advocate|child advocate|family advocate|housing advocate|community organizer|youth leader|youth minister|worship leader|church musician|",
        "church administrator|religious sister|lay minister|deaconess|elder in my church|sunday school teacher|camp counselor|residential counselor|shelter worker|",
        "foster care worker|adoption worker|child welfare worker|community health worker|harm reduction worker|refugee caseworker|immigration caseworker")),
    (OFFICE, concat!("receptionist|secretary|admin assistant|administrative assistant|admin|office manager|data entry clerk|data entry operator|data entry specialist|clerk|office clerk|",
        "file clerk|customer service rep|customer service representative|customer service agent|customer service advisor|customer service associate|csr|call center agent|",
        "call centre agent|call center worker|call centre worker|call center rep|office worker|executive assistant|personal assistant|virtual assistant|office assistant|",
        "front desk receptionist|medical secretary|medical receptionist|administrative coordinator|scheduler|records clerk|mail clerk|typist|transcriptionist|medical transcriptionist|",
        "medical coder|medical biller|billing clerk|claims processor|insurance clerk|customer support agent|customer support specialist|customer support representative|",
        "support agent|help desk agent|administrator|administrative officer|administration officer|office administrator|team administrator|clerical worker|desk clerk|",
        "front office assistant|patient coordinator|patient access representative|unit secretary|ward clerk|operations assistant|logistics assistant|purchasing assistant|",
        "hr assistant|accounts assistant|admin officer|admin worker|office temp|temp worker|data analyst assistant|document controller|records manager|court administrator|",
        "school secretary|church secretary|legal receptionist|dental receptionist|vet receptionist|chat support agent|email support agent|technical support agent|",
        "call center representative|call centre representative|telephone operator|switchboard operator")),
    (SERVICE, concat!("janitor|custodian|cleaner|house cleaner|office cleaner|commercial cleaner|housekeeper|maid|maintenance worker|maintenance man|maintenance technician|maintenance tech|",
        "building maintenance worker|groundskeeper|stylist|barber|cosmetologist|nail tech|nail technician|manicurist|esthetician|",
        "aesthetician|beautician|lash tech|lash technician|brow artist|masseuse|masseur|nanny|au pair|babysitter|dog walker|pet sitter|dog groomer|groomer|pet groomer|",
        "dog trainer|personal trainer|fitness instructor|fitness trainer|fitness coach|yoga teacher|yoga instructor|pilates instructor|spin instructor|life coach|butler|valet|",
        "window cleaner|pool cleaner|exterminator|pest control technician|laundry worker|dry cleaner|funeral director|mortician|embalmer|undertaker|chimney sweep|",
        "car wash attendant|detailer|car detailer|professional organizer|home organizer|room attendant|housekeeping attendant|building superintendent|caretaker|",
        "concierge at a building|doorman|porter|cobbler|shoe repairer|key cutter|tanning consultant|spa therapist|beauty therapist|skin therapist|wax specialist|",
        "electrologist|personal stylist|image consultant|wedding officiant|pet care worker|kennel worker|kennel attendant|animal care worker|doggy daycare worker|",
        "house sitter|handyperson|property maintenance worker|custodial worker|sanitation worker|garbage man|garbage collector|bin man|binman|refuse collector|recycling worker")),
    (OUTDOOR, concat!("farmer|rancher|farmhand|farm hand|farm worker|farm labourer|dairy farmer|cattle rancher|cattleman|gardener|horticulturist|forester|logger|lumberjack|fisherman|",
        "commercial fisherman|arborist|tree surgeon|park ranger|forest ranger|beekeeper|apiarist|shepherd|ranch hand|vineyard worker|grower|hunting guide|fishing guide|",
        "greenhouse worker|nursery worker|zookeeper|animal keeper|horse trainer|stable hand|groom at a stable|wrangler|trail guide|mountain guide|river guide|outdoor educator|",
        "wildlife biologist|conservation officer|conservationist|ecologist in the field|tree planter|orchardist|fruit picker|crop farmer|grain farmer|poultry farmer|",
        "pig farmer|sheep farmer|goat farmer|organic farmer|market gardener|groundsman|greenkeeper|golf course superintendent|landscape gardener|lawn care technician")),
    (ADULT, concat!("escort|sex worker|cam girl|camgirl|cam model|webcam model|cam boy|camboy|stripper|exotic dancer|porn star|pornstar|adult performer|",
        "adult content creator|adult film actress|adult film actor|porn actress|porn actor|dominatrix|pro domme|prodomme|phone sex operator|sugar baby|nsfw creator|",
        "content seller|camwhore|call girl|courtesan|sex worker and escort|lingerie model|fetish model|findom")),
    (OTHER, concat!("translator|interpreter|sign language interpreter|courtroom interpreter|gig worker|landlord|auctioneer|appraiser|estate agent assistant|pawnbroker|surveyor of quantities|",
        "quantity surveyor|genealogist|archivist|museum curator|curator|docent|lab animal technician|clockmaker|watchmaker|gunsmith|taxidermist|sommelier trainee|",
        "professional gamer|esports player|pro gamer|professional athlete|athlete|footballer|soccer player|basketball player|baseball player|hockey player|jockey|referee|umpire|",
        "golf pro|tennis pro|professional poker player|poker player|astronaut|domain expert|ai trainer|data annotator|data labeler|freelance translator|proofreader|",
        "scuba instructor|ski instructor|snowboard instructor|surf instructor|climbing instructor|sports coach|cheerleader|mascot|caddie")),
    (FOUNDER, "founder|co-founder|cofounder|entrepreneur|business owner|small business owner|solopreneur|startup founder|business woman|businesswoman|businessman|business man"),
    (OWNER, "freelancer|sole trader|sole proprietor|bar owner|restaurant owner|shop owner|store owner|salon owner|contractor|independent contractor|self-employed contractor"),
];

pub const SKILL: &str = concat!("good|great|bad|decent|terrible|awful|amazing|better|best|worse|worst|home|amateur|hobby|hobbyist|aspiring|wannabe|wanna-be|future|former|ex|retired|noob|newbie|",
    "beginner|budding|failed|frustrated|would-be|prospective|fake|pretend|big|huge|massive|total|natural|born|picky|lazy|self-taught|shitty|crappy|mediocre|average|okay|ok|",
    "competent|excellent|fantastic|awesome|horrible|poor|weekend|backyard|armchair|bedroom|closet|student|wanna|sucky|lousy|messy|careful|safe|nervous|confident|avid");
pub const BLOCK_WORDS: &str = "and or but with to of for in at on who that like this my your his her their our the a an not no than as is was can cant can't";
pub const HEADS: &str = concat!("engineer|developer|dev|manager|officer|assistant|technician|tech|worker|analyst|specialist|consultant|nurse|scientist|designer|director|architect|administrator|",
    "operator|supervisor|coordinator|aide|teacher|artist|writer|editor|producer|agent|representative|rep|clerk|student|lead|instructor|therapist|counselor|counsellor|",
    "attorney|lawyer|driver|mechanic|inspector|owner|practitioner|apprentice|trainee|intern|major|graduate|grad|candidate|friend|fan|school|program|programme|degree|",
    "course|class|classes|job|position|wife|husband|girlfriend|boyfriend|partner|mom|mum|dad|parent|family|kid|daughter|son|simulator|game|citizen|character|wannabe|",
    "cosplay|costume|outfit|role|roleplay|rp|fantasy|kink|fetish|uniform|show|movie|series");

pub const SOC: &[(&str, &str)] = &[
    ("11", BUSINESS), ("11-2", MEDIA), ("11-2022", SALES), ("11-3021", SOFTWARE), ("11-3031", FINANCE), ("11-3051", WAREHOUSE), ("11-3071", TRANSPORT), ("11-9013", OUTDOOR), ("11-9021", TRADE),
    ("11-903", TEACHING), ("11-9041", ENGINEERING), ("11-9051", FOOD), ("11-9071", FOOD), ("11-9081", FOOD), ("11-9121", SCIENCE), ("11-9131", GOVERNMENT), ("11-9151", SOCIAL),
    ("11-9161", SAFETY), ("11-917", SERVICE), ("13", BUSINESS), ("13-1031", FINANCE), ("13-1032", FINANCE), ("13-1161", MEDIA), ("13-2", FINANCE), ("15", SOFTWARE), ("15-2", SCIENCE),
    ("15-2011", FINANCE), ("15-2051", SOFTWARE), ("17", ENGINEERING), ("17-1011", ARTS), ("17-1012", ARTS), ("19", SCIENCE), ("19-303", CLINICAL), ("19-3051", GOVERNMENT), ("21", SOCIAL),
    ("23", LAW), ("25", TEACHING), ("25-401", OTHER), ("27", ARTS), ("27-3", MEDIA), ("27-3043", ARTS), ("27-3091", OTHER), ("27-2021", OTHER), ("27-2022", TEACHING), ("27-2023", OTHER),
    ("29", CLINICAL), ("29-2052", CARE), ("29-2053", CARE), ("31", CARE), ("33", SAFETY), ("35", FOOD), ("37", SERVICE), ("37-3", OUTDOOR), ("39", SERVICE), ("39-7", FOOD), ("39-9011", TEACHING),
    ("41", SALES), ("41-3031", FINANCE), ("43", OFFICE), ("43-3031", FINANCE), ("43-3071", FINANCE), ("43-5021", TRANSPORT), ("43-5031", SAFETY), ("43-505", TRANSPORT),
    ("43-5071", WAREHOUSE), ("43-5081", SALES), ("45", OUTDOOR), ("47", TRADE), ("49", TRADE), ("51", WAREHOUSE), ("51-3011", FOOD), ("51-3021", FOOD), ("51-6052", ARTS), ("51-9071", ARTS),
    ("53", TRANSPORT), ("53-7", WAREHOUSE), ("53-7081", SERVICE), ("55", MILITARY),
];

pub const ONET_STOP: &str = concat!("owner captain player hunter hiker climber comic helper president agent advocate builder breeder boarder guide sewer anchor mixer closer checker dresser ",
    "hanger buffer roller receiver spinner tender filler seater searcher examiner deputy dealer collector trader planner picker sacker scribe messenger ",
    "cowboy caster blender spotter burner chipper bundler runner reader rider starter member observer leader mentor organizer volunteer survivor novice ",
    "delegate resident catcher grader feeder stapler wrapper winder sorter scaler shipper bagger mover pusher");

pub const FOREIGN: &[(&str, &str)] = &[
    (CLINICAL, concat!("médico|médica|doctor|doctora|enfermero|enfermera|dentista|farmacéutico|farmacéutica|psicólogo|psicóloga|fisioterapeuta|enfermeiro|enfermeira|farmacêutico|farmacêutica|",
        "arzt|ärztin|zahnarzt|zahnärztin|krankenschwester|krankenpfleger|apotheker|apothekerin|psychologe|psychologin|physiotherapeut|physiotherapeutin|hebamme|médecin|",
        "infirmier|infirmière|dentiste|pharmacien|pharmacienne|psychologue|kiné|kinésithérapeute|sage-femme|medico|infermiere|infermiera|farmacista|psicologo|psicologa|",
        "lekarz|lekarzem|lekarką|pielęgniarka|pielęgniarką|pielęgniarz|pielęgniarzem|dentystą|farmaceutą|psychologiem|arts|dokter|verpleegkundige|verpleger|tandarts|psycholoog")),
    (CARE, concat!("cuidador|cuidadora|altenpfleger|altenpflegerin|pflegekraft|pfleger|pflegerin|pflegehelfer|pflegehelferin|aide-soignant|aide-soignante|badante|opiekunką|opiekunem|",
        "verzorgende|verzorger")),
    (TEACHING, concat!("profesor|profesora|maestro|maestra|docente|professor|professora|lehrer|lehrerin|erzieher|erzieherin|dozent|dozentin|professeur|prof|enseignant|enseignante|",
        "instituteur|institutrice|insegnante|professore|professoressa|nauczyciel|nauczycielem|nauczycielka|nauczycielką|leraar|lerares|docent|juf")),
    (SOFTWARE, concat!("programador|programadora|desarrollador|desarrolladora|informático|informática|desenvolvedor|desenvolvedora|programmierer|programmiererin|entwickler|entwicklerin|",
        "softwareentwickler|softwareentwicklerin|informatiker|informatikerin|fachinformatiker|développeur|développeuse|informaticien|informaticienne|programmeur|",
        "programmeuse|programmatore|sviluppatore|sviluppatrice|informatico|programista|programistą|ontwikkelaar")),
    (ENGINEERING, "ingeniero|ingeniera|engenheiro|engenheira|ingenieur|ingenieurin|ingénieur|ingénieure|ingegnere|inżynier|inżynierem"),
    (LAW, concat!("abogado|abogada|advogado|advogada|anwalt|anwältin|rechtsanwalt|rechtsanwältin|jurist|juristin|avocat|avocate|avvocato|avvocata|prawnik|prawnikiem|adwokat|adwokatem|",
        "advocaat")),
    (FINANCE, "contador|contadora|contable|buchhalter|buchhalterin|steuerberater|steuerberaterin|comptable|commercialista|contabile|księgowy|księgowym|księgowa|księgową|boekhouder"),
    (GOVERNMENT, concat!("funcionario público|funcionaria pública|funcionário público|funcionária pública|servidor público|servidora pública|beamter|beamtin|fonctionnaire|",
        "funzionario pubblico|dipendente pubblico|urzędnik|urzędnikiem|urzędniczką|ambtenaar")),
    (SAFETY, concat!("policía|policial|polizist|polizistin|policier|policière|poliziotto|poliziotta|policjant|policjantem|politieagent|bombero|bombera|bombeiro|bombeira|feuerwehrmann|",
        "pompier|pompière|vigile del fuoco|strażak|strażakiem|brandweerman")),
    (MILITARY, "soldado|militar|soldat|soldatin|soldato|żołnierz|żołnierzem|soldaat"),
    (TRADE, concat!("electricista|eletricista|elektriker|électricien|elettricista|elektryk|elektrykiem|elektricien|fontanero|encanador|klempner|installateur|plombier|idraulico|hydraulik|",
        "hydraulikiem|loodgieter|carpintero|carpinteiro|tischler|schreiner|menuisier|falegname|stolarz|stolarzem|timmerman|mecánico|mecânico|mechaniker|kfz-mechatroniker|",
        "mécanicien|meccanico|mechanik|mechanikiem|monteur|albañil|pedreiro|maurer|maçon|muratore|murarz|murarzem|metselaar|handwerker|soldador|schweißer|soudeur|saldatore|",
        "spawacz|spawaczem|lasser")),
    (FOOD, concat!("cocinero|cocinera|cozinheiro|cozinheira|koch|köchin|cuisinier|cuisinière|cuoco|cuoca|kucharz|kucharzem|kok|camarero|camarera|mesero|mesera|garçom|garçonete|kellner|",
        "kellnerin|serveur|serveuse|cameriere|cameriera|kelner|kelnerem|kelnerką|ober|serveerster|barista|panadero|padeiro|bäcker|boulanger|fornaio|piekarz|bakker")),
    (SALES, concat!("vendedor|vendedora|verkäufer|verkäuferin|vendeur|vendeuse|commesso|commessa|sprzedawca|sprzedawcą|sprzedawczynią|verkoper|verkoopster|cajero|cajera|kassierer|",
        "kassiererin|caissier|caissière|cassiere|cassiera|kasjer|kasjerem|kasjerką")),
    (TRANSPORT, concat!("camionero|camionera|caminhoneiro|motorista|fahrer|fahrerin|lkw-fahrer|busfahrer|berufskraftfahrer|chauffeur|routier|camionista|kierowca|kierowcą|",
        "vrachtwagenchauffeur|piloto|pilot|pilotin|pilote|pilota|pilotem|piloot|repartidor|entregador|zusteller|livreur")),
    (ARTS, concat!("artista|künstler|künstlerin|artiste|artysta|artystą|artystką|kunstenaar|diseñador|diseñadora|designer|designerin|grafiker|grafikerin|graphiste|grafik|grafikiem|",
        "músico|música|musiker|musikerin|musicien|musicienne|musicista|muzyk|muzykiem|muzikant|fotógrafo|fotógrafa|fotograf|fotografin|photographe|fotografo|fotografa|",
        "fotografem|fotograaf|escritor|escritora|schriftsteller|schriftstellerin|écrivain|écrivaine|scrittore|scrittrice|pisarz|pisarzem|schrijver|actor|actriz|ator|atriz|",
        "schauspieler|schauspielerin|acteur|actrice|attore|attrice|aktor|aktorem|aktorką|ilustrador|ilustradora|illustrator|illustratorin|illustrateur|illustratrice|",
        "illustratore|ilustratorem|arquitecto|arquiteto|arquitecta|arquiteta|architekt|architektin|architecte|architetto|architektem")),
    (SCIENCE, concat!("investigador|investigadora|pesquisador|pesquisadora|forscher|forscherin|wissenschaftler|wissenschaftlerin|chercheur|chercheuse|ricercatore|ricercatrice|",
        "naukowiec|naukowcem|onderzoeker|wetenschapper|científico|científica|cientista|doktorand|doktorandin|doctorant|doctorante|dottorando|doktorantem")),
    (OFFICE, concat!("secretario|secretaria|secretária|sekretär|sekretärin|secrétaire|segretario|segretaria|sekretarka|sekretarką|secretaresse|recepcionista|rezeptionist|",
        "rezeptionistin|réceptionniste|receptionist|receptionista|recepcjonistką|bürokaufmann|bürokauffrau|administrativo|administrativa")),
    (SERVICE, concat!("peluquero|peluquera|cabeleireiro|cabeleireira|friseur|friseurin|friseuse|coiffeur|coiffeuse|parrucchiere|parrucchiera|fryzjer|fryzjerem|fryzjerką|kapper|",
        "kapster|limpiador|limpiadora|reinigungskraft|niñera|babá|kindermädchen|nounou|niania|nianią")),
    (SOCIAL, concat!("trabajador social|trabajadora social|assistente social|sozialarbeiter|sozialarbeiterin|sozialpädagoge|sozialpädagogin|assistant social|assistante sociale|",
        "assistente sociale|sacerdote|pfarrer|pfarrerin|prêtre|prete|ksiądz|księdzem|priester|pastor|pastora|pastoor|dominee")),
    (OUTDOOR, concat!("agricultor|agricultora|campesino|campesina|fazendeiro|fazendeira|landwirt|landwirtin|bauer|bäuerin|agriculteur|agricultrice|agricoltore|rolnik|rolnikiem|boer|",
        "jardinero|jardinera|jardineiro|gärtner|gärtnerin|jardinier|giardiniere|ogrodnik|hovenier|tuinman")),
    (BUSINESS, concat!("gerente|gestor|gestora|manager|managerin|geschäftsführer|geschäftsführerin|consultor|consultora|berater|beraterin|unternehmensberater|consultant|consultante|",
        "consulente|konsultant|konsultantem|adviseur|kierownik|kierownikiem|bedrijfsleider")),
    (WAREHOUSE, concat!("operario|operaria|operário|operária|lagerarbeiter|lagerist|lageristin|fabrikarbeiter|magasinier|magasinière|operaio|operaia|magazynier|magazynierem|",
        "magazijnmedewerker|produktionsmitarbeiter")),
    (OWNER, concat!("autónomo|autónoma|autônomo|autônoma|selbstständig|selbständig|freiberufler|freiberuflerin|unternehmer|unternehmerin|empresario|empresaria|empresário|empresária|",
        "emprendedor|emprendedora|empreendedor|empreendedora|entrepreneur|entrepreneuse|indépendant|indépendante|imprenditore|imprenditrice|libero professionista|",
        "freelancer|freelance|ondernemer|zzp'er|zelfstandige|przedsiębiorcą|przedsiębiorca")),
];
pub const FOREIGN_BLOCK: &str = "kein keine keiner geen pas nie não no non nicht plus ex";

pub const BUSINESSES: &[(&str, &str)] = &[
    (FOOD, concat!("bar|pub|restaurant|cafe|café|coffee shop|bakery|pizza shop|pizzeria|pizza place|food truck|diner|brewery|hotel|motel|b&b|bed and breakfast|catering business|catering company|",
        "taqueria|food stall|food cart|deli|bistro|sandwich shop|ice cream shop|donut shop|tea shop|bubble tea shop|burger joint|food business|restaurant business")),
    (SERVICE, concat!("salon|hair salon|nail salon|barbershop|barber shop|spa|cleaning business|cleaning company|grooming business|dog grooming business|pet sitting business|dog walking business|",
        "daycare for dogs|laundromat|car wash|detailing business")),
    (ARTS, concat!("tattoo shop|tattoo studio|tattoo parlor|tattoo parlour|photography business|photography studio|art studio|recording studio|design studio|design agency|dance studio|",
        "music studio|production company|record label|pottery studio|gallery")),
    (OUTDOOR, "farm|ranch|landscaping business|landscaping company|lawn care business|lawn care company|orchard|vineyard|nursery|tree service"),
    (TRADE, concat!("construction company|construction business|construction firm|plumbing business|plumbing company|electrical business|electrical company|roofing company|roofing business|",
        "hvac company|hvac business|auto shop|repair shop|body shop|mechanic shop|handyman business|painting business|painting company|remodeling company|",
        "renovation business|carpentry business|welding shop|machine shop|fabrication shop|woodworking shop")),
    (TRANSPORT, "trucking company|trucking business|moving company|courier business|delivery business|logistics company|taxi company"),
    (FINANCE, "accounting firm|accounting practice|bookkeeping business|tax business|tax practice|financial advisory firm|insurance agency"),
    (LAW, "law firm|law practice|legal practice"),
    (CLINICAL, "dental practice|medical practice|vet practice|veterinary practice|veterinary clinic|clinic|private practice|therapy practice|chiropractic practice|physiotherapy clinic|pharmacy"),
    (TEACHING, "daycare|tutoring business|tutoring company|preschool|music school|dance school|driving school|language school"),
    (MEDIA, "marketing agency|ad agency|advertising agency|digital agency|pr firm|pr agency|seo agency|media company|publishing company"),
    (SOFTWARE, "software company|software business|tech company|tech startup|saas company|web development agency|web design business|it company|it business|dev shop|game studio"),
    (BUSINESS, "business|company|startup|small business|firm|agency|llc|own business|own company|online business|franchise"),
    (SALES, "shop|store"),
    ("", "practice|side business"),
];

pub const FIELDS: &[(&str, &str)] = &[
    (CARE, "aged care|elder care|eldercare|elderly care|disability services|disability support|home care|home health|home health care|social care|residential care|dementia care|behavioral health|behavioural health"),
    (SOFTWARE, "tech|technology|ai|software|cybersecurity|cyber security|data science|web development|game development|gamedev|game dev|saas|fintech|devops|it industry|it field|information technology"),
    (CLINICAL, "healthcare|health care|nursing|medicine|the medical field|medical field|dentistry|veterinary medicine|mental health|emergency medicine|pharma|pharmaceuticals"),
    (ENGINEERING, "engineering"),
    (TRADE, "construction|the trades|trades|plumbing|electrical|hvac|roofing|welding|oil and gas|oilfield|the oilfield|mining|the mines|the mine"),
    (SALES, "retail|sales|real estate|car sales"),
    (FINANCE, "finance|banking|insurance|accounting|investment banking|private equity|wealth management|asset management|audit|tax|payroll"),
    (MEDIA, "marketing|advertising|media|journalism|public relations|pr|publishing|digital marketing|social media marketing|communications|comms|broadcasting"),
    (FOOD, "hospitality|food service|the restaurant industry|restaurants|kitchens|fast food|the service industry|service industry|catering|the hotel industry|hotels|tourism"),
    (GOVERNMENT, "government|the government|local government|public service|the public sector|public sector|civil service|the civil service|politics|policy"),
    (MILITARY, "the military|military|the army|the navy|the air force|the marines|the marine corps|the coast guard|the national guard|the reserves|the army reserve|the armed forces"),
    (SAFETY, "law enforcement|policing|corrections|security|private security|the fire service|fire service|ems|emergency services"),
    (SCIENCE, "research|academia|science|a lab|biotech"),
    (TEACHING, "education|teaching|higher education|higher ed|early childhood education|childcare|child care|special education|special ed|edtech"),
    (BUSINESS, concat!("consulting|management consulting|management|hr|human resources|recruiting|recruitment|operations|project management|product management|supply chain|procurement|",
        "business development|corporate|strategy")),
    (TRANSPORT, "logistics|trucking|transportation|aviation|shipping|delivery|freight|the airline industry|airlines|rail|railroads"),
    (WAREHOUSE, "manufacturing|a factory|a warehouse|warehousing|production|fulfillment|distribution"),
    (SOCIAL, "social work|social services|ministry|nonprofits|the nonprofit sector|non-profits|harm reduction|child welfare|addiction treatment|youth work"),
    (OFFICE, "customer service|customer support|admin|administration|a call center|a call centre|call centers|data entry|reception"),
    (ARTS, "film|entertainment|the film industry|music|the music industry|fashion|design|graphic design|animation|game design|theater|theatre|photography|tv|television|vfx|art"),
    (LAW, "law|legal|big law|biglaw"),
    (SERVICE, "beauty|the beauty industry|cosmetology|hairdressing|cleaning|janitorial|fitness|pest control|funeral services"),
    (OUTDOOR, "agriculture|farming|landscaping|forestry|fishing|conservation|horticulture"),
    (ADULT, "sex work|the adult industry|adult entertainment|porn"),
];

pub const PLACES: &[(&str, &str)] = &[
    (CARE, "nursing home|care home|assisted living facility|assisted living|group home|hospice|retirement home|memory care facility|home care agency"),
    (FOOD, concat!("restaurant|bar|pub|hotel|motel|kitchen|cafe|café|coffee shop|bakery|pizza place|pizza shop|fast food restaurant|fast food place|diner|brewery|casino|resort|catering company|",
        "steakhouse|sushi restaurant|deli|cafeteria|food truck|cruise ship|country club|golf club|night club|nightclub|club")),
    (SALES, concat!("store|grocery store|supermarket|gas station|retail store|department store|mall|car dealership|dealership|bookstore|clothing store|shoe store|thrift store|furniture store|jewelry store|pet store|",
        "convenience store|liquor store|shop|boutique|phone store|electronics store|hardware store|big box store|retailer")),
    (WAREHOUSE, concat!("warehouse|factory|distribution center|distribution centre|fulfillment center|fulfilment centre|plant|manufacturing plant|mill|sawmill|",
        "processing plant|meat plant|meatpacking plant|cannery|print shop|assembly plant|steel mill|paper mill|refinery")),
    (TEACHING, concat!("school|elementary school|middle school|high school|primary school|secondary school|preschool|kindergarten|daycare|university|college|community college|",
        "tutoring center|learning center|library|academy|charter school|private school|public school|montessori school|boarding school|language school")),
    (FINANCE, "bank|credit union|accounting firm|insurance company|investment bank|hedge fund|brokerage|tax firm|financial firm"),
    (LAW, "law firm|courthouse|court|public defender's office|da's office|prosecutor's office|legal aid office|legal clinic"),
    (OFFICE, "call center|call centre|front desk|reception desk|office|corporate office|head office"),
    (TRADE, "construction site|construction company|auto shop|body shop|mechanic shop|garage|machine shop|repair shop|oil rig|mine|coal mine|shipyard|power plant|car shop|tire shop"),
    (TRANSPORT, "airport|airline|trucking company|post office|train station|bus depot|shipping company|logistics company|moving company|port"),
    (SAFETY, "police department|police station|fire department|fire station|prison|jail|correctional facility|detention center|sheriff's office|sheriff's department|security company"),
    (GOVERNMENT, "city hall|government agency|federal agency|state agency|council|dmv|social security office|embassy|consulate|town hall|county office"),
    (SOCIAL, concat!("church|nonprofit|non-profit|charity|shelter|homeless shelter|women's shelter|food bank|community center|mosque|synagogue|temple|youth center|treatment center|rehab|",
        "detox center|halfway house")),
    (SOFTWARE, "tech company|software company|startup|tech startup|it company|game studio|data center|saas company|big tech"),
    (MEDIA, "newspaper|magazine|news station|tv station|radio station|ad agency|advertising agency|marketing agency|pr firm|publishing house|publisher|media company"),
    (ARTS, "studio|recording studio|design studio|museum|gallery|theater|theatre|cinema|movie theater|film studio|animation studio|tattoo shop|tattoo studio|photography studio"),
    (SCIENCE, "lab|laboratory|research lab|research institute|research center|observatory|biotech company|pharma company|pharmaceutical company"),
    (SERVICE, "salon|hair salon|nail salon|barbershop|barber shop|spa|gym|fitness center|car wash|funeral home|dry cleaners|laundromat|kennel|doggy daycare|grooming salon"),
    (OUTDOOR, "farm|ranch|nursery|garden center|greenhouse|vineyard|orchard|zoo|aquarium|park|national park|golf course|stable|stables|dairy farm"),
    (BUSINESS, "consulting firm|consultancy|staffing agency|recruitment agency"),
    ("", concat!("company|firm|agency|business|corporation|small business|family business|organization|organisation|nonprofit organization|place|",
        "hospital|clinic|medical clinic|dental office|dentist office|dentist's office|doctor's office|vet clinic|vet office|veterinary clinic|animal hospital|er|icu|nicu|",
        "emergency room|urgent care|pharmacy|surgery center|rehab center|psych ward|psychiatric hospital|mental hospital|medical center|health center|optometrist office")),
];

pub const VERBS: &[(&str, &str)] = &[
    ("sell", SALES), ("teach", TEACHING), ("tutor", TEACHING), ("clean", SERVICE), ("drive", TRANSPORT), ("cook", FOOD), ("bartend", FOOD), ("code", SOFTWARE), ("program", SOFTWARE),
    ("nurse", CLINICAL), ("deliver", TRANSPORT), ("repair", TRADE), ("fix", TRADE), ("build", TRADE), ("install", TRADE), ("cut", SERVICE), ("tattoo", ARTS), ("farm", OUTDOOR),
    ("trade", FINANCE), ("edit", ARTS), ("photograph", ARTS), ("film", ARTS), ("stream", ARTS), ("cam", ADULT), ("dance", ARTS), ("model", ARTS), ("dj", ARTS), ("translate", OTHER), ("design", ARTS),
    ("write", ARTS), ("develop", SOFTWARE), ("groom", SERVICE), ("paint", ARTS), ("sing", ARTS), ("act", ARTS), ("illustrate", ARTS), ("animate", ARTS), ("audit", FINANCE), ("manage", BUSINESS),
    ("consult", BUSINESS), ("recruit", BUSINESS), ("plumb", TRADE), ("weld", TRADE), ("wait", FOOD), ("serve", FOOD), ("bake", FOOD), ("landscape", OUTDOOR),
];

pub const INTERNSHIPS: &[(&str, &str)] = &[
    ("banking", FINANCE), ("finance", FINANCE), ("accounting", FINANCE), ("audit", FINANCE), ("tax", FINANCE), ("marketing", MEDIA), ("journalism", MEDIA), ("media", MEDIA),
    ("engineering", ENGINEERING), ("software", SOFTWARE), ("it", SOFTWARE), ("data", SOFTWARE), ("tech", SOFTWARE), ("coding", SOFTWARE), ("developer", SOFTWARE), ("law", LAW), ("legal", LAW),
    ("nursing", CLINICAL), ("clinical", CLINICAL), ("pharmacy", CLINICAL), ("medical", CLINICAL), ("hospital", CLINICAL), ("teaching", TEACHING), ("research", SCIENCE), ("design", ARTS),
    ("consulting", BUSINESS), ("hr", BUSINESS), ("sales", SALES), ("retail", SALES), ("hotel", FOOD), ("government", GOVERNMENT), ("electrical", TRADE), ("plumbing", TRADE),
    ("carpentry", TRADE), ("welding", TRADE), ("mechanic", TRADE), ("hvac", TRADE),
];

const CS: &str = "computer science or IT";
const NAT: &str = "natural sciences";
const SOC_SCI: &str = "social sciences";
const MED: &str = "medicine or health";
const MATH: &str = "mathematics or statistics";
const BIZ: &str = "business or finance";
const HUM: &str = "humanities";
const ART: &str = "arts or design";

pub const SUBJECT_PAIRS: &[(&str, &str)] = &[
    ("computer systems", CS), ("information systems", CS), ("infosys", CS), ("informatics", CS),
    ("social science", SOC_SCI), ("social sciences", SOC_SCI), ("chem", NAT), ("bio", NAT), ("econ", SOC_SCI), ("psych", "psychology"), ("poli sci", SOC_SCI), ("polisci", SOC_SCI),
    ("computer science", CS), ("cs", CS), ("comp sci", CS), ("software engineering", CS),
    ("information technology", CS), ("it", CS), ("data science", CS), ("cybersecurity", CS),
    ("engineering", "engineering"), ("mechanical engineering", "engineering"), ("electrical engineering", "engineering"), ("civil engineering", "engineering"),
    ("chemical engineering", "engineering"), ("aerospace engineering", "engineering"), ("math", MATH), ("maths", MATH),
    ("mathematics", MATH), ("statistics", MATH), ("physics", NAT), ("chemistry", NAT),
    ("biology", NAT), ("biochemistry", NAT), ("geology", NAT), ("astronomy", NAT), ("neuroscience", NAT),
    ("environmental science", NAT), ("medicine", MED), ("nursing", MED), ("pharmacy", MED),
    ("public health", MED), ("kinesiology", MED), ("physical therapy", MED), ("psychology", "psychology"),
    ("sociology", SOC_SCI), ("political science", SOC_SCI), ("anthropology", SOC_SCI), ("economics", SOC_SCI), ("criminology", SOC_SCI),
    ("international relations", SOC_SCI), ("geography", SOC_SCI), ("business", BIZ), ("finance", BIZ),
    ("accounting", BIZ), ("marketing", BIZ), ("management", BIZ), ("business administration", BIZ),
    ("law", "law"), ("education", "education"), ("history", HUM), ("english", HUM), ("philosophy", HUM), ("literature", HUM),
    ("linguistics", HUM), ("classics", HUM), ("theology", HUM), ("religious studies", HUM), ("art", ART), ("fine arts", ART),
    ("graphic design", ART), ("music", ART), ("film", ART), ("theater", ART), ("theatre", ART),
    ("architecture", ART), ("design", ART), ("journalism", HUM), ("communications", SOC_SCI),
    ("cse", CS), ("ai", CS), ("med", MED), ("vet", MED), ("mech", "engineering"), ("ece", "engineering"),
    ("eee", "engineering"), ("life sci", NAT), ("life science", NAT),
];

pub const SUBJECT_TABLE: &[(&str, &str)] = &[
    (CS, "computer engineering|software development|web development|information security|game development|data analytics|artificial intelligence|machine learning"),
    ("engineering", concat!("biomedical engineering|industrial engineering|environmental engineering|materials engineering|petroleum engineering|nuclear engineering|mechatronics|",
        "electronics engineering|nanotechnology|robotics|engineering physics|computer and electrical engineering")),
    (MATH, "applied math|applied mathematics|actuarial science|stats"),
    (NAT, concat!("biochem|microbiology|molecular biology|cell biology|genetics|zoology|botany|ecology|marine biology|astrophysics|earth science|materials science|physiology|",
        "biotechnology|forensic science|life sciences|biological sciences|natural sciences")),
    (MED, concat!("dentistry|veterinary medicine|nutrition|dietetics|occupational therapy|speech pathology|radiography|midwifery|paramedicine|health science|health sciences|",
        "exercise science|pharmacology|biomedical science|premed|pre-med|optometry|physiotherapy|nuclear medicine")),
    (SOC_SCI, "social work|criminal justice|public policy|public administration|urban planning|homeland security|gender studies"),
    (BIZ, "human resources|supply chain management|hospitality management|entrepreneurship|international business|commerce|business management|economics and finance"),
    (HUM, "art history|english literature|comparative literature|creative writing|religion|archaeology"),
    (ART, "game design|fashion design|interior design|animation|photography|film studies|music production|music theory|dance|drama|illustration|industrial design"),
    ("education", "early childhood education|special education|elementary education|secondary education"),
    ("law", "legal studies|pre-law|prelaw"),
    ("psychology", "clinical psychology|counseling psychology"),
];

const BACH: &str = "bachelor's degree";
const MAST: &str = "master's degree";
const PROF: &str = "professional degree such as law or medicine";
const TRADE_SCHOOL: &str = "trade school or associate degree";

pub const DEGREES: &[(&str, &str)] = &[
    ("bachelor", BACH), ("bachelors", BACH), ("bachelor's", BACH), ("ba", BACH), ("bs", BACH), ("bsc", BACH),
    ("b.s.", BACH), ("b.a.", BACH), ("bcom", BACH), ("b.com", BACH), ("btech", BACH), ("b.tech", BACH),
    ("beng", BACH), ("bba", BACH), ("bfa", BACH), ("bsn", BACH), ("undergrad degree", BACH), ("undergraduate degree", BACH),
    ("master", MAST), ("masters", MAST), ("master's", MAST), ("ma", MAST), ("ms", MAST), ("msc", MAST), ("m.s.", MAST),
    ("mba", MAST), ("msw", MAST), ("mtech", MAST), ("m.tech", MAST), ("mfa", MAST), ("meng", MAST), ("mse", MAST),
    ("phd", "doctorate"), ("ph.d", "doctorate"), ("ph.d.", "doctorate"), ("doctorate", "doctorate"), ("dphil", "doctorate"), ("jd", PROF),
    ("md", PROF), ("mbbs", PROF), ("dds", PROF),
    ("pharmd", PROF), ("dvm", PROF), ("llb", BACH), ("associate's", TRADE_SCHOOL),
    ("associates", TRADE_SCHOOL), ("associate degree", TRADE_SCHOOL), ("ged", "high school diploma"), ("high school diploma", "high school diploma"),
];
pub const SHORT_DEGREES: &[&str] = &["ba", "bs", "ma", "ms", "md", "jd", "b.s.", "b.a.", "m.s.", "mse", "dds", "dvm", "mfa", "ged", "associates", "associate's"];

pub const SCHOOLS: &[(&str, &str)] = &[
    ("law", "law"), ("l", "law"), ("med", MED), ("medical", MED), ("pharmacy", MED), ("nursing", MED), ("dental", MED),
    ("vet", MED), ("veterinary", MED), ("residency", MED), ("engineering", "engineering"),
    ("business", BIZ), ("b", BIZ), ("art", ART), ("film", ART), ("architecture", ART),
];

pub const FOREIGN_SUBJECTS: &[(&str, &str)] = &[
    ("engineering", "engenharia|ingeniería|ingenieria|ingegneria|ingénierie|ingenieurwesen|maschinenbau|elektrotechnik"),
    (MED, "medicina|médecine|medizin|enfermagem|enfermería|enfermeria|farmácia|farmacia|pharmacie|odontologia|odontología|fisioterapia|pflege"),
    ("law", "direito|derecho|droit|jura|jus|giurisprudenza|rechten|rechtswissenschaft|prawo"),
    (CS, "informática|informatica|informatique|informatik|computação|computacion|computación|wirtschaftsinformatik"),
    ("psychology", "psicologia|psicología|psychologie|psychologia"),
    (ART, "arquitetura|arquitectura|architettura|architecture|architektur|design|diseño|artes|arte|kunst"),
    (BIZ, "administração|administración|administracion|contabilidade|contabilidad|economia|economía|économie|bwl|betriebswirtschaft|gestion|finanzas|finanças"),
    (NAT, "biologia|biología|biologie|bio|química|quimica|chimie|chemie|física|fisica|physique|physik|geologia|geología"),
    (MATH, "matemática|matemáticas|matematica|mathématiques|mathe|mathematik|estatística|estadística|statistik"),
    (SOC_SCI, "sociologia|sociología|sociologie|soziologie|ciência política|ciencias políticas|politikwissenschaft|antropologia"),
    ("education", "pedagogia|pedagogía|pédagogie|pädagogik|lehramt|magisterio"),
    (HUM, "história|historia|geschichte|letras|filosofia|filosofía|philosophie|literatura|germanistik|anglistik"),
];

pub const DEGREE_SUBJECT_EXTRA: &[(&str, &str)] = &[
    ("it management", CS), ("accountancy", BIZ), ("ultrasound", MED), ("electronics", "engineering"),
    ("electronics and communication", "engineering"), ("electronics and communication engineering", "engineering"),
];

pub const DEGREE_FIELDS: &[(&str, &str)] = &[
    (BIZ, "mba|bba|bcom|b.com|mcom|m.com"), (MED, "mbbs|bsn|msn|pharmd|dvm|bds"), ("law", "llb"),
    (ART, "bfa|mfa"), (SOC_SCI, "msw|bsw"), ("engineering", "btech|b.tech|mtech|m.tech|beng|meng"),
];

pub const AMBIGUOUS_SUBJECTS: &[&str] = &["it", "ai", "art", "design", "film", "music", "dance", "business", "management", "marketing", "history", "english", "photography", "drama", "religion",
    "nutrition", "med", "vet", "education", "commerce"];
