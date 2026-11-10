use crate::*;

const ELIDED: &str = concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n]\s*)(?:also |currently |now |still |unfortunately |sadly |just |recently |happily )?");
const STATED: &str = r"(?=\s*(?:$|[.,!;:)(\n-]|\b(?:for|since|and|now|right|currently|again|atm|rn|lol|but|so|too|myself|here|with|as|in|at)\b))";
const ADVERB: &str = r"(?:(?:also|now|currently|still|actually|literally|basically|just|only|really|officially|finally|myself|technically|already|proudly|both|happily|full[- ]?time|part[- ]?time) )*";
const BEFORE: &str = r"us\$|usd|c\$|ca\$|cad|a\$|au\$|aud|nz\$|nzd|s\$|sgd|hk\$|hkd|r\$|brl|€|eur|£|gbp|₹|inr|rs\.?|chf|sek|nok|dkk|pln|jpy|cny|rmb|¥|\$";
const AFTER: &str = r"us dollars?|american dollars?|canadian dollars?|australian dollars?|us\$|usd|cad|aud|nzd|sgd|hkd|brl|reais|eur|euros?|gbp|pounds?|quid|inr|rupees?|chf|sek|nok|dkk|pln|zł|jpy|yen|cny|rmb|yuan|kr|dollars?|bucks|€|£|₹|¥|\$";
const SCALE: &str = r"k|thousand|grand|mil|million|lpa|lakhs?|lacs?|crores?";
const BMOD: &str = r"(?:(?!(?:local|favorite|favourite|usual|nearest|go-to|regular|closest|neighborhood|neighbourhood|nearby|preferred|dad's|mom's|mum's|parents'|family's|friend's|old)\b)[\w'&-]+ ){0,2}?";

fn names(map: &Map) -> String {
    longest_first(map.keys().map(|k| k.as_str()))
}

fn plain(find: fn(&Match) -> Option<&'static str>) -> impl Fn(&Match) -> Option<&'static str> + Send + Sync + 'static {
    find
}

type Finder = Box<dyn Fn(&Match) -> Option<&'static str> + Send + Sync>;

fn finder(find: impl Fn(&Match) -> Option<&'static str> + Send + Sync + 'static) -> Finder {
    Box::new(find)
}

fn boxed(value: impl Fn(&Match) -> Option<String> + Send + Sync + 'static) -> V {
    Box::new(value)
}

fn gates(rules: &mut [Rule], table: &[(&str, &[&str])]) {
    for entry in rules.iter_mut() {
        if let Some((_, anchors)) = table.iter().find(|(pattern, _)| *pattern == entry.re.pattern) {
            entry.gate = Some(anchors.iter().map(|a| a.chars().collect()).collect());
        }
    }
}

