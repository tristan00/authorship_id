use crate::relationship::SOLO_AD;
use crate::shared::*;
use claimcore::*;
use std::collections::HashSet;
use std::sync::LazyLock;

const AKC_BREEDS: &[&str] = &[
    "affenpinscher", "afghan hound", "airedale terrier", "akita", "alaskan klee kai", "alaskan malamute", "american bulldog", "american english coonhound", "american eskimo dog", "american foxhound", "american hairless terrier",
    "american leopard hound", "american staffordshire terrier", "american water spaniel", "anatolian shepherd dog", "appenzeller sennenhund", "australian cattle dog", "australian kelpie", "australian shepherd",
    "australian stumpy tail cattle dog", "australian terrier", "azawakh", "barbado da terceira", "barbet", "basenji", "basset fauve de bretagne", "basset hound", "bavarian mountain scent hound", "beagle", "bearded collie",
    "beauceron", "bedlington terrier", "belgian laekenois", "belgian malinois", "belgian sheepdog", "belgian tervuren", "bergamasco sheepdog", "berger picard", "bernese mountain dog", "bichon frise", "biewer terrier",
    "black and tan coonhound", "black russian terrier", "bloodhound", "blue picardy spaniel", "bluetick coonhound", "boerboel", "bohemian shepherd", "bolognese", "border collie", "border terrier", "borzoi", "boston terrier",
    "bouvier des ardennes", "bouvier des flandres", "boxer", "boykin spaniel", "bracco italiano", "braque du bourbonnais", "braque francais pyrenean", "braque saint-germain", "brazilian terrier", "briard", "brittany", "broholmer",
    "brussels griffon", "bull terrier", "bulldog", "bullmastiff", "cairn terrier", "calupoh", "canaan dog", "canadian eskimo dog", "cane corso", "cardigan welsh corgi", "carolina dog", "catahoula leopard dog",
    "caucasian shepherd dog", "cavalier king charles spaniel", "central asian shepherd dog", "cesky terrier", "chesapeake bay retriever", "chihuahua", "chinese crested", "chinese shar-pei", "chinook", "chow chow",
    "cirneco dell etna", "clumber spaniel", "cocker spaniel", "collie", "coton de tulear", "croatian sheepdog", "curly-coated retriever", "czechoslovakian vlciak", "dachshund", "dalmatian", "dandie dinmont terrier",
    "danish-swedish farmdog", "deutscher wachtelhund", "doberman pinscher", "dogo argentino", "dogue de bordeaux", "drentsche patrijshond", "drever", "dutch shepherd", "english cocker spaniel", "english foxhound", "english setter",
    "english springer spaniel", "english toy spaniel", "entlebucher mountain dog", "estrela mountain dog", "eurasier", "field spaniel", "finnish lapphund", "finnish spitz", "flat-coated retriever", "french bulldog",
    "french spaniel", "german longhaired pointer", "german pinscher", "german shepherd dog", "german shorthaired pointer", "german spitz", "german wirehaired pointer", "giant schnauzer", "glen of imaal terrier",
    "golden retriever", "gordon setter", "grand basset griffon vendéen", "great dane", "great pyrenees", "greater swiss mountain dog", "greyhound", "hamiltonstovare", "hanoverian scenthound", "harrier", "havanese",
    "hokkaido", "hovawart", "ibizan hound", "icelandic sheepdog", "irish red and white setter", "irish setter", "irish terrier", "irish water spaniel", "irish wolfhound", "italian greyhound", "jagdterrier",
    "japanese akitainu", "japanese chin", "japanese spitz", "japanese terrier", "kai ken", "karelian bear dog", "keeshond", "kerry blue terrier", "kishu ken", "komondor", "korean jindo dog", "kromfohrlander", "kuvasz",
    "labrador retriever", "lagotto romagnolo", "lakeland terrier", "lancashire heeler", "lapponian herder", "large munsterlander", "leonberger", "lhasa apso", "löwchen", "lucas terrier", "maltese",
    "manchester terrier (standard)", "manchester terrier (toy)", "mastiff", "miniature american shepherd", "miniature bull terrier", "miniature pinscher", "miniature schnauzer", "mountain cur", "mudi", "neapolitan mastiff",
    "nederlandse kooikerhondje", "nenets laika", "newfoundland", "norfolk terrier", "norrbottenspets", "norwegian buhund", "norwegian elkhound", "norwegian lundehund", "norwich terrier", "nova scotia duck tolling retriever",
    "old danish pointer", "old english sheepdog", "otterhound", "papillon", "parson russell terrier", "pekingese", "pembroke welsh corgi", "peruvian inca orchid", "petit basset griffon vendéen", "pharaoh hound", "plott hound",
    "pointer", "polish lowland sheepdog", "pomeranian", "pont-audemer spaniel", "poodle (miniature)", "poodle (standard)", "poodle (toy)", "porcelaine", "portuguese podengo", "portuguese podengo pequeno", "portuguese pointer",
    "portuguese sheepdog", "portuguese water dog", "presa canario", "pudelpointer", "pug", "puli", "pumi", "pyrenean mastiff", "pyrenean shepherd", "rafeiro do alentejo", "rat terrier", "redbone coonhound",
    "rhodesian ridgeback", "romanian carpathian shepherd", "romanian mioritic shepherd dog", "rottweiler", "russell terrier", "russian toy", "russian tsvetnaya bolonka", "saarloos wolfhond", "saint bernard", "saluki", "samoyed",
    "schapendoes", "schipperke", "scottish deerhound", "scottish terrier", "sealyham terrier", "segugio italiano", "shetland sheepdog", "shiba inu", "shih tzu", "shikoku ken", "siberian husky", "silken windhound",
    "silky terrier", "skye terrier", "sloughi", "slovakian wirehaired pointer", "slovensky cuvac", "slovensky kopov", "small munsterlander", "smooth fox terrier", "soft coated wheaten terrier", "spanish mastiff",
    "spanish water dog", "spinone italiano", "stabyhoun", "staffordshire bull terrier", "standard schnauzer", "sussex spaniel", "swedish lapphund", "swedish vallhund", "taiwan dog", "teddy roosevelt terrier", "thai bangkaew",
    "thai ridgeback", "tibetan mastiff", "tibetan spaniel", "tibetan terrier", "tornjak", "tosa", "toy fox terrier", "transylvanian hound", "treeing tennessee brindle", "treeing walker coonhound", "vizsla", "volpino italiano",
    "weimaraner", "welsh springer spaniel", "welsh terrier", "west highland white terrier", "wetterhoun", "whippet", "wire fox terrier", "wirehaired pointing griffon", "wirehaired vizsla", "working kelpie", "xoloitzcuintli",
    "yakutian laika", "yorkshire terrier",
];
const COAT_PATTERNS: &[&str] = &[
    r"(?:mackerel |classic |blotched |spotted |ticked )?tabby", "tabbies", r"tortoiseshells?", r"torties?", r"torbies?", r"calicos?", r"tuxedos?", r"bicolou?rs?", r"vans?", r"harlequins?",
    r"colou?rpoints?", r"smokes?", r"shaded", r"chinchillas?", r"solids?",
];
const OTHER: &str = concat!(
    r"(?:hamsters?|gerbils?|guinea pigs?|rabbits?|bunny|bunnies|ferrets?|parrots?|budgies?|cockatiels?|cockatoos?|parakeets?|conures?|lovebirds?|macaws?|birds?|chickens?|hens|ducks?|goats?|horses?|pony|ponies|ball pythons?|corn snakes?|pet snakes?|snakes?|shrimps?|rodents?|",
    r"geckos?|lizards?|bearded dragons?|beardies?|iguanas?|tortoises?|turtles?|fish|betta|bettas|goldfish|axolotls?|hedgehogs?|tarantulas?|chinchillas?|degus?|pet rats?|rats|mini pigs?|pet pigs?|alpacas?|llamas?|donkeys?|aquarium|fish tank)"
);
const OWN: &str = concat!(
    r"\b(?:my|our) (?:(?!(?:friends|parents|moms|dads|mums|neighbors|neighbours|brothers|sisters|sons|daughters|boyfriends|girlfriends|bfs|gfs|cousins|grandmas|grandparents|roommates|aunts|uncles|exs|exes|kids|bosses|",
    r"husbands|wifes|future|dream|next|favorite|favourite|fave|hello|reply|neighbor|neighbour|friend|sister|brother|family|families|childhood|late|previous|former|deceased|departed|first|last|the|a|an|and|but|or|so|after|before|of|to|in|on|at|for|with|from|by|about|like|than|as|that|this|these|those|which|who|where|when|while|if|is|was|are|were|be|been|am|has|had|have|do|does|did|i|you|he|she|it|we|they|me|him|her|us|them|not|no)\b)[a-z\d-]+ ){0,4}"
);
const HAVE: &str = r"(?:i(?<=\bi)|we(?<=\bwe))(?: (?:also |both |still |do |currently |now |already )?(?:have|got|own|adopted|rescued|recently adopted|just adopted|just got|bought myself|got myself|just bought)|'ve (?:also |still )?got) (?:a |an |two |three |four |\d+ )?(?:(?!(?:to|seen|been|heard|watched|met|noticed|found|called|named|the|this|that|these|those|of|for|with|from|in|on|at|by|about|like|no|not|never|ever|always|is|was|are|were|and|or|but|my|your|his|her|their|our)\b)[a-z\d-]+ ){0,2}";
const NOT_DWELLING: &str = r"(?! (?:music|party|parties|rules|of|plants?|cat|guest|wine|band|special|keys?|key|country|town|city|state|office|page|screen|base|team|game|gym|network|router|server|assistant|lab|workout|cooked|made|school|schooling|planet|world|island|province|club|ground|turf|button|feed|depot|address|phone|internet|wifi|life|health|care|nurse|visits?|remedies|remedy|console|computer|pc|theater|theatre)\b)";

