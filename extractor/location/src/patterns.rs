use crate::lexicon::LEXICON;
use claimcore::re::{I as IGNORE, M};
use claimcore::*;
use std::sync::LazyLock;

const DIRS: &str = "north|south|east|west|northern|southern|eastern|western|central|upstate|downstate|rural|coastal|middle|sw|se|nw|ne|northeast|northwest|southeast|southwest|downtown|uptown|metro|inner|outer|far|deep";
const ADVERB: &str = r"(?:(?:currently|now|still|also|just|actually|already|really|basically|technically|originally|both|all|recently|happily|finally|permanently)\s+)*";
const WAY: &str = r"(?:(?:just|right|somewhere|up|down|out|over|back|here|there|mostly)\s+)*(?:(?:north|south|east|west|northeast|northwest|southeast|southwest|outside|close to|next to|near)\s+(?:of\s+)?)?";
const PREP: &str = r"(?:in|near|outside(?: of)?|around|by|at|out of)\s+";
const SUBJECT: &str = r"(?:\bi|\bwe|\bme and my \w+|\bmy (?:wife|husband|partner|family|girlfriend|boyfriend|fiance|fiancee|kids|parents) and i)";
const PERSON_NOUN: &str = r"(?:guy|girl|man|woman|boy|lady|dude|gal|person|couple|cpl|student|kid|teen|teenager|mom|mum|dad|father|mother|wife|husband|bro|native|immigrant|expat|top|bottom|vers|bear|twink|femboy|sub|dom|daddy|milf|bull|transfem|transmasc|nurse|doctor|engineer|teacher|developer|artist|writer|player|gamer)";
const PERSON: &str = r"(?:guy|girl|man|woman|boy|lady|dude|gal|person|couple|cpl|student|kid|teen|teenager|mom|mum|dad|father|mother|wife|husband|bro|native|immigrant|expat|top|bottom|vers|bear|twink|femboy|sub|dom|daddy|milf|bull|transfem|transmasc|nurse|doctor|engineer|teacher|developer|artist|writer|player|gamer)s?";
const BRIEF: &str = r"(?!(?:pro|anti|as|mistaken|good|bad|great|ethnically|racially|culturally|sorry|sure|pretty|glad|afraid|aware|against|about|any|some|every|on|at|over|so|very|not|never|no|half|part|partly|quarter|mixed|fan|big|huge|of|in|to|from|with|the|for|into|like|than|fluent|native|married|probably|maybe|ex|former|formerly|called)\b)(?!\w+ing\b)[\w'-]+ ";
const BELIEF: &str = r"christian|muslim|jew|jewish|catholic|atheist|conservative|liberal|i|we|\w+ly";
const NOUNS: &str = r"teacher|tutor|speaker|speaking|learner|major|lit|literature|class|course|translator|food|cuisine|company|restaurant|accent|dish|product|brand|movie|film|show|song|word|name|language|music|culture|history|government|team|prof|professor|degree|program|programme|department|cheese";
const SELF_LEAD: &str = r"(?:(?<![\w.$#'/:+-])\d{2}(?:\s?(?:yo|y/o|m|f|years?(?: old)?))?|(?<![\w.$#'/:+-])[mf]\s?\d{2}s?|\bjust an?|\bi'?m an?|\bim an?|\bi am an?)[\s,/|)\]-]+(?:[a-z0-9']+\s+){0,3}?";

static S_END: LazyLock<String> = LazyLock::new(|| format!(r"(?:(?:an?|the)\s+(?:\w+\s+){{0,2}}(?:town|village|city|suburb|part|side|area|middle of nowhere)\s+(?:in|of|near|outside(?: of)?)\s+)?(?:the\s+)?(?:city of\s+|state of\s+|town of\s+|province of\s+|greater\s+)?(?:(?:{DIRS})\s+)?[*_]*\Z"));

pub static S_NATION: LazyLock<String> = LazyLock::new(|| {
    let mut escaped: Vec<String> = LEXICON.nation_names.iter().map(|name| escape(name)).collect();
    escaped.sort_by(|a, b| b.chars().count().cmp(&a.chars().count()).then(a.cmp(b)));
    escaped.join("|")
});

