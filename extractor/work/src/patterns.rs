use crate::*;

const ELIDED: &str = r"(?:^|[.!?\n]\s*)(?:also |currently |now |still |unfortunately |sadly |just |recently |happily )?";
const STATED: &str = r"(?=\s*(?:$|[.,!;:)(\n-]|\b(?:for|since|and|now|right|currently|again|atm|rn|lol|but|so|too|myself|here|with|as|in|at)\b))";
const ADVERB: &str = r"(?:(?:also|now|currently|still|actually|literally|basically|just|only|really|officially|finally|myself|technically|already|proudly|both|happily|full[- ]?time|part[- ]?time) )*";
const BMOD: &str = r"(?:(?!(?:local|favorite|favourite|usual|nearest|go-to|regular|closest|neighborhood|neighbourhood|nearby|preferred|dad's|mom's|mum's|parents'|family's|friend's|old)\b)[\w'&-]+ ){0,2}?";

fn names(map: &Map) -> String {
    longest_first(map.keys().map(|k| k.as_str()))
}

fn job(find: fn(&Match, Use) -> Option<&'static str>) -> impl Fn(&Match) -> Option<&'static str> + Send + Sync + 'static {
    move |m| find(m, Use::Job)
}

fn field(find: fn(&Match, Use) -> Option<&'static str>) -> V {
    Box::new(move |m| found(find(m, Use::Field)))
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
    let place_names = names(&PLACE_MAP);
    let business_names = names(&BUSINESS_MAP);
    let my_business_names = longest_first(BUSINESS_MAP.keys().map(|k| k.as_str()).filter(|name| name.contains(' ') || ["business", "startup", "bakery", "pizzeria", "brewery", "restaurant", "cafe", "café", "llc"].contains(name)));
    let verb_names = names(&VERB_MAP);
    let subject_names = names(&SUBJECTS);
    let degree_subject_names = names(&DEGREE_SUBJECTS);
    let degree_field_names = names(&DEGREE_FIELD_MAP);
    let long_degree_names = longest_first(DEGREES.iter().map(|(name, _)| *name).filter(|name| !SHORT_DEGREES.contains(name)));
    let short_degree_names = longest_first(SHORT_DEGREES.iter().copied());

    let cased_it = [
        r"\b(?:(?:i|i've|ive|i have|i had|i've been|i have been)(?: (?:also|currently|now|still|actually|mostly|mainly|already))* (?:work|worked|working)|(?:i'm|im|i am)(?: (?:also|currently|now|still|actually|mostly|mainly|already))*(?: working| employed)?) in (?:corporate |enterprise |the )?it\b".to_string(),
        r"(?:^|[.!?\n,(]\s*)(?:currently |also |now )?(?:work|working) in (?:corporate |enterprise |the )?it\b".to_string(),
        r"\b(?:my|i have an?|i've got an?|i got an?|i landed an?)(?: [\w-]+){0,2}? it(?= (?:job|career|role|position|gig)\b)".to_string(),
    ];
    let in_it = r"\bi(?:'m| am|'ve been| have been)? (?:also |currently |now |still |actually )?work(?:ing)? in it\b(?=\s*(?:[,.;!)]|$|\b(?:and|for|as|support|now|myself|too|so|but)\b))".to_string();
    let working_in = format!(r"(?:^|[.,;!\n]\s*|\band )(?:also |currently |now |still )?(?:work|working) in (?:the )?({field_names})(?: industry| field| sector| department| dept| business| world| trade)?\b")
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
        vec![finder(job(after)), finder(job(after)), finder(job(after)), finder(job(after)), finder(plain(abroad)), finder(plain(abroad))]
    };
    let opener_pattern = r"(?:^|[.!?\n]\s*)(?:as|being|speaking as) an? ".to_string();
    let gerund = r"\bworking as (?:an? |the )?".to_string();
    let named_rest = concat!(r"\s+(?!(?:not|so|very|sorry|sure|afraid|guessing|confused|curious|glad|happy|tired|just|also|like|really|honestly|currently|still|okay|ok|fine|good|here|back|done|new|old|aware|thinking|wondering|asking|saying|going|trying|looking|getting|being|talking|actually|always|never|now|single|married|alone|well|but|and|or)\b)",
        r"\**[a-z][\w.'-]*(?: [a-z][\w.'-]*)?\**\s?,\s*(?:\d{2}\s?[mf]?\s?,\s*)?(?:an? |the )");
    let named = [format!(r"i(?<!\wi)(?:'m|m| am){named_rest}"), format!(r"my(?<!\wmy) name(?: is|'s){named_rest}")];
    let mentions: Vec<String> = vec![
        [r"(?:^|[.!?\n:(,]\s*|\s[-–—]\s+|\b(?:hi|hey|hello|hiya|yo|greetings)\b[ ,!.]*)(?:an? |fellow |another |a fellow |also an? |as an? |just an? )?((?:[\w'&/.+-]+ ){1,6}?)",
         r"(?:by (?:trade|profession|training) )?here\b(?=\s*(?:[^\w\s]|\b(?:and|with|who|so|but|in|from|too|lol|haha|for)\b|$))"].concat(),
        r"\b(?:as|being|speaking as) an? ".to_string(),
        r"\[\s*(?:for hire|hire me)\s*\][\W_]*".to_string(),
        r"(?:^|\n)[^\w\n]*(?:occupation|profession|job|work|career|job title|current job|current role|me)[^\w\n]{0,4}?[:=][^\w\n]*".to_string(),
        r"(?:^|[.!?\n]\s*)currently (?:working as )?an? ".to_string(),
        r"(?:^|[.!?\n]\s*)((?:[\w'&/.+-]+ ){1,6}?)by (?:trade|profession)\b".to_string(),
        r"\b(?:we(?:'re| are)|and i are|and me are|and myself are) both ((?:[\w'&/.+-]+ ){0,3}?[\w'&/.+-]+s)\b".to_string(),
    ];
    let mention_finds = || -> Vec<Finder> {
        vec![finder(job(here)), finder(job(opened)), finder(job(hired)), finder(job(hired)), finder(job(opener)), finder(job(here)), finder(job(here))]
    };
    let lead = [r"(?:^|\n)[ \t>*#\\-]*+(?:(?:\d{2}\s?(?:yo|y/o|yrs? old|years? old)|\d{2}\s?[mf]?|[mf]\s?\d{2}|[\[(][\w /+-]{1,12}[\])]|#[\w/-]+|[-–—|,]+)[ \t]*)*+(?:(?:also|just|another|fellow|a|an) )*+",
        r"(?:(?:married|professional|licensed|certified|registered|senior|junior|qualified|experienced|freelance|hung|single|divorced|tired|exhausted) )*+(?=[^\W_])"].concat();
    let tagged_title = r"(?<![\w$#])(?:\d{2}\s?[mf]|[mf]\s?\d{2})\b(?: and)?[ ,]+(?:an? )?|(?<![\w$#.,])\d{2},? and an? |(?<![\w$#])[\[(]?[mf]4[a-z]+[\])]?[ ,]+(?:an? )?|\(\d{2}\)[ ,]+(?:an? )?".to_string();
    let cell = r"[,|][ \t]*(?:an? )?".to_string();
    let workplace = [
        format!(r"(?:\bi(?:(?:(?:'ve| have) (?:been )?(?:currently |now |also |still |mostly |mainly |actually )?(?:work|working|worked)|(?:'m| am)? (?:currently |now |also |still |mostly |mainly |just started |started |actually )?(?:work|working|employed)) (?:(?:in|for) )?(?:the |an? )?(?:(?!(?:same|this|that|my|your|his|her|their|our|other|different|any|every|no)\b)[\w-]+ ){{0,2}}?|(?:'m| am|m|'ve been| have been) (?:currently |now |also |still |actually |mostly |mainly )?in (?:the )?)|\bas (?:someone|somebody) (?:who (?:also |currently |now |still |actually )?(?:works|has worked) |working )?in (?:the )?)({field_names})")
            + r"(?: industry| field| sector| department| dept| business| world| trade)?\b(?! (?:class|classes|school|course|program|degree|student|home|homes|facility|facilities)\b)",
        format!(r"\bi(?:'ve| have)? (?:been )?(?:currently |now |also |still |mostly |mainly |just started |started |actually )?(?:work|working) (?:at|in|for) (?:a |an |the |my local |our local |this |our |one of the )?")
            + &format!(r"(?:(?!(?:same|this|that|my|your|his|her)\b)[\w'-]+ ){{0,2}}?({place_names})s?\b"),
        format!(r"\b{I} (?:currently |now |also |still )?(?:working|employed) (?:at|in|for) (?:a |an |the )?(?:(?!(?:same|this|that|my|your)\b)[\w'-]+ ){{0,2}}?({place_names})s?\b"),
    ];
    let ownership = [
        format!(r"(?:\b(?:i|we)(?:'ve| have)? (?:also |now |still |currently |actually |just |recently )?(?:own and run|own and operate|run and own|own|run|co-?own|opened|started|founded|operate|launched)|(?:^|[.!?\n,]\s*)(?:own and run|own|run|co-?own)) ")
            + &format!(r"(?:a|an|my own|my|two|three|four|several|a few|\d+|our|our own|a small|a little) {BMOD}({business_names})(?:es|s)?\b")
            + r"(?! (?:card|account|class|classes|school|trip|degree|plan|idea|name|loan|license|partner|tab|game|simulator|course|major|student)\b)",
        format!(r"(?=my )(?<!of )(?<!mind )(?<!minding )\bmy (?:own )?(?:small |little |tiny |online |family |new )?({my_business_names})\b")
            + r"(?! (?:card|account|class|classes|school|trip|degree|plan|idea|name|loan|license|partner|apartment|flat|tab|game|simulator|course|major|student|friends?)\b)",
    ];
    let teach = concat!(r"\bi(?:'ve| have)? (?:currently |now |also |still |actually )?(?:teach|taught) (?:both )?(?:high school|middle school|elementary|kindergarten|preschool|pre-k|\w+ grade(?:rs)?|\d+(?:st|nd|rd|th) grade(?:rs)?|grade \d+|year \d+|",
        r"math|maths|english|science|history|art|music|pe|biology|chemistry|physics|special ed|sped|esl|efl|college|university|uni|at|in|for|classes|courses|a class|students|",
        r"undergrads|freshmen|ap|french|spanish|german|reading|kids|children|teens)\b|\bi(?:'ve| have) been teaching (?:for|since|\d|at|in)\b|",
        r"\bi(?:'m| am|'ve been| have been)? (?:currently |now |also |still |actually |mostly |mainly )?(?:teach|teaching) (?!(?:me|you|him|her|them|myself|yourself|themselves|it|that|this|us|",
        r"my (?:\w+ )*?(?:kids?|son|daughter|children|baby|girl|boy|dog|cat|puppy|wife|husband|partner|friends?))\b)[a-z]|\bmy (?:students|pupils|classroom|",
        r"lesson plans?|class of|kindergarteners|kinders|first graders|second graders|third graders|fourth graders|fifth graders|\d+(?:st|nd|rd|th) graders|homeroom)\b");
    let care_terms = r"\bmy (?:patients|patient load|caseload|case load|charge nurse|unit manager|nurse manager)\b";
    let activity: Vec<(String, fn() -> V)> = vec![
        (format!(r"\bi ({verb_names}) (?:\w+ ){{0,3}}?(?:for a living|for work|professionally|as a job|as my job|for my job|for a job|full[- ]?time|part[- ]?time|for clients|on the side|as a side hustle|")
            + r"cars|houses|homes|real estate|insurance)\b", || lookup(&VERB_MAP, 1)),
        ([r"\b(?:doing|started|got|landed|have|finished|completed|in|on|accepted|start) (?:a|an|my) (?:\w+ )?(banking|finance|accounting|marketing|engineering|software|it|law|legal|nursing|",
          r"teaching|research|design|consulting|sales|hr|government|journalism|data|audit|tax|clinical|pharmacy|medical|hospital|retail|hotel|media|tech|coding|developer|",
          r"electrical|plumbing|carpentry|welding|mechanic|hvac) (?:internship|apprenticeship|placement|residency|co-?op|traineeship|rotation)\b"].concat(), || lookup(&INTERNSHIP_MAP, 1)),
        (teach.to_string(), || fixed(TEACHING)),
        (care_terms.to_string(), || fixed(CLINICAL)),
        (r"\b(?:i'm|im|i am|i've been) an rn\b".to_string(), || fixed(CLINICAL)),
        (r"(?:^|[.!?\n]\s*)(?:an? )?(?:\w+ )?rn here\b".to_string(), || fixed(CLINICAL)),
    ];
    let role_terms: Vec<(String, fn() -> V)> = vec![
        (r"\bi(?:'ve| have)? (?:see|saw|treat|treated|have|had|'ve had|have had) (?:\w+ )?patients\b|\ba patient of mine\b|\bour patients\b(?=[^.!?\n]*\b(?:i|i'm|i've|my|me)\b)".to_string(), || fixed(CLINICAL)),
        (r"\bmy (?:(?!(?:fellow|former|old|future|international|college|own)\b)[\w-]+ ){1,3}?students\b|\ba student of mine\b".to_string(), || fixed(TEACHING)),
    ];
    let coding = r"\bi(?:'ve| have)?(?: been)? (?:writing|write|wrote|ship|shipping) (?:code|software)\b|\b\d+\+? yoe\b|\bi(?:'m| am)? (?:a |an )?(?:software|computer|tech) (?:guy|person|nerd by trade)\b";
    let got_job = r"\b(?:got|landed|accepted|offered) the job\b";
    let working_role = r"working (?:mom|mum|mother|dad|father|parent|professional|adult|woman|man)\b(?! (?:to|on|in|at|for)\b)";
    let working_lines = [
        format!(r"i(?<!\wi)(?:'m|m| am)(?: also| now| currently| just)? (?:an? )?(?:[\w-]+ ){{0,4}}?{working_role}"),
        format!(r"(?:(?m:^)[ \t>*#\\-]*|,[ \t]*)(?:(?:\d{{2}}\s?[mf]?|[mf]4[a-z]+|[mf]\s?\d{{2}}|[\[(][\w /+-]{{1,12}}[\])])[ \t,|-]*)*+(?:an? )?(?:[\w-]+ ){{0,2}}?{working_role}"),
    ];
    let mut employed_patterns: Vec<String> = vec![
        concat!(r"\bi (?:currently |now |also |still |only |mostly |usually |just |actually |normally |typically |literally |basically |both )?work (?:as|at|for|in|from home|remotely|remote|",
            r"hybrid|part[- ]?time|full[- ]?time|ft|pt|nights|night shift|nightshift|days|day shift|evenings|mornings|weekends|weekdays|overnights?|graveyard|swing|doubles|overtime|",
            r"\d|one|two|three|four|five|six|seven|long|every|monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tues|retail|construction|the same|on (?:a|the) (?:\w+ )?(?:team|floor|unit|ward|site|line)|",
            r"an? \d+|a few|a couple|several|odd|crazy|irregular|rotating|split|shifts|alone|by myself|nine|forty|40|full|part|till|until|late|early|weekend|on call|12s|10s|three 12s|close|opening|the closing|the opening|closing|opening|retail|",
            r"with (?:kids|children|patients|clients|students|customers|people with|adults with|families|veterans|seniors|the elderly)|under|directly|closely|alongside|next to|",
            r"near|around (?:\d|forty|40|50|60)|about (?:\d|forty|40|50|60)|like (?:\d|forty|40|50|60)|nearly|over (?:\d|forty|40)|more than|less than|so much|too much|a lot)\b").to_string(),
        concat!(r"(?=my )(?<!quit )(?<!lost )(?<!left )(?<!leave )(?<!leaving )(?<!quitting )(?<!losing )\bmy (?:day job|full[- ]?time job|part[- ]?time job|current job|new job|job)\b",
            r"(?! (?:hunt|hunting|search|application|applications|interview|offer|is to|to|of|from)\b)").to_string(),
        concat!(r"\b(?:i have|i've got|i have got|i got|i landed|i accepted|i took|i started|i hold|i work|i now have|i currently have|i also have|i just got|i finally got|i recently got) ",
            r"(?:an? |two |2 |three |3 |multiple |several )(?:[\w-]+ ){0,3}?(?:job|jobs|position|career)\b",
            r"(?! (?:interview|offer|application|hunt|search|fair|posting|listing)\b)").to_string(),
        concat!(r"\bi (?:[\w'-]+ ){1,4}?for a living\b|\b(?:i'?m at work|i get paid|i got paid|i'm getting paid|i'm paid|i am paid|i got hired|i just got hired|i was hired|i'm on shift|i got promoted|i was promoted|my first day at work|",
            r"my first week at|my new employer|my employment|i clock in|i clocked in|i clock out|i clocked out|i'm salaried|i am salaried|i'm hourly|i'm full[- ]?time|i'm part[- ]?time|",
            r"i'm a full[- ]?time employee|i'm an employee|i'm staff|i'm on salary|i'm on the payroll|i'm unionized|i'm in a union|my union|i'm a union member|",
            r"i'm (?:a )?(?:salaried|hourly) (?:worker|employee)|i(?:'ve| have) been teaching|i(?:'ve| have) been nursing)\b").to_string(),
        r"\b(?:i|i'm|im|me|my|while|and)\b[^.!?\n]{0,60}?\b(?:working from home|work from home|wfh|working remotely)\b".to_string(),
        concat!(r"\b(?:i'm|im|i am) (?:currently |now |still |gainfully |fully )?employed\b(?! (?:as|by|at|in)\b)|",
            r"\b(?:i'm|im|i am) (?:currently |now )?on (?:maternity|paternity|parental|mat) leave\b|\bmy (?:maternity|paternity|parental|mat) leave\b|\bmy (?:9 ?(?:-|to) ?5|nine to five)\b|",
            r"\bi(?:'ve| have) been working (?:at|for|in|as|there|here|full[- ]?time|part[- ]?time|nights|from home|remotely|\d|since)\b|",
            r"\bi(?:'m| am) (?:currently |now |still )?working (?:full[- ]?time|part[- ]?time|nights|days|weekends|from home|remotely|remote|two jobs|\d+ hours|overtime|doubles|tonight|tomorrow|this weekend|a double)\b|",
            r"\b(?:i|i'm|im|me|my|while)\b[^.!?\n]{0,40}?\bworking (?:a |the |my )?(?:night|day|graveyard|overnight|double|evening|morning|closing|opening|swing|\d+[- ]hour|twelve[- ]hour) shifts?\b|",
            r"\bmy work (?:pays|offers|gives|provides|covers|requires|makes me|schedule|load|week|day|place)\b").to_string(),
        r"\bi (?:also |currently |now |still |mainly |mostly |actually |professionally )?work (?:with|on) (?!(?:you|him|her|them|my|me|myself|it|this|that|what|whatever|anything|everything|something|someone|somebody|people who|a therapist|the assumption)\b)[a-z]".to_string(),
        r"\b(?:i|me) (?:just )?(?:started|start|starting) (?:a |my )?(?:new )?(?:job|position|role|work)\b(?! (?:hunt|search|application|interview)\b)|\bmy (?:first|second) (?:day|week|month) at (?:my|the) (?:new )?(?:job|work|office)\b".to_string(),
        r"\bi (?:also |currently |still |now )?work(?: there| here)?\b(?=\s*(?:[.,!;)]|$|\b(?:and|but|so|too|as well|now)\b))".to_string(),
        concat!(r"\b(?<!no )(?:yo trabajo|trabajo en (?:un|una|el|la)|trabalho (?:em|na|no|numa|num)|je travaille (?:dans|chez|à|au|en|pour)|ich arbeite (?:bei|in|im|als|für)|",
            r"lavoro (?:in|presso|come|per)|ik werk (?:bij|in|als|voor)|pracuję (?:w|jako|na|dla)|jeg (?:arbejder|jobber|arbeider) (?:som|i|på|hos|for)|jag (?:jobbar|arbetar) (?:som|i|på|hos|med)|",
            r"lucrez (?:la|ca|în|in|pentru)|pracuji (?:v|ve|jako|na|pro)|työskentelen|я работаю|çalışıyorum)\b").to_string(),
        r"\b(?:mi|meu|minha|mein|meine|meinem|meinen|mon|il mio|la mia|mia|mój|moja|mojej|mijn|mitt) (?:trabajo|trabalho|emprego|empleo|job|jobb|arbeit|arbeitsplatz|travail|boulot|lavoro|praca|pracy|werk|baan|jefe|jefa|chefe|chefa|chef|chefin|gerente|capo)\b".to_string(),
        r"\b(?:we|and i) (?:both|each|all) (?:work|have jobs|have full[- ]?time jobs|are employed|wfh|work from home|work remotely|work full[- ]?time|work part[- ]?time)\b".to_string(),
        got_job.to_string(),
    ];
    employed_patterns.extend(working_lines.iter().cloned());
    let self_employed = [
        format!("{ELIDED}{}{STATED}", r"(?:self[- ]employed|freelancer|sole trader)\b"),
        concat!(r"\b(?:i|i'm|im|i am|i've|ive|me|myself)\b[^.!?\n]{0,40}?\b(?:self[- ]employed|work for myself|working for myself|freelance work|freelance gigs|freelancing|freelancer)\b|",
            r"\bi (?:also |currently |now |mostly )?(?:freelance|do freelance)\b").to_string(),
        r"\b(?:solo|indie) (?:game )?dev(?:eloper)?\b|\bsolo developing\b|\b1099 (?:worker|contractor|employee|income|job)\b".to_string(),
        concat!(r"\b(?:i'm|im|i am|i've been|ive been|i have been) (?:currently |now |also |still |fully |technically )?(?:self[- ]employed|freelancing|a freelancer|freelance|my own boss|",
            r"an independent contractor|a contractor|a sole trader|a sole proprietor|a solopreneur|an entrepreneur|a business owner|a small business owner|a (?:solo |serial |first[- ]time |startup |tech )?(?:co-?)?founder)\b").to_string(),
    ];
    let unemployed = [
        format!("{ELIDED}{}{STATED}", r"(?:unemployed|jobless|out of work|between jobs)\b"),
        format!(r"\b{I} (?:currently |now |still |officially |technically |basically |just |recently |unfortunately |sadly )?(?:unemployed|jobless|between jobs|out of work|out of a job|without (?:a )?(?:job|work)|")
            + concat!(r"on unemployment|on the dole|on jobseeker'?s|job hunting|job searching|laid off|furloughed|redundant|looking for (?:a |another |any )?(?:job|work)|searching for (?:a )?(?:job|work)|",
            r"applying (?:for|to) jobs|in between jobs|on ei)\b"),
        concat!(r"\bi (?:just |recently |unfortunately |finally )?(?:lost my job|got laid off|was laid off|got let go|was let go|got fired|was fired|got made redundant|was made redundant|got terminated|",
            r"was terminated)\b").to_string(),
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
        r"(?:^|[.!?\n]\s*)(?:a )?(?:\w+ ){0,1}retired (?:\w+ ){0,2}here\b".to_string(),
        concat!(r"\bas an? (?:\w+ )?retiree\b|\b(?:since|after|when|now that|until|before) i (?:retired|am retired)\b|",
            r"\bi (?:just |recently |finally )?retired (?:in|last|a few|from|at|early|after|two|three|four|five|\d|this|back|recently|young|on)\b|\bi(?:'ve| have) been retired\b|",
            r"\b(?:in|since|during|enjoying|into|throughout|after|before) my retirement\b(?! (?:account|fund|savings|plan|age|goals?|portfolio))|\bi(?:'m| am) a retiree\b|\b(?:retired|retiree) (?:myself|too)\b").to_string(),
        r"\(\s*retired\s*\)|\b(?:since|after|when|now that|until|before) we (?:retired|'re retired|are retired)\b|\A[^\n]{0,60}?[\[(][mf]4[a-z]+[\])][^\n]{0,40}?\bretired\b".to_string(),
        r"\b(?:i'm|im|i am) (?:on|living on|drawing) (?:my |a )?(?:pension|social security|state pension|retirement income)\b|\bi (?:draw|collect|get) (?:my )?(?:pension|social security)\b|\b(?:i'm|im|i am) (?:\d{2}) and retired\b".to_string(),
    ];
    let homemaker = [
        format!(r"\b{I} {ADVERB}(?:an? )?(?:full[- ]?time |proud |happy |exhausted |tired )?(?:stay[- ]at[- ]home (?:mom|mum|dad|parent|wife|mother|father|husband)|sahm|sahd|sahp|homemaker|housewife|")
            + r"househusband|home ?maker|home ?keeper|domestic engineer|work[- ]at[- ]home mom)\b",
        r"(?:^|[.!?\n]\s*)(?:\d{2}\s?[mf]?\s+)?(?:sahm|sahd|stay[- ]at[- ]home (?:mom|mum|dad|parent)|homemaker|housewife)\b|(?:^|[.!?\n]\s*)(?:a |fellow |another )?(?:sahm|sahd|stay[- ]at[- ]home (?:mom|mum|dad|parent)|homemaker|housewife) here\b".to_string(),
        concat!(r"\bas an? (?:sahm|sahd|stay[- ]at[- ]home (?:mom|mum|dad|parent)|",
            r"homemaker|housewife)\b(?=[^.!?\n]{0,60}\b(?:i|my|me)\b)|\bi stay (?:at )?home (?:full[- ]?time )?(?:with|to raise|to take care of) (?:my|the|our) (?:kids|son|daughter|baby|children|toddler|twins|boys|girls)\b|",
            r"\bi (?:quit|left|gave up) (?:my job|work|my career) to (?:stay home|raise|be a (?:sahm|stay at home))\b").to_string(),
    ];
    let unable = [
        format!(r"\b{I} {ADVERB}(?:permanently |medically |totally |partially )?(?:on disability|on ssdi|on ssi|on pip|on esa|on dsp|on odsp|on aish|on pwd|unable to work|too sick to work|too ill to work|")
            + concat!(r"on long[- ]term disability|on ltd|on short[- ]term disability|on medical leave|on sick leave|on workers'? comp|on workman'?s comp|disabled and (?:can't|cannot|unable to) work|",
            r"medically retired|retired on disability|unfit (?:for|to) work)\b"),
        concat!(r"\bi (?:can't|cannot|can no longer|am unable to|couldn't) (?:work|hold (?:down )?a job|keep a job)(?: anymore| any more)? (?:because|due|since|anymore|any more|with|after)\b|",
            r"\bi (?:get|receive|collect|was granted|got approved for|was approved for|finally got|won my|got awarded|was awarded|live on|survive on) (?:my )?(?:ssdi|ssi|disability|pip|esa|",
            r"disability benefits|disability payments|dsp|odsp|aish)\b|\b(?:i was |i got |was |been )?granted (?:ssdi|ssi|disability|pip)\b|\bmy (?:ssdi|ssi|disability|pip|esa|odsp|aish) ",
            r"(?:check|checks|payments?|benefits|income|claim|award|hearing|case|application)\b").to_string(),
    ];
    let student = [
        concat!(r"\b(?:i'm|im|i am) (?:almost |nearly |currently |now )?(?:in )?(?:my )?(?:1st|2nd|3rd|4th|first|second|third|fourth|final|last) year (?:of|in|at)\b(?! (?:high ?school|hs)\b)|\bmy (?:bs|ba|bsc|major|course|courses|uni|thesis|dissertation|lecturer|lectures|semester|finals|coursework|midterms?|syllabus|campus|student id|student visa|transcript|academic advisor|class schedule)\b(?! (?:was|were) (?:great|fun|hard)\b)|",
            r"\b(?:i'?m|i am)(?: currently| still| also| now| actually)? (?:studying|in school|in college|in uni|at uni|at college|at university|in university|back in school|back at school)\b|\bwhile (?:i'm |im |i am )?studying\b|\bi study\b(?! (?:the|it|this|that|them|him|her|how|why|what)\b)").to_string(),
        concat!(r"\b(?:i'm|im|i am|i'm currently|im currently|i am currently) (?:a |an )?(?:(?!(?:former|ex|old|past|of|the|my|his|her|their|to|with|for|and|that|who|not)\b)[\w'-]+ ){0,4}?(?:student|undergrad|undergraduate|freshman|sophomore|fresher|postgrad|uni student|phd student|",
            r"grad student|masters student|med student|law student|nursing student)\b|\bmy (?:semester|finals|midterm|midterms)\b").to_string(),
        r"(?:^|[.!?\n,]\s*)(?:a |an )?(?:\w+ )?student (?:from|at|of|here)\b".to_string(),
        concat!(r"\bas an? (?:(?!(?:former|ex|old|past|of|the|my)\b)[\w'-]+ ){0,3}?student\b(?=[^.!?\n]{0,60}\b(?:i|my|me)\b)|",
            r"\b(?:mein(?:em)? studium|ins studium|im studium|ich studiere|studiere ich|ich bin student(?:in)?|je suis (?:étudiant|étudiante|en (?:licence|master|fac))|soy estudiante|",
            r"sou estudante|estudo (?:na|no|em)|faço faculdade|estoy estudiando|jestem student(?:em|ką)|studiuję|sono (?:uno |una )?(?:studente|studentessa)|ik studeer|ik ben student|",
            r"estoy en la (?:universidad|facultad|uni)|estou na (?:faculdade|universidade|facul)|estudio en|je suis à la fac|je fais (?:une licence|un master|des études))\b").to_string(),
    ];
    let studying = concat!(r"\b\d(?:st|nd|rd|th) sem(?:ester)?\b|\b(?:i'm|im|i am) (?:almost |nearly |currently |now |only )?(?:in |a )?(?:my )?(?:(?:1st|2nd|3rd|4th|5th|first|second|third|fourth|final|last)[- ]year|year [1-5])\b(?! of (?:high school|marriage|work))",
        r"|\b(?:1st|2nd|3rd|4th|first|second|third|final) year (?:electives|student|courses|exams|project)\b|\b(?:i'm|im|i am) (?:currently |also |still |now )?(?:in|at) (?:an? (?:[\w'-]+ ){0,3}?)?(?:college|uni|university)\b",
        r"|\b(?:college|university|uni|undergrad|undergraduate|community college|first[- ]generation college|first[- ]gen(?:eration)? college) student\b(?! (?:loans?|debt|visa|athlete|housing|discount)\b)|\bmy (?:freshman|sophomore|junior|senior|first|second|third|final) (?:year|semester) (?:of|in|at) (?:college|uni|university)\b|\bmy (?:major|lectures?|lecturer|uni|campus|coursework|semester|syllabus|midterms?)\b",
        r"|\b(?:i'm|im|i am) (?:currently )?(?:studying|majoring)\b|\bwhile (?:i'm |im |i am |i )?(?:studying|study)\b|\bi(?:'m| am)? (?:in|doing) (?:the|my) (?:bs|ba|bsc|bachelor'?s?|undergrad) (?:program|degree)\b|\b(?:meu|minha) (?:primeiro|segundo|terceiro|primeira) (?:ano|período|semestre)\b|\bfaço (?:uma )?(?:segunda )?graduação\b|\bich studiere\b|\b\w+ studieren\b|\bestudio (?:en la|en el|una|la)\b|\bje suis (?:étudiant|étudiante|à la fac)\b|\b(?:faço faculdade|estoy en la (?:universidad|facultad)|estou na (?:faculdade|universidade|facul)|jestem student(?:em|ką)|studiuję|sono (?:uno |una )?(?:studente|studentessa)|ik studeer|estoy estudiando|sou estudante|soy estudiante|estudo (?:na|no|em))\b",
        r"|\bi have (?:a |my )?(?:midterm|midterms|final exam|finals) (?:coming up|tomorrow|next week|this week|today)\b|\bmy (?:college|university|uni) (?:classes|courses|professor|campus|dorm|roommate|application)\b|\b(?:mein(?:em)? studium|ins studium|im studium)\b|\bstudent (?:from|at) (?:the )?(?:main campus|\w+ (?:university|college|campus))\b");
    let graduate = r"\b(?:grad|graduate|phd|ph\.d\.?|doctoral|masters?|master's|msc|mba|msw|ma|ms|mfa) (?:student|candidate|program|programme)\b(?! (?:loans?|debt|visa|housing)\b)|\bmy (?:thesis|dissertation|phd|doctorate)\b|\bfinishing (?:my )?(?:grad|graduate|masters?|master's|phd) (?:program|degree)?\b|\bi study an? (?:jd|ma|ms|msc|masters|phd|llm)\b|\bmeiner dissertation\b|\bmi (?:tesis|doctorado|maestría)\b|\b(?:accepted|admitted) (?:in)?to (?:the |a )?(?:\w+ ){0,3}?(?:masters?|master's|phd|graduate|msw|mba|doctoral) program\b";
    const PRO_SCHOOL: &str = r"(?:law|med|medical|dental|vet|veterinary|pharmacy|grad|graduate)";
    let pro_student = format!(r"\b(?:{I}|i'm currently|currently) (?:still |now |also )?(?:in|at|attending|finishing) (?:my (?:\w+ )?(?:year|semester) (?:of|in|at) )?{PRO_SCHOOL} school\b|")
        + &format!(r"\b(?:{I}|as) (?:an? |the )?(?:current |first[- ]year |second[- ]year |third[- ]year |fourth[- ]year |final[- ]year |\d(?:st|nd|rd|th)[- ]year )?{PRO_SCHOOL} student\b|")
        + &format!(r"\bmy (?:\w+ )?(?:year|semester) (?:of|in|at) {PRO_SCHOOL} school\b|\bi (?:go to|attend|started|start) {PRO_SCHOOL} school\b");
    let high_grade = r"\b(?:i'm|im|i am|currently|still) (?:still |currently )?in (?:(?:9th|10th|11th|12th)(?: class| std)?|(?:grade|class) (?:9|10|11|12))\b|\b(?:grade|class|year) (?:9|10|11|12) student\b";
    let high_school = concat!(r"\b(?:i'm|im|i am|just) (?:an? )?(?:[\w-]+ )?(?:high ?schooler|high-schooler|(?:\d+th|seventh|eighth|ninth|tenth|eleventh|twelfth) grader)\b|\b(?:i'm|im|i am) (?:still |currently )?in (?:high ?school|hs|(?:9th|10th|11th|12th) grade|year (?:9|10|11|12))\b|\b(?:high ?school|hs) (?:student|senior|junior|sophomore|freshman)\b|\b(?:i'm|im|i am) (?:currently |still |now )?(?:a )?(?:senior|junior|sophomore|freshman) in (?:high ?school|hs)\b|\bmy (?:high school|highschool) (?:teacher|classes|graduation|exams)\b|",
        r"\b(?:i'm|im|i am) (?:currently |now |still |about to start |entering |starting |going into )?(?:in )?my (?:freshman|sophomore|junior|senior|sr|final|last|first|second|third|fourth|1st|2nd|3rd|4th) year (?:of|in|at) (?:high ?school|hs)\b");
    let college_pattern = concat!(r"\b(?:i'm|im|i am|this|just an?|\d{2}\s?[mf]?,?|[mf]4[a-z]+\]?) (?:(?!(?:former|ex|retired)\b)[\w-]+ ){0,2}?(?:college|uni) (?:boy|girl|guy|dude|bro|kid|twink|jock|athlete|lad|stud|frat)s?\b|\bstudent,? here\b|\bjust an? (?:\w+ )?student\b|",
        r"\b(?:my|next|this) (?:\w+ )?year (?:of|at|in) (?:uni|college|university)\b|\bi (?:take|am taking|'m taking|m taking) (?:\w+ )?(?:classes|courses|units|credits)\b");
    let campus = concat!(r"\bi (?:currently |now |still |also )?(?:go to|attend|am attending|'m attending|transferred to) (?:a |an |the )?(?:[\w'&.-]+ ){0,3}?(?:college|university|uni|community college|polytechnic)\b|",
        r"\b(?!(?:any|a|the|every|no|some)\b)(?:undergrad|undergraduate|fresher|freshman|sophomore|[\w'-]+ (?:major|student)) here\b|",
        r"\bmy (?:college|uni|university|class|course|semester|final[- ]year|capstone|group) (?:project|assignment|exams?|presentation|essay|paper|lectures?)\b|",
        r"\b(?:i'm|im|i am) (?:now |currently |almost |nearly )?(?:in|into|starting) (?:my )?(?:\d(?:st|nd|rd|th)|first|second|third|fourth|fifth|final|last) (?:year|semester|sem) (?:of|in|at) (?:college|uni|university|my degree|my bachelor'?s|undergrad)\b|",
        r"\b(?:i'm|im|i am) (?:about to |almost |nearly |currently |finally )?(?:finishing|graduating from|graduating|done with) (?:college|uni|university|my degree|my bachelor'?s|my undergrad)\b|",
        r"\b(?:\d+|one|two|three|four|a) (?:more )?(?:semesters?|years?|terms?|quarters?) (?:away from|left (?:of|in|until|before)) (?:graduation|graduating|my degree|college|uni)\b|",
        r"\b(?:i'm|im|i am) (?:an? )?(?:[\w'-]+ ){0,2}?major\b(?! (?:issue|problem|concern|fan|reason|part|key|league|player|city|brand|company)\b)");
    let campus_started = concat!(r"\bi(?:'m| am|m)? (?:currently |now |still |also |just |finally |recently |about to )?(?:attending|enrolled in|enrolled at|got into|gotten into|starting|start|going to|heading to|heading into|joining|entering) ",
        r"(?:a |an |the )?(?:[\w'&.-]+ ){0,3}?(?:college|university|uni|community college|polytechnic)\b|",
        r"\b(?:i'm|im|i am) (?:about to graduate from|about to graduate|about to finish) (?:college|uni|university|my degree|my bachelor'?s|my undergrad)\b");
    let any_student = concat!(r"\b(?:i'm|im|i am)(?: currently| still| just| also| now)? (?:an? )?(?:(?!(?:former|ex|old|past|of|the|my|his|her|their|to|with|for|and|that|who|not|high|school|grad|graduate|phd|masters?|master's|doctoral|level)\b|(?:grade|class|year) \d)",
        r"[\w'-]+ ){0,4}?student\b(?! (?:loans?|visa|athlete|housing|discount|of|pilot|nurse|teacher|driver|worker|union)\b)|",
        r"\b(?:already|still) a student\b|",
        r"\bas an? (?:(?!(?:former|ex|old|past|of|the|my|high|school|grad|graduate|phd|masters?|doctoral|level)\b)[\w'-]+ ){0,3}?student\b(?=[^.!?\n]{0,60}\b(?:i|my|me)\b)");
    let undergrad = concat!(r"\b(?:i'm|im|i am)(?: currently| now| just| also| still)? (?:an? )?(?:(?!(?:former|ex|old|past|the|my|not|high|school)\b)[\w-]+ ){0,3}?(?:freshman|sophomore|fresher|freshie|undergrad|undergraduate)\b",
        r"(?! (?:year|class|classes|course|courses|degree|program|programme|in high ?school|at high ?school)\b)|\b(?:i'm|im|i am)(?: currently| now)? (?:an? )?(?:rising |incoming )?(?:junior|senior) (?:in|at) (?:college|uni|university)\b");
    let student_here = r"(?:^|[.!?\n,]\s*)(?:a |an )?(?:college |uni |university )?student here\b";
    let student_line = concat!(r"(?:(?m:^)[ \t>*#\\-]*|,[ \t]*)(?:(?:\d{2}\s?[mf]?|[mf]4[a-z]+|[mf]\s?\d{2}|[\[(][\w /+-]{1,12}[\])])[ \t,|-]*)*+(?:an? )?",
        r"(?:(?!(?:the|this|that|these|those|my|your|his|her|their|our|every|each|any|some|no|one|which|what|why|how|when|is|are|was|were|do|does|did|former|ex|old|future|fellow)\b)[\w'-]+ ){0,3}?",
        r"(?:student|college (?:girl|boy|guy|student|kid))\b(?! (?:loans?|visa|athlete|housing|discount|debt|union|card|id|council|account|accommodation|life|government|body|aid|finance)\b)",
        r"(?=\s*(?:$|[.,!;|(\n-]|\d|\b(?:here|looking|seeking|from|in|at|with|who|and)\b))");
    let student_twins = [studying.to_string(), pro_student.clone(), any_student.to_string(), student_here.to_string(), student_line.to_string()];
    let worklife = [
        r"\b(?:at|after|before|outside of|outside|during) work\b(?! (?:on|out)\b)".to_string(),
        concat!(r"\b(?:walk|walking|walked|commute|commuting|head|heading|headed|late|ride|riding|bike|biking|leave|leaving|left|ready|got|came|come|coming) ",
            r"(?:to|for) work\b(?! (?:on|out|for|with|it|this|that|together|well|better|properly|again)\b)").to_string(),
        concat!(r"\bmy (?:boss|bosses|supervisor|coworkers|co-workers|employer|place of work|line manager|shift|shifts|work schedule|work hours|",
            r"working hours|work day|workday|work week|workweek|work friends|break room|paycheck|paychecks|payslip|pay stub|paystub|work laptop|work phone|work email|work computer|",
            r"work uniform|work clothes|work boots)\b(?! (?:fired|let me go|laid me off)\b)").to_string(),
        concat!(r"\b(?:i|i'm|im|i've|ive)\b[^.!?\n]{0,25}?\b(?:a|long|night|day|double|late|early|morning|evening|closing|opening|graveyard|overnight|\d+ ?(?:hr|hour)|\d+-hour|twelve[- ]hour) shifts?\b|",
            r"\b(?:got|get|getting|coming|came|home) off (?:a |my |the )?(?:\w+ )?shift\b|\bbusy with work\b").to_string(),
    ];
    let self_work = [
        r"\b(?:off|from) work\b",
        r"(?=for work)(?<!looking )(?<!look )(?<!searching )(?<!search )(?<!apply )(?<!applying )(?<!ready )(?<!late )(?<!hunting )\bfor work\b(?! (?:to|that|in|at|on|online)\b)",
        r"\b(?:work|working) (?:full[- ]?time|part[- ]?time|\d+ days a week|\d+ hours a week|\d+ ?hrs a week)\b",
    ];
    let selling = concat!(r"\b(?:i'm |im |i am |i )?(?:selling|sell) (?:my )?(?:[\w-]+ ){0,2}?(?:nudes|pics|pictures|videos|vids|content|premades|pre-mades|pre mades|sex tapes|gfe|customs|sexting)\b|",
        r"\boffering (?:[\w-]+,? ){0,3}?(?:sexting|customs?|content|gfe|video calls|facetime)\b");
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
    rules.push(rule("occupation", &gerund, scoped(mine(occupied(job(after)))), TAGGED));
    for pattern in &named {
        rules.push(rule("occupation", pattern, occupied(job(after)), TAGGED));
    }
    for pattern in &named {
        rules.push(rule("employment_status", pattern, employed(job(after)), TAGGED));
    }
    rules.push(rule("occupation", &cell, occupied(plain(celled)), TAGGED));
    let retired_title = r"(?:(?:^|[.!?\n]\s*)(?:an? |just an? |also an? )?|\b(?:i'm|im|i am|as|being) an? (?:[\w-]+ )?)retired ";
    rules.push(rule("occupation", retired_title, scoped(occupied(plain(retiree))), TAGGED));
    rules.push(rule("occupation", r"\bi(?:'ve| have) (?:also |actually |always |previously )?worked as (?:an? |the )?", scoped(occupied(job(after))), TAGGED));
    rules.push(said("occupation", &tagged_title, occupied(plain(tagged)), &SELF_HEDGE));
    for (index, pattern) in workplace.iter().enumerate() {
        rules.push(rule("occupation", pattern, scoped(lookup(if index == 0 { &FIELD_MAP } else { &PLACE_MAP }, 1)), TAGGED));
    }
    for pattern in &workplace {
        rules.push(rule("employment_status", pattern, scoped(fixed("employed")), TAGGED));
    }
    rules.push(rule("occupation", &working_in, scoped(lookup(&FIELD_MAP, 1)), TAGGED));
    rules.push(rule("occupation", &in_it, scoped(fixed(SOFTWARE)), TAGGED));
    for pattern in &cased_it {
        rules.push(rule("occupation", pattern, scoped(boxed(cased)), TAGGED));
    }
    for pattern in &ownership {
        rules.push(rule("occupation", pattern, scoped(boxed(|m| if eq(m.text(), "my business") { None } else { get(&BUSINESS_MAP, m.group(1)) })), TAGGED));
    }
    for pattern in &ownership {
        rules.push(rule("employment_status", pattern, scoped(fixed(OWNER)), TAGGED));
    }
    for (pattern, value) in &activity {
        rules.push(rule("occupation", pattern, scoped(value()), TAGGED));
    }
    for (pattern, _) in &activity {
        rules.push(rule("employment_status", pattern, scoped(fixed("employed")), TAGGED));
    }
    for (pattern, value) in &role_terms {
        rules.push(rule("occupation", pattern, scoped(value()), TAGGED));
    }
    rules.push(rule("occupation", coding, scoped(fixed(SOFTWARE)), TAGGED));
    rules.push(rule("employment_status", coding, scoped(fixed("employed")), TAGGED));
    for pattern in &employed_patterns {
        rules.push(rule("employment_status", pattern, scoped(fixed("employed")), TAGGED));
    }
    for pattern in &self_employed {
        rules.push(rule("employment_status", pattern, scoped(fixed(OWNER)), TAGGED));
    }
    rules.push(rule("employment_status", &independent, scoped(boxed(|m| title(m.string, m.end(), None, Use::Job).map(|_| OWNER.to_string()))), TAGGED));
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
        r"(?:^|[.!?\n]\s*)(?:(?:\d{2}\s?[mf]|[mf]\s?\d{2})\s+)?(?:still |currently |now )?(?:looking|searching) for (?:a |any )?(?:job|work)\b",
        r"(?:^|[.!?\n]\s*)(?:i've |ive |i have )?been (?:unemployed|out of work|jobless)\b",
        r"\bi(?:'ve| have)? (?:not|never) (?:had a (?:\w+ )?job|been employed)\b|\bi (?:haven't|havent|hadn't|have not|had not) (?:had a (?:\w+ )?job|been employed)\b|\bhaven't had a job\b",
    ];
    for pattern in &jobless {
        rules.push(rule("employment_status", pattern, scoped_with(mine(near(fixed("unemployed"))), if pattern.contains("find") { &CONDITIONAL } else { &SELF_HEDGE }, false), TAGGED));
    }
    for pattern in &jobless_lead {
        rules.push(rule("employment_status", pattern, scoped_with(fixed("unemployed"), &CONDITIONAL, false), TAGGED));
    }
    let job_held = [
        r"\b(?:a|two|2|three|3|one|both) (?:full|part)[- ]?time jobs?\b",
        r"\bi(?:'ve| have) (?:just |recently |finally |now )?(?:started|landed|got|gotten) (?:a |my )?(?:new )?(?:job|position|role)\b(?! (?:hunt|search|application|interview|offer)\b)",
        r"\bi(?:'ve| have) (?:also |now |actually )?worked (?:for|at) (?:the same|this|my current|\d+|over|almost|nearly|about|several|many|two|three|four|five|six|seven|eight|nine|ten)\b|\bi(?:'ve| have) been employed\b",
    ];
    for pattern in &job_held {
        rules.push(rule("employment_status", pattern, scoped(mine(near(fixed("employed")))), TAGGED));
    }
    let persona_status = concat!(r"\b(?:(working from home|wfh|working remotely|working full[- ]?time|working part[- ]?time|full[- ]?time job|part[- ]?time job|working professional)|",
        r"(stay[- ]at[- ]home (?:mom|mum|dad|parent|wife)|sahm|sahd|housewife|homemaker)|(neet(?! (?:pg|ug|exam|exams|prep|preparation|aspirant|aspirants|coaching|score|result|results|paper|mock|syllabus|cutoff))|jobless|unemployed)|(self[- ]employed|freelancer|small business owner|business owner|entrepreneur))\b");
    rules.push(said("employment_status", persona_status, boxed(|m| if !personal(m) { None } else if m.nonempty(1).is_some() { Some("employed".to_string()) } else if m.nonempty(2).is_some() { Some("homemaker".to_string()) } else if m.nonempty(3).is_some() { Some("unemployed".to_string()) } else { Some(OWNER.to_string()) }), &SELF_HEDGE));
    for pattern in &retired {
        rules.push(rule("employment_status", pattern, scoped(fixed("retired")), TAGGED));
    }
    for pattern in &homemaker {
        rules.push(rule("employment_status", pattern, scoped(fixed("homemaker")), TAGGED));
    }
    for pattern in &unable {
        rules.push(rule("employment_status", pattern, scoped_with(fixed("unable to work"), &CONDITIONAL, false), TAGGED));
    }
    for pattern in student.iter().chain(student_twins.iter()) {
        rules.push(rule("employment_status", pattern, scoped(fixed("student")), TAGGED));
    }
    rules.push(rule("employment_status", campus, scoped(fixed("student")), self_hedge));
    for pattern in &worklife {
        rules.push(rule("employment_status", pattern, scoped(mine(fixed("employed"))), TAGGED));
    }
    for pattern in &self_work {
        rules.push(rule("employment_status", pattern, scoped(mine(near(fixed("employed")))), TAGGED));
    }
    rules.push(rule("employment_status", selling, scoped_with(fixed(OWNER), &SELF_HEDGE, true), TAGGED));
    rules.push(rule("occupation", selling, scoped_with(fixed(ADULT), &SELF_HEDGE, true), TAGGED));
    for pattern in &owners {
        rules.push(rule("employment_status", pattern, scoped(fixed(OWNER)), TAGGED));
    }
    rules.push(rule("education", college_item, scoped(boxed(college)), TAGGED));

    let degree_in_pattern = concat!(r"\b(bachelor's|bachelors|master's|masters|phd|ph\.d|bsc|msc|b\.s|m\.s|ba|bs|ma|ms|mba|bfa|mfa|llb|jd|md|btech|b\.tech|mtech|m\.tech|bcom|b\.com|bba|bsn|msn|",
        r"meng|beng)\.? (?:degree |hons |honours |honors )?(?:in|of) ([a-z]+(?: [a-z]+)?)");
    let pursuing = concat!(r"\b(?:i'm|im|i am|i'm currently|im currently|i am currently|currently) (?:still |now |also )?(?:doing|pursuing|finishing|completing|working on|working towards|in the middle of|halfway through) (?:up )?",
        r"(?:a |an |my )(?:(?!(?:the|a|an|my|and|or|first|second|new)\b)[\w-]+ ){0,2}?(?:(masters?|master's|phd|ph\.d|doctorate|msc|mba|msw|mfa|ma|ms|grad school)|(bachelor'?s|bachelors|undergrad|undergraduate degree|degree|bsc|ba|bs|bba|bcom|btech))\b");
    let sh: &'static Re = &SELF_HEDGE;
    rules.push(said("education", degree_in_pattern, boxed(degree_in), sh));
    rules.push(said("education", pursuing, boxed(|m| Some(if m.nonempty(1).is_some() { "graduate student" } else { "college student" }.to_string())), sh));
    rules.push(said("education", studying, fixed("college student"), sh));
    rules.push(said("education", college_pattern, fixed("college student"), sh));
    rules.push(said("education", undergrad, fixed("college student"), sh));
    rules.push(rule("education", campus, scoped(fixed("college student")), self_hedge));
    rules.push(rule("education", campus_started, scoped(fixed("college student")), self_hedge));
    rules.push(said("education", &student[0], fixed("college student"), sh));
    rules.push(said("education", r"\b(?:my|a) (?:master'?s|masters|master|msc|mba) (?:thesis|dissertation|gpa|coursework)\b|\bfinishing (?:a|my) (?:master'?s|masters)\b|\bi did my (?:ms|msc|ma|mba|masters|master's)\b", fixed("master's degree"), sh));
    rules.push(said("education", r"\b(?:i'm|im|i am) (?:still |currently |now )?(?:finishing|in|attending) (?:high ?school|class 1[012](?:th)?|1[012]th class|class (?:xi|xii))\b|\ban? a[- ]levels? student\b", fixed("high school student"), sh));
    rules.push(said("education", any_student, boxed(|m| if LEVELLESS.test(m.text()) { None } else { Some("college student".to_string()) }), sh));
    rules.push(said("education", student_here, fixed("college student"), sh));
    rules.push(said("education", student_line, boxed(leveled), sh));
    rules.push(said("education", r"\b(?:i'm|im|i am|as|just finished|finished|i was|during|after|since) (?:an? |my )?[123]l\b", fixed("professional degree such as law or medicine"), sh));
    rules.push(said("education", graduate, fixed("graduate student"), sh));
    rules.push(said("education", &pro_student, fixed("graduate student"), sh));
    rules.push(said("education", r"\bmy residency\b|\b(?:i'm|im|i am) (?:in|doing|finishing|starting) (?:my )?residency\b", fixed("professional degree such as law or medicine"), sh));
    rules.push(said("education", &format!(r"\b(?:i have|i've got|i got|i hold|i earned|i finished|i completed|i just finished|i just completed|i recently finished|i recently completed|i finally finished|i've done|i have done|i did|i've gotten|ive gotten|i have gotten|i obtained|i received|i've earned|i've completed|i've finished|got|just got|have|with) (?:a |an |my |both |two )?(?:({long_degree_names})(?: degree| degrees| hons| in| from)?|({short_degree_names}) (?:degree|degrees|in|from))\b(?! (?:student|program|programme|candidate|course|class)\b)|\b({long_degree_names}) hons\b"),
        boxed(|m| if m.text().first() == Some(&'i') || owned(m.string, m.start(), 50) { get(&DEGREE_MAP, m.first()) } else { None }), sh));
    rules.push(said("education", concat!(r"\b(?:i have|i've got|i hold|i earned|i got|i completed|i finished|i do have|i also have) (?:a |an |my |both |two )?",
        r"(?:(?!(?:associate'?s?|masters?|master's|phd|doctoral|online|honorary|useless|worthless|second|new)\b)[\w'-]+ ){0,3}?degrees?\b(?! (?:program|programme|course|apprenticeship)\b)|\b(?:college|university|uni)[- ]educated\b"),
        fixed("bachelor's degree"), sh));
    rules.push(rule("education", &format!(r"(?:^|\n)[^\w\n]*(?:education|degree|qualifications?|highest degree)[^\w\n]{{0,4}}?[:=][^\w\n]*(?:an? )?({long_degree_names}|{short_degree_names})\b"), lookup(&DEGREE_MAP, 1), self_hedge));
    rules.push(said("education", r"\b(?:masters?|master's)[- ]educated\b", fixed("master's degree"), sh));
    rules.push(needs(said("education", r"\b(?:i (?:graduated|have graduated|just graduated|recently graduated|finally graduated|just finished|recently finished|finished)|(?:^|[.!?\n]\s*)(?:just |recently |finally )?(?:graduated|finished)|(?:since|after|when|once) (?:i )?graduat(?:ed|ing)) (?:from )?(?:college|university|uni|undergrad|with (?:a|my|honors))\b|\b(?:college|university) graduate\b|\b(?:as an? |i'm an? |im an? |i am an? )(?!(?:\w+ )?high ?school)(?:\w+ ){0,3}?(?:graduate|grad)\b(?! (?:student|program|school)\b)|\b\w+ (?:and \w+ )?grad\b(?= (?:having|here|with|who|and|looking)\b)|\bme formei\b|\bi went back to school for\b|\bmy (?:bachelor'?s|bachelors|undergrad|degree) (?:is|was) in\b",
        fixed("bachelor's degree"), sh), &["grad", "finished", "formei", "went back to school", "bachelor", "undergrad", "degree"]));
    rules.push(said("education", r"\b(?:i )?(?:graduated|finished) (?:from )?high ?school\b|\bhigh ?school (?:graduate|diploma)\b|\bcompleted (?:my )?12th\b|\bpassed (?:my )?12th\b|\bi have (?:a|my) ged\b", fixed("high school diploma"), sh));
    rules.push(said("education", high_school, fixed("high school student"), sh));
    rules.push(said("education", high_grade, fixed("high school student"), sh));
    let persona_school = r"\b(?:(college) (?:boy|girl|guy|dude|bro|kid|twink|jock|athlete|lad|stud|nerd|bwc|chick|babe|cutie|student|man)s?|high ?schoolers?|high-schoolers?)\b";
    let school_student = r"\b(?:i'm|im|i am) an? school (?:student|boy|girl|kid)\b";
    let grad_school = r"\b(?:i'm|im|i am|currently|now|i'm currently|i'm back|i am back|i'm now) (?:in|at|attending|starting) grad(?:uate)? school\b|\b(?:moving|moved|relocating|going back|back|here|starting|start) (?:[\w-]+ ){0,4}?(?:for|to) grad(?:uate)? school\b";
    rules.push(said("education", persona_school, boxed(|m| if personal(m) { Some(if m.nonempty(1).is_some() { "college student" } else { "high school student" }.to_string()) } else { None }), sh));
    rules.push(said("education", school_student, fixed("high school student"), sh));
    rules.push(said("education", grad_school, mine(near(fixed("graduate student"))), sh));
    rules.push(said("education", r"\b(?:a|an|my) (master'?s|masters|bachelor'?s|bachelors|doctorate|phd|associate'?s) degree\b", boxed(|m| if (owned(m.string, m.start(), 50) || personal(m)) && !ASPIRING.test_in(m.string, clause(m.string, m.start()), m.start()) { get(&DEGREE_MAP, m.group(1)) } else { None }), sh));
    rules.push(said("education", r"(?:^|[.!?\n]\s*)(?:\d{2}\s?[mf]\s+)?(?:a )?(?:fresh|recent|new) (?:college )?grad(?:uate)? here\b", fixed("bachelor's degree"), sh));
    rules.push(said("education", r"\bi dropped out of (?:college|uni|university)\b|\bi have some college\b|\bi never finished (?:college|my degree)\b|\btransferred (?:to \w+ )?from a community college\b|\bput myself back in college\b|\bacademic(?:ally)? (?:dismissed|suspended|probation)\b", fixed("some college, no degree"), &UNLESS));
    rules.push(said("education", r"\bi dropped out of high ?school\b|\bi never finished high ?school\b|\bi didn't finish high ?school\b", fixed("no high school diploma"), &UNLESS));
    rules.push(said("education", r"\bi (?:have|got|earned) (?:an? )?associate'?s(?: degree)?\b|\bi went to (?:a )?trade school\b|\bi(?:'m| am) a (?:journeyman|licensed electrician|licensed plumber)\b", fixed("trade school or associate degree"), sh));

    rules.push(said("employment_status", pursuing, fixed("student"), sh));
    rules.push(said("employment_status", graduate, fixed("student"), sh));
    rules.push(said("employment_status", high_school, fixed("student"), sh));

    let subject_line = r"(?:(?m:^)\W*|[,|][ \t]*)(?:(?:\d{2}\s?[mf]?|[mf]4[a-z]+|[mf]\s?\d{2}|[\[(][\w /+-]{1,12}[\])])[ \t,|-]*)*+(?:an? )?([\w'-]+(?: [\w'-]+){0,3}?) (?:student|major)\b";
    let studying_subject = format!(r"(?:^|[.,;!\n]\s*[-*•]?\s*|\b(?:and|student|college|uni|university) )(?:currently |also |still |now )?(?:studying|majoring in) ({subject_names})\b");
    let hedge = hedge();
    rules.push(rule("field_of_study", &studying_subject, lookup(&SUBJECTS, 1), hedge));
    rules.push(rule("field_of_study", &(format!(r"\bmy (?:\w+ )?({subject_names}) (?:class|classes|course|courses|module|modules|lab|labs|lecture|lectures|lecturer|professor|professors|prof|exam|exams|")
        + &format!(r"final|finals|midterm|midterms|coursework|assignment|assignments|thesis|dissertation|program|programme|department|dept|cohort|classmates|seminar|studies)\b|")
        + &format!(r"\bmy (?:thesis|dissertation|capstone|research|phd|ph\.d|masters|master's) (?:is |was )?(?:on|about|in) (?:the )?({subject_names})\b|")
        + &format!(r"\b(?:i'm|im|i am) (?:currently |also )?(?:taking|in|doing) (?:a |an |my |two |some )?({subject_names}) (?:class|classes|course|courses|module|modules|degree|program|programme)\b")),
        boxed(|m| get(&SUBJECTS, m.first())), self_hedge));
    rules.push(rule("field_of_study", &(format!(r"(?:\bi(?:'m| am|m)? (?:currently |now |also |still |actually )?|\bcurrently )(?:study|studied|studying|majored in|major in|majoring in|have a degree in|got my degree in|")
        + &format!(r"have a (?:bachelor'?s|bachelors|master'?s|masters|phd|ba|bs|bsc|ms|msc) in|graduated in|did my degree in)\s+({subject_names})\b")), lookup(&SUBJECTS, 1), hedge));
    rules.push(rule("field_of_study", &format!(r"\b{I} (?:a |an )?(?:(?:first|second|third|fourth|final|\d(?:st|nd|rd|th))[- ]year )?({subject_names}) (?:major|student|graduate|grad|undergrad|undergraduate)\b|\bmy ({subject_names}) (?:degree|major)\b"),
        boxed(|m| get(&SUBJECTS, m.nonempty(1).or(m.group(2)))), hedge));
    rules.push(rule("field_of_study", &format!(r"\b(?:a|an|my) ({subject_names}) (?:degree|diploma|bachelor'?s|bachelors|masters?|master's|phd|major)\b"),
        boxed(|m| if starts_at(m.text(), 0, "my") || owned(m.string, m.start(), 50) { get(&SUBJECTS, m.group(1)) } else { None }), self_hedge));
    rules.push(rule("field_of_study", r"\b(?:student|major|grad) here\b", boxed(|m| subject_before(m.string, m.start())), self_hedge));
    rules.push(rule("field_of_study", student_line, scoped(boxed(|m| match rfind(m.text(), "student", m.text().len()) {
        Some(k) if k > 0 => subject_before(m.string, m.start() + k),
        _ => None,
    })), TAGGED));
    rules.push(rule("field_of_study", subject_line, lookup(&SUBJECTS, 1), self_hedge));
    rules.push(rule("field_of_study", &format!(r"\b(?:degree|degrees|bachelors?|bachelor's|masters?|master's|phd|bsc|ba|bs|ms|msc|ma|major|majoring|majored|graduate|student|year|diploma|course|studies|studying|study|studied|undergrad|undergraduate|graduation|schooling|background)(?: is| was)? in (?:(?!(?:the|a|an|my|this|that|their|his|her|which|what)b)[a-z]+ )??({degree_subject_names})\b"),
        lookup(&DEGREE_SUBJECTS, 1), self_hedge));
    rules.push(rule("field_of_study", &format!(r"\bi(?:'m| am|m)? (?:currently |now |also |still )?(?:going (?:back )?to|go to|in|back in|attending) (?:school|college|uni|university|grad school) for ({subject_names})\b"), lookup(&SUBJECTS, 1), self_hedge));
    rules.push(rule("field_of_study", &format!(r"\b(?:as an? |i'm an? |im an? |i am an? )(?:[\w-]+ ){{0,2}}({subject_names}) (?:graduate|grad|student|major)\b"), lookup(&SUBJECTS, 1), self_hedge));
    rules.push(rule("field_of_study", concat!(r"\b(law|med|medical|pharmacy|nursing|dental|vet|veterinary|engineering|business|art|film|architecture|b) (?:school|college)\b|\b(?:i'm|im|i am|i was|as) (?:a |an )?[123](l)\b|",
        r"\b(?:my|in|doing|finishing|starting|out of) (?:my )?(residency)\b"), boxed(|m| if owned(m.string, m.start(), 60) { get(&SCHOOL_MAP, m.first()) } else { None }), self_hedge));
    rules.push(needs(rule("field_of_study", concat!(r"\b(?:estudante|estudiante|étudiante?|studente(?:ssa)?|studentin?|student) (?:de |d'|di |en |der )(?:la |el |a |o )?(\w+)|\b(?:faço|estudo|estudio|curso|cursando|studiere|studio|j'étudie|étudie|studeer) ",
        r"(?:de |la |el |a |o |in )?(\w+)|\b(?:facoltà|faculdade|facultad|faculté|fakultät) (?:di |de |d'|für )(?:la |el |a |o )?(\w+)|\b(\w+) (?:zu )?studieren\b"),
        boxed(|m| get(&FOREIGN_SUBJECT_MAP, m.first())), self_hedge), &["estud", "étud", "studen", "studi", "studeer", "faço", "curs", "facolt", "faculdade", "facultad", "faculté", "fakultät"]));
    rules.push(rule("field_of_study", &occupation[0], field(after), TAGGED));
    rules.push(rule("field_of_study", &occupation[1], field(after), TAGGED));
    rules.push(rule("field_of_study", &occupation[3], field(after), TAGGED));
    rules.push(rule("field_of_study", &opener_pattern, field(opener), TAGGED));
    rules.push(rule("field_of_study", &format!(r"\b(?:have|got|hold|earned|finished|completed|did|doing|pursuing|my|an?) (?:an? |my )?({degree_field_names})\b|\b({degree_field_names}) (?:student|graduate|grad|holder|hons)\b"),
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
    rules.push(said("field_of_study", &degree_subject, boxed(|m| if anchored(m.string, m.start()) { get(&SUBJECTS, m.group(1)) } else { None }), sh));
    rules.push(said("field_of_study", &doing_subject, boxed(|m| subject(m, &AMBIGUOUS)), sh));
    rules.push(said("field_of_study", &major_is, boxed(|m| subject(m, &NO_SUBJECTS)), sh));

    let amount = concat!(r"(?:about |around |roughly |over |like |~|almost |just under |just over |close to |nearly |an? |approximately |approx |more than |barely |only |just |(?:a bit|a little|slightly) (?:over|under|more than|less than) |just shy of |upwards of |north of )?",
        r"\$?(\d[\d,]*(?:\.\d+)?)\s*(k|thousand|grand|mil|million)?(?:\s*(?:-|–|to)\s*\$?\d[\d,]*(?:\.\d+)?\s*(k|thousand|grand|mil|million)?)?",
        r"\s*(?:(?:usd|cad|aud|eur|gbp|dollars|pounds|euros)\s*)?(?:(?:a|per|/|an?|each)\s*(year|yr|annum|month|mo|hour|hr|week|wk)\b|(annually|yearly|monthly|hourly|weekly)\b|",
        r"(?=\s*(?:$|[.,!;)+]|before|after|pre|post|gross|net|base|salary|total|tc|as|currently|now|right now|working|plus|and|but|so|with|which)))");
    let paid = concat!(r"(?:\b(?:i|me) (?:currently |now |only |just |still )?(?:make|made|earn|earned|bring in|bring home|gross|grossed|net|netted|take home|clear|cleared|pull|pulled|pull in|get paid|got paid|passed|hit|crossed|topped)|",
        r"\b(?:i'm|im|i am) (?:currently |now |only |just |still )?(?:making|earning|paid|getting paid|bringing in|bringing home|pulling in|clearing|netting|grossing|taking home|(?:on|at)(?=\s+(?:about |around |like |~)?\$|\s+\d[\d,.]*\s*k\b))|\bmy (?:salary|income|pay|base|base salary|base pay|tc|total comp|total compensation|",
        r"take home|take-home|take home pay|comp|annual salary|gross income|net income|household income|paycheck|wage|hourly rate|rate) (?:is|was|went up to|of|:|=|is now|just hit|is around|is about|is like))");
    let income_patterns = [
        format!(r"{paid}\s+{amount}"),
        format!(r"(?:^|[.!?\n]\s*)(?:passed|cleared|hit|crossed|made|make|earn|earning|making|grossed|netted|took home|take home)\s+{amount}"),
    ];
    let earning_pattern = format!(r"\b(?<!from )(?:making|earning|earn|make|bringing in|pulling in|clearing)\s+{amount}");
    let six_figures = format!(r"{paid}\s+(?:(?:about|around|over|almost|nearly|just over|just under|close to|low|solid|a) )?(?:six|6)[- ]figures?\b(?! (?:range|total|net worth|in debt))|")
        + r"\bi(?:'ve| have)? (?:just |finally |recently |now )?(?:got|have|landed|make|earn) (?:a |my )(?:\w+ )?(?:six|6)[- ]figure (?:salary|income|job)\b";
    for pattern in &income_patterns {
        rules.push(rule("income", pattern, boxed(|m| income(m, false)), self_hedge));
    }
    rules.push(rule("income", &six_figures, fixed("100000"), self_hedge));
    rules.push(said("income", &earning_pattern, boxed(earning), sh));
    for pattern in &income_patterns {
        rules.push(rule("employment_status", pattern, boxed(|m| income(m, true).map(|_| "employed".to_string())), self_hedge));
    }
    let term = r"\b(?:this|next) (?:semester|quarter|sem)\b|\bcurrently (?:studying|pursuing|enrolled|doing (?:my|a|an) (?:degree|bachelor'?s|masters?|master's|bsc|ba|bs|btech|undergrad))\b";
    rules.push(said("employment_status", term, near(fixed("student")), sh));
    rules.push(said("education", term, near(fixed("college student")), sh));

    let it_anchors: &[&str] = &["in it", "in the it", "in corporate it", "in enterprise it"];
    let retire: &[&str] = &["retire"];
    let working: &[&str] = &["working"];
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
        (role_terms[0].0.as_str(), &["patient"]),
        (role_terms[1].0.as_str(), &["student"]),
        (got_job, &["the job"]),
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
        (working_lines[0].as_str(), working),
        (working_lines[1].as_str(), working),
    ];
    gates(&mut rules, &gate_table);
    rules
}