static WORDNET_DOGS: LazyLock<HashSet<String>> = LazyLock::new(|| data_file("wordnet_dogs.txt").lines().map(str::to_string).collect());
regex!(BREED_SUFFIX, r" \(.*\)| dog$");
regex!(FELINE, r"\bcats?\b|\bkitten|meow|litter|purr|feline|\bvet\b|catnip|scratching post|\bfur\b|indoor|outdoor|feral|adopt|rescue");
regex!(CANINE, r"\b(?:dogs?|pups?|puppy|puppies|vet|walks?|walked|walking|leash|bark\w*|fetch|kibble|breed|breeder|groomer|crate|treats?|paws?|fur|tail|neutered|spayed)\b");
regex!(GENERIC_DOG, r"(?:dogs?|pups?|puppy|puppies|doggos?|pupper|doggy|doggie|pooch|mutt)$");
regex!(MOURNED, r"\b(?:lost|losing|death of|passing of|loss of|rip|buried|bury|in memory of|used to|grew up|growing up|childhood)\b");
regex!(DIED, r"(?:'s)?\s*(?:\w+ ){0,3}(?:passed|died|die|was put down|was put to sleep|crossed the rainbow bridge|is gone)\b");
regex!(GAME, r"\b(?:game|games|gaming|gameplay|played|playing|playthrough|quests?|npcs?|server|mods?|dlc|console|ps4|ps5|xbox|steam|nintendo|minecraft|sims|stardew|terraria|valheim)\b");
regex!(CAT_WORD, r"cats?|kittens?|catto|kitteh|kitty|kitties");
regex!(FOREIGN_CAT, r"gat|chat|kat|poes|kot|ked|pusa");
regex!(OWNING, r"\b(?:mortgage|bought|buy|own|owned|paid|renovat\w*|remodel\w*|contractor|roof|hoa|property|selling|sell|sold|equity|yard|garage|basement|insurance|apprais\w*|built|build|attic|foundation|plumb\w*|furnace|hvac|siding|gutters?|lawn|deck|porch|driveway|landscap\w*)\b");
regex!(RENTING, r"\b(?:rent|rents|rented|renting|landlord|landlady|lease|leasing|tenant|tenants|tenancy|security deposit|sublet\w*|letting agent|property manager|leasing office)\b");
regex!(RENT_OUT, r"\brent(?:s|ed|ing)? (?:it |them |\w+ )?out\b|\b(?:my|our) tenants?\b");
regex!(OTHER_PEOPLE, r"\b(?:he|she|they|his|her|their|them|him|people|someone|anyone|everyone|you|your|op)\b");
regex!(MAYBE, r"\b(?:would|wish|if|could|might|should|maybe)\b");
regex!(SPEAKER_WORD, r"\b(?:i|i'm|im|i've|me|my)\b");
regex!(SOLO_HEAD, SOLO_AD);
regex!(PARENTS, r"\b(?:parents?|folks|mom|dad|mum|mother|father|at home)\b");
regex!(MATES, r"\b(?:roommates?|roomates?|room mates?|flatmates?|housemates?|roomies?|friends?|wg)\b");
regex!(PARTNER, r"\b(?:wife|husband|hubby|partner|girlfriend|boyfriend|gf|bf|so|fianc\w*|spouse|man|together)\b");
regex!(ALONE, r"\b(?:alone|solo|by myself|on my own)\b");
regex!(IN_LAWS, r"\b(?:in-?laws|mil|fil|(?:mother|father)[- ]in[- ]law)\b");
regex!(CHILDREN, r"\b(?:kids|children|sons?|daughters?)\b");
regex!(RELATIVES, r"\b(?:sisters?|brothers?|siblings?|cousins?|aunt|uncle|relatives)\b");
regex!(PAID_OFF, r"\bpaid (?:off|for|in full)\b|\bmortgage[- ]free\b");
regex!(KIN_SUBJECT, r"\b(?:my|our) (?:sister|brother|mom|dad|mum|mother|father|friend|parents|son|daughter|aunt|uncle|cousin|neighbou?r|boss|ex)\b");
regex!(OWNED, r"\b(?:mortgage|renovat\w*|remodel\w*|hoa|property tax(?:es)?|equity|apprais\w*|refinanc\w*|paid off|for sale|on the market|homeowners? insurance|closing costs?)\b");
regex!(BYGONE, r"\b(?:in college|college days|at the time|back then|used to|years ago|when i was|freshman|sophomore|in (?:high school|uni|university)|damals|growing up)\b");
regex!(VEHICLE,r"\b(?:car|cars|vehicle|truck|ev|tesla|auto|mileage|miles|bmw|honda|toyota|lease deal|lease payment)\b");

fn breeds() -> String {
    let mut names: Vec<String> = AKC_BREEDS.iter().map(|name| st(&BREED_SUFFIX.sub(&chars(name), ""))).collect();
    names.extend(WORDNET_DOGS.iter().cloned());
    longest_first(names.iter().map(|name| name.as_str()))
}