static S_AS_TAIL: LazyLock<String> = LazyLock::new(|| format!(r"({NATION})(?:[- ]born)?(?=$|[\s.,!;:)])(?![ \t]+(?!(?:and|but|so|myself|citizen|national|person|man|woman|guy|girl|dude|male|female|living|who|born|raised|here|in|from|it|its|there|that|by|expat|immigrant|veteran|mom|mother|dad|father|parent|voter|taxpayer|kid|child|adult|student|resident|native|lol|{BELIEF}|can|could|would|will|should|do|does|did|have|has|had|am|our|my|me|us|where|looking|with|this|you|though|too)\b)[a-z])", NATION = &*S_NATION));

pub fn as_nation() -> String {
    format!(r"(?:\bas (?:an?|another|a fellow)(?: proud| native| born and raised)? |\bme as (?=\w+,)|\bas (?<!such as )(?<!same as )(?=\w+,?\s+(?:i|i'm|im|we|myself)\b)){AS_TAIL}", AS_TAIL = &*S_AS_TAIL)
}

pub fn as_nation_start() -> String {
    format!(r"(?:^|[.!?\n]\s*)as (?=\w+,){AS_TAIL}", AS_TAIL = &*S_AS_TAIL)
}

pub fn loose_nation() -> String {
    format!(r"(?:\b{I}|(?:^|[.!?\n(]\s*)am) {ADVERB}(?:an? |a proud |a born and raised |proud(?:ly)? )?(?:{BRIEF}){{0,3}}?({NATION})(?: citizen| national)?(?=$|[\s.,!;:)—–]|-\s)(?!\s+(?:teacher|tutor|speaker|speaking|learner|major|lit|literature|class|course|translator|food|cuisine|company|restaurant|accent|prof|professor|degree|program|programme|department|cheese)\b)", NATION = &*S_NATION)
}

macro_rules! pattern {
    ($name:ident, $flags:expr, $body:expr) => {
        pub static $name: LazyLock<Re> = LazyLock::new(|| Re::with(&$body, $flags));
    };
}

pattern!(LIVE, 0, format!(r"{SUBJECT}(?:\s+(?:currently|now|still|also|just|actually|already|really|recently|both|all|happily|finally))*(?:\s+(?:live|stay|reside|moved|relocated|settled)|(?:'ve|\s+have)\s+(?:been\s+)?(?:lived|living|based|settled))(?!(?:\s+\w+){{0,2}}\s+out\s+of\b)\s+{ADVERB}{WAY}(?:{PREP}|to\s+|on\s+)?(?:(?!(?:a|an|the|my|our|with|and|but|for|of|to|in|by|near|at|from|this|that|fear|hope|peace|sin|denial)\b)[a-z]+\s+){{0,2}}?{END}", END = &*S_END));
pattern!(BEING, 0, format!(r"(?:\bi'm|\bim|\bi am|\bwe're|\bwe are|\biam|\bi (?:now|currently|still|also) am)(?:\s+(?:currently|now|still|also|just|actually|already|really|basically|technically|both|all|living|based|located|residing|settled|here|out|over|down|up|back|happily|permanently|right|somewhere))*\s+(?:{WAY}{PREP}|(?:(?:just|right)\s+)?(?:north|south|east|west|northeast|northwest|southeast|southwest|outside)\s+of\s+){END}", END = &*S_END));
pattern!(BARE, 0, format!(r"(?:^|[\n.!?;:•*>(|/-]\s*|\b(?:and|but|also|currently|now|so|still)\s+|\bas someone\s+(?:who\s+)?|(?<![\w.$#'/:+-])\d{{2}}\s?[mf]?\s+)(?:currently\s+|now\s+|also\s+|still\s+)?(?:live|living|lives|based|located|residing|reside)\s+(?:here\s+)?{PREP}{END}", END = &*S_END));
pattern!(HERE, 0, format!(concat!(r"\b(?:here|over here|out here|down here|up here)\s+in\s+{END}|(?:^|[\n.!?,;:(]\s*|\b(?:for|of|to|with|among)\s+)(?:we|us)\s+(?:here\s+)?in\s+{END}|\b(?:greetings|hello|hi|hey|love|cheers|regards|blessings|hugs|howdy|saludos|grüße|grüsse)\s+from\s+{END}",
    r"|\b(?:my|our) (?:city|town|country|state|province|county|neighborhood|neighbourhood|island|village|area|house|building|apartment|flat)(?:\s*(?:of residence|of|,|:|-|\(|\.|is in|in))*\s*{END}"), END = &*S_END));