pub fn build() -> Vec<Rule> {
    let field_names = names(&FIELD_MAP);
    let business_names = names(&BUSINESS_MAP);
    let my_business_names = longest_first(BUSINESS_MAP.keys().map(|k| k.as_str()).filter(|name| name.contains("business") || ["startup", "bakery", "pizzeria", "brewery", "restaurant", "cafe", "café", "llc", "own company", "private practice"].contains(name)));
    let verb_names = names(&VERB_MAP);
    let subject_names = names(&SUBJECTS);
    let degree_subject_names = names(&DEGREE_SUBJECTS);
    let degree_field_names = names(&DEGREE_FIELD_MAP);
    let long_degree_names = longest_first(DEGREES.iter().map(|(name, _)| *name).filter(|name| !SHORT_DEGREES.contains(name)));
    let short_degree_names = longest_first(SHORT_DEGREES.iter().copied());

    let cased_it = [
        r"\b(?:(?:i|i've|ive|i have|i had|i've been|i have been)(?: (?:also|currently|now|still|actually|mostly|mainly|already))* (?:work|worked|working)|(?:i'm|im|i am)(?: (?:also|currently|now|still|actually|mostly|mainly|already))*(?: working| employed)?) in (?:corporate |enterprise |the )?it\b".to_string(),
        concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n,(]\s*)(?:currently |also |now )?(?:work|working) in (?:corporate |enterprise |the )?it\b").to_string(),
        r"\b(?:my|i have an?|i've got an?|i got an?|i landed an?)(?: [\w-]+){0,2}? it(?= (?:job|career|role|position|gig)\b)".to_string(),
    ];
    let in_it = r"\bi(?:'m| am|'ve been| have been)? (?:also |currently |now |still |actually )?work(?:ing)? in it\b(?=\s*(?:[,.;!)]|$|\b(?:and|for|as|support|now|myself|too|so|but)\b))".to_string();
    let working_in = format!(r"(?:^{flair}|[.,;!\n]\s*|\band )(?:also |currently |now |still )?(?:work|working) in (?:the )?({field_names})(?: industry| field| sector| department| dept| business| world| trade)?\b", flair = claimcore::flair!())
        + r"(?! (?:class|classes|school|course|program|degree|student|home|homes|facility|facilities)\b)";
    let occupation: Vec<String> = vec![
        format!(r"\b(?:{I}|and am) {ADVERB}(?:an?|the) "),
        [r"\b(?:i|i'm|im|i am|i've been|ive been|i have been|currently|now)(?: (?:also|now|currently|still|actually|mostly|mainly|primarily|full[- ]?time|part[- ]?time|employed))* ",
         r"(?:work|working|employed|hired|serving|trained|qualified|certified|licensed|practicing|practising|moonlighting|freelancing|contracting)",
         r"(?: (?:there|here|remotely|full[- ]?time|part[- ]?time)| (?:at|for|in|with)(?: [^\s.!?,;()]+){1,5}?)? as (?:an? |the )?"].concat(),
        [r"\bi (?:just |recently |finally |eventually )?(?:became|got hired as|was hired as|started (?:work(?:ing)? )?as|got a job as|landed a job as|got promoted to|was promoted to|",
         r"got a position as|accepted a (?:job|position|role) as|took a job as|started a (?:new )?(?:job|role|position) as|now work as) (?:an? |the )?"].concat(),
        [r"\bmy (?:(?!(?:previous|old|former|last|first|dream|ideal|future|next|dad's|mom's|mum's|husband's|wife's)\b)\w+ )?(?:job|career|work|role|position|title|day job|gig|profession) ",
         r"(?:as|is) (?:an? |the )?"].concat(),
        r"\b(?<!no )(?<!não )(?<!non )(?<!nie )(?:yo soy|soy|sou|eu sou|ich bin|bin ich|je suis|sono|jestem|ik ben|ben ik)\s+(?:von beruf\s+)?(?:(?:un|una|um|uma|ein|eine|une|een)\s+)?".to_string(),
        r"\b(?:trabajo|trabajando|trabalho|trabalhando|arbeite|travaille|lavoro|pracuję|pracuje|werk|werkzaam)\s+(?:como|als|comme|come|jako)\s+(?:(?:un|una|um|uma|ein|eine|une|een)\s+)?".to_string(),
    ];
    let occupation_finds = || -> Vec<Finder> {
        vec![finder(plain(after)), finder(plain(after)), finder(plain(after)), finder(plain(after)), finder(plain(abroad)), finder(plain(abroad))]
    };
    let gerund = r"\bworking as (?:an? |the )?".to_string();
    let named_rest = concat!(r"\s+(?!(?:not|so|very|sorry|sure|afraid|guessing|confused|curious|glad|happy|tired|just|also|like|really|honestly|currently|still|okay|ok|fine|good|here|back|done|new|old|aware|thinking|wondering|asking|saying|going|trying|looking|getting|being|talking|actually|always|never|now|single|married|alone|well|but|and|or)\b)",
        r"\**[a-z][\w.'-]*(?: [a-z][\w.'-]*)?\**\s?,\s*(?:\d{2}\s?[mf]?\s?,\s*)?(?:an? |the )");
    let named = [format!(r"i(?<!\wi)(?:'m|m| am){named_rest}"), format!(r"my(?<!\wmy) name(?: is|'s){named_rest}")];
    let mentions: Vec<String> = vec![
        [concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n:(,]\s*|\s[-–—]\s+|\b(?:hi|hey|hello|hiya|yo|greetings)\b[ ,!.]*)(?:an? |fellow |another |a fellow |also an? |as an? |just an? )?((?:[\w'&/.+-]+ ){1,6}?)"),
         r"(?:by (?:trade|profession|training) )?here\b(?=\s*(?:[^\w\s]|\b(?:and|with|who|so|but|in|from|too|lol|haha|for)\b|$))"].concat(),
        r"\b(?:as|being|speaking as) an? ".to_string(),
        r"\[\s*(?:for hire|hire me)\s*\][\W_]*".to_string(),
        concat!(r"(?:^", claimcore::flair!(), r"|\n)[^\w\n]*(?:occupation|profession|job|work|career|job title|current job|current role|me)[^\w\n]{0,4}?[:=][^\w\n]*").to_string(),
        concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n]\s*)currently (?:working as )?an? ").to_string(),
        concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n]\s*)((?:[\w'&/.+-]+ ){1,6}?)by (?:trade|profession)\b").to_string(),
        r"\b(?:we(?:'re| are)|and i are|and me are|and myself are) both ((?:[\w'&/.+-]+ ){0,3}?[\w'&/.+-]+s)\b".to_string(),
    ];
    let mention_finds = || -> Vec<Finder> {
        vec![finder(plain(here)), finder(plain(opened)), finder(plain(hired)), finder(plain(hired)), finder(plain(opener)), finder(plain(here)), finder(plain(here))]
    };
    let lead = [concat!(r"(?:^", claimcore::flair!(), r"|\n)[ \t>*#\\-]*+(?:(?:\d{2}\s?(?:yo|y/o|yrs? old|years? old)|\d{2}\s?[mf]?|[mf]\s?\d{2}|[\[(][\w /+-]{1,12}[\])]|#[\w/-]+|[-–—|,]+)[ \t]*)*+(?:(?:also|just|another|fellow|a|an) )*+"),
        r"(?:(?:married|professional|licensed|certified|registered|senior|junior|qualified|experienced|freelance|hung|single|divorced|tired|exhausted) )*+(?=[^\W_])"].concat();
    let tagged_title = r"(?<![\w$#])(?:\d{2}\s?[mf]|[mf]\s?\d{2})\b(?: and)?[ ,]+(?:an? )?|(?<![\w$#.,])\d{2},? and an? |(?<![\w$#])[\[(]?[mf]4[a-z]+[\])]?[ ,]+(?:an? )?|\(\d{2}\)[ ,]+(?:an? )?".to_string();
    let cell = r"[,|][ \t]*(?:an? )?".to_string();
    let workplace = format!(r"(?:\bi(?:(?:(?:'ve| have) (?:been )?(?:currently |now |also |still |mostly |mainly |actually )?(?:work|working|worked)|(?:'m| am)? (?:currently |now |also |still |mostly |mainly |just started |started |actually )?(?:work|working|employed)) (?:(?:in|for) )?(?:the |an? )?(?:(?!(?:same|this|that|my|your|his|her|their|our|other|different|any|every|no|with|on|from|to|alongside|closely|around|near|under|over|about|like|as|into|through|including|among|against)\b)[\w-]+ ){{0,2}}?|(?:'m| am|m|'ve been| have been) (?:currently |now |also |still |actually |mostly |mainly )?in (?:the )?)|\bas (?:someone|somebody) (?:who (?:also |currently |now |still |actually )?(?:works|has worked) |working )?in (?:the )?)({field_names})")
            + r"(?: industry| field| sector| department| dept| business| world| trade)?\b(?! (?:class|classes|school|course|program|degree|student|home|homes|facility|facilities)\b)";
    let ownership = [
        format!(r"(?:\b(?:i|we)(?:'ve| have)? (?:also |now |still |currently |actually |just |recently )?(?:own and run|own and operate|run and own|own|run|co-?own|opened|started|founded|operate|launched)|(?:^{flair}|[.!?\n]\s*)(?:own and run|own|run|co-?own)) ", flair = claimcore::flair!())
            + &format!(r"(?:a|an|my own|my|two|three|four|several|a few|\d+|our|our own|a small|a little) {BMOD}({business_names})(?:es|s)?\b")
            + r"(?! (?:card|account|class|classes|school|trip|degree|plan|idea|name|loan|license|partner|tab|game|simulator|course|major|student)\b)",
        format!(r"(?=my )(?<!of )(?<!mind )(?<!minding )(?<!minded )(?<!it )(?<!prefer )(?<!enjoy )(?<!love )(?<!like )(?<!keep )(?<!in )(?<!for )(?<!ran )(?<!had )(?<!sold )(?<!closed )(?<!lost )(?<!left )(?<!quit )\bmy (?:own (?:small |little |tiny |online |family |new )?|(?:small |little |tiny |online |family |new )?(?=(?:{my_business_names})\b))({business_names})\b")
            + r"(?! (?:cards?|account|class|classes|school|trip|degree|plan|idea|name|loan|license|partner|apartment|flat|tab|game|simulator|course|major|student|friends?)\b)",
    ];
    let teach = concat!(r"\bi(?:'ve| have)? (?:currently |now |also |still |actually )?teach (?:both )?(?:high school|middle school|elementary|kindergarten|preschool|pre-k|\w+ grade(?:rs)?|\d+(?:st|nd|rd|th) grade(?:rs)?|grade \d+|year \d+|",
        r"math|maths|english|science|history|art|music|pe|biology|chemistry|physics|special ed|sped|esl|efl|college|university|uni|at|in|for|classes|courses|a class|students|",
        r"undergrads|freshmen|ap|french|spanish|german|reading|kids|children|teens)\b|\bi(?:'ve| have) been teaching (?:for|since|\d|at|in)\b|",
        r"\bi(?:'m| am|'ve been| have been)? (?:currently |now |also |still |actually |mostly |mainly )?(?:teach|teaching) (?!(?:me|you|him|her|them|myself|yourself|themselves|it|that|this|us|",
        r"my (?:\w+ )*?(?:kids?|son|daughter|children|baby|girl|boy|dog|cat|puppy|wife|husband|partner|friends?))\b)[a-z]|\bmy (?:students|pupils|classroom|",
        r"lesson plans?|class of|kindergarteners|kinders|first graders|second graders|third graders|fourth graders|fifth graders|\d+(?:st|nd|rd|th) graders|homeroom)\b");
    let activity: Vec<(String, fn() -> V)> = vec![
        (format!(r"\bi ({verb_names}) (?:\w+ ){{0,3}}?(?:for a living|for work|professionally|as a job|as my job|for my job|for a job|full[- ]?time|part[- ]?time|for clients|on the side|as a side hustle|")
            + r"cars|houses|homes|real estate|insurance)\b", || lookup(&VERB_MAP, 1)),
        (teach.to_string(), || fixed("teacher")),
        (r"\b(?:i'm|im|i am|i've been) an rn\b".to_string(), || fixed("rn")),
        (concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n]\s*)(?:an? )?(?:\w+ )?rn here\b").to_string(), || fixed("rn")),
    ];
    let self_employed = [
        format!("{ELIDED}{}{STATED}", r"(?:self[- ]employed|freelancer|sole trader)\b"),
        concat!(r"\b(?:i'm|im|i am|i've been|ive been|i have been)\b[^.!?\n]{0,40}?\b(?:self[- ]employed|freelancer)\b|\bi (?:currently |now |also |still |mostly |mainly |just |only )?(?:work|'m working|am working) for myself\b|",
            r"\bi (?:also |currently |now |mostly )?(?:freelance|do freelance(?: work)?|do freelancing|take freelance (?:work|gigs))\b|\bi (?:just |recently )?(?:started|began) freelancing\b").to_string(),
        concat!(r"(?:\b(?:i'm|im|i am|as) (?:an? )?|(?:^", claimcore::flair!(), r"|[.!?\n:]\s*))(?:solo|indie) (?:game )?dev(?:eloper)?\b(?! (?:team|teams|studio|studios|games?|community|scene)\b)|\bsolo developing\b|\b1099 (?:worker|contractor|employee|income|job)\b").to_string(),
        concat!(r"\b(?:i'm|im|i am|i've been|ive been|i have been) (?:currently |now |also |still |fully |technically )?(?:self[- ]employed|freelancing|a freelancer|freelance|my own boss|",
            r"an independent contractor|a contractor|a sole trader|a sole proprietor|a solopreneur)\b").to_string(),
    ];
    let business_owner = r"\b(?:i'm|im|i am|i've been|ive been|i have been) (?:currently |now |also |still |fully |technically )?(?:an entrepreneur|a business owner|a small business owner|a (?:solo |serial |first[- ]time |startup |tech )?(?:co-?)?founder)\b";
    let unemployed = [
        format!("{ELIDED}{}{STATED}", r"(?:unemployed|jobless|out of work|between jobs)\b"),
        format!(r"\b{I} (?:currently |now |still |officially |technically |basically |just |recently |unfortunately |sadly )?(?:unemployed|jobless|between jobs|out of work|out of a job|without (?:a )?(?:job|work)|")
            + concat!(r"on unemployment|on the dole|on jobseeker'?s|job hunting|job searching|laid off|furloughed|redundant|looking for (?:a |another |any )?(?:job|work)|searching for (?:a )?(?:job|work)|",
            r"applying (?:for|to) jobs|in between jobs|on ei)\b"),
        concat!(r"(?<!when )(?<!after )(?<!before )\bi (?:just |recently |unfortunately |finally )?(?:lost my job|got laid off|was laid off|got let go|was let go|got fired|was fired|got made redundant|was made redundant|got terminated|",
            r"was terminated)\b(?![^.!?\n]{0,30}\b(?:years? ago|in (?:19|20)\d\d|back in|back then|last year|once|twice)\b)").to_string(),
        concat!(r"\bi(?:'ve| have) been (?:unemployed|out of work|jobless|job hunting|job searching|looking for (?:a )?(?:job|work)|",
            r"searching for (?:a )?(?:job|work)|applying (?:for|to) jobs)\b|\bmy (?:unemployment|job search|job hunt|job applications)\b|\b(?:being|as an?) unemployed\b(?=[^.!?\n]{0,40}\b(?:i|my|me)\b)").to_string(),
        concat!(r"\bi (?:can't|cannot|can not|couldn't) (?:find|get) (?:a |any )?(?:job|work)\b|\bno one (?:will|wants to) hire me\b|\bnobody (?:will|wants to) hire me\b|\bcan't get hired\b|",
            r"\b(?:\d+|hundreds of|dozens of) (?:job )?applications\b(?=[^.!?\n]{0,60}\b(?:no|not|zero|none|nothing|haven't|still)\b)").to_string(),
        concat!(r"\b(?:cerco lavoro|busco trabajo|busco empleo|procuro emprego|estou desempregad[oa]|estoy desemplead[oa]|soy desemplead[oa]|je cherche du travail|je suis au chômage|",
            r"ich bin arbeitslos|ich suche arbeit|jestem bezrobotn[ya]|ik ben werkloos|sono disoccupat[oa])\b").to_string(),
    ];
    let retired = [
        format!("{ELIDED}{}", r"(?:semi[- ])?retired(?=\s*(?:$|[.,!;\n]|\b(?:now|last|since|in \d|and)\b))"),
        format!(r"\b{I}\s+(?:(?:an?|now|happily|semi|recently|newly|fully|medically|early|proudly|officially|also|old|finally|just|basically|technically|long|partially)[- ]?\s*)*retired\b")
            + r"(?! (?:gamer|player|from (?:the |this )?(?:game|gaming|league|sport|competitive|scene)|streamer|lurker|redditor|account|from (?:reddit|twitter|social media)))",
        concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n]\s*)(?:a )?(?:\w+ ){0,1}retired (?:\w+ ){0,2}here\b").to_string(),
        concat!(r"\bas an? (?:\w+ )?retiree\b|\b(?:since|after|when|now that|until|before) i (?:retired|am retired)\b|",
            r"\bi (?:just |recently |finally )?retired (?:in|last|a few|from|at|early|after|two|three|four|five|\d|this|back|recently|young|on)\b|\bi (?:just |recently |finally )retired(?=\s*(?:$|[.,!;\n]))|\bi(?:'ve| have) been retired\b|",
            r"\b(?:in|since|during|enjoying|into|throughout|after|before) my retirement\b(?! (?:account|fund|savings|plan|age|goals?|portfolio))|\bi(?:'m| am) a retiree\b|\b(?:retired|retiree) (?:myself|too)\b").to_string(),
        r"\(\s*retired\s*\)|\b(?:since|after|when|now that|until|before) we (?:retired|'re retired|are retired)\b|\A[^\n]{0,60}?[\[(][mf]4[a-z]+[\])][^\n]{0,40}?\bretired\b".to_string(),
        r"\b(?:i'm|im|i am) (?:on|living on|drawing) (?:my |a )?(?:pension|social security|state pension|retirement income)\b|\bi (?:draw|collect|get) (?:my )?(?:pension|social security)\b|\b(?:i'm|im|i am) (?:\d{2}) and retired\b".to_string(),
    ];
    let homemaker = [
        format!(r"\b{I} {ADVERB}(?:an? )?(?:full[- ]?time |proud |happy |exhausted |tired )?(?:stay[- ]at[- ]home (?:mom|mum|dad|parent|wife|mother|father|husband)|sahm|sahd|sahp|homemaker|housewife|")
            + r"househusband|house husband|home ?maker|home ?keeper|domestic engineer|tradwife)\b",
        concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n]\s*)(?:\d{2}\s?[mf]?\s+)?(?:sahm|sahd|stay[- ]at[- ]home (?:mom|mum|dad|parent|wife)|homemaker|housewife|tradwife)\b|(?:^", claimcore::flair!(), r"|[.!?\n]\s*)(?:a |fellow |another )?(?:sahm|sahd|stay[- ]at[- ]home (?:mom|mum|dad|parent|wife)|homemaker|housewife|tradwife) here\b").to_string(),
        concat!(r"\bas an? (?:sahm|sahd|stay[- ]at[- ]home (?:mom|mum|dad|parent)|",
            r"homemaker|housewife)\b(?=[^.!?\n]{0,60}\b(?:i|my|me)\b)|\bi stay (?:at )?home (?:full[- ]?time )?(?:with|to raise|to take care of) (?:my|the|our) (?:kids|son|daughter|baby|children|toddler|twins|boys|girls)\b|",
            r"\bi (?:quit|left|gave up) (?:my job|work|my career) to (?:stay home|raise|be a (?:sahm|stay at home))\b").to_string(),
    ];
    let unable = [
        format!(r"\b{I} {ADVERB}(?:permanently |medically |totally |partially )?(?:on disability|on ssdi|on ssi|on pip|on esa|on dsp|on odsp|on aish|on pwd|unable to work|too sick to work|too ill to work|")
            + concat!(r"on long[- ]term disability|on ltd|disabled and (?:can't|cannot|unable to) work|",
            r"medically retired|retired on disability|unfit (?:for|to) work)\b(?! (?:at times|sometimes|for (?:a|the|two|three|\d+)|today|tonight|this week|right now)\b)"),
        concat!(r"\bi (?:can't|cannot|can no longer|am unable to|couldn't) (?:work|hold (?:down )?a job|keep a job)(?: anymore| any more)? (?:because|due|since|anymore|any more|with|after)\b|",
            r"\bi (?:get|receive|collect|was granted|got approved for|was approved for|finally got|won my|got awarded|was awarded|live on|survive on) (?:my )?(?:ssdi|ssi|disability|pip|esa|",
            r"disability benefits|disability payments|dsp|odsp|aish)\b|\b(?:i was |i got |was |been )?granted (?:ssdi|ssi|disability|pip)\b|\bmy (?:ssdi|ssi|disability|pip|esa|odsp|aish) ",
            r"(?:check|checks|payments?|benefits|income|claim|award|hearing|case|application)\b").to_string(),
    ];
    let student = concat!(r"\b(?:i'm|im|i am) (?:almost |nearly |currently |now )?(?:in )?(?:my )?(?:1st|2nd|3rd|4th|first|second|third|fourth|final|last) year (?:of|in|at)\b(?! (?:high ?school|hs)\b)|\bmy (?:major(?! (?:\w+ )?(?:client|clients|issue|issues|problem|problems|concern|regret|complaint|reason|thing|things|part|role|surgery|depression|project|projects|account|accounts|crush|award|league|update|flaw|win|loss|key|fan|city|brand|company|advice|point|takeaway|tip|tips|difference|benefit|downside|upside|mistake|goal|goals|priority|focus|source|factor|scales?|chords?)\b)|uni(?! (?:days|years|life)\b)|dissertation|lecturer|lectures|semester|finals|coursework|midterms?|campus|student id|student visa|academic advisor|class schedule)\b(?! (?:was|were) (?:great|fun|hard)\b)|",
            r"\b(?:i'?m|i am)(?: currently| still| also| now| actually)? (?:studying|in school|in college|in uni|at uni|at college|at university|in university|back in school|back at school)\b|\bwhile (?:i'm |im |i am )?studying\b|\bi study\b(?! (?:the|it|this|that|them|him|her|how|why|what)\b)");
    let studying = concat!(r"\b(?:i'm|im|i am) (?:currently |now )?(?:in )?(?:my |the )?\d(?:st|nd|rd|th) sem(?:ester)?\b|\b(?:i'm|im|i am) (?:almost |nearly |currently |now |only )?(?:in |a )?(?:my )?(?:(?:1st|2nd|3rd|4th|5th|first|second|third|fourth|final|last)[- ]year|year [1-5])\b(?! of (?:high school|marriage|work))",
        r"|\bmy (?:1st|2nd|3rd|4th|first|second|third|final) year (?:electives|courses|exams|project)\b|\b(?:i'm|im|i am) (?:currently |also |still |now )?(?:in|at) (?:an? (?:[\w'-]+ ){0,3}?)?(?:college|uni|university)\b",
        r"|\bmy (?:freshman|sophomore|junior|senior|first|second|third|final) (?:year|semester) (?:of|in|at) (?:college|uni|university)\b|\bmy (?:major(?! (?:\w+ )?(?:client|clients|issue|issues|problem|problems|concern|regret|complaint|reason|thing|things|part|role|surgery|depression|project|projects|account|accounts|crush|award|league|update|flaw|win|loss|key|fan|city|brand|company|advice|point|takeaway|tip|tips|difference|benefit|downside|upside|mistake|goal|goals|priority|focus|source|factor|scales?|chords?)\b)|lectures?|lecturer|uni(?! (?:days|years|life)\b)|campus|coursework|semester|midterms?)\b",
        r"|\b(?:i'm|im|i am) (?:currently )?(?:studying|majoring)\b|\bwhile (?:i'm |im |i am )?studying\b|\bi(?:'m| am)? (?:in|doing) (?:the|my) (?:bs|ba|bsc|bachelor'?s?|undergrad) (?:program|degree)\b|\b(?:meu|minha) (?:primeiro|segundo|terceiro|primeira) (?:ano|período|semestre)\b|\bfaço (?:uma )?(?:segunda )?graduação\b|\bich studiere\b|\bestudio (?:en la|en el|una|la)\b|\bje suis (?:étudiant|étudiante|à la fac)\b|\b(?:faço faculdade|estoy en la (?:universidad|facultad)|estou na (?:faculdade|universidade|facul)|jestem student(?:em|ką)|studiuję|sono (?:uno |una )?(?:studente|studentessa)|ik studeer|estoy estudiando|sou estudante|soy estudiante|estudo (?:na|no|em))\b",
        r"|\bi have (?:a |my )?(?:midterm|midterms|final exam|finals) (?:coming up|tomorrow|next week|this week|today)\b|\bmy (?:college|university|uni) (?:classes|courses|professor|campus|dorm)\b|\b(?:mein(?:em)? studium|ins studium|im studium)\b|\bstudent (?:from|at) (?:the )?(?:main campus|\w+ (?:university|college|campus))\b");
    let graduate = concat!(r"(?:\b(?:i'm|im|i am|am|as) (?:[\w'-]+ ){0,5}?|(?:^", claimcore::flair!(), r"|[.!?\n:|,(\[]\s*)(?:[\w'-]+ ){0,2}?)(?:grad|graduate|phd|ph\.d\.?|doctoral|masters?|master's|msc|mba|msw|ma|ms|mfa) (?:student|candidate)\b(?!(?:loans?|debt|visa|housing)\b)|\b(?:my|in (?:a|an|the|my)) (?:\w+ )?(?:grad|graduate|phd|ph\.d\.?|doctoral|masters?|master's|msc|mba|msw|ma|ms|mfa) (?:program|programme)\b|\bmy (?:thesis|dissertation|phd|doctorate)\b|\bfinishing (?:my )?(?:grad|graduate|masters?|master's|phd) (?:program|degree)?\b|\bi study an? (?:jd|ma|ms|msc|masters|phd|llm)\b|\bmeiner dissertation\b|\bmi (?:tesis|doctorado|maestría)\b|\b(?:accepted|admitted) (?:in)?to (?:the |a )?(?:\w+ ){0,3}?(?:masters?|master's|phd|graduate|msw|mba|doctoral) program\b");
    const PRO_SCHOOL: &str = r"(?:law|med|medical|dental|vet|veterinary|pharmacy|grad|graduate)";
    let pro_student = format!(r"\b(?:{I}|i'm currently|currently) (?:still |now |also )?(?:in|at|attending|finishing) (?:my (?:\w+ )?(?:year|semester) (?:of|in|at) )?{PRO_SCHOOL} school\b|")
        + &format!(r"\b(?:{I}|as) (?:an? |the )?(?:current |first[- ]year |second[- ]year |third[- ]year |fourth[- ]year |final[- ]year |\d(?:st|nd|rd|th)[- ]year )?{PRO_SCHOOL} student\b|")
        + &format!(r"\bmy (?:\w+ )?(?:year|semester) (?:of|in|at) {PRO_SCHOOL} school\b|\bi (?:go to|attend|started|start) {PRO_SCHOOL} school\b");
    let high_grade = r"\b(?:i'm|im|i am|currently|still) (?:still |currently )?in (?:(?:9th|10th|11th|12th)(?: class| std)?|(?:grade|class) (?:9|10|11|12))\b|\b(?:grade|class|year) (?:9|10|11|12) student\b";
    let high_school = concat!(r"\b(?:i'm|im|i am|just) (?:an? )?(?:[\w-]+ )?(?:high ?schooler|high-schooler|(?:\d+th|seventh|eighth|ninth|tenth|eleventh|twelfth) grader)\b|\b(?:i'm|im|i am) (?:still |currently )?in (?:high ?school|hs|(?:9th|10th|11th|12th) grade|year (?:9|10|11|12))\b|\b(?:i'm|im|i am|as|just) (?:an? )?(?:[\w-]+ )?(?:high ?school|hs) (?:student|senior|junior|sophomore|freshman)\b|\b(?:i'm|im|i am) (?:currently |still |now )?(?:a )?(?:senior|junior|sophomore|freshman) in (?:high ?school|hs)\b|\bmy (?:high school|highschool) (?:teacher|classes|graduation|exams)\b|",
        r"\b(?:i'm|im|i am) (?:currently |now |still |about to start |entering |starting |going into )?(?:in )?my (?:freshman|sophomore|junior|senior|sr|final|last|first|second|third|fourth|1st|2nd|3rd|4th) year (?:of|in|at) (?:high ?school|hs)\b");
    let college_pattern = concat!(r"\b(?:i'm|im|i am|this|just an?|\d{2}\s?[mf]?,?|[mf]4[a-z]+\]?) (?:(?!(?:former|ex|retired)\b)[\w-]+ ){0,2}?(?:college|uni) (?:boy|girl|guy|dude|bro|kid|twink|jock|athlete|lad|stud|frat)s?\b|\bstudent,? here\b|\bjust an? (?:\w+ )?student\b|",
        r"\b(?:my|next|this) (?:\w+ )?year (?:of|at|in) (?:uni|college|university)\b|\bi (?:take|am taking|'m taking|m taking) (?:\w+ )?(?:classes|courses|units|credits)\b");
    let campus = concat!(r"\bi (?:currently |now |still |also )?(?:go to|attend|am attending|'m attending|transferred to) (?:a |an |the )?(?:[\w'&.-]+ ){0,3}?(?:college|university|uni|community college|polytechnic)\b|",
        r"\b(?!(?:any|a|the|every|no|some)\b)(?:undergrad|undergraduate|fresher|freshman|sophomore|[\w'-]+ (?:major|student)) here\b|",
        r"\bmy (?:college|uni|university|class|course|semester|final[- ]year|capstone|group) (?:project|assignment|exams?|presentation|essay|paper|lectures?)\b|",
        r"\b(?:i'm|im|i am) (?:now |currently |almost |nearly )?(?:in|into|starting) (?:my )?(?:\d(?:st|nd|rd|th)|first|second|third|fourth|fifth|final|last) (?:year|semester|sem) (?:of|in|at) (?:college|uni|university|my degree|my bachelor'?s|undergrad)\b|",
        r"\b(?:i'm|im|i am) (?:about to |almost |nearly |currently |finally )?(?:finishing|graduating from|graduating|done with) (?:college|uni|university|my degree|my bachelor'?s|my undergrad)\b|",
        r"\b(?:\d+|one|two|three|four|a) (?:more )?(?:semesters?|years?|terms?|quarters?) (?:away from|left (?:of|in|until|before)) (?:graduation|graduating|my degree|college|uni)\b|",
        r"\b(?:i'm|im|i am) (?:an? )?(?:[\w'-]+ ){1,2}?major\b(?! (?:issue|problem|concern|fan|reason|part|key|league|player|city|brand|company)\b)");
    let campus_started = concat!(r"\bi(?:'m| am|m)? (?:currently |now |still |also |just |finally |recently |about to )?(?:attending|enrolled in|enrolled at) ",
        r"(?:a |an |the )?(?:[\w'&.-]+ ){0,3}?(?:college|university|uni|community college|polytechnic)\b|",
        r"\b(?:i'm|im|i am) (?:about to graduate from|about to graduate|about to finish) (?:college|uni|university|my degree|my bachelor'?s|my undergrad)\b");
    let any_student = concat!(r"\b(?:i'm|im|i am)(?: currently| still| just| also| now)? (?:an? )?(?:(?!(?:former|ex|old|past|of|the|my|his|her|their|to|with|for|and|that|who|not|high|school|grad|graduate|phd|masters?|master's|doctoral|level)\b|(?:grade|class|year) \d)",
        r"[\w'-]+ ){0,4}?student\b(?! (?:loans?|visa|athlete|housing|discount|of|pilot|nurse|teacher|driver|worker|union)\b)|",
        r"\b(?:already|still) a student\b|",
        r"\bas an? (?:(?!(?:former|ex|old|past|of|the|my|high|school|grad|graduate|phd|masters?|doctoral|level)\b)[\w'-]+ ){0,3}?student\b(?=[^.!?\n]{0,60}\b(?:i|my|me)\b)");
    let undergrad = concat!(r"\b(?:i'm|im|i am)(?: currently| now| just| also| still)? (?:an? )?(?:(?!(?:former|ex|old|past|the|my|not|high|school)\b)[\w-]+ ){0,3}?(?:freshman|sophomore|fresher|freshie|undergrad|undergraduate)\b(?: (?:in|at) (?:college|uni|university)\b)?",
        r"(?! (?:year|class|classes|course|courses|degree|program|programme|in high ?school|at high ?school)\b)|\b(?:i'm|im|i am)(?: currently| now)? (?:an? )?(?:rising |incoming )?(?:junior|senior) (?:in|at) (?:college|uni|university)\b");
    let student_here = concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n,]\s*)(?:a |an )?(?:college |uni |university )?student here\b");
    let student_line = concat!(concat!(r"(?:(?m:^)", claimcore::flair!(), r"[ \t>*#\\-]*|,[ \t]*)(?:(?:\d{2}\s?[mf]?|[mf]4[a-z]+|[mf]\s?\d{2}|[\[(][\w /+-]{1,12}[\])])[ \t,|-]*)*+(?:an? )?"),
        r"(?:(?!(?:the|this|that|these|those|my|your|you|you're|youre|whether|if|for|his|her|their|our|every|each|any|some|no|one|which|what|why|how|when|is|are|was|were|do|does|did|former|ex|old|future|fellow|i|we|have|has|had|got|met|know|teach|teaching|tutor)\b)[\w'-]+ ){0,3}?",
        r"(?:student|college (?:girl|boy|guy|student|kid))\b(?! (?:loans?|visa|athlete|housing|discount|debt|union|card|id|council|account|accommodation|life|government|body|aid|finance)\b)",
        r"(?=\s*(?:$|[.,!;|(\n-]|\d|\b(?:here|looking|seeking|from|in|at|with|who|and)\b))");
    let owners = [
        r"\b(?:(?:commissions|comms) (?:are )?(?:open|opened)|open(?:ing)? (?:my )?(?:commissions|comms)|open (?:for|to) (?:commissions|comms)|(?:taking|accepting|doing|started taking) (?:commissions|comms)|working (?:on|with) commissions)\b",
        r"\[\s*for hire\s*\]",
    ];
    let college_item = r"(?:,|\band|\b\d{2}\s?[mf]\b)\s*(?:currently |still |now |also )?in (college|uni|university)\b(?=\s*(?:$|[.,!;:)(\n-]|\b(?:and|but|so|atm|rn|now|lol)\b))";
    let independent = format!(r"\b{I}(?: [a-z]+(?:[ -][a-z]+)?,)? {ADVERB}an? (?:independent|freelance|freelancing|self[- ]employed) ");

    let mut rules: Vec<Rule> = Vec::new();
    let self_hedge = self_hedge();
    for (pattern, find) in occupation.iter().zip(occupation_finds()).chain(mentions.iter().zip(mention_finds())).chain([(&lead, finder(plain(fragment)))]) {
        rules.push(rule("occupation", pattern, occupied(find), TAGGED));
    }
    let mut occ = occupation.iter().zip(occupation_finds()).enumerate().filter(|(i, _)| *i != 2).map(|(_, p)| p).collect::<Vec<_>>();
    let ment = mentions.iter().zip(mention_finds()).enumerate().filter(|(i, _)| [0, 1, 3].contains(i)).map(|(_, p)| p);
    occ.extend(ment);
    occ.push((&lead, finder(plain(fragment))));
    for (pattern, find) in occ {
        rules.push(rule("employment_status", pattern, employed(find), TAGGED));
    }
    rules.push(rule("occupation", &gerund, scoped(mine(occupied(plain(after)))), TAGGED));
    for pattern in &named {
        rules.push(rule("occupation", pattern, occupied(plain(after)), TAGGED));
    }
    for pattern in &named {
        rules.push(rule("employment_status", pattern, employed(plain(after)), TAGGED));
    }
    rules.push(rule("occupation", &cell, occupied(plain(celled)), TAGGED));
    rules.push(rule("occupation", r"\b(?:i'm|im|i am) (?!(?:an?|the|not|so|very|just|also|still|now|really|here)\b)", scoped(occupied(plain(bare))), TAGGED));
    let retired_title = concat!(r"(?:(?:^", claimcore::flair!(), r"|[.!?\n]\s*)(?:an? |just an? |also an? )?|\b(?:i'm|im|i am|as|being) an? (?:[\w-]+ )?)retired ");
    rules.push(rule("occupation", retired_title, scoped(boxed(|m| retiree(m).filter(|key| job_kind(key) != OWNER).map(|key| format!("retired {key}")))), TAGGED));
    rules.push(rule("occupation", r"\bi(?:'ve| have) (?:also |actually |always |previously )?worked as (?:an? |the )?", scoped(occupied(plain(after))), TAGGED));
    rules.push(said("occupation", &tagged_title, occupied(plain(tagged)), &SELF_HEDGE));
    rules.push(rule("occupation", &workplace, scoped(boxed(sector)), TAGGED));
    rules.push(rule("occupation", &working_in, scoped(boxed(sector)), TAGGED));
    rules.push(rule("military_branch", &workplace, scoped(boxed(branch)), TAGGED));
    rules.push(rule("military_branch", &working_in, scoped(boxed(branch)), TAGGED));
    rules.push(rule("occupation", &in_it, scoped(fixed("it")), TAGGED));
    for pattern in &cased_it {
        rules.push(rule("occupation", pattern, scoped(boxed(cased)), TAGGED));
    }
    let ownership_open = |m: &Match| !ASPIRING.test_in(m.string, clause(m.string, m.start()), m.start());
    for pattern in &ownership {
        rules.push(rule("occupation", pattern, scoped(boxed(move |m| if eq(m.text(), "my business") || !ownership_open(m) { None } else { keyed(&BUSINESS_MAP, m.group(1)).map(|key| format!("{} owner", key.trim_start_matches("own "))) })), TAGGED));
    }
    for pattern in &ownership {
        rules.push(rule("employment_status", pattern, scoped(boxed(move |m| (ownership_open(m) && !eq(m.text(), "my business")).then(|| super::standing::BUSINESS_OWNER.to_string()))), TAGGED));
    }
    for (pattern, value) in &activity {
        rules.push(rule("occupation", pattern, scoped(value()), TAGGED));
    }
    for pattern in &self_employed {
        rules.push(rule("employment_status", pattern, scoped(fixed(SELF_EMPLOYED)), TAGGED));
    }
    rules.push(rule("employment_status", business_owner, scoped(fixed(super::standing::BUSINESS_OWNER)), TAGGED));
    rules.push(rule("employment_status", &independent, scoped(boxed(|m| title(m.string, m.end(), None).map(|_| SELF_EMPLOYED.to_string()))), TAGGED));
    for pattern in &unemployed {
        rules.push(rule("employment_status", pattern, scoped_with(fixed("unemployed"), &CONDITIONAL, false), TAGGED));
    }
    let jobless = [
        r"(?<!my )(?<!the )\b(?:unemployed|jobless)\b(?! (?:people|persons?|folks|friends|men|women|guys|population|youth|workers|rate|benefits|insurance|check|office|line)\b)",
        r"\b(?:looking|searching|hunting) for (?:a |an |any )?(?:(?:remote|entry[- ]level|stable|steady|proper|real|decent) )?(?:job|work|employment)\b",
        r"\b(?:can't|cannot|couldn't|unable to|struggling to|failing to|failed to) (?:find|get|land|secure) (?:a |an |any |new |a new )?(?:job|jobs|work|employment)\b",
        r"\b(?:fired|laid) me\b",
    ];
    let jobless_lead = [
        concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n]\s*)(?:(?:\d{2}\s?[mf]|[mf]\s?\d{2})\s+)?(?:still |currently |now )?(?:looking|searching) for (?:a |any )?(?:job|work)\b"),
        concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n]\s*)(?:i've |ive |i have )?been (?:unemployed|out of work|jobless)\b"),
        r"\bi(?:'ve| have)? (?:not|never) (?:had a (?:\w+ )?job|been employed)\b|\bi (?:haven't|havent|hadn't|have not|had not) (?:had a (?:\w+ )?job|been employed)\b|\bhaven't had a job\b",
    ];
    for pattern in &jobless {
        rules.push(rule("employment_status", pattern, scoped_with(mine(near(fixed("unemployed"))), if pattern.contains("find") { &CONDITIONAL } else { &SELF_HEDGE }, false), TAGGED));
    }
    for pattern in &jobless_lead {
        rules.push(rule("employment_status", pattern, scoped_with(fixed("unemployed"), &CONDITIONAL, false), TAGGED));
    }
    const QUIT: &str = r"(?<!quit )(?<!lost )(?<!left )(?<!leave )(?<!leaving )(?<!quitting )(?<!losing )(?<!from )(?<!after )";
    const WORK_NOW: &str = r"\b(?:i (?:currently |now |also |still |only |just |actually |mostly )?work|(?:i'm|im|i am|i've been|i have been) (?:currently |now |also |still |only |just |actually |mostly )?working)";
    let full_time = [
        format!(r"{WORK_NOW} full[- ]?time\b(?! (?:on|as an? (?:mom|mum|dad|parent|student|caregiver|carer))\b)"),
        format!(r"\bi (?:have|hold|work|got|landed|started|accepted) an? (?:new |permanent |steady |stable )?full[- ]?time (?:job|position|role)\b|{QUIT}\bmy (?:current |new )?full[- ]?time job\b"),
        r"\b(?:i'm|im|i am) (?:a )?(?:full[- ]?time (?:employee|worker|staff member)|salaried(?: employee| worker)?|on (?:a )?salary)\b".to_string(),
        concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n]\s*)(?:currently |now |still |also )?working full[- ]?time\b(?! (?:on|as an? (?:mom|mum|dad|parent|student|caregiver|carer))\b)|\b(?:i'm|im|i am) [^.!?\n]{0,40}?\band (?:i )?(?:also )?work full[- ]?time\b|\bi (?:have|work) an? (?:regular |normal |boring |standard |typical |full[- ]?time )?(?:9[- ]?(?:to |-)?5|nine[- ]to[- ]five)(?: job)?\b").to_string(),
    ];
    for pattern in &full_time {
        rules.push(rule("employment_status", pattern, scoped(fixed("employed full-time")), TAGGED));
    }
    let part_time = [
        format!(r"{WORK_NOW} part[- ]?time\b"),
        format!(r"\bi (?:have|hold|work|got|landed|started|accepted) an? (?:new )?part[- ]?time (?:job|position|role|gig)\b|{QUIT}\bmy (?:current |new )?part[- ]?time job\b"),
        r"\b(?:i'm|im|i am) (?:only )?(?:a )?part[- ]?time(?:r| employee| worker| staff member)?\b(?=\s*(?:$|[.,!;)]|\b(?:at|for|in|now|so|but|and)\b))".to_string(),
    ];
    for pattern in &part_time {
        rules.push(rule("employment_status", pattern, scoped(fixed("part-time")), TAGGED));
    }
    let several = [
        r"\bi (?:currently |now |also |still )?(?:have|work|hold|juggle) (?:two|2|three|3|four|4|multiple|several) (?:(?:part[- ]?time|full[- ]?time|different|separate) )?jobs\b",
        r"\b(?:i'm|im|i am|i've been|i have been) (?:currently |now |still )?(?:working|juggling) (?:two|2|three|3|four|4|multiple|several) (?:(?:part[- ]?time|full[- ]?time|different|separate) )?jobs\b",
        r"\bi (?:just |recently )?(?:have|got|accepted|took|started) a temp(?:orary)? (?:job|position|role|contract)\b|\b(?:i'm|im|i am) (?:currently |now |still )?temping\b|\bboth (?:of )?my jobs\b",
    ];
    for pattern in &several {
        rules.push(rule("employment_status", pattern, scoped(fixed("several jobs / temp")), TAGGED));
    }
    let intern = [
        r"\b(?:i'm|im|i am) (?:currently |now |also |still |just )?(?:an? )?(?:(?!(?:former|ex|old|future)\b)[\w-]+ ){0,2}?intern\b",
        r"\b(?:i'm|im|i am) (?:currently |now |also |still )?(?:interning|doing (?:an? |my )?(?:[\w-]+ ){0,2}?internship|on (?:an? |my )?(?:[\w-]+ ){0,2}?internship)\b|\bmy (?:current )?internship (?:supervisor|manager|mentor|boss|company)\b",
        r"\bi (?:just )?started (?:an? |my )(?:[\w-]+ ){0,2}?internship\b",
    ];
    for pattern in &intern {
        rules.push(rule("employment_status", pattern, scoped(fixed("intern")), TAGGED));
    }
    rules.push(rule("employment_status", r"\b(?:i'm|im|i am|i've been|i have been) (?:a |an )?(?:(?!(?:former|ex|recovering|reformed|retired)\b)\w+ )?neet\b(?! (?:pg|ug|exam|exams|prep|preparation|aspirant|aspirants|coaching|score|result|results|paper|mock|syllabus|cutoff|student|students|candidate|repeater|dropper|\d+)\b)", scoped(fixed("neet")), TAGGED));
    let persona_status = concat!(r"\b(?:(working full[- ]?time)|(working part[- ]?time)|",
        r"(stay[- ]at[- ]home (?:mom|mum|dad|parent|wife)|sahm|sahd|housewife|homemaker)|(neet(?! (?:pg|ug|exam|exams|prep|preparation|aspirant|aspirants|coaching|score|result|results|paper|mock|syllabus|cutoff))|jobless|unemployed)|(self[- ]employed|freelancer)|((?<!aspiring )(?<!wannabe )(?<!future )(?:small business owner|business owner|entrepreneur))|(working professional))\b");
    rules.push(said("employment_status", persona_status, boxed(|m| {
        if !personal(m) {
            return None;
        }
        let value = if m.nonempty(1).is_some() {
            "employed full-time"
        } else if m.nonempty(2).is_some() {
            "part-time"
        } else if m.nonempty(3).is_some() {
            return super::standing::homemaking(m);
        } else if let Some(word) = m.nonempty(4) {
            if eq(word, "neet") { "neet" } else { "unemployed" }
        } else if m.nonempty(5).is_some() {
            SELF_EMPLOYED
        } else if m.nonempty(6).is_some() {
            super::standing::BUSINESS_OWNER
        } else {
            "employed (hours unstated)"
        };
        Some(value.to_string())
    }), &SELF_HEDGE));
    for pattern in &retired {
        rules.push(rule("employment_status", pattern, scoped(fixed("retired")), TAGGED));
    }
    for pattern in &homemaker {
        rules.push(rule("employment_status", pattern, scoped(boxed(super::standing::homemaking)), TAGGED));
    }
    for pattern in &unable {
        rules.push(rule("employment_status", pattern, scoped_with(fixed("disabled / unable to work"), &CONDITIONAL, false), TAGGED));
    }
    for pattern in &owners {
        rules.push(rule("employment_status", pattern, scoped(fixed(SELF_EMPLOYED)), TAGGED));
    }
    rules.push(rule("current_study_level", college_item, scoped(boxed(college)), TAGGED));

    let degree_in_pattern = concat!(r"\b(bachelor's|bachelors|master's|masters|phd|ph\.d|bsc|msc|b\.s|m\.s|ba|bs|ma|ms|mba|bfa|mfa|llb|jd|md|btech|b\.tech|mtech|m\.tech|bcom|b\.com|bba|bsn|msn|",
        r"meng|beng)\.? (?:degree |hons |honours |honors )?(?:in|of) ([a-z]+(?: [a-z]+)?)");
    let pursuing = concat!(r"\b(?:i'm|im|i am|i'm currently|im currently|i am currently|currently) (?:still |now |also )?(?:doing|pursuing|finishing|completing|working on|working towards|in the middle of|halfway through) (?:up )?",
        r"(?:a |an |my )(?:(?!(?:the|a|an|my|and|or|first|second|new)\b)[\w-]+ ){0,2}?(?:(masters?|master's|phd|ph\.d|doctorate|msc|mba|msw|mfa|ma|ms|grad school)|(bachelor'?s|bachelors|undergrad|undergraduate degree|degree|bsc|ba|bs|bba|bcom|btech))\b");
    let sh: &'static Re = &SELF_HEDGE;
    rules.push(said("highest_degree", degree_in_pattern, boxed(degree_in), sh));
    rules.push(said("current_study_level", pursuing, boxed(|m| Some(match m.nonempty(1) { Some(level) => super::graduate(level), None => UNDERGRAD }.to_string())), sh));
    rules.push(said("current_study_level", studying, boxed(level), sh));
    rules.push(said("current_study_level", college_pattern, boxed(level), sh));
    rules.push(said("current_study_level", undergrad, boxed(level), sh));
    rules.push(rule("current_study_level", campus, scoped(boxed(level)), self_hedge));
    rules.push(rule("current_study_level", campus_started, scoped(boxed(level)), self_hedge));
    rules.push(said("current_study_level", student, boxed(level), sh));
    rules.push(said("current_study_level", r"\bmy (?:master'?s|masters|master|msc|mba) (?:thesis|dissertation|coursework)\b|\bfinishing (?:a|my) (?:master'?s|masters)\b", fixed("master's student"), sh));
    rules.push(said("highest_degree", r"\bi did my (?:ms|msc|ma|mba|masters|master's)\b", fixed("master's"), sh));
    rules.push(said("current_study_level", r"\b(?:i'm|im|i am) (?:still |currently |now )?(?:finishing|in|attending) (?:high ?school|class 1[012](?:th)?|1[012]th class|class (?:xi|xii))\b|\ban? a[- ]levels? student\b", boxed(grade), sh));
    rules.push(said("current_study_level", any_student, boxed(level), sh));
    rules.push(said("current_study_level", student_here, boxed(level), sh));
    rules.push(said("current_study_level", student_line, boxed(level), sh));
    rules.push(said("current_study_level", r"\b(?:i'm|im|i am|as) (?:an? )?(?:[123]l|ms[1-4])\b", fixed(PROFESSIONAL_SCHOOL), sh));
    rules.push(said("current_study_level", graduate, boxed(|m| Some(if contains(m.text(), "thesis") { "student (level unstated)" } else { super::graduate(m.text()) }.to_string())), sh));
    rules.push(said("current_study_level", &pro_student, boxed(|m| Some(if GRAD_SCHOOL.test(m.text()) { super::graduate(m.text()) } else { PROFESSIONAL_SCHOOL }.to_string())), sh));
    rules.push(said("highest_degree", &format!(r"\b(?:i have|i've got|i got|i hold|i earned|i finished|i completed|i just finished|i just completed|i recently finished|i recently completed|i finally finished|i've done|i have done|i did|i've gotten|ive gotten|i have gotten|i obtained|i received|i've earned|i've completed|i've finished|got|just got|have) (?:a |an |my |both |two )?(?:({long_degree_names})(?: degree| degrees| hons| in| from)?|({short_degree_names}) (?:degree|degrees|in|from))\b(?! (?:student|program|programme|candidate|course|class|party|parties|weekend|trip|night|pad|plan|application|recital|recitals|thesis|exams?|key|bedroom|suite|copy)\b)|\b({long_degree_names}) hons\b"),
        boxed(|m| if m.text().first() == Some(&'i') || owned(m.string, m.start(), 50) { get(&DEGREE_MAP, m.first()) } else { None }), sh));
    rules.push(said("highest_degree", concat!(r"\b(?:i have|i've got|i hold|i earned|i got|i completed|i finished|i do have|i also have) (?:a |an |my |both |two )?",
        r"(?:(?!(?:associate'?s?|masters?|master's|phd|doctoral|online|honorary|useless|worthless|second|new|been|pursuing|doing|studying|working|getting|earning|finishing|completing|started|starting|high|low|severe|first|third|1st|2nd|3rd|some|any|no)\b)[\w'-]+ ){0,3}?degrees?\b(?! (?:program|programme|course|apprenticeship|burns?|scoliosis|of)\b)|\b(?:college|university|uni)[- ]educated\b"),
        boxed(|m| if IN_PROGRESS.test(m.text()) || ASPIRING.test(m.text()) { None } else { Some(GRADUATED.to_string()) }), sh));
    rules.push(rule("highest_degree", &format!(r"(?:^{flair}|\n)[^\w\n]*(?:education|degree|qualifications?|highest degree)[^\w\n]{{0,4}}?[:=][^\w\n]*(?:an? )?({long_degree_names}|{short_degree_names})\b", flair = claimcore::flair!()), lookup(&DEGREE_MAP, 1), self_hedge));
    rules.push(said("highest_degree", r"\b(?:masters?|master's)[- ]educated\b", fixed("master's"), sh));
    rules.push(said("highest_degree", r"\bi (?:have|hold|earned|got) (?:an? |my )(md|mbbs|jd|llb|dds|dvm|dnp|psyd|edd|dpt|pharmd|phd|dphil|mba|msw|msn|bsn)\b(?=\s*(?:$|[.,!;)]|\b(?:and|from|in|but|so|too)\b))|\b(?:i'm|im|i am) an? (md|mbbs)\b(?=\s*(?:$|[.,!;)]|\b(?:and|from|in|but|so|too)\b))", boxed(|m| get(&DEGREE_MAP, m.first())), sh));
    rules.push(needs(said("highest_degree", concat!(r"\b(?:i (?:graduated|have graduated|just graduated|recently graduated|finally graduated|just finished|recently finished|finished)|(?:^", claimcore::flair!(), r"|[.!?\n]\s*)(?:just |recently |finally )?(?:graduated|finished)|(?:since|after|when|once) (?:i )?graduat(?:ed|ing)) (?:from )?(?:college|university|uni|undergrad|with (?:a|my|honors))\b|\b(?:as an? |i'm an? |im an? |i am an? )(?!(?:\w+ )?high ?school)(?:\w+ ){0,3}?(?:graduate|grad)\b(?! (?:student|program|school)\b)|\b\w+ (?:and \w+ )?grad\b(?= (?:having|here|with|who|and|looking)\b)|\bme formei\b|\bmy (?:bachelor'?s|bachelors|undergrad|degree) (?:is|was) in\b|\b(?:i'm|im|i am) (?:an? )?(?:proud )?(?:alum|alumnus|alumna|alumni) (?:of|from)\b"),
        boxed(|m| Some(if contains(m.text(), "bachelor") || contains(m.text(), "undergrad") { "bachelor's" } else { GRADUATED }.to_string())), sh), &["grad", "finished", "formei", "bachelor", "undergrad", "degree", "alum"]));
    rules.push(said("highest_degree", r"\bi (?:graduated|finished) (?:from )?high ?school\b|\bi (?:have|got|earned|hold) (?:a |my )?high ?school diploma\b|\b(?:i'm|im|i am) (?:a )?high ?school graduate\b|\bcompleted (?:my )?12th\b|\bpassed (?:my )?12th\b|\bi have (?:a|my) ged\b", fixed("secondary school"), sh));
    rules.push(said("current_study_level", high_school, boxed(grade), sh));
    rules.push(said("current_study_level", high_grade, boxed(grade), sh));
    let persona_school = r"\b(?:(college) (?:boy|girl|guy|dude|bro|kid|twink|jock|athlete|lad|stud|nerd|bwc|chick|babe|cutie|student|man)s?|high ?schoolers?|high-schoolers?)\b";
    let school_student = r"\b(?:i'm|im|i am) an? school (?:student|boy|girl|kid)\b";
    let grad_school = r"\b(?:i'm|im|i am|currently|now|i'm currently|i'm back|i am back|i'm now) (?:in|at|attending|starting) grad(?:uate)? school\b|\b(?:moving|moved|relocating|going back|back|here|starting|start) (?:[\w-]+ ){0,4}?(?:for|to) grad(?:uate)? school\b";
    rules.push(said("current_study_level", persona_school, boxed(|m| if personal(m) { Some(if m.nonempty(1).is_some() { UNDERGRAD } else { "high school (year unstated)" }.to_string()) } else { None }), sh));
    rules.push(said("current_study_level", school_student, fixed("student (level unstated)"), sh));
    rules.push(said("current_study_level", grad_school, mine(near(fixed("graduate student (level unstated)"))), sh));
    rules.push(said("highest_degree", r"\b(?:a|an|my) (master'?s|masters|bachelor'?s|bachelors|doctorate|phd|associate'?s) degree\b(?! (?:plan|plans|program|programme|application|applications|course|courses|admission)\b)", boxed(|m| if (owned(m.string, m.start(), 50) || personal(m)) && !ASPIRING.test_in(m.string, clause(m.string, m.start()), m.start()) && !IN_PROGRESS.test_in(m.string, clause(m.string, m.start()), m.start()) { get(&DEGREE_MAP, m.group(1)) } else { None }), sh));
    rules.push(said("highest_degree", concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n]\s*)(?:\d{2}\s?[mf]\s+)?(?:a )?(?:fresh|recent|new) (?:college )?grad(?:uate)? here\b"), fixed(GRADUATED), sh));
    rules.push(said("highest_degree", r"(?<!should )(?<!do )(?<!can )(?<!could )(?<!shall )(?<!will )\bi (?:dropped out of|never finished|didn't finish|did not finish|quit) (?:high ?school|hs|secondary school)\b|\bi left school at (?:1[3-6]|thirteen|fourteen|fifteen|sixteen)\b|\b(?:i'm|im|i am|as) an? (?:high ?school|hs) drop-?out\b", fixed("high school dropout"), &UNLESS));
    rules.push(said("highest_degree", r"(?<!should )(?<!do )(?<!can )(?<!could )(?<!shall )(?<!will )\bi (?:dropped out of|never finished|didn't finish|did not finish|quit) (?:college|uni|university|community college|my degree|my bachelor'?s|undergrad)\b|\b(?:i'm|im|i am|as) an? (?:college|uni|university) drop-?out\b|\bi have some college\b", fixed("college dropout"), &UNLESS));
    rules.push(said("highest_degree", r"(?<!should )(?<!do )(?<!can )(?<!could )(?<!shall )(?<!will )\bi (?:dropped out of|never finished|didn't finish|did not finish|quit) (?:my )?(?:grad(?:uate)? school|phd|ph\.d|masters?|master's|med school|medical school|law school|doctorate|phd program)\b|\b(?:i'm|im|i am|as) an? (?:phd|grad school) drop-?out\b", fixed("graduate school dropout"), &UNLESS));
    rules.push(said("highest_degree", r"\b(?:i'm|im|i am) an? (?:proud )?drop-?out\b(?! (?:from|of)\b)|\bi dropped out of school\b", fixed("dropout (level unstated)"), &UNLESS));
    rules.push(said("highest_degree", r"\bi never went to (?:college|uni|university)\b|\bi (?:don't|do not) have (?:a|any) (?:college |university )?degree\b", fixed("no degree"), &UNLESS));
    rules.push(said("highest_degree", r"\bi (?:have|got|earned) (?:an? )?associate'?s(?: degree)?\b", fixed("associate"), sh));
    rules.push(said("highest_degree", r"\bi went to (?:a )?trade school\b|\bi(?:'m| am) a (?:journeyman|licensed electrician|licensed plumber)\b", fixed("trade / vocational certificate"), sh));

    let subject_line = concat!(r"(?:(?m:^)", claimcore::flair!(), r"\W*|[,|][ \t]*)(?:(?:\d{2}\s?[mf]?|[mf]4[a-z]+|[mf]\s?\d{2}|[\[(][\w /+-]{1,12}[\])])[ \t,|-]*)*+(?:an? )?([\w'-]+(?: [\w'-]+){0,3}?) (?:student|major)\b");
    let studying_subject = format!(r"(?:^{flair}|[.,;!\n]\s*[-*•]?\s*|\b(?:and|student|college|uni|university) )(?:currently |also |still |now )?(?:studying|majoring in) ({subject_names})\b", flair = claimcore::flair!());
    let hedge = hedge();
    rules.push(rule("field_of_study", &studying_subject, keys(&SUBJECTS, 1), hedge));
    rules.push(rule("field_of_study", &(format!(r"\bmy (?:\w+ )?({subject_names}) (?:class|classes|course|courses|module|modules|lab|labs|lecture|lectures|lecturer|professor|professors|prof|exam|exams|")
        + &format!(r"final|finals|midterm|midterms|coursework|assignment|assignments|thesis|dissertation|program|programme|department|dept|cohort|classmates|seminar|studies)\b|")
        + &format!(r"\bmy (?:thesis|dissertation|capstone|research|phd|ph\.d|masters|master's) (?:is |was )?(?:on|about|in) (?:the )?({subject_names})\b|")
        + &format!(r"\b(?:i'm|im|i am) (?:currently |also )?(?:taking|in|doing) (?:a |an |my |two |some )?({subject_names}) (?:class|classes|course|courses|module|modules|degree|program|programme)\b")),
        boxed(|m| keyed(&SUBJECTS, m.first())), self_hedge));
    rules.push(rule("field_of_study", &(format!(r"(?:\bi(?:'m| am|m)? (?:currently |now |also |still |actually )?|\bcurrently )(?:study|studied|studying|majored in|major in|majoring in|have a degree in|got my degree in|")
        + &format!(r"have a (?:bachelor'?s|bachelors|master'?s|masters|phd|ba|bs|bsc|ms|msc) in|graduated in|did my degree in)\s+({subject_names})\b")), keys(&SUBJECTS, 1), hedge));
    rules.push(rule("field_of_study", &format!(r"\b{I} (?:a |an )?(?:(?:first|second|third|fourth|final|\d(?:st|nd|rd|th))[- ]year )?({subject_names}) (?:major|student|graduate|grad|undergrad|undergraduate)\b|\bmy ({subject_names}) (?:degree|major)\b"),
        boxed(|m| keyed(&SUBJECTS, m.nonempty(1).or(m.group(2)))), hedge));
    rules.push(rule("field_of_study", &format!(r"\b(?:a|an|my) ({subject_names}) (?:degree|diploma|bachelor'?s|bachelors|masters?|master's|phd|major)\b"),
        boxed(|m| if starts_at(m.text(), 0, "my") || owned(m.string, m.start(), 50) { keyed(&SUBJECTS, m.group(1)) } else { None }), self_hedge));
    rules.push(rule("field_of_study", r"\b(?:student|major|grad) here\b", boxed(|m| subject_before(m.string, m.start())), self_hedge));
    rules.push(rule("field_of_study", student_line, scoped(boxed(|m| match rfind(m.text(), "student", m.text().len()) {
        Some(k) if k > 0 => subject_before(m.string, m.start() + k),
        _ => None,
    })), TAGGED));
    rules.push(rule("field_of_study", subject_line, keys(&SUBJECTS, 1), self_hedge));
    rules.push(rule("field_of_study", &format!(r"\b(?<!no )(?<!any )(?:degree|degrees|bachelors?|bachelor's|masters?|master's|phd|bsc|ba|bs|ms|msc|ma|major|majoring|majored|graduate|student|year|diploma|course|studies|studying|study|studied|undergrad|undergraduate|graduation|schooling|background)(?: is| was)? in (?:(?!(?:the|a|an|my|this|that|their|his|her|which|what)\b)[a-z]+ )??({degree_subject_names})\b"),
        boxed(|m| if owned(m.string, m.start(), 60) && !super::FUTURE.test_in(m.string, clause(m.string, m.start()), m.start()) && !m.group(1).is_some_and(|k| eq(k, "it")) { keyed(&DEGREE_SUBJECTS, m.group(1)) } else { None }), self_hedge));
    rules.push(rule("field_of_study", &format!(r"\bi(?:'m| am|m)? (?:currently |now |also |still )?(?:going (?:back )?to|go to|in|back in|attending) (?:school|college|uni|university|grad school) for ({subject_names})\b"), keys(&SUBJECTS, 1), self_hedge));
    rules.push(rule("field_of_study", &format!(r"\b(?:as an? |i'm an? |im an? |i am an? )(?:[\w-]+ ){{0,2}}({subject_names}) (?:graduate|grad|student|major)\b"), keys(&SUBJECTS, 1), self_hedge));
    rules.push(rule("field_of_study", concat!(r"\b(law|med|medical|pharmacy|nursing|dental|vet|veterinary|engineering|business|art|film|architecture|b) (?:school|college)\b|\b(?:i'm|im|i am|i was|as) (?:a |an )?[123](l)\b"), boxed(|m| if owned(m.string, m.start(), 60) { get(&SCHOOL_MAP, m.first()) } else { None }), self_hedge));
    rules.push(needs(rule("field_of_study", concat!(r"\b(?:estudante|estudiante|étudiante?|studente(?:ssa)?|studentin?|student) (?:de |d'|di |en |der )(?:la |el |a |o )?(\w+)|\b(?:faço|estudo|estudio|curso|cursando|studiere|studio|j'étudie|étudie|studeer) ",
        r"(?:de |la |el |a |o |in )?(\w+)|\b(?:facoltà|faculdade|facultad|faculté|fakultät) (?:di |de |d'|für )(?:la |el |a |o )?(\w+)|\b(\w+) (?:zu )?studieren\b"),
        boxed(|m| keyed(&FOREIGN_SUBJECT_MAP, m.first())), self_hedge), &["estud", "étud", "studen", "studi", "studeer", "faço", "curs", "facolt", "faculdade", "facultad", "faculté", "fakultät"]));
    rules.push(rule("field_of_study", &format!(r"\b(?:have|got|hold|earned|finished|completed|did|doing|pursuing|my|an?) (?:an? |my )?({degree_field_names})\b(?! (?:method|passcode|code|codes|app|device|token|prompt|key|setup|display|authentication|authenticator|login|request|requests|enabled)\b)|\b({degree_field_names}) (?:student|graduate|grad|holder|hons)\b"),
        boxed(|m| if starts_at(m.text(), 0, "my") || owned(m.string, m.start(), 50) { get(&DEGREE_FIELD_MAP, m.nonempty(1).or(m.group(2))) } else { None }), self_hedge));
    let year_of = format!(r"\bmy (?:freshman|sophomore|junior|senior|first|second|third|fourth|fifth|final|last|\d(?:st|nd|rd|th)) (?:year|yr|semester|sem) (?:of|in) (?:an? |my )?({subject_names})\b")
        + r"(?! (?:class|classes|course|courses|school|teacher|teachers|teaching)\b)";
    let degree_subject = r"\b(?:b\. ?tech|btech|m\. ?tech|mtech|b\.? ?sc|m\.? ?sc|b\.e|m\.e|b\.s|b\.a|bs|ba|ma|ms|bba|bcom|b\.com|bca|mca|bachelor'?s? of|bachelors of|master'?s? of|masters of)\.?(?:'?\d\d)?".to_string()
        + &format!(r"(?: (?:of )?(?:science|arts|engineering) in)?[ -]+({subject_names})\b");
    let doing_subject = format!(r"\b(?:i'm|im|i am|student|currently) (?:currently |also |now |still )?(?:doing|taking) ({subject_names})\b")
        + r"(?! (?:class|classes|course|courses|exam|exams|module|modules|test|tests|lesson|lessons|homework|assignment|at|for|with|and)\b)";
    let major_is = format!(r"\bmy (?:major|course|degree|program|programme|stream|branch|specialization|specialisation|field of study)(?: is| was|:| -)\s*(?:in )?({subject_names})\b|")
        + &format!(r"\b(?:chose|picked|chosen|declared) ({subject_names}) as my (?:major|degree|course)\b");
    rules.push(said("field_of_study", &year_of, boxed(|m| subject(m, &AI_SUBJECTS)), sh));
    rules.push(said("field_of_study", &degree_subject, boxed(|m| if anchored(m.string, m.start()) { keyed(&SUBJECTS, m.group(1)) } else { None }), sh));
    rules.push(said("field_of_study", &doing_subject, boxed(|m| subject(m, &AMBIGUOUS)), sh));
    rules.push(said("field_of_study", &major_is, boxed(|m| subject(m, &NO_SUBJECTS)), sh));

    let school_year = format!(r"\b{I} (?:currently |still |now |just |only )?(?:in (?:(?:year|yr|y) ?(?:9|10|11|12|13)|(?:6th|7th|8th|sixth|seventh|eighth) grade|year [78]|middle school|junior high)|an? (?:(?:year|yr|y) ?(?:9|10|11|12|13)|middle school(?:er| kid| student)?))\b(?! (?:of|ago|old|since|teacher|teachers|class|classes|students|kids)\b)")
        + concat!(r"|(?:^", claimcore::flair!(), r"|[.!?\n]\s*)(?:an? |just an? )?(?:year|yr|y) ?(?:9|10|11|12|13) (?:student|here)\b");
    rules.push(said("current_study_level", &school_year, boxed(|m| if contains(m.text(), "middle school") || contains(m.text(), "junior high") { Some("middle school".to_string()) } else { grade(m) }), sh));
    rules.push(rule("current_study_level", r"\Ar/(\w+): ([^\n]{0,80})", boxed(flair_level), TAGGED));
    const GRAD_YEAR: &str = r"((?:19[5-9]\d|20[0-2]\d|203[0-2]))\b";
    let graduated = [
        format!(r"\bi(?: (?:graduated|graduate|will graduate|am graduating|finished (?:college|uni|university|school|high ?school))|'ll graduate|'m graduating|m graduating) (?:from (?:[\w'&.-]+ ){{1,4}}?)?(?:in |back in |this |next )?(?:(?:may|june|july|august|december|spring|summer|fall|autumn|winter) )?(?:of )?{GRAD_YEAR}"),
        format!(r"\b(?:i'm|im|i am|i was) (?:in |part of )?(?:the )?class of {GRAD_YEAR}"),
    ];
    for pattern in &graduated {
        rules.push(said("graduation_year", pattern, boxed(|m| m.gs(1)), sh));
    }
    let class_of = format!(r"(?:^{flair}|[.!?\n,(]\s*)(?:(?:hs|high school|college|uni) )?class of '?{GRAD_YEAR}(?= here\b|\s*(?:$|[.,!;:)\n]))", flair = claimcore::flair!());
    rules.push(needs(said("graduation_year", &class_of, boxed(|m| m.gs(1)), sh), &["class of"]));
    let grade = r"([0-4](?:\.\d{1,3})?)";
    let unscaled = r"(?! ?/ ?(?:[5-9]|10|100)\b|\.\d|\s*(?:-|to)\s*\d|\s*w\b|\s*weighted| (?:is|or|and) (?:required|needed|the minimum|above|higher|better)\b)";
    let kinds = r"(?:cumulative |overall |current |unweighted |uw |final |college |undergrad |undergraduate |high school |hs |major |term |semester |solid |perfect |decent |low |high |cgpa )*";
    let gpa_patterns = [
        format!(r"\bi(?: (?:currently|now|still|only|just|also|actually))* (?:have|had|got|ended with|graduated with|finished with|maintain|maintained|hold|'ve got|ve got|have got|earned|kept) (?:a |an |my )?{kinds}{grade}(?: ?/ ?4(?:\.0+)?)? ?(?:uw |unweighted |cumulative |overall )?(?:c?gpa|grade point average)\b"),
        format!(r"\bmy {kinds}(?:c?gpa|grade point average)(?: is| was| is now| is currently| sits at| is around| is about| of|:| =| -| is only| is like| ended up)?(?: (?:a|an|around|about|like|roughly|only|just|~|currently|now|at))* ~?{grade}{unscaled}"),
        format!(r"(?:^{flair}|[\n|•,;(]\s*)(?:[-*]\s*)?(?:uw |unweighted |cumulative |overall )?c?gpa\s*[:=-]\s*{grade}{unscaled}", flair = claimcore::flair!()),
        format!(r"(?:^{flair}|[\n|•,;(]\s*)(?:[-*]\s*)?{grade}(?: ?/ ?4(?:\.0+)?)? ?(?:uw |unweighted |cumulative |overall )?gpa\b(?! (?:is|or|and|requirement|required|minimum|cutoff|needed)\b|\+)", flair = claimcore::flair!()),
        format!(r"\bi (?:have|had|got|ended with|graduated with|finished with) an? (?:overall |cumulative |final )?(?:c?gpa|grade point average) of (?:about |around |roughly |~)?{grade}{unscaled}"),
    ];
    for pattern in &gpa_patterns {
        rules.push(needs(said("gpa", pattern, boxed(|m| ranged(m, 0.0, 4.0)), sh), &["gpa", "grade point"]));
    }
    for (attribute, test, score, low, high) in [("mcat_score", "mcat", r"(4[7-9]\d|5[0-2]\d)", 472.0, 528.0), ("lsat_score", "lsat", r"(1[2-7]\d|180)", 120.0, 180.0)] {
        let patterns = [
            format!(r"\bi(?: (?:just|recently|finally|also|only|actually))* (?:got|scored|received|earned|have|ended up with|pulled|'ve got) (?:a |an )?~?{score}(?: on (?:the |my )?{test}| {test})\b"),
            format!(r"\bmy {test}(?: score)?(?: is| was| of|:| =| -)?(?: (?:a|an|around|about|only|just))* {score}\b"),
            format!(r"\bi (?:took|wrote|sat|did) (?:the |my )?{test}\b[^.!?\n]{{0,40}}?\b(?:got|scored|received) (?:a |an )?{score}\b"),
            format!(r"(?:^{flair}|[\n|•,;(]\s*)(?:[-*]\s*)?(?:{test}\s*[:=-]\s*{score}|{score} {test})\b", flair = claimcore::flair!()),
        ];
        for pattern in &patterns {
            rules.push(needs(said(attribute, pattern, boxed(move |m| ranged(m, low, high)), sh), &[test]));
        }
    }
    let broke = r"\b(?:i'm|im|i am) (?:so |too |very |really |pretty |super |dirt |flat |fucking |always |perpetually |still |literally )*(?:broke|poor)\b(?! (?:up|off|down|out|into|in|at|with|by|from)\b)|\bi(?:'m| am)? living paycheck to paycheck\b|\bi live paycheck to paycheck\b";
    rules.push(said("financial_situation", broke, fixed("broke / struggling"), sh));
    rules.push(said("financial_situation", r"\b(?:i'm|im|i am) (?:already )?(?:a )?(?:multi-?)?millionaire\b", fixed("wealthy"), sh));
    rules.push(said("financial_situation", r"\b(?:i'm|im|i am) (?:already |now )?(?:fi|financially independent)\b(?=\s*(?:$|[.,!;)]|\b(?:and|now|since|at)\b))|\bi retired early\b|(?<![\w.])\d{1,3}(?:\.\d+)?% (?:to )?fi(?:re)?\b", fixed("financially independent / retired early"), sh));
    rules.push(said("financial_situation", r"\b(?:i'm|im|i am|i've been|i have been) (?:currently |now |still )?on (?:benefits|welfare|universal credit|food stamps|centrelink)\b", fixed("on benefits"), sh));
    let amount = format!(concat!(r"(?:about |around |roughly |over |like |~|almost |just under |just over |close to |nearly |an? |approximately |approx |more than |barely |only |just |(?:a bit|a little|slightly) (?:over|under|more than|less than) |just shy of |upwards of |north of )?",
        r"(?:({BEFORE})\s?)?(\d[\d,]*(?:\.\d+)?)\s*({SCALE})?(?:\s*(?:-|–|to)\s*(?:{BEFORE})?\s?\d[\d,]*(?:\.\d+)?\s*({SCALE})?)?",
        r"\s*(?:({AFTER})(?![a-z])\s*)?(?:(?:a|per|/|an?|each)\s*(year|yr|annum|month|mo|hour|hr|week|wk)\b|(annually|yearly|monthly|hourly|weekly)\b|",
        r"(?=\s*(?:$|[.,!;)+]|before|after|pre|post|gross|net|base|salary|total|tc|as|currently|now|right now|working|plus|and|but|so|with|which)))"), BEFORE = BEFORE, SCALE = SCALE, AFTER = AFTER);
    let paid = concat!(r"(?:\b(?:i|me) (?:currently |now |only |just |still )?(?:make|made|earn|earned|bring in|bring home|gross|grossed|net|netted|take home|clear|cleared|pull|pulled|pull in|get paid|got paid|passed|hit|crossed|topped)|",
        r"\b(?:i'm|im|i am) (?:currently |now |only |just |still )?(?:making|earning|paid|getting paid|bringing in|bringing home|pulling in|clearing|netting|grossing|taking home|(?:on|at)(?=\s+(?:about |around |like |~)?\$|\s+\d[\d,.]*\s*k\b))|\bmy (?:salary|income|pay|base|base salary|base pay|tc|total comp|total compensation|",
        r"take home|take-home|take home pay|comp|annual salary|gross income|net income|household income|paycheck|wage|hourly rate|rate) (?:is|was|went up to|of|:|=|is now|just hit|is around|is about|is like))");
    let income_patterns = [
        format!(r"{paid}\s+{amount}"),
        format!(r"(?:^{flair}|[.!?\n]\s*)(?:passed|cleared|hit|crossed|made|make|earn|earning|making|grossed|netted|took home|take home)\s+{amount}", flair = claimcore::flair!()),
    ];
    let earning_pattern = format!(r"\b(?<!from )(?:making|earning|earn|make|bringing in|pulling in|clearing)\s+{amount}");
    let six_figures = format!(r"{paid}\s+(?:(?:about|around|over|almost|nearly|just over|just under|close to|low|solid|a) )?(?:six|6)[- ]figures?\b(?! (?:range|total|net worth|in debt))|")
        + r"\bi(?:'ve| have)? (?:just |finally |recently |now )?(?:got|have|landed|make|earn) (?:a |my )(?:\w+ )?(?:six|6)[- ]figure (?:salary|income|job)\b";
    for pattern in &income_patterns {
        rules.push(rule("income", pattern, boxed(income), self_hedge));
    }
    rules.push(rule("income", &six_figures, boxed(figures), self_hedge));
    rules.push(said("income", &earning_pattern, boxed(earning), sh));
    let term = r"\bcurrently (?:studying|pursuing|enrolled|doing (?:my|a|an) (?:degree|bachelor'?s|masters?|master's|bsc|ba|bs|btech|undergrad))\b";
    rules.push(said("current_study_level", term, near(boxed(level)), sh));

    let it_anchors: &[&str] = &["in it", "in the it", "in corporate it", "in enterprise it"];
    let retire: &[&str] = &["retire"];
    let gate_table: Vec<(&str, &[&str])> = vec![
        (student_line, &["student", "college"]),
        (subject_line, &["student", "major"]),
        (named[1].as_str(), &["my name"]),
        (gerund.as_str(), &["working as"]),
        (working_in.as_str(), &["working in", "work in"]),
        (in_it.as_str(), &["work in it", "working in it"]),
        (cased_it[0].as_str(), it_anchors),
        (cased_it[1].as_str(), it_anchors),
        (cased_it[2].as_str(), &["it job", "it career", "it role", "it position", "it gig"]),
        (studying_subject.as_str(), &["studying", "majoring"]),
        (mentions[0].as_str(), &["here"]),
        (mentions[3].as_str(), &["occupation", "profession", "job", "work", "career", "current role", "me"]),
        (mentions[4].as_str(), &["currently"]),
        (mentions[5].as_str(), &["by trade", "by profession"]),
        (mentions[6].as_str(), &["both"]),
        (homemaker[1].as_str(), &["sahm", "sahd", "stay", "homemaker", "housewife"]),
        (retired[0].as_str(), retire),
        (retired[1].as_str(), retire),
        (retired[2].as_str(), retire),
        (retired[3].as_str(), retire),
        (retired[4].as_str(), retire),
        (unemployed[0].as_str(), &["unemployed", "jobless", "out of work", "between jobs"]),
        (campus_started, &["college", "uni"]),
        (high_grade, &["9th", "10th", "11th", "12th", "grade", "class", "year"]),
        (college_item, &["in college", "in uni"]),
        (undergrad, &["freshman", "sophomore", "fresher", "freshie", "undergrad", "junior", "senior"]),
        (self_employed[0].as_str(), &["employed", "freelancer", "sole trader"]),
    ];
    gates(&mut rules, &gate_table);
    rules.extend(super::schools::rules());
    rules.extend(super::standing::rules());
    rules
}