fn departed(m: &Match) -> bool {
    MOURNED.test_in(m.string, clause(m.string, m.start()), m.start()) || DIED.at(m.string, m.end()).is_some()
}

fn pet(m: &Match, kind: &'static str) -> V {
    if !free(m) || departed(m) {
        return None;
    }
    if let Some(word) = m.nonempty(1) {
        if kind == "cat" && CAT_WORD.fullmatch(word, 0, word.len()).is_none() && !FELINE.test(m.string) {
            return None;
        }
        if kind == "dog" && !word.contains(&' ') && GENERIC_DOG.at(word, 0).is_none() && !WORDNET_DOGS.contains(&st(word)) && !WORDNET_DOGS.contains(&st(&word[..word.len() - 1])) && !CANINE.test(m.string) {
            return None;
        }
    }
    Some(kind)
}

const ANIMALS: [(&str, &str); 43] = [
    ("fish", "fish / aquarium"), ("betta", "fish / aquarium"), ("aquarium", "fish / aquarium"), ("cockatiel", "cockatiel"), ("budgie", "budgie / parakeet"), ("parakeet", "budgie / parakeet"),
    ("parrot", "parrot"), ("cockatoo", "parrot"), ("conure", "parrot"), ("lovebird", "parrot"), ("macaw", "parrot"), ("african grey", "parrot"), ("bird", "bird (unnamed)"), ("rabbit", "rabbit"),
    ("bunn", "rabbit"), ("hamster", "hamster"), ("gerbil", "gerbil"), ("guinea pig", "guinea pig"), ("chinchilla", "chinchilla"), ("degu", "degu"), ("mice", "mice"), ("rat", "rat"),
    ("python", "snake"), ("snake", "snake"), ("gecko", "gecko"), ("bearded dragon", "bearded dragon"), ("beardie", "bearded dragon"), ("lizard", "lizard"), ("iguana", "lizard"), ("tortoise", "tortoise / turtle"),
    ("turtle", "tortoise / turtle"), ("chicken", "chicken"), ("hens", "chicken"), ("duck", "duck"), ("goat", "goat"), ("pig", "pig"), ("horse", "horse"), ("pony", "horse"), ("ponies", "horse"), ("ferret", "ferret"), ("tarantula", "tarantula"), ("isopod", "isopods"), ("snail", "snails"),
];

fn animal(word: &[char]) -> V {
    let word = st(word);
    ANIMALS.iter().find(|(part, _)| word.contains(part)).map(|(_, value)| *value)
}

fn other_pet(m: &Match) -> V {
    if free(m) && !departed(m) && !GAME.test(m.string) {
        animal(m.group(1)?)
    } else {
        None
    }
}

fn housemates(m: &Match) -> V {
    let text = m.text();
    if IN_LAWS.test(text) {
        Some("with in-laws")
    } else if contains(text, "grand") {
        Some("with grandparents")
    } else if PARENTS.test(text) {
        Some("with parents")
    } else if MATES.test(text) {
        Some("with roommates")
    } else if ALONE.test(text) {
        Some("alone")
    } else if CHILDREN.test(text) {
        Some("with children")
    } else if RELATIVES.test(text) {
        Some("with siblings / relatives")
    } else if PARTNER.test(text) {
        Some("with partner")
    } else {
        None
    }
}

fn tenure(m: &Match) -> &'static str {
    let (a, b) = sentence(m);
    if PAID_OFF.test_in(m.string, a, b) {
        "owns outright"
    } else {
        "homeowner (unstated)"
    }
}

fn dwelling(m: &Match) -> V {
    let word = st(m.first()?);
    let value = match word.as_str() {
        "house" | "bungalow" => "house",
        "apartment" | "apt" | "flat" | "studio apartment" => "apartment",
        "condo" | "townhouse" | "townhome" => "condo / townhouse",
        _ => "student housing",
    };
    stated(m, &FUTURE, || kept(m, value))
}

fn first_person(m: &Match) -> bool {
    let (a, b) = sentence(m);
    SELF.test_in(m.string, a, b) && !OTHER_PEOPLE.test_in(m.string, a, b) && !MAYBE.test_in(m.string, a, b)
}