pattern!(MOVED, 0, format!(r"(?:(?:^|[\n.!?;:(]\s*|\bthen\s+|\b\d{{2}}\s?[mf]\s+)(?:just\s+|recently\s+|finally\s+|eventually\s+)?(?:moved|relocated)|\bdecided to (?:move|relocate))\s+(?:back\s+)?(?:over\s+)?(?:here\s+)?to\s+{END}", END = &*S_END));
pattern!(ABROAD, 0, concat!(r"\b(?:vivo|vivimos|resido|radico|estoy|estamos|moro|moramos|wohne|wohnen|lebe|leben|j'habite|habite|je vis|je réside|j'vis|je me trouve|me trouve|abito|risiedo|woon|wonen)\s+(?:actualmente\s+|atualmente\s+|aktuell\s+|derzeit\s+|zurzeit\s+|actuellement\s+|attualmente\s+|nu\s+)?",
    r"(?:en|em|no|na|in|im|à|a|au|aux|dans le|dans la|dans les|dans|nel|nella|bei|nahe|cerca de|perto de|près de|vicino a|in der nähe von)\s+(?:el\s+|la\s+|o\s+|a\s+|der\s+|den\s+|le\s+|il\s+|het\s+)?\Z",
    r"|\b(?:aquí|aqui|acá|hier|ici|qui)\s+(?:en|em|no|na|in|à|a)\s+\Z|\b(?:jeg|jag|eg|vi)\s+bor\s+i\s+\Z"));
pattern!(FROM, 0, format!(concat!(r"(?:\bi'm|\bim|\bi am|\bwe're|\bwe are|\bi come|\bwe come|\boriginally|(?<!for )\bbeing|\bme being)(?:\s+(?:currently|still|also|just|actually|originally|both|all|here|over|out|down|up|\w+ly))*\s+from\s+{END}",
    r"|(?:^|[\s(\[])(?:\d{{2}}\s?[mfw]|[mfw]\s?\d{{2}}|cpl)(?:\s+here)?\s+from\s+{END}",
    r"|\b(?:i'm|im|i am)\s+(?:an?\s+)?\d{{2}}(?:\s*-?\s*(?:years?[- ]old|yo|y/o|[mf]))?(?:\s+[a-z]+){{0,3}}\s+from\s+{END}"), END = &*S_END));
pattern!(GERMAN, 0, r"\b(?:ich\s+)?(?:komme|kommen|bin)\s+(?:\w+\s+)?(?:aus|von)\s+(?:der nähe von\s+|dem\s+|der\s+)?\Z|(?:^|[,(\[/])\s*aus\s+\Z|\b(?:[mwf]\s?\d{2}|\d{2}\s?[mwf]|[mwf])\s+aus\s+\Z");
pattern!(LEFT, 0, concat!(r"(?<!\bno )(?<!\bnão )(?<!\bnao )\b(?:soy|somos|sou)\s+(?:de|del|da|do|originario de|originaria de|natural de)\s+(?:la\s+|el\s+|o\s+|a\s+)?\Z|\b(?:ich\s+)?stamme\s+(?:\w+\s+)?(?:aus|von)\s+(?:der nähe von\s+|dem\s+|der\s+)?\Z",
    r"|\bje (?:suis|viens) (?:de|du|d')\s*\Z|\bsono di\s+\Z|\bvengo (?:de|da|dal|dalla)\s+\Z|\b(?:ik\s+)?kom (?:uit|van)\s+\Z"));
