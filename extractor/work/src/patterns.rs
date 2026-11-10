use crate::*;

const ELIDED: &str = concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n]\s*)(?:also |currently |now |still |unfortunately |sadly |just |recently |happily )?");
const STATED: &str = r"(?=\s*(?:$|[.,!;:)(\n-]|\b(?:for|since|and|now|right|currently|again|atm|rn|lol|but|so|too|myself|here|with|as|in|at)\b))";
const ADVERB: &str = r"(?:(?:also|now|currently|still|actually|literally|basically|just|only|really|officially|finally|myself|technically|already|proudly|both|happily|full[- ]?time|part[- ]?time) )*";
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
    for (pattern, _) in table {
        assert!(rules.iter().any(|entry| entry.re.pattern == *pattern), "gate pattern matches no rule: {pattern}");
    }
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
        (r"\b(?:i'm|im|i am|i've been) an rn\b".to_string(), || fixed("registered nurse")),
        (concat!(r"(?:^", claimcore::flair!(), r"|[.!?\n]\s*)(?:an? )?(?:\w+ )?rn here\b").to_string(), || fixed("registered nurse")),
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
    let owners = [
        r"\b(?:(?:commissions|comms) (?:are )?(?:open|opened)|open(?:ing)? (?:my )?(?:commissions|comms)|open (?:for|to) (?:commissions|comms)|(?:taking|accepting|doing|started taking) (?:commissions|comms)|working (?:on|with) commissions)\b",
        r"\[\s*for hire\s*\]",
    ];
    let independent = format!(r"\b{I}(?: [a-z]+(?:[ -][a-z]+)?,)? {ADVERB}an? (?:independent|freelance|freelancing|self[- ]employed) ");

    let mut rules: Vec<Rule> = Vec::new();
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


    let it_anchors: &[&str] = &["in it", "in the it", "in corporate it", "in enterprise it"];
    let retire: &[&str] = &["retire"];
    let gate_table: Vec<(&str, &[&str])> = vec![
        (named[1].as_str(), &["my name"]),
        (gerund.as_str(), &["working as"]),
        (working_in.as_str(), &["working in", "work in"]),
        (in_it.as_str(), &["work in it", "working in it"]),
        (cased_it[0].as_str(), it_anchors),
        (cased_it[1].as_str(), it_anchors),
        (cased_it[2].as_str(), &["it job", "it career", "it role", "it position", "it gig"]),
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
        (self_employed[0].as_str(), &["employed", "freelancer", "sole trader"]),
    ];
    gates(&mut rules, &gate_table);
    rules.extend(super::standing::rules());
    rules
}