#[allow(non_snake_case)]
pub fn pets() -> Vec<Rule> {
    let BREEDS = breeds();
    let DOG = format!(r"(?:dogs?|pups?|puppy|puppies|doggos?|pupper|doggy|doggie|pooch|mutt|(?!sham|snicker)[a-z]{{3,}}(?:poo|doodle)s?|(?:{BREEDS})s?)");
    let COATS = COAT_PATTERNS.join("|");
    let CAT = format!(r"(?:cats?|kittens?|kitty|kitties|catto|kitteh|(?:{COATS}))");
    let BOTH = r"\b(?:my|our|i have|we have|i've got|we've got|i own|we own) (?:\w+ ){0,2}(?:(?:dogs?|pups?|puppy|puppies|doggos?) (?:and|&|\+) (?:a |an |my |our |\d+ |two |three |four |multiple |several )?(?:\w+ )?(?:cats?|kitt(?:y|ies|ens?))|(?:cats?|kitt(?:y|ies|ens?)) (?:and|&|\+) (?:a |an |my |our |\d+ |two |three |four |multiple |several )?(?:\w+ )?(?:dogs?|pups?|puppy|puppies|doggos?))\b";
    vec![
        r("pets", &format!(r"{OWN}({DOG})(?:'s)?\b(?! (?:girl|boy|face|eyes|fat|dog eyes|play|collection|of [a-z]+ back)\b)(?!(?<=puppy) love\b)"), |m| pet(m, "dog"), TAGGED),
        r("pets", &format!(r"{OWN}({CAT})(?:'s)?\b(?! (?:litter )?(?:is wet|pussy))"), |m| pet(m, "cat"), TAGGED),
        r("pets", &format!(r"{HAVE}({DOG})\b(?! (?:in (?:this|the) (?:fight|race)|food|treats?|stickers?|shirts?|tattoos?|costumes?|emojis?|videos?|pics?|pictures?|photos?|memes?|gifs?|toys?|people|walkers?|sitters?|allerg\w*|saying)\b)"), |m| pet(m, "dog"), self_hedge()),
        r("pets", &format!(r"{HAVE}({CAT})\b(?! (?:food|treats?|stickers?|shirts?|tattoos?|videos?|pics?|pictures?|photos?|memes?|gifs?|toys?|people|ears|costumes?|allerg\w*|called|calls?|calling)\b)"), |m| pet(m, "cat"), self_hedge()),
        r("pets", &format!(r"{HAVE}((?:hamsters?|gerbils?|guinea pigs?|rabbits?|bunny|bunnies|ferrets?|parrots?|budgies?|cockatiels?|cockatoos?|parakeets?|conures?|lovebirds?|macaws?|chickens|hens|ducks|goats|ball pythons?|corn snakes?|pet snakes?|snakes|geckos?|lizards?|bearded dragons?|tortoises?|turtles?|bettas?|goldfish|axolotls?|hedgehogs?|tarantulas?|chinchillas?|degus?|pet rats?|mini pigs?|pet pigs?|(?<!guinea )pigs|horses|ponies|isopods|snails|fish tank|aquarium|mice))\b(?! (?:in (?:this|the|a)|to fry|in a row)\b)"), other_pet, self_hedge()),
        needs(r("pets", &format!(r"(?:{ME} an? |{AS} an? )(?:proud |\w+ )?owner of (?:a |an |two |three |\d+ )?(?:[a-z-]+ ){{0,2}}(?:({DOG})|({CAT})|({OTHER}))\b"),
          |m| if m.nonempty(1).is_some() { pet(m, "dog") } else if m.nonempty(2).is_some() { pet(m, "cat") } else if free(m) && !departed(m) { animal(m.group(3)?) } else { None }, self_hedge()), &["owner"]),
        r("pets", &format!(r"(?:{ME} an? |{AS} an? )(?:proud |crazy |\w+ )?(dog|cat) (?:mom|mum|dad|mama|daddy|parent|owner|lady|person)\b|\b(dog|cat) (?:mom|mum|dad|mama|parent) here\b|\b(dog|cat) (?:mom|mum|dad|mama|daddy|parent|owner)s? (?:of|to) (?:\d+|one|two|three|four|five|a|an)\b"),
          |m| { let word = m.nonempty(1).or(m.nonempty(2)).or(m.group(3)); pet(m, if word.map_or(false, |w| eq(w, "dog")) { "dog" } else { "cat" }) }, self_hedge()),
        needs(r("pets", BOTH, |m| pet(m, "dog"), self_hedge()), &["dog", "pup", "doggo", "cat", "kitt"]),
        needs(r("pets", BOTH, |m| pet(m, "cat"), self_hedge()), &["dog", "pup", "doggo", "cat", "kitt"]),
        r("pets", concat!(r"\b(?:mi|mis) (perr[oa]s?|perrit[oa]s?|gat[oa]s?|gatit[oa]s?)\b|\b(?:meu|minha|meus|minhas) (cachorr[oa]s?|cadel[oa]s?|gat[oa]s?|gatinh[oa]s?)\b|\b(?:mon|ma|mes) (chien|chienne|chiens|chat|chatte|chats|chaton)\b|\b(?:mein|meine|meinen|meinem) (hund|hunde|hündin|katze|katzen|kater)\b",
          r"|\bmijn (hond|honden|kat|katten|poes)\b|\b(?:il mio|la mia|i miei|le mie) (cane|cani|cagnolino|gatto|gatta|gatti|gattino)\b|\b(?:mój|moja|moje) (pies|psy|piesek|kot|kotka|koty)\b|\b(köpeğim|kedim)\w*|\b(aso|pusa) ko\b"),
          |m| if free(m) { Some(if m.first().map_or(false, |w| FOREIGN_CAT.at(w, 0).is_some()) { "cat" } else { "dog" }) } else { None }, TAGGED),
        r("pets", r"(?:my (?<=\bmy )|our (?<=\bour ))(?:(?!from|of|with|and|to|in|on|at|for|is|was|the|a|an|are|were|be|been|has|had|have|by|little|high|lizard|favou?rite|fave|dream)[\w-]+ ){0,2}((?:hamsters?|gerbils?|guinea pigs?|rabbits?|bunny|bunnies|ferrets?|parrots?|budgies?|cockatiels?|cockatoos?|parakeets?|conures?|lovebirds?|macaws?|hens|chickens|ball pythons?|corn snakes?|snakes?|rodents?|geckos?|lizards?|bearded dragons?|beardies?|iguanas?|tortoises?|turtles?|betta|bettas|goldfish|axolotls?|hedgehogs?|tarantulas?|chinchillas?|degus?|rats|horses?|ponies|snails?|shrimps?|fish tank|aquarium|fish(?:es)?|birds?|ducks?|ducklings?|frogs?|toads?|hermit crabs?|canar(?:y|ies)|pony|donkeys?|alpacas?|llamas?|piglets?|mini pigs?|pet pigs?|(?<!guinea )pigs|goats|rat(?! terrier)|mice|isopods|newts?|salamanders?))\b(?! (?:brain|toy|game|collab|knight|kigu|ears|costume|plush\w*|slippers|tacos?|sticks?|fingers?|and chips|oil|sauce|market|soup|fry|dinner|recipe|curry|cakes?|fillets?|bones?|pie)\b)", other_pet, TAGGED),
    ]
}

pub fn living() -> Vec<Rule> {
    vec![
        r("living_arrangement", r"\bi (?:still |currently |now |already |also )?live (?:all )?(?:alone|solo|by myself|on my own)\b(?! with)|\b(?:i'm|im|i am|i've been|i have been) (?:currently |still |now )?living (?:alone|solo|by myself|on my own)\b(?! with)|\bi (?:love|like|enjoy|prefer) living alone\b|\bwohne (?:ich )?allein\b", constant("alone"), self_hedge()),
        r("living_arrangement", r"\bi (?:have )?(?:lived|live|am living|still live) (?:at home )?with my (?:(?:mother|father)[- ]in[- ]law|in-?laws|mil|fil|mom and dad|parents|mom|dad|mum|mother|father|folks|family|grandparents)\b|\bmy parents' (?:house|place|home)\b(?= where i)|\bi (?:still )?live at home\b|\b(?:i'm|im|i am|i've been|i have been|still) living at home with\b",
          housemates, self_hedge()),
        r("living_arrangement", concat!(r"\bi live with my (?:wife|husband|partner|girlfriend|boyfriend|gf|bf|fianc\w*|kids|children|spouse|sisters?|brothers?|siblings|sons?|daughters?|aunt|uncle|cousins?|in-?laws)\b|\bwe live together\b",
          r"|\b(?:we|my (?:wife|husband|partner|girlfriend|boyfriend|gf|bf|fianc\w*) and i) (?:just |recently |finally )?moved in together\b|\bmoved in (?:with|together with) my (?:girlfriend|boyfriend|partner|gf|bf|fianc\w*)\b",
          r"|\bmy (?:wife|husband|partner|girlfriend|boyfriend|gf|bf|fianc\w*|spouse|hubby) and i (?:live|share (?:a|an|our)|rent|bought (?:a|our)|own (?:a|our)|have (?:a|an|our) (?:house|home|apartment|place|flat))\b|\bwho lives with me\b",
          r"|\b(?:our|my) (?:house|home|apartment|place)\b(?= with my (?:wife|husband|partner))"), housemates, self_hedge()),
        needs(r("living_arrangement", r"\b(?:still |currently |now |also )?(?:live|living|stay|staying|moved back in|move back in|moving back in|moved in|moving in|back home) (?:with|w/?) (?:my|the) (?:(?!(?:friends?|boyfriend|girlfriend|partner|bf|gf)\b)\w+ )?((?:mother|father)[- ]in[- ]law|in-?laws|parents?|folks|mom and dad|mum and dad|grandparents|grandma|grandmother|mom|dad|mum|mother|father)\b|\b(?:i'm|im|i am)(?: still| currently| now)? living (at home)\b|\bliving in my (parents?)'?(?:'s)? (?:house|home|place|basement)\b|\b(?:i (?:\w+ )?live|i'm living|i am living|i've been living|we live|living) with (?:my|the) (?:\w+ )?(partner|man|boyfriend|girlfriend|bf|gf|so|fianc\w*|wife|husband|hubby|spouse|kids|children|son|daughter|sister|brother|siblings|cousins?|aunt|uncle|family)\b|\bi (?:also |now |currently )?live with (someone|somebody)\b|(?:^|[.,;!\n]\s*|\band )(?:i )?(?:currently |still |now )?(?:live|living) (alone|solo|by myself|on my own)\b|\bliving (solo)\b|\bi (?:also |now |currently )?(?:have|got) (?:a |two |\d |some )?(roommates?|room ?mates?|flatmates?|housemates?)\b|\bi(?:'m| am)? (?:also |now |currently )?(?:live|living) with (?:a |two |\d |some )?(friends?|roommates?|flatmates?|housemates?)\b(?! (?:who|that|and (?:family|their))\b)",
          |m| {
              if !SPEAKER_WORD.test_in(m.string, sentence(m).0, m.end()) && !SOLO_HEAD.test(m.string) || OTHER_PEOPLE.test_in(m.string, sentence(m).0, m.start()) { return None; }
              housemates(m)
          }, self_hedge()), &["live", "living", "stay", "moved", "move", "moving", "back home", "roommate", "flatmate", "housemate"]),
        r("living_arrangement", r"\b(?:we(?:'ve| have)? been|we (?:just |recently )?started|we're|we are|we've been) living together\b|\bcohabit(?:ing|ate)? with my (?:gf|bf|girlfriend|boyfriend|partner|fianc\w*)\b|\b(?:i'm|im|i am) (?:just |now )?moving in with my (?:gf|bf|girlfriend|boyfriend|partner|fianc\w*)\b", housemates, self_hedge()),
        r("living_arrangement", r"\b(?:yo )?vivo (sol[oa]|con mis (?:padres|papás|papas|viejos|tatas))\b|\bje vis (seule?)\b|\bmieszkam (sama?)\b|\bmoro (sozinh[oa])\b|\bmoro com (meus pais|minha mãe|meu pai)\b|\b(?:ich )?wohne (?:noch )?(bei meinen eltern)\b",
          |m| if contains(m.first()?, "sol") || contains(m.first()?, "seul") || contains(m.first()?, "sam") || contains(m.first()?, "sozinh") { Some("alone") } else { Some("with parents") }, self_hedge()),
        r("living_arrangement", r"\bi\s*[\(\[][^\)\]\n]{1,8}[\)\]],? (?:currently |still |now |also )?live (?:alone|by myself|on my own|with (?:my|a|two|\d|some) (?:[\w-]+ ){0,2}?(?:parents?|folks|mom|dad|mum|mother|father|grandparents|grandma|grandmother|grandpa|wife|husband|hubby|partner|girlfriend|boyfriend|gf|bf|fianc\w*|spouse|roommates?|flatmates?|housemates?))\b", housemates, self_hedge()),
        r("living_arrangement", r"\b(?:my|our) (?:(?!(?:old|former|ex|previous|college|freshman|first|last|future|potential|childhood|dorm)\b)\w+ ){0,2}(?:roommates?|roomates?|room mates?|flatmates?|housemates?|roomie|roomies)\b|\bi live with (?:\w+ )?(?:roommates?|flatmates?|housemates?)\b|\b(?:ner|einer) wg\b", |m| if BYGONE.test_in(m.string, sentence(m).0, sentence(m).1) { None } else { Some("with roommates") }, self_hedge()),
    ]
}