pattern!(ORIGIN, 0, format!(concat!(r"(?:{SUBJECT}|\bas an? (?:person|guy|girl|woman|man|kid|someone) who)(?:\s+(?:was|were|got))?(?:\s+(?:\w+ly|also|both|all))*\s+(?:grew up|raised|born|brought up)(?:\s+and\s+(?:raised|bred))?\s+(?:in|on|near|outside(?: of)?|around)\s+{END}",
    r"|\bborn and (?:raised|bred) (?:in|on)\s+{END}|(?:^|[\n.!?(]\s*)(?:grew up|born|raised|born and raised) in\s+{END}",
    r"|(?:^|[\n.!?(,]\s*)(?:growing up|having grown up) (?:in|on)\s+{END}|\b(?:i|i'm|im|i was|me)\b[^.!?\n]{{0,60}}?\b(?<!kids )(?<!children )(?<!son )(?<!daughter )(?<!they )(?<!who )growing up (?:in|on)\s+{END}|\b(?:i|we)\s+(?:\w+ly\s+)?hail from\s+{END}|\b(?:i|we)\s+spent (?:my|our) (?:\w+\s+)?(?:childhood|youth|teens|teenage years|early years) (?:in|on)\s+{END}|\b(?:i'm|im|i am) (?:an?\s+)?native of\s+{END}",
    r"|\b(?:my|our) (?:\w+\s+)?(?:hometown|home town|home country|homeland|birthplace|birth country|native country|motherland|home state)(?:\s*(?:is|was|of|in|,|:|-|\())*\s*{END}",
    r"|\b(?:nací|naci|nasci|nacido|nacida|nascido|nascida|geboren|né|née|nato|nata)\s+(?:en|em|no|na|in|à|a|au)\s+\Z"), END = &*S_END, SUBJECT = SUBJECT));