pub fn housing() -> Vec<Rule> {
    vec![
        r("housing_tenure", concat!(r"\b(?:i|we) (?:just |recently |finally )?(?:own|bought|purchased|closed on) (?:a|my|our|the|this) (?:first |new |own )?(?:\w+ )?(?:house|home|condo|townhouse|townhome|property)\b|\bfirst[- ]time home ?buyers?\b(?= here)|\b(?:as a|i'm a|im a) homeowner\b|\bwe (?:own|bought) (?:a|our) (?:\w+ )?(?:house|home|condo)\b|\bwhen (?:i|we) bought (?:my|our) (?:house|home)\b",
          r"|\b(?:,|and|[.!?]) (?:recently |just |finally )?(?:bought|purchased) (?:a|my|our) (?:new |first |\w+ )?(?:house|home|condo|townhouse)\b|\bselling (?:my|our) (?:house|home|condo)\b|\bin the middle of selling the house\b|\bmy house is (?:assessed|worth|paid off|valued|appraised)\b|\bclos(?:ed|ing) on (?:my|our) (?:\w+ )?(?:house|home|condo)\b",
          r"|\b(?:i|we) (?:have|own) (?:a|my own|our own) (?:\d+[- ]?(?:bed(?:room)?|br) )?(?:house|condo|townhouse|home)\b(?! (?:office|gym|studio|theater|theatre|bar|network|server|lab|loan|equity|warranty|base|page|game|birth|visit|care|health|nurse|depot))|\bpaid off (?:my|our) (?:house|mortgage|home)\b"), |m| Some(tenure(m)), hedge()),
        r("housing_tenure", r"(?:my|our)(?<=\bmy|\bour) (?:\w+ )?mortgage\b(?! (?:loans?|brokers?|rates? (?:is|are|was|went)|lenders?|industry|market|bankers?|officers?|advisors?|calculator|application|pre-?approval)\b)|\b(?:i|we) (?:\w+ )?(?:have|got|took out|pay|paid) (?:a |the |our |my )?mortgage\b(?! (?:loans?|brokers?|lenders?|bankers?|officers?|advisors?)\b)", |m| if first_person(m) && !PAID_OFF.test_in(m.string, sentence(m).0, sentence(m).1) { kept(m, "owns with mortgage") } else { None }, TAGGED),
        r("housing_tenure", r"\b(?:my|our) (?:landlord|landlady|rent|leasing office|property manager|property owner|security deposit|tenancy|letting agent)\b|\b(?:ich )?wohne in (?:einer|ner) wg\b", |m| kept(m, "renter"), TAGGED),
        r("housing_tenure", r"\bwe rent\b(?! (?:a car|cars|out)\b)|\b(?:i'm|im|i am|as) a tenant\b|\b(?:i|we) (?:pay|paid) (?:\$?\d[\d,]* (?:in |for |a month |per month )?|my |our |)rent\b|\bi rent (?:a|an|my)\b(?!(?: [\w-]+){0,3} out\b)|\bi'm renting\b|\b(?:as a|i'm a) renter\b|\bi rent\b(?! (?:a car|cars|out|movies|equipment|tools|bikes?|a truck|a van|a uhaul|boats?|kayaks?|skis?)\b)(?!(?: [\w-]+){0,3} out\b)|\bwe(?:'re| are) (?:currently )?renting\b", constant("renter"), hedge()),
        r("housing_tenure", r"\b(?:i'm|im|i am|as|as new|as first[- ]time) (?:now |finally |also |officially )?(?:a |an )?(?:new |first[- ]time |proud )?(home ?owner|renter|tenant)\b(?!s)|\b(?:we're|we are) (?:now |finally |also |officially )?(?:new |first[- ]time |proud )?(home ?owners|renters|tenants)\b",
          |m| Some(if m.group(1).map_or(false, |g| contains(g, "own")) { "homeowner (unstated)" } else { "renter" }), hedge()),
        r("housing_tenure", r"\b(?:i'm|im|i am) (?:currently |now )?homeless\b|\bbeing homeless (?:for|since)\b|\bi(?:'ve| have) been homeless\b|\bi live in my car\b|\bi(?:'m| am) (?:living|sleeping) in (?:my|a) (?:car|van|tent|shelter)\b", constant("homeless"), hedge()),
        r("housing_tenure", r"\bmy (?:current |new |apartment |\w+ )?lease\b|\b(?:i|we) (?:just |recently )?(?:signed|renewed|broke|break|re-?signed) (?:a|my|our|the) (?:\w+ )?lease\b|\b(?:resigning|renewing|breaking) (?:my|our) lease\b", |m| if VEHICLE.test(m.string) { None } else { kept(m, "renter") }, TAGGED),
        r("housing_tenure", &(r"(?:my (?<=\bmy )|our (?<=\bour ))(?:own |new |current |\d+[- ]?(?:bed(?:room)?|br) )?(?:house|home|condo|townhouse)\b".to_string() + NOT_DWELLING),
          |m| { let (a, b) = sentence(m); if OWNED.test_in(m.string, a, b) { stated(m, &FUTURE, || kept(m, tenure(m))) } else { None } }, TAGGED),
        r("housing_tenure", r"(?:my (?<=\bmy )|our (?<=\bour ))(?:own |new |current |first |old |\d+[- ]?(?:bed(?:room)?|br) )?(?:apartment|apt|flat|studio|unit)\b(?! (?:complex|building)? ?(?:manager|managers|owner|owners)\b)",
          |m| { let (a, b) = bounds(m); if RENTING.test_in(m.string, a, b) && !RENT_OUT.test_in(m.string, a, b) { stated(m, &FUTURE, || kept(m, "renter")) } else { None } }, TAGGED),
        r("housing_tenure", &(r"(?:my (?<=\bmy )|our (?<=\bour ))(?:current |new )?(?:house|home|room|bedroom|place)\b".to_string() + NOT_DWELLING),
          |m| { let (a, b) = bounds(m); if RENTING.test_in(m.string, a, b) && !OWNING.test_in(m.string, a, b) && !RENT_OUT.test_in(m.string, a, b) { stated(m, &FUTURE, || kept(m, "renter")) } else { None } }, TAGGED),
        r("housing_tenure", r"\b(?:(bought|purchased|closed on|built) (?:a|my|our|the|this) (?:[\w-]+ ){0,2}(?:house|home|condo|townhouse|place|property)\b(?! (?:for|as an investment)\b)|(?:renting|leasing|rent|rented|lease|leased) (?:a|an|my|our|this|the) (?:[\w-]+ ){0,2}(?:apartment|apt|flat|room|house|home|place|studio|unit|condo|townhouse)\b(?! out\b))",
          |m| if first_person(m) && !GAME.test(m.string) && !KIN_SUBJECT.test_in(m.string, sentence(m).0, m.start()) { kept(m, if m.nonempty(1).is_some() { "homeowner (unstated)" } else { "renter" }) } else { None }, self_hedge()),
        r("housing_tenure", r"\b(?:my|our) first (?:house|home|condo|townhouse)\b(?! (?:game|run|base|office|page|screen)\b)|\bmoved into (?:my|our) (?:new |current )?(?:house|home|condo)\b|\bbought (?:my|our) own (?:place|house|home)\b|\bin the process of (?:buying|purchasing|closing on)\b",
          |m| { let (a, b) = sentence(m); if SELF.test_in(m.string, a, b) { stated(m, &FUTURE, || kept(m, tenure(m))) } else { None } }, TAGGED),
        needs(r("housing_tenure", concat!(r"(?:\b(?:i'm|im|i am|i've been|i was|we're|we are|as|being|and|also)(?: (?:a|an|the|now|also|still|currently|finally|proudly|happily|just))*(?: [\w-]+){0,2} |^", claimcore::flair!(), r"\W*|[\n.!?(\[,]\s*)(home ?owners?|renters?)\b(?! (?:who|that|insurance|policy|association|associations|rights|protections?|credit|grant|programs?|market|groups?)\b)(?=\s*(?:[.,!;:)\]\n]|$|here|too|myself|and|but|with|in|for|since|now|so)\b|\s*[.,!;:)\]\n]|\s*$)"),
          |m| {
              let start = sentence(m).0;
              if spoken(m) && !THIRD.test_in(m.string, start, m.start()) && !MAYBE.test_in(m.string, start, m.start()) {
                  Some(if m.group(1).map_or(false, |g| contains(g, "own")) { "homeowner (unstated)" } else { "renter" })
              } else {
                  None
              }
          }, TAGGED), &["owner", "renter"]),
        needs(r("housing_tenure", concat!(r"\b(?:i|i'm|im|i am|i've been|i have been|i became|i ended up|i'm about to be|i am about to be|i'm going to be)(?: (?:just|now|currently|still|literally|basically|technically|actually|recently|already|officially|essentially|briefly|temporarily))? (?:became |become |ended up |end up |been )?homeless\b(?! (?:people|person|man|woman|guy|men|women|folks|shelters?|population|encampments?|camps?|kids|youth|veterans?)\b)",
          r"|\bi (?:\w+ )?(?:live|living|lived) (?:in|out of) (?:a|my) (?:tent|car|van|vehicle|truck|shelter)\b|\bi(?:'m| am|'ve been| have been)? (?:\w+ )?unhoused\b"), |m| stated(m, &FUTURE, || kept(m, "homeless")), TAGGED),
          &["homeless", "tent", "car", "van", "vehicle", "truck", "shelter", "unhoused"]),
        needs(r("housing_tenure", concat!(r"\b(?:i|we)(?:'ve| have)? (?:actually |also |already |finally |now |still |currently |just )?(?:own|owned) (?:a|my|our|\d|two|three) (?:[\w-]+ ){0,2}(?:house|home|condo|townhouse|townhome|place|flat|apartment|homes|houses|condos)\b(?! (?:for|as an investment|games?|office|gym|theater|theatre|network|page|screen)\b)",
          r"|\b(?:i|we) (?:\w+ )?(?:live|living|lived) in (?:a|an) (?:\w+ )?rented (?:apartment|flat|house|room|place|home|condo|unit|studio)\b|\b(?:i|we)(?:'ve| have) (?:only |always |never |also )?(?:ever )?rented\b(?! (?:a car|cars?|out|it|them|movies?|equipment|tools?|bikes?|a truck|a van|boats?|kayaks?)\b)|\b(?:i|we)(?:'re| are|'m| am)? (?:about to be |being |getting |got |just got )evicted\b"),
          |m| if first_person(m) { let text = m.text(); stated(m, &FUTURE, || kept(m, if contains(text, "rent") || contains(text, "evict") { "renter" } else { "homeowner (unstated)" })) } else { None }, TAGGED),
          &["own", "rent", "evict"]),
        needs(r("housing_tenure", concat!(r"\bi (?:currently |still |just |now |also )rent\b(?! (?:a car|cars|out|movies|equipment|tools|bikes?|a truck|a van|a uhaul|boats?|kayaks?|skis?)\b)|\b(?:i|we)(?:'m| am|'re| are) (?:just |currently |still |now |only |also )renting\b(?! (?:a car|cars|out|it|them)\b)",
          r"|\b(?:i|we)(?:'m| am|'re| are)?(?: \w+)? (?:live|living|lived|staying) in an? (?:\w+ )?(?:rented|rental) (?:apartment|flat|house|room|place|home|condo|unit|studio|property)\b"),
          |m| if MAYBE.test_in(m.string, sentence(m).0, m.start()) { None } else { stated(m, &FUTURE, || kept(m, "renter")) }, TAGGED), &["rent"]),
        needs(r("housing_tenure", r"\b(?:i'm|im|i am|we're|we are)(?: (?!(?:not|never|thinking|considering|planning|looking|going|trying|hoping)\b)\w+){0,3} renting (?:a|an|my|our) (?:[\w-]+ ){0,3}(?:apartment|apt|flat|room|house|home|place|studio|unit|condo|townhouse|bedroom)\b", |m| if MAYBE.test_in(m.string, sentence(m).0, m.start()) { None } else { stated(m, &FUTURE, || kept(m, "renter")) }, TAGGED), &["renting"]),
        needs(r("housing_tenure", r"\b(?:i|we) (?:\w+ )?(?:spend|pay) (?:about |around |over |almost |nearly |roughly |like )?\$?\d[\d,.]*k? (?:\w+ ){0,2}(?:on|in|for) rent\b", |m| if first_person(m) { kept(m, "renter") } else { None }, TAGGED), &["rent"]),
        needs(r("housing_tenure", concat!(r"\bown (?:my|our) own (?:place|house|home|flat|apartment|condo|property)\b|\b(?:lucky|fortunate|blessed) enough to own (?:a|my|our) (?:\w+ )?(?:house|home|place|condo|flat|apartment|property)\b",
          r"|\bas (?:someone|somebody|a person|one|an? \w+) who owns? (?:a|my|an) (?:\w+ )?(?:house|home|condo|property)\b|(?:^|[\n,;:]\s*|\b(?:my|our) )(?:home|house) (?:is )?(?:fully |completely |now )?paid (?:off|for)\b|(?:^|[\n.!?]\s*)paid off (?:home|house)\b"),
          |m| if SELF.test(m.string) && !MAYBE.test_in(m.string, sentence(m).0, m.start()) { stated(m, &FUTURE, || kept(m, tenure(m))) } else { None }, TAGGED), &["own", "paid"]),
        needs(r("housing_tenure", concat!(r"\b(?:my|this) (?:\w+ )?homeless ass\b|\b\d{2} and (?:about to be |now |currently )?homeless\b|^", claimcore::flair!(), r"\W*homeless\b(?! (?:people|person|man|men|woman|women|shelters?|population|guy|guys|folks|kids|youth|veterans?|camps?|encampments?|crisis|problem|issue)\b)|(?:^|[\n.!?]\s*)(?:(?:i'm|im|i am|i've been|currently|now|still) )?(?:living |staying |sleeping )?in a (?:homeless |women's |family )?shelter\b"), |m| kept(m, "homeless"), TAGGED), &["homeless", "shelter"]),
        needs(r("home_type", r"\b(?:i|we)(?:'m| am|'re| are)? (?:currently |still |now |also |just )?(?:live|living|stay|staying|rent|renting|own) (?:in )?an? (?:(?:small|tiny|little|big|large|shared|cramped|cheap|nice|new|rented|studio|\d[- ]?(?:bed(?:room)?|br)|one[- ]bedroom|two[- ]bedroom|three[- ]bedroom|basement|detached|semi[- ]detached|terraced) ){0,2}(house|bungalow|apartment|apt|flat|condo|townhouse|townhome|dorm)\b(?! (?:area|land|part|region|complex|building|party|boat)\b)",
          |m| if first_person(m) { dwelling(m) } else { None }, TAGGED), &["house", "bungalow", "apartment", "apt", "flat", "condo", "townhouse", "townhome", "dorm"]),
        needs(r("home_type", r"(?:my (?<=\bmy )|our (?<=\bour ))(?:own |new |current |tiny |small |little |shared |studio |one[- ]bedroom |two[- ]bedroom |\d[- ]?(?:bed(?:room)?|br) )?(apartment|apt|condo|townhouse|townhome|dorm)(?: room)?\b(?! (?:complex|building|manager|managers|hunt|hunting|search|searching|application|listing|owner|owners|association|board|community|games?)\b)",
          |m| if first_person(m) { dwelling(m) } else { None }, TAGGED), &["apartment", "apt", "condo", "townhouse", "townhome", "dorm"]),
        needs(r("home_type", r"(?:my (?<=\bmy )|our (?<=\bour ))(?!(?:old|former|previous|last|ex|future|dream|next|first|childhood|college|parents?|friends?|moms?|dads?|own|new|current|tiny|small|little|shared|studio|doctors?|dentist|dr|vet|medical|hair|eye)\b)[\w-]+ (apartment|apt|condo|townhouse|townhome|bungalow)\b(?! (?:complex|building|manager|managers|hunt|hunting|search|searching|application|listing|owner|owners|association|board|community|games?)\b)", dwelling, TAGGED), &["apartment", "apt", "condo", "townhouse", "townhome", "bungalow"]),
        needs(r("home_type", r"\bi (?:currently |still |now |also )?(?:live|living|stay|staying) at an? (?:[\w-]+ ){0,2}(apartment|apt|flat|condo|townhouse|townhome|bungalow|house)\b(?! (?:complex|building|area|party|for|with|of)\b)|\bi (?:also |now |currently |still )?(?:have|got|own|rent) (?:an?|my own|my) (?:[\w-]+ ){0,2}?(apartment|apt|condo|townhouse|townhome|bungalow)\b(?! (?:complex|building|manager|owner|for (?:sale|rent)|as)\b)", dwelling, TAGGED), &["apartment", "apt", "flat", "condo", "townhouse", "townhome", "bungalow", "house"]),
        needs(r("home_type", r"(?:\b(?:i|we)(?:'ve| have)? (?:just |recently |finally |now )?|(?<![^\n.!?~])\s*(?:just |recently |finally )?)moved into (?:an?|my|our) (?:(?:new|first|own|beautiful|small|tiny|little|nice|cute|studio|spacious|\d[- ]?(?:bed(?:room)?|br)|one[- ]bedroom|two[- ]bedroom) ){0,2}(apartment|apt|flat|condo|townhouse|townhome|bungalow|house|dorm)\b(?! (?:complex|building)\b)|\bi (?:\w+ )?(?:have|own) my own (house|bungalow)\b",
          |m| if OTHER_PEOPLE.test_in(m.string, sentence_start(m), m.start()) { None } else { dwelling(m) }, self_hedge()), &["moved into", "my own"]),
        needs(r("home_type", r"\bi (?:currently |still |now |also )?(?:live|living|stay|staying) in (?:the )?(dorms|residence halls?|student housing|student accommodation|halls of residence)\b",
          |m| if first_person(m) { dwelling(m) } else { None }, TAGGED), &["dorm", "residence", "student"]),
        needs(r("home_type", r"\b(?:i|we)(?:'m| am|'re| are)? (?:currently |still |now |also |both |actually )?(?:live|living|reside|residing) on (?:a |an |our |my |the )?(?:(?:small|little|big|family|working|rural|\d+[- ]acre|horse|dairy|cattle|hobby) )?(?:farm|ranch|homestead|smallholding|acreage)\b(?! (?:job|work|hand|stand)\b)|\b(?:i'm|im|i am|we're|we are) (?:\w+ )?homesteaders?\b|\b(?:my|our) (?:little |small |own |family )?(?:homestead|farmhouse|smallholding)\b|\b(?:i|we) (?:own|have|run) (?:a|an|our|my) (?:(?:small|little|family|working|hobby|\d+[- ]acre) )?(?:farm|ranch|homestead)\b(?! (?:job|game|map|mod)\b)",
          |m| if first_person(m) && !GAME.test(m.string) { stated(m, &FUTURE, || kept(m, "farm / ranch / homestead")) } else { None }, TAGGED), &["farm", "ranch", "homestead", "smallholding", "acreage"]),
        needs(r("home_type", r"\b(?:i|we)(?:'m| am|'re| are)? (?:currently |still |now |also |both |actually |basically )?(?:full[- ]time )?(?:live|living|reside|residing|stay|staying) (?:full[- ]time )?(?:in|out of|on) (?:an?|my|our) (?:(?:old|small|tiny|little|converted|own|single[- ]wide|double[- ]wide|\d{4}|travel) ){0,2}(?:rv|fifth[- ]wheel(?: camper| trailer)?|camper(?: ?van)?|van|mobile home|motorhome|motor home|trailer|caravan|tiny (?:house|home)|narrowboat|house ?boat|sailboat|skoolie|manufactured home)\b(?! (?:down|by|for|with my (?:mom|dad|parents))\b)",
          |m| if first_person(m) { stated(m, &FUTURE, || kept(m, "mobile home / rv / van")) } else { None }, TAGGED), &["rv", "camper", "van", "mobile home", "motor", "trailer", "caravan", "tiny h", "boat", "skoolie", "manufactured"]),
    ]
}

const NATION: &str = r"(?:us|u\.s\.|usa|uk|u\.k\.|eu|nz|new zealand|south african|swiss|thai|swede|dane|finn|pole|scot|brit|aussie|kiwi|greek|[a-z]+(?:an|ian|ish|ese|ic|ch|i))";
const VISA: &str = r"(h-?1-?b|h-?4 ead|l-?1|tn|e-?3|o-?1|482|485|457|skilled worker|tier 2|work|working|employment|pgwp|working holiday|whv|417|462|f-?1|opt|stem opt|student|study|tier 4|500|spouse|spousal|partner|marriage|k-?1|820|801|309|100)";

regex!(HOLIDAY, r"holiday|whv|417|462");
regex!(STUDY, r"f-?1|opt|student|study|tier 4|500");
regex!(SPOUSAL, r"spous|partner|marriage|k-?1|820|801|309|100");
regex!(DUAL, r"\bboth\b|\w/\w| and ");

fn residency_status(m: &Match) -> V {
    let text = m.text();
    let value = if contains(text, "dual") || contains(text, "citizen") && DUAL.test(text) {
        "dual citizen"
    } else if contains(text, "naturali") {
        "naturalized citizen"
    } else if contains(text, "citizen") {
        "citizen"
    } else if contains(text, "permanent") || contains(text, "green card") || contains(text, "pr") || contains(text, "ilr") || contains(text, "indefinite") || contains(text, "settled") || contains(text, "landed") {
        "permanent resident"
    } else {
        let kind = m.first()?;
        if HOLIDAY.test(kind) {
            "working holiday"
        } else if STUDY.test(kind) {
            "student visa"
        } else if SPOUSAL.test(kind) {
            "partner / spouse visa"
        } else {
            "work visa"
        }
    };
    kept(m, value)
}