pattern!(DOUBTED, 0, r"\b(?:if|when|whenever|unless|whether|wish|wished|hope|imagine|pretend|once|until|till|before|would|could|should|wanna|want to|plan to|planning to|used to|thinking about|considering)\s+(?:\w+\s+){0,2}\Z");
pattern!(LATER, 0, r"\s*(?:for\s+(?:(?:a|an|the|this|next|one|two|three|few|couple|\d+)\s+){0,2}(?:of\s+)?(?:day|days|week|weeks|weekend|night|nights|month|months|trip|holiday|holidays|vacation|work|business|bit|while|now|summer|conference)\b|on|until|till|next|this|last|right now|today|tonight|tomorrow|again|visiting|at the moment)\b");
pattern!(START, 0, r"(?:^|[\n.!?,;(:]\s*|\b(?:also|fellow|another|a|an|proud)\s+)\Z");
pattern!(HERE_AFTER, 0, format!(r"(?:\s+(?:{PERSON}|people|resident|local|area|family|fan|collector|redditor|user))?,?\s+here\b(?=\s*(?:$|[\n.!,;:)\-–—(&]|and\b|too\b|as well\b|lol|haha|so\b|but\b|with\b))"));
pattern!(SELF, 0, r"(?:\b(?:i'm|im|i am|we're|we are|am)\s+(?:an?\s+)?|^(?:r/\w+:\s*)?|[\n.!?,;]\s*)\Z");
pattern!(BORN, 0, r"(?:\b(?:i'm|im|i am|we're|we are|am|my|i was)\s+(?:an?\s+)?|^(?:r/\w+:\s*)?|[\n.!?,;(]\s*)\Z");
pattern!(CITIZEN, 0, r"\b(?:i'm|im|i am|as|am|we're|we are|being|dual)\s+(?:an?\s+)?(?:\w+\s+)?\Z|\(\Z");
pattern!(TITLE, M, format!(r"(?<![\w-])(?:{FOR}|{TAG}|\b\d{{2}},\s*[mf]\b|\[\d{{2}}\]|\(\d{{2}}\)|\b[mft]4[mfatr]\w*|\bage:?\s*\d{{2}}\b|\b\d{{2}}\s*/\s*[mf]\b|\b[mf]\s*/\s*\d{{2}}\b)|^(?:r/\w+:)?\s*\d{{2}}(?=\s+(?:[\[(]\s*)?(?!(?:years?|days?|weeks?|months?|hours?|minutes?|seconds?|times?|percent|people|of)\b(?!\s+old))[a-z])"));
pattern!(LEAD, M, format!(r"(?:{FOR}|{TAG}|[\[\](){{}}#/|,:;!.–-]|\b(?:in|from|near|around|aus|de|em|en|di|loc|male|female)|^(?:r/\w+:)?\s*\(?\d{{2}}\)?|^)\s*(?:(?:{DIRS})\s+)?\Z"));
pattern!(TOWN_LEAD, 0, format!(r"\b(?:in|from|to|of|near|around|outside|at)\s+(?:(?:{DIRS})\s+)?\Z"));
pattern!(TAG_LEAD, 0, format!(r"(?:{FOR}|{TAG})\s*\Z"));
pattern!(LAST, 0, r"[\W_]*\Z");
pattern!(NEAR, 0, r"\b(?:in|from|near|around|aus)\s+\Z");
pattern!(ASKING, 0, r"\b(?:for|looking|seeking|searching|want|wants|need|needs|into|with|like|likes|love|loves|any|anyone|you|you're|youre|your|if)\b");
pattern!(ADMINISTRATIVE, 0, r"\b(?:region|city|province|district|county|governorate|prefecture|department|municipality|oblast|division|capital)\b");
pattern!(LOOSE, 0, format!(r"\b(?:and|but|so)\s+(?:then\s+|just\s+|recently\s+|finally\s+|eventually\s+)?(?:moved|relocated)\s+(?:back\s+)?(?:here\s+)?to\s+{END}|(?<!be )(?<!it's )(?<!its )(?<!it )(?<!is )(?<!are )(?<!was )(?<!were )(?<!they're )\b(?:living|based|located|residing)\s+(?:here\s+)?{PREP}{END}|\b(?:currently|now)\s+(?:living\s+|based\s+)?in\s+{END}", END = &*S_END));
pattern!(SELF_FROM, 0, format!(r"\b(?:i'm|im|i am)\s+(?:(?!(?:with|to|for|about|of|in|on|at|and|or|but|that|who|my|his|her|their|our|your|the|this|it|is|was|not|never|from|away|far|apart|miles?|mi|km|hours?|hrs|minutes?|mins?|drive|walk|days?|weeks?|months?|back|home|free|safe|different|done|off|out|coming|moved|relocated|transferred|graduated|returned|retired|escaped|fled|immigrated|emigrated|banned|removed|separated|divorced|exiled|kicked|evacuated|deported|isolated|disconnected|\w+ing)\b)[\w'/()-]+,?\s+){{1,8}}?from\s+{END}", END = &*S_END));
pattern!(TAG_FROM, 0, format!(r"(?:^|[\s(\[\]/|,-])(?:\d{{2}}|{PERSON}|male|female|[mft]4[mfatr]\w*)\s+from\s+{END}", END = &*S_END));
pattern!(AGED_IN, 0, format!(r"(?:{TAG}|\b\d{{2}}[- ]?(?:years?[- ]old|yrs?[- ]old|yo|y/o)\b)(?:\s+(?!(?:for|looking|seeking|want|wants|need|needs|into|with|like|likes|love|loves|any|anyone|you|your|if|visiting|going|travel|traveling|travelling|staying|stuck|be|will)\b)[\w'-]+){{0,5}}\s+in\s+{END}", END = &*S_END));
pattern!(ROLE, 0, format!(r"\b(?:i'm|im|i am)\s+an?\s+(?:(?!not\b|never\b)[\w-]+\s+){{1,4}}in\s+{END}", END = &*S_END));
pattern!(OPENING, 0, r#"(?:^|[.!?\n])[\s\"'*]*\Z"#);
pattern!(AREA, IGNORE, r"\s+(?:area|county)\b");
pattern!(FLAIR, 0, r"\Ar/[a-z0-9_]+:\s*");
pattern!(VENUE, IGNORE, r"\s+(?:stadium|arena|airport|university|college|time|zone|street|avenue|mall|hospital|station)\b");
pattern!(TRIP, 0, r"\b(?:visiting|business trip|road trip|(?<!come )(?<!can )(?<!you )travel(?:l?ing)? (?:to|through)|in town (?:for|this|until|till)|passing through|layover|on vacation|on holiday|checked into|hotel room|my hotel|coming (?:to|up to|down to)|heading to|will be in|going to be in)\b");
pattern!(TRADE, 0, r"[\w ,/-]{0,12}\]\s*\[h\]");
pattern!(COPULA, 0, r"(?<!no )(?<!não )(?<!nao )(?<!non )\b(?:soy|somos|sou|je suis|nous sommes|ich bin|bin|wir sind|sono|siamo|ik ben|wij zijn)\s+(?:(?:un|una|um|uma|ein|eine|re|muy|bien|très|tres|molto|sehr|auch|también|tambien|aussi|anche|também|tambem|ook)\s+)?\Z");
pattern!(OPENER, 0, format!(r"(?:^|[\n.!?]\s*)(?:originally\s+)?from\s+{END}", END = &*S_END));
pattern!(OPENER_END, 0, r"\s*(?:$|[.!,\n]|\s+(?:and|but|here|originally)\b)");
pattern!(WHERE, 0, r"\s*,?\s+(?:is |that's |which is )?where i(?:'m| am|'ve| have)?\s+(?:(live|living|reside|currently live|lived|now live|stay)|(?:originally )?(?:am |'m )?(from|come from)|(grew up|was born|was raised|was born and raised))\b");
pattern!(LOCAL, 0, r"\s+(native|local|resident)\b");
pattern!(LOCAL_LEAD, 0, format!(r"\b(?:i'm|im|i am|as|am)\s+an?\s+{ADVERB}(?:(?:{DIRS})\s+)?\Z"));
pattern!(CITIZEN_AFTER, 0, r"\.?\s+(?:citizen|national|passport holder)s?\b");
pattern!(HOME_COUNTRY, M, r"(?:\b(?:my|our) (?:home |own |native )?country\s*(?:,|\(|:|-|is|of)?\s*|\b(?:i|i'm|im|i am|i was|me)\b[^.!?\n]*\bborn and (?:raised|bred) in (?:the )?)\Z");
pattern!(HOSTING, 0, format!(r"\b(?:hosting|can host|new)\s+(?:in|to)\s+{END}", END = &*S_END));
pattern!(LOCATION, 0, r"(?:^(?:r/\w+:\s*)?|\n)[\W_]*(?:location|loc|based)[\W_]*[:=-][\W_]*\Z");
pattern!(HOMETOWN, 0, r"\s*[,.(-]?\s*(?:(?:it's|its|it is|is|was)\s+)?my\s+(?:hometown|home town|birthplace)\b");
pattern!(LIFE, 0, r"(?:,?\s+[a-z]+){0,2}?,?\s+(?:my|all my|for my) (?:entire |whole )?life\b");
pattern!(AUTOMATED, 0, r"\bi am a bot\b|\bperformed automatically\b|\bplease (?:make sure|include)\b|\bpost (?:has been |was )?removed\b|\bmust (?:include|contain)\b");
pattern!(REPOST, 0, r"(?:original (?:post|text)|copy of (?:your|the) post|backup of your post|post body)[^\n:]{0,30}:[*\s]*");
pattern!(SUBJECTIVE, 0, r"\b(?:i|i'm|im|we|we're|me|as an?)\b");
pattern!(CHAIN, 0, r"[\s,(:–—-]*(?:(?:more\s+)?specifically|namely|in|near|around|outside(?: of)?|just outside(?: of)?|close to)?[\s,(:–—-]*(?:the\s+)?");
pattern!(GROUP, 0, r"(?:\b(?:we|us)(?: (?:fellow|proud|all))? \(?|\bwe(?:'re| are) (?:all |both )?|\bproud to be (?:an? )?|(?<!him )(?<!her )(?<!them )(?<!his )(?<!their )(?<!its )(?<!it )(?<!he )(?<!she )(?<!they )(?<!you )(?<!your )(?<!people )(?<!someone )(?<!to )(?<!with )(?<!just )(?<!while )(?<!about )\bbeing (?:an? )?)\Z");
pattern!(NOUN_AFTER, 0, format!(r"\s+(?:{NOUNS})s?\b"));
pattern!(GROUP_END, 0, format!(r"\)?(?=$|[\s.,!;:)])(?!\s+(?:{NOUNS})s?\b)"));
pattern!(AGE_FRAME, M, format!(r"(?<![\w.$#'/:+-])\d\d(?<!my \d\d)(?<!a \d\d)(?<!an \d\d)(?<!the \d\d)(?<!her \d\d)(?<!his \d\d)(?<!our \d\d)[- ]?(?:years?[- ]old|yrs?[- ]old|yo|y/o)[\s,-]+(?:{BRIEF}){{0,2}}?({NATION})(?=$|[\s.,!;:)])", NATION = &*S_NATION));
pattern!(HELD_FRAME, M, format!(r"\b(?:my|have|hold|holding|got|own)\s+(?:an?\s+|dual\s+)?({NATION})\s+(?:passport|citizenship)\b|\bdual (?:citizenship|nationality|citizen|national)s?\s*[:,(-]?\s*({NATION})\b", NATION = &*S_NATION));
pattern!(SELF_PAREN, M, format!(r"\b(?:i|me|myself)\s*\(\s*(?:an?\s+)?({NATION})(?![\w'-])|\bme,\s+an?\s+({NATION})(?![\w'-])", NATION = &*S_NATION));
pattern!(LABEL_FRAME, M, format!(r"\bnationality(?: is)?[\W_]+(?:an?\s+)?({NATION})(?![\w'-])", NATION = &*S_NATION));
pattern!(COMPOUND_FRAME, M, format!(r"(?:\b{I}|\bas) (?:an? )?(?:\w+ )?({NATION})(?:wo)?m[ae]n\b", NATION = &*S_NATION));
pattern!(AM_FRAME, M, format!(r"(?:^|:\s*|\bbut )am (?:an? )?({NATION})(?![\w'/-])|\b{I} (?:also )?\d\d,\s*({NATION})(?![\w'-])", NATION = &*S_NATION));
pattern!(AS_WIDE, M, format!(r"\bas (?:an?|another) (?:[\w-]+ ){{1,3}}?({NATION})(?:[- ]born)?(?:\s+{PERSON})?(?=\s*[,.;!]|\s+(?:i|i'm|im|we|myself|it|this|that|there)\b)", NATION = &*S_NATION));
pattern!(LOOSE_NATION, 0, loose_nation());
pattern!(AS_NATION, 0, as_nation());
pattern!(AS_NATION_START, 0, as_nation_start());
pattern!(SELF_DESCRIBED, 0, format!(r"{SELF_LEAD}({NATION})(?:\s+[a-z']+){{0,3}}?\s+(?:{PERSON_NOUN}|male|female|cuck|gentleman|lad|chick|hubby|here)\b", NATION = &*S_NATION));
pattern!(SELF_FROM_LEAD, 0, format!(r"{SELF_LEAD}from\s+(?:the\s+)?\Z"));
pattern!(TAG_BEFORE, M, format!(r"(?:{TAG}|{FOR}|\A[^\w\n]*\d{{2}}|\b\d{{2}}\s?(?:yo|y/o|male|female)|^[^\w\n]*[mf])[\s,/|:()\[\]-]*\Z"));
pattern!(TAG_AFTER, 0, format!(r"[\s,/|(\[-]*(?:{TAG}|\d{{2}}\s?(?:yo|y/o)\b|(?:1[89]|[2-9]\d)\s*[)\]]|(?:m|f|male|female)\s*[,/|]\s*\d{{2}}\b)"));
pattern!(NATION_HERE, 0, format!(r"(?:\s+(?:{PERSON}|fan|citizen|national))?(?:\s+(?:living in|based in|from)\s+[a-z]+(?: [a-z]+)?)?,?\s+(?:over |out |down |up )?here\b(?!\s+(?:is|are|was|were|in|on|at|for|to|from|of)\b)"));
pattern!(OPENS, 0, r"(?:^(?:r/\w+:)?|[.!?\n]\s*)[\W_]*(?:(?:hi|hey|hello|yeah|yes|also|just|sadly|proudly|proud|nope|no|well|lol)[,.!]*\s+)*(?:(?!(?:my|his|her|their|our|your|the|this|that|these|those|some|any|every|no|not|of|to|for|with|from|in|on|at|is|was|are|were|a|an|and|or|but|if|when|i|you|he|she|they|we|it|me|him|them|us|like|love|than|as|so)\b)[a-z-]+,?\s+(?:and\s+)?){0,3}\Z");
pattern!(CLOSES, 0, format!(r"(?:(?:\s+(?!couple|cpl){PERSON_NOUN})?(?:,?\s+(?:here|based|living|moving|looking|seeking)\b|[ \t]*,?[ \t]*\d\d(?![\w%]))|(?:\s+(?!(?:is|are|was|were|and|or|but|in|on|at|from|of|to|the|a|an|who|that)\b)[a-z]+){{1,3}},?\s+here\b(?!\s+(?:is|are|was|were|in|on|at|for|to|from|of)\b))(?![ \t]*(?:and|or|/|&)?[ \t]*(?:{NATION})\b)", NATION = &*S_NATION));
pattern!(OTHERS_LEAD, 0, r"\b(?:the|these|those|his|her|their|your|our|any|some|many|most|other|no|of|every|each|all)\s+\Z");
pattern!(CITIZEN_OF, 0, r"\b(?:i'm|im|i am|as|am|being)\s+(?:an?\s+)?(?:\w+\s+)?citizen of\s+(?:the\s+)?\Z");
pattern!(SELF_IN_LEAD, 0, format!(r"{SELF_LEAD}(?:in|near|around)\s+(?:the\s+)?\Z"));

pub type Frame = (&'static Re, &'static [&'static str], bool, bool);

pub fn frames() -> [Frame; 7] {
    [
        (&AGE_FRAME, &["y"], true, true),
        (&HELD_FRAME, &["passport", "citizenship", "dual"], false, false),
        (&SELF_PAREN, &["(", "me,"], true, false),
        (&LABEL_FRAME, &["nationality"], true, false),
        (&COMPOUND_FRAME, &["man", "men"], false, false),
        (&AM_FRAME, &["am ", ","], true, false),
        (&AS_WIDE, &["as a"], true, false),
    ]
}

pub fn asked_frames() -> [Frame; 3] {
    [(&LOOSE_NATION, &[""], true, false), (&AS_NATION, &[""], true, false), (&AS_NATION_START, &[""], true, false)]
}

pub fn all() -> Vec<&'static Re> {
    vec![
        &LIVE, &BEING, &BARE, &HERE, &MOVED, &ABROAD, &FROM, &GERMAN, &LEFT, &ORIGIN, &DOUBTED, &LATER, &START, &HERE_AFTER, &SELF, &BORN, &CITIZEN, &TITLE, &LEAD,
        &TOWN_LEAD, &TAG_LEAD, &LAST, &NEAR, &ASKING, &ADMINISTRATIVE, &LOOSE, &SELF_FROM, &TAG_FROM, &AGED_IN, &ROLE, &OPENING, &AREA, &VENUE, &FLAIR, &TRIP, &TRADE, &COPULA, &OPENER,
        &OPENER_END, &WHERE, &LOCAL, &LOCAL_LEAD, &CITIZEN_AFTER, &HOME_COUNTRY, &HOSTING, &LOCATION, &HOMETOWN, &LIFE, &AUTOMATED, &REPOST, &SUBJECTIVE, &CHAIN,
        &GROUP, &NOUN_AFTER, &GROUP_END, &AGE_FRAME, &HELD_FRAME, &SELF_PAREN, &LABEL_FRAME, &COMPOUND_FRAME, &AM_FRAME, &AS_WIDE, &LOOSE_NATION, &AS_NATION, &AS_NATION_START,
        &SELF_DESCRIBED, &SELF_FROM_LEAD, &TAG_BEFORE, &TAG_AFTER, &NATION_HERE, &OPENS, &CLOSES, &OTHERS_LEAD, &CITIZEN_OF, &SELF_IN_LEAD,
    ]
}