pub fn residency() -> Vec<Rule> {
    vec![
        needs(r("immigration_status", &format!(r"\b(?:i'm|im|i am) (?:an? )?(?:naturali[sz]ed |dual )?(?:{NATION}(?:[/ -]{NATION})? )?(?:dual )?citizen\b(?<!\bi'm citizen)(?<!\bim citizen)(?<!\bam citizen)(?<!\bas citizen)(?<!\ban citizen)(?<!\ba citizen)(?! (?:of the world|scientist|journalist|science|developer|band|kane|army|app)\b)|\b(?:i'm|im|i am) an? citizen of (?:the )?(?!world\b)[a-z]+|\bas an? (?:(?:naturali[sz]ed |dual )(?:{NATION}(?:[/ -]{NATION})? )?|{NATION}(?:[/ -]{NATION})? (?:dual )?)citizen,? (?:i|i'm|im|i've|my|we)\b"), residency_status, self_hedge()), &["citizen"]),
        needs(r("immigration_status", &format!(r"\bi (?:have|hold|got|received|obtained) (?:my |dual |both |a |an )?(?:{NATION} )?(?:and {NATION} )?(?:dual )?citizenship\b"), residency_status, self_hedge()), &["citizenship"]),
        needs(r("immigration_status", &format!(r"\b(?:i'm|im|i am) an? (?:{NATION} )?(?:permanent resident|green card holder|pr holder|lawful permanent resident|landed immigrant)\b|\bi (?:have|hold|got|received) (?:my |a |an )?(?:{NATION} )?(?:green card|permanent residency|permanent resident status|pr status|pr card|indefinite leave to remain|ilr|settled status)\b|\bi (?:just |finally )?got my pr\b(?![\w-]| (?:experience|team|skills|job|firm|agency|work|degree)\b)"), residency_status, self_hedge()), &["permanent res", "green card", "pr", "landed", "indefinite", "ilr", "settled"]),
        needs(r("immigration_status", &format!(r"\b(?:(?:i'm|im|i am|i've been|i have been) (?:currently |still |now |here )?(?:on|in|holding) (?:an? |my |the )?|\bi (?:currently )?(?:have|hold|got|received|was granted|just got) (?:an? |my ))(?:{VISA}[- ](?:subclass )?(?:visa|status|permit)|(h-?1-?b|f-?1|stem opt|opt|pgwp|whv|l-?1|tn)\b(?! (?:program|programs|classes|class)\b))|\bas an? (h-?1-?b|f-?1|opt|whv) (?:holder|student|worker|employee|visa holder)\b"), residency_status, self_hedge()), &["visa", "status", "permit", "h1b", "h-1b", "f1", "f-1", "opt", "pgwp", "whv", "l1", "l-1", "tn"]),
        needs(r("immigration_status", &format!(r"\b(?:on|holding) my {VISA}[- ](?:subclass )?(?:visa|status|permit)\b(?! (?:application|interview|appointment|stamping|to be|was|got|is (?:pending|processing))\b)|\bhere on (?:an? |my )?(h-?1-?b|f-?1|stem opt|opt|pgwp|whv|l-?1|tn)\b"), |m| if OTHER_PEOPLE.test_in(m.string, sentence_start(m), m.start()) { None } else { residency_status(m) }, self_hedge()), &["visa", "status", "permit", "h1b", "h-1b", "f1", "f-1", "opt", "pgwp", "whv", "l1", "l-1", "tn"]),
        needs(r("immigration_status", &format!(r"\b(?:i'm|im|i am) (?:an? )?naturali[sz]ed(?: {NATION})?\b|\bi (?:just |finally |recently )?(?:got|became|was|have been|'ve been) naturali[sz]ed\b|\bi naturali[sz]ed\b"), |m| if OTHER_PEOPLE.test_in(m.string, sentence_start(m), m.start()) { None } else { kept(m, "naturalized citizen") }, self_hedge()), &["naturali"]),
        needs(r("immigration_status", r"\b(?:i'm|im|i am|i've been|i have been) (?:currently |still |also )?(?:an )?undocumented\b(?! (?:workers?|people|immigrants? (?:who|that))\b)|\bas an undocumented (?:immigrant|person|student|worker)\b", |m| kept(m, "undocumented"), self_hedge()), &["undocumented"]),
        needs(r("immigration_status", &format!(r"\b(?:i'm|im|i am) an? (?:{NATION} |political |war )?(?:refugee|asylum seeker|asylee|daca recipient)\b(?! (?:camp|crisis|from (?:r/|reddit|twitter|tumblr|facebook|another|that|this))\b)|\bi (?:was granted|got|received|have|hold) (?:political )?(?:asylum|refugee status|daca|tps)\b|\bi(?:'m| am) (?:on|a) (?:daca|tps)\b(?! (?:program|policy)\b)|\bi came (?:here |to \w+ )?as an? (?:{NATION} )?refugee\b"),
          |m| if OTHER_PEOPLE.test_in(m.string, sentence_start(m), m.start()) { None } else { kept(m, "refugee / asylum") }, self_hedge()), &["refugee", "asylum", "asylee", "daca", "tps"]),
    ]
}
