import re

from .common import SELF_HEDGE, hedged
from .schema import fan_value

NAME = r"((?:[Tt]he )?[A-Z0-9][\w'&.:!+-]*(?:,? (?:of|the|and|&|de|la|le|vs\.?|in|on|a|to|[A-Z0-9][\w'&.:!+-]*)){0,6})"
TRAILING = re.compile(r"(?:\s+(?:of|the|and|&|de|la|le|vs\.?|in|on|a|to))+$|[\s,.:!]+$")

KINDS = {"band": "artist", "artist": "artist", "singer": "artist", "rapper": "artist", "musician": "artist", "group": "artist", "musical artist": "artist", "composer": "artist",
         "show": "franchise", "tv show": "franchise", "series": "franchise", "anime": "franchise", "manga": "franchise", "movie": "franchise", "film": "franchise",
         "franchise": "franchise", "book series": "franchise", "cartoon": "franchise", "sitcom": "franchise", "comic": "franchise", "game": "video_game", "video game": "video_game",
         "videogame": "video_game", "book": "franchise", "novel": "franchise", "author": "author", "writer": "author", "team": "sports_team", "club": "sports_team",
         "player": "athlete", "athlete": "athlete", "driver": "athlete", "fighter": "athlete", "wrestler": "athlete", "character": "character", "pokemon": "character",
         "hero": "character", "villain": "character", "champion": "character", "streamer": "creator", "youtuber": "creator", "podcast": "creator", "podcaster": "creator",
         "creator": "creator", "actor": "celebrity", "actress": "celebrity", "comedian": "celebrity", "celebrity": "celebrity"}
KIND_WORDS = "|".join(sorted(map(re.escape, KINDS), key=len, reverse=True))
LETTERS = re.compile(r"[^\W\d_]{2}")
RULES = []
FAVORITE = re.compile(rf"(?i:\bmy (?:all[- ]time |absolute |personal |current |top |favou?rite |most favou?rite )*(?:favou?rite|fave|fav|favs) ({KIND_WORDS})(?: of all time| ever| right now| atm| at the moment)? (?:is|has to be|would be|would have to be|was always|remains|are)\s+){NAME}")
FAVORED = re.compile(rf"{NAME}(?i: (?:is|are|was|has always been|will always be) (?:still |definitely |probably |easily |honestly |hands down )?my (?:all[- ]time |absolute |personal |current |top |favou?rite |most favou?rite )*(?:favou?rite|fave|fav|goat)(?: ({KIND_WORDS}))?\b)")
FAN = re.compile(rf"(?i:\b(?:i'm|im|i am) (?:an? )?(?:huge|big|massive|die[- ]?hard|lifelong|life[- ]long|long[- ]?time|proud|loyal|true|real|giant|enormous|devoted) ){NAME}(?i: (?:fan|supporter|stan)\b)")
MAIN = re.compile(rf"(?i:\bi (?:main|mained|play as|always play as) ){NAME}")
SPORTS = re.compile(r"(?i:fc|united|city|athletic|rovers|wanderers|lakers|celtics|yankees|dodgers|cowboys|patriots|packers|eagles|giants|warriors|bulls|knicks|chiefs|steelers|bears|"
                    r"49ers|niners|raiders|ravens|broncos|seahawks|rams|jets|dolphins|bills|lions|vikings|saints|falcons|panthers|buccaneers|bucs|titans|colts|texans|jaguars|"
                    r"browns|bengals|chargers|cardinals|commanders|red sox|cubs|mets|astros|braves|phillies|padres|mariners|blue jays|orioles|twins|tigers|royals|rangers|"
                    r"brewers|pirates|reds|rockies|marlins|nationals|white sox|guardians|athletics|heat|nets|bucks|suns|mavericks|mavs|nuggets|spurs|rockets|thunder|jazz|"
                    r"clippers|kings|pelicans|grizzlies|hawks|hornets|pistons|pacers|cavaliers|cavs|magic|wizards|raptors|76ers|sixers|timberwolves|wolves|blazers|"
                    r"maple leafs|leafs|canadiens|habs|bruins|oilers|flames|canucks|penguins|flyers|blackhawks|red wings|avalanche|lightning|capitals|islanders|devils|sabres|"
                    r"senators|jets|kraken|predators|stars|blues|wild|ducks|sharks|golden knights|arsenal|chelsea|liverpool|tottenham|spurs|everton|barcelona|real madrid|"
                    r"juventus|bayern|dortmund|psg|ajax|celtic|rangers|milan|inter|napoli|roma|benfica|porto|galatasaray|fenerbahce|boca|river plate)\b")
POSITIVE = re.compile(r"(?i:\bi (?:really |absolutely |just |also |still |honestly |totally |seriously |genuinely |do |personally )?(?:love|loved|adore|adored|enjoy|enjoyed|like|liked|dig|recommend|second|rewatched|replayed)\b|"
                      r"\bi'?m (?:so |really |totally |kinda |completely )?(?:obsessed with|addicted to|into|a (?:huge |big )?fan of|hooked on|in love with)\b|\bcan'?t get enough of\b|"
                      r"\bmy (?:all[- ]time |absolute |personal |current |top )?(?:favou?rites?|faves?|favs?)\b|\bfell in love with\b|"
                      r"\b(?:is|are|was|were) (?:so |really |very |absolutely |just |still |honestly |such an? |pretty |easily |definitely |by far )?(?:good|great|amazing|awesome|excellent|fantastic|"
                      r"underrated|underappreciated|goated|incredible|perfect|beautiful|fun|peak|fire|the goat|the best|my jam|a banger|bangers|a masterpiece|a classic|brilliant|"
                      r"phenomenal|gorgeous|lovely|wonderful|so fun)\b|\b(?:been|currently|finally|started) (?:playing|watching|listening to|reading|bingeing|binging|replaying|rewatching)\b|"
                      r"\bfor me\b|\bmine is\b|\bhands down\b|\bthe goat\b|\bi'?m (?:playing|watching|listening to|reading|replaying|rewatching)\b)")
NEGATIVE = re.compile(r"(?i:\b(?:hate|hated|don'?t like|didn'?t like|not a fan|dislike|overrated|boring|worst|trash|garbage|sucks|terrible|awful|meh|never (?:played|watched|liked))\b)")
CONTEXTS = {
    "video_game": re.compile(r"(?i:\b(?:games?|gaming|gamer|play|played|playing|playthrough|steam|xbox|playstation|ps[1-5]|switch|nintendo|console|dlc|boss|bosses|speedrun|multiplayer|co-?op|rpg|jrpg|mmo|mmorpg|fps|roguelike|patch|grind|raid|quest|controller|remake|remaster|sequel|campaign|achievements?|platinum)\b)"),
    "franchise": re.compile(r"(?i:\b(?:show|shows|series|season|seasons|episode|episodes|anime|manga|movie|movies|film|films|watch|watched|watching|rewatch|rewatching|binge|tv|netflix|hbo|disney|sitcom|cartoon|comic|comics|trilogy|franchise|novel|novels|books?)\b)"),
    "artist": re.compile(r"(?i:\b(?:songs?|albums?|band|bands|music|concerts?|tour|listen|listened|listening|tracks?|singer|rapper|vinyl|ep|lp|spotify|lyrics|discography|gig|setlist|live show|banger|bangers|vocals|guitarist|drummer)\b)"),
    "character": re.compile(r"(?i:\b(?:character|characters|main|maining|mains|waifu|husbando|ship|shipped|arc|villain|protagonist|cosplay|pokemon|pokémon|hero|heroes|champion|skin)\b)"),
    "author": re.compile(r"(?i:\b(?:author|authors|novelist|writer)\b)"),
    "creator": re.compile(r"(?i:\b(?:streamer|streams|streaming|twitch|youtuber|youtube channel|podcast|podcasts|podcaster|vlogs?)\b)"),
}
CANDIDATE = re.compile(r"(?<![\w'])((?:[A-Z][\w'&:.!+-]*|\d+[a-z]*)(?: (?:of|the|and|&|de|la|vs\.?|in|on|a|to|no|[A-Z0-9][\w'&:.!+-]*))*)|[\"“]([^\"”\n]{2,40})[\"”]")
COMMON = frozenset("i i'm im i've i'd i'll it it's its the this that these those my me mine we our you your he she they them his her their a an and but or so if when what why how where who which "
                   "yes no yeah yep nope ok okay lol lmao omg oh hey hi hello thanks thank also just honestly literally well not then there here now today tomorrow yesterday "
                   "love loved great best good amazing awesome edit update tldr tl;dr op reddit google youtube god jesus christmas monday tuesday wednesday thursday friday saturday "
                   "sunday january february march april may june july august september october november december english american nta yta esh nah imo imho idk tbh btw "
                   "definitely probably maybe sure same agreed true right wow damn dude bro man guys please sorry what's that's there's".split())


def fandom(text, found):
    for sentence in re.finditer(r"[^.!?\n]+[.!?]*", text):
        part = sentence.group()
        if not (cue := POSITIVE.search(part)) or NEGATIVE.search(part):
            continue
        if hedged(part.lower(), cue.start(), cue.end(), SELF_HEDGE):
            continue
        first = len(part) - len(part.lstrip())
        names = []
        for match in CANDIDATE.finditer(part):
            name = (match.group(1) or match.group(2)).strip()
            words = name.lower().split()
            if words and words[0] in COMMON:
                name, words = " ".join(name.split()[1:]), words[1:]
            if not words or not LETTERS.search(name) or re.fullmatch(r"[\d\W]*\w?\d[\w-]*", name):
                continue
            if len(words) == 1 and (words[0] in COMMON or len(name) < 4 or match.start() == first or re.search(rf"(?<![\w'])(?-i:{re.escape(words[0])})(?![\w'])", text)):
                continue
            if cue.start() <= match.start() < cue.end():
                continue
            window = part[max(0, match.start() - 80):match.end() + 80]
            kinds = {kind: 3 * len(pattern.findall(window)) + len(pattern.findall(part)) for kind, pattern in CONTEXTS.items()}
            kind = max(kinds, key=kinds.get)
            if kinds[kind]:
                names.append((abs(match.start() - cue.start()), kind, name))
        for _, kind, name in sorted(names)[:2]:
            named(kind, name, found, sentence.start())


ADJACENT = re.compile(r"\b(?:i (?:really |absolutely |just |also |still |honestly |do |genuinely )?(?:love|loved|adore|adored|enjoy|enjoyed)|obsessed with|addicted to|can'?t get enough of|a (?:huge |big |massive )?fan of|in love with|hooked on|"
                      r"my (?:all[- ]time |absolute |personal )?(?:favou?rite|fave|fav)(?: \w+)? (?:is|has to be|would be|was)|i'?m (?:currently |still |also )?(?:playing|watching|reading|listening to|replaying|rewatching|bingeing|binging)|"
                      r"i'?ve been (?:playing|watching|reading|listening to|replaying|rewatching|bingeing|binging|obsessed with)|i (?:just )?(?:finished|beat|started) (?:playing |watching |reading )?)\s+"
                      r"((?:the )?[\w'&:.!+-]+(?: [\w'&:.!+-]+){0,4}?)(?=\s*(?:[.,!?;:)\n]|$)| (?:and|but|so|because|it|is|was|lol|too|again|right|atm|lately|recently|these|since|for|with|on|in|at|when|while|haha|tbh|honestly|now|today)\b)")
GENERIC = frozenset("it this that these those him her them you me my your his their our how when being having to a an some any all every everything anything something nothing games game gaming music songs song anime "
                    "shows show movies movie films film books book reading watching playing food sex cock dick pussy ass porn people men women guys girls kids dogs cats animals life it's them. "
                    "him. you. that. this. here there out up down so very much more most doing going getting seeing playing talking working".split())


def adjacent(text, found):
    lowered = text.lower()
    for match in ADJACENT.finditer(lowered):
        name = re.sub(r"^the ", "", match.group(1)).strip()
        words = name.split()
        if not words or words[0] in GENERIC or words[-1] in GENERIC or words[0] in COMMON or len(name) < 3 or not LETTERS.search(name) or hedged(lowered, match.start(), match.end(), SELF_HEDGE) or NEGATIVE.search(lowered[match.start():match.end() + 40]):
            continue
        part = text[max(0, match.start() - 150):match.end() + 150]
        kinds = {kind: 3 * len(pattern.findall(part)) + len(pattern.findall(text)) for kind, pattern in CONTEXTS.items()}
        kind = max(kinds, key=kinds.get)
        if kinds[kind]:
            named(kind, name, found, match.start())


def favorites(text, found):
    for pattern in (FAVORITE, FAVORED):
        for match in pattern.finditer(text):
            name, kind = (match.group(2), match.group(1)) if pattern is FAVORITE else (match.group(1), match.group(2))
            attribute = KINDS.get((kind or "").lower())
            if attribute and not hedged(text.lower(), match.start(), match.end(), SELF_HEDGE):
                named(attribute, name, found, match.start())
    for match in FAN.finditer(text):
        if SPORTS.search(match.group(1)) and not hedged(text.lower(), match.start(), match.end(), SELF_HEDGE):
            named("sports_team", match.group(1), found, match.start())
    for match in MAIN.finditer(text):
        if not hedged(text.lower(), match.start(), match.end(), SELF_HEDGE):
            named("character", match.group(1), found, match.start())
    known(text, found)


def named(attribute, name, found, position):
    name = TRAILING.sub("", name).strip()
    if 1 < len(name) <= 40 and (value := fan_value(attribute, name.lower())):
        found.setdefault((attribute, value), position)


GAMES = """minecraft;fortnite;roblox;league of legends|LoL;valorant;overwatch|overwatch 2;counter-strike|counter strike|cs2|csgo|cs:go|cs 2;dota 2|dota;
grand theft auto|gta|gta v|gta 5|gta online|gta iv|gta san andreas|grand theft auto v;grand theft auto vi|gta 6|gta vi|gta six;red dead redemption|red dead|red dead redemption 2|rdr2;
elden ring;dark souls|dark souls 3|dark souls iii;bloodborne;sekiro;demon's souls;armored core;the witcher|the witcher 3|witcher 3;cyberpunk 2077|cyberpunk;skyrim;Oblivion;morrowind;
fallout 4;fallout new vegas|new vegas;fallout 76;fallout 3;starfield;baldur's gate 3|bg3;baldur's gate;divinity original sin|divinity: original sin;mass effect;dragon age;Halo;
call of duty|CoD|warzone|black ops|modern warfare;Battlefield;apex legends|Apex;pubg;rainbow six siege|r6 siege|rainbow six;destiny 2|Destiny;The Division;
borderlands|borderlands 2|borderlands 3;bioshock;Half-Life|Half Life|half-life 2;portal 2|Portal;team fortress 2|tf2;left 4 dead|l4d2;garry's mod|gmod;terraria;stardew valley|stardew;
animal crossing;the legend of zelda|zelda|breath of the wild|botw|tears of the kingdom|totk|ocarina of time|majora's mask|twilight princess|wind waker|skyward sword;
mario kart;super mario odyssey;super mario bros|super mario;super smash bros|smash bros|smash ultimate|super smash bros ultimate;metroid|metroid prime;Kirby;splatoon;
xenoblade|xenoblade chronicles;fire emblem;persona 5|p5r|persona 4|persona 3;final fantasy vii|ff7|ffvii|final fantasy 7;final fantasy xiv|ffxiv|ff14;final fantasy xvi|ff16;
kingdom hearts;dragon quest;monster hunter|monhun|mhw|monster hunter world|monster hunter wilds|monster hunter rise;resident evil 4|re4;silent hill 2;metal gear solid|mgs;death stranding;
street fighter|street fighter 6|sf6;tekken|tekken 8;mortal kombat;guilty gear;god of war;The Last of Us|Last of Us|tlou;Uncharted;horizon zero dawn|horizon forbidden west;ghost of tsushima;
hollow knight|silksong;Celeste;Hades|hades ii|hades 2;dead cells;the binding of isaac|binding of isaac|tboi;enter the gungeon;slay the spire;balatro;undertale;deltarune;cuphead;
ori and the blind forest|ori and the will of the wisps;risk of rain|risk of rain 2;noita;factorio;Satisfactory;rimworld;subnautica;no man's sky;valheim;Rust;dayz|day z;
escape from tarkov|tarkov;hunt showdown|hunt: showdown;dead by daylight|DBD;phasmophobia;lethal company;Among Us;fall guys;rocket league;fifa|ea fc|ea sports fc;Madden;nba 2k;
gran turismo;forza horizon|forza horizon 5|forza horizon 6|forza motorsport|forza;Need for Speed;the sims|the sims 4|sims 4|Sims;Civilization|civ 6|civ vi|civ 7;stellaris;crusader kings|ck3;
europa universalis|eu4;hearts of iron|hoi4;Total War|total war: warhammer;age of empires|aoe2|age of empires ii;starcraft|starcraft ii|starcraft 2|sc2;warcraft iii|warcraft 3;diablo|diablo iv|diablo 4|diablo ii|diablo 2;
path of exile|path of exile 2|PoE|poe2;world of tanks;war thunder;eve online;runescape|osrs|old school runescape;guild wars 2|guild wars;elder scrolls online|ESO;black desert online|black desert;
lost ark;genshin impact|genshin;honkai star rail|honkai: star rail|hsr;honkai impact;zenless zone zero|ZZZ;wuthering waves;arknights;fate/grand order|fgo;blue archive;limbus company;
goddess of victory: nikke|nikke;azur lane;clash of clans;clash royale;brawl stars;candy crush;hearthstone;marvel rivals;marvel snap;Smite;heroes of the storm;teamfight tactics|TFT;
warframe;the first descendant|TFD;helldivers 2|helldivers;deep rock galactic|DRG;sea of thieves;palworld;ark survival evolved|ark: survival evolved|ark survival ascended;doom eternal|Doom|DOOM;
Quake;wolfenstein;Far Cry|far cry 5|far cry 3;assassin's creed;watch dogs;tomb raider;Hitman;Dishonored;Deus Ex;alan wake|alan wake 2;max payne;Sleeping Dogs;saints row;
Dying Light;dead island;Dead Space;the outer worlds;kingdom come deliverance|kingdom come: deliverance;mount & blade|mount and blade|bannerlord;ghost recon;titanfall|titanfall 2;
star wars jedi|jedi survivor|jedi fallen order;knights of the old republic|kotor;star wars battlefront|battlefront 2|battlefront ii;star wars: the old republic|swtor;lego star wars;
batman arkham|arkham city|arkham knight|arkham asylum;marvel's spider-man|spider-man 2;nier automata|nier: automata|nier replicant;ace attorney;danganronpa|danganronpa 2|danganronpa v3;
doki doki literature club|ddlc;five nights at freddy's|fnaf;friday night funkin|fnf;geometry dash;osu!;beat saber;vrchat;half-life alyx;detroit become human|detroit: become human;
Life is Strange|Life Is Strange;Until Dawn;Heavy Rain;disco elysium;outer wilds;inscryption;return of the obra dinn;papers please|papers, please;It Takes Two;cult of the lamb;Don't Starve;spiritfarer;
Stray;Tunic;dave the diver;vampire survivors;brotato;Dredge;pizza tower;ultrakill;hotline miami;katana zero;sonic frontiers|sonic adventure 2|sonic mania;crash bandicoot;
spyro;ratchet & clank|ratchet and clank;jak and daxter;sly cooper;Yakuza|yakuza 0|Like a Dragon;shin megami tensei|smt v;octopath traveler;chrono trigger;earthbound;mother 3;
dragon ball xenoverse 2|xenoverse 2|dragon ball xenoverse;dragon ball fighterz;dragon ball sparking zero|sparking zero;xcom 2|xcom;darkest dungeon;frostpunk;cities: skylines|cities skylines;
planet coaster;rollercoaster tycoon;simcity;euro truck simulator 2|euro truck simulator|ets2;microsoft flight simulator|msfs;kerbal space program|ksp;arma 3|Arma;hell let loose;
insurgency sandstorm;Ready or Not;payday 2|payday 3;gears of war;Fable;halo infinite;Overcooked;mario party;luigi's mansion;donkey kong country;pikmin;tetris;pac-man;
street fighter iii: third strike;world of warships;mechwarrior;battletech;dwarf fortress;project zomboid|zomboid;7 days to die;sons of the forest;green hell;
dyson sphere program;oxygen not included;core keeper;my time at portia;disney dreamlight valley|dreamlight valley;infinity nikki;love and deepspace;Second Life;club penguin;neopets;
maplestory;ragnarok online;Tibia;albion online;metal gear solid 2|mgs2;metal gear solid 3|mgs3|snake eater;metal gear solid v|mgsv|phantom pain;devil may cry|dmc5|devil may cry 5;
bayonetta;splatoon 3;pokemon go|pokémon go;pokemon scarlet|pokémon scarlet|pokemon violet|pokemon legends arceus|pokemon legends z-a|pokemon sword|pokemon shield;
the elder scrolls v: skyrim;mega man|megaman;castlevania;animal crossing new horizons|acnh;super mario 64|mario 64;super mario galaxy|mario galaxy;the legend of zelda: breath of the wild"""

SERIES = """pokemon|pokémon|Pokemon|Pokémon;final fantasy;world of warcraft|WoW|warcraft;resident evil;the elder scrolls|elder scrolls;prince of persia;
the witcher|witcher;Fallout;Persona;metal gear;sonic the hedgehog"""

FRANCHISES = """star wars|star wars rogue one|rogue one|the mandalorian|mandalorian|Mando|Andor|the clone wars|clone wars;star trek;Marvel|mcu|marvel cinematic universe;harry potter;
lord of the rings|lotr|the lord of the rings|the hobbit|rings of power;game of thrones|a song of ice and fire|asoiaf|house of the dragon;james bond|007;Mission Impossible|Mission: Impossible;
Fast and Furious|Fast & Furious|fast & furious;jurassic park|jurassic world;indiana jones;Back to the Future;The Matrix|Matrix;Terminator;Rocky;john wick;pirates of the caribbean;
Transformers;godzilla;gamera;king kong;mad max;toy story;shrek;the godfather;pulp fiction;kill bill;Scream;nightmare on elm street;the conjuring;
The Office;seinfeld;breaking bad;better call saul;the sopranos|sopranos;The Wire;mad men;the walking dead|twd;Stranger Things;the simpsons|simpsons;family guy;
south park;futurama;rick and morty;bojack horseman|bojack;avatar the last airbender|avatar: the last airbender|atla|the legend of korra|legend of korra;Adventure Time;gravity falls;
steven universe;spongebob|spongebob squarepants;Bluey;peppa pig;Arcane;The Boys;Invincible;Succession;Severance;The Bear;ted lasso;
doctor who;Sherlock;downton abbey;peaky blinders;black mirror;The Crown;grey's anatomy;house md|House M.D.;Scrubs;how i met your mother|himym;parks and recreation|parks and rec;
brooklyn nine-nine|brooklyn 99|b99;Arrested Development;it's always sunny in philadelphia|Always Sunny|iasip;curb your enthusiasm|Curb;30 rock;Frasier;
The Big Bang Theory|Big Bang Theory;Modern Family;New Girl;schitt's creek;The Good Place;abbott elementary;what we do in the shadows;sons of anarchy;Yellowstone;
Ozark;Dexter;true detective;twin peaks;the x-files|x-files;buffy the vampire slayer|buffy;Supernatural;smallville;the vampire diaries|vampire diaries;
gilmore girls;one tree hill;gossip girl;pretty little liars;Euphoria;bridgerton;Outlander;the handmaid's tale;westworld;The Expanse;battlestar galactica;
babylon 5;Firefly;stargate;wheel of time|the wheel of time;Shogun|Shōgun;chicago fire;chicago pd|chicago p.d.;chicago med;Law & Order|Law and Order;criminal minds;NCIS;CSI;
american horror story;squid game;money heist;the umbrella academy|umbrella academy;Daredevil;Loki;wandavision;agents of shield;The Flash;teen titans;
justice league;x-men|xmen|x men;avengers|the avengers;guardians of the galaxy;deadpool;Sandman;love island;rupaul's drag race|Drag Race;Top Gear;mr. show|mr show;
saturday night live|SNL;mystery science theater 3000|mst3k;anne with an e;eastenders;coronation street;emmerdale;Neighbours;Home and Away;Red Dwarf;blackadder;
fawlty towers;the inbetweeners;Peep Show;gavin and stacey;only fools and horses;derry girls;Love Is Blind|Love is Blind;mythbusters;One Piece;naruto|boruto|naruto shippuden;Bleach;
dragon ball|dragon ball z|dbz|dragon ball super|dragonball;attack on titan|shingeki no kyojin|snk|SNK|aot|AoT;my hero academia|mha|MHA|boku no hero academia|bnha;demon slayer|kimetsu no yaiba;
jujutsu kaisen|jjk|JJK;chainsaw man;hunter x hunter|hxh;fullmetal alchemist|fma|fmab|fullmetal alchemist brotherhood;death note;neon genesis evangelion|evangelion;cowboy bebop;
spy x family|spy family;one punch man|one-punch man;mob psycho 100|mob psycho;jojo's bizarre adventure|jojo|jjba;sailor moon;spirited away;my neighbor totoro|totoro;howl's moving castle;
princess mononoke;frieren|sousou no frieren|frieren: beyond journey's end;solo leveling;tokyo ghoul;Berserk;vinland saga;Vagabond;haikyuu|haikyu;kuroko no basket;blue lock;
Slam Dunk;hajime no ippo;code geass;steins gate;gurren lagann;kill la kill;fairy tail;black clover;sword art online|SAO;re:zero|re zero;konosuba;Overlord;
mushoku tensei|jobless reincarnation;that time i got reincarnated as a slime|tensura;the rising of the shield hero|shield hero;dr. stone|dr stone;the promised neverland;made in abyss;
violet evergarden;your lie in april;clannad;toradora;oshi no ko;kaguya-sama|kaguya sama;bocchi the rock;k-on;lucky star;gintama;yu yu hakusho;inuyasha;ranma 1/2;cardcaptor sakura;
yu-gi-oh|yugioh|yu gi oh;digimon;beyblade;gundam|mobile suit gundam;macross;ghost in the shell;dandadan|dan da dan;kaiju no. 8|kaiju no 8;sakamoto days;the apothecary diaries;
dungeon meshi|delicious in dungeon;ranking of kings;to your eternity;land of the lustrous;sleepy princess in the demon castle;the misfit of demon king academy|misfit of the demon king academy;
unnamed memory;mushishi;natsume's book of friends;fruits basket;ouran high school host club;hellsing;Trigun;samurai champloo;durarara;bungo stray dogs;black butler;blue exorcist;
soul eater;noragami;Seven Deadly Sins;assassination classroom;horimiya;my dress-up darling;yuri on ice;banana fish;omniscient reader's viewpoint|omniscient reader|orv;tower of god;
the beginning after the end|tbate;lookism;the hunger games|hunger games;Twilight;percy jackson;the chronicles of narnia|narnia;his dark materials;discworld;the stormlight archive|stormlight;
mistborn;cosmere;Dune;the dark tower;throne of glass;a court of thorns and roses|acotar;fourth wing;the empyrean;zodiac academy;Divergent;the maze runner|maze runner;sherlock holmes;
the hitchhiker's guide to the galaxy|hitchhiker's guide;Goosebumps;diary of a wimpy kid;dungeons and dragons|dungeons & dragons|d&d|dnd|DnD;warhammer 40k|warhammer 40,000|warhammer;
magic: the gathering|magic the gathering|MTG;the secret garden;anne of green gables;Little Women;pride and prejudice;the great gatsby;to kill a mockingbird;red rising;
spider-man|spiderman|spider-verse;Batman;Superman;the dark knight;doctor strange;captain america;iron man;
the twilight zone;the muppets;sesame street;my little pony|mlp;bob's burgers;King of the Hill;Archer;the venture bros;regular show;over the garden wall;the amazing world of gumball|gumball;
she-ra;voltron;samurai jack;dexter's laboratory;powerpuff girls;scooby-doo|scooby doo;looney tunes;tom and jerry;the flintstones;the jetsons"""

CHARACTERS = """Mario;Luigi;princess peach|Peach;Bowser;Yoshi;Link;ganondorf|Ganon;samus|samus aran;donkey kong;pikachu;charizard;bulbasaur;ivysaur;venusaur;
charmander;charmeleon;squirtle;wartortle;blastoise;butterfree;Pidgeot;Rattata;Fearow;Ekans;Arbok;Raichu;sandslash;Nidoking;Nidoqueen;clefairy;Clefable;Vulpix;ninetales;jigglypuff;
Zubat;Golbat;Oddish;Vileplume;Venomoth;Diglett;meowth;Psyduck;Golduck;Mankey;Primeape;growlithe;arcanine;Poliwag;poliwrath;Kadabra;alakazam;Machop;machamp;bellsprout;
Tentacool;tentacruel;Geodude;Graveler;Ponyta;Rapidash;slowpoke;Slowbro;Magnemite;Magneton;farfetch'd;Dodrio;Dewgong;Grimer;Cloyster;Gastly;Haunter;gengar;Onix;Drowzee;
Krabby;Kingler;Voltorb;exeggutor;Cubone;Marowak;hitmonlee;hitmonchan;lickitung;Koffing;Weezing;Rhyhorn;Rhydon;Chansey;Tangela;kangaskhan;Horsea;Seadra;Goldeen;Seaking;
Staryu;Starmie;Mr. Mime;scyther;Jynx;electabuzz;Magmar;Pinsir;Tauros;magikarp;gyarados;Lapras;eevee;vaporeon;jolteon;flareon;Porygon;Omanyte;Omastar;Kabutops;Aerodactyl;
snorlax;articuno;zapdos;moltres;Dratini;dragonair;dragonite;mewtwo;Mew;lucario;greninja;umbreon;espeon;sylveon;glaceon;leafeon;gardevoir;blaziken;sceptile;swampert;mudkip;torchic;
treecko;chikorita;cyndaquil;totodile;typhlosion;feraligatr;meganium;piplup;chimchar;turtwig;infernape;empoleon;torterra;garchomp;rayquaza;lugia;ho-oh;kyogre;groudon;dialga;palkia;
giratina;arceus;darkrai;tyranitar;scizor;metagross;salamence;Absol;mimikyu;rowlet;litten;popplio;decidueye;incineroar;primarina;grookey;scorbunny;sobble;cinderace;sprigatito;fuecoco;
quaxly;meowscarada;skeledirge;quaquaval;koraidon;miraidon;togepi;marill;wooper;mareep;ampharos;chimecho;bouffalant;sigilyph;zoroark;hydreigon;volcarona;chandelure;lopunny;
Sonic;Tails;Knuckles;shadow the hedgehog;Kratos;master chief;lara croft;geralt|geralt of rivia;Ciri;yennefer;cloud strife;sephiroth;tifa|tifa lockhart;aerith;
leon kennedy|leon s. kennedy;jill valentine;ada wong;solid snake;arthur morgan;john marston;nathan drake;kazuma kiryu|Kiryu;goro majima|Majima;
astarion;shadowheart;karlach;minthara;lae'zel;garrus|garrus vakarian;tali'zorah;commander shepard;glados;gordon freeman;Sans;Papyrus;undyne;toriel;
zagreus;Monika;sayori;Natsuki;raiden shogun|raiden ei;zhongli;Venti;hu tao;kujou sara;ganyu;childe|tartaglia;Klee;paimon;furina;neuvillette;
nahida;kazuha;Xiao;diluc;kaeya;Albedo;ayaka;yae miko;Tracer;Mercy;Genji;Hanzo;reinhardt;d.va;widowmaker;soldier 76|soldier: 76;lúcio;
kiriko;Ahri;yasuo;Jinx;teemo;ezreal;thresh;lee sin;monkey d. luffy|luffy;roronoa zoro|Zoro;sanji;usopp;tony tony chopper;nico robin;
jinbe;Shanks;portgas d. ace;dracule mihawk|mihawk;whitebeard;Kaido;naruto uzumaki;sasuke|sasuke uchiha;sakura haruno;kakashi;itachi|itachi uchiha;
hinata hyuga;gaara;goku|son goku;vegeta;gohan;piccolo;frieza;eren yeager|eren jaeger|Eren;mikasa|mikasa ackerman;levi ackerman;armin|armin arlert;erwin smith;hange zoe;
izuku midoriya|Deku;bakugo|katsuki bakugo|bakugou;shoto todoroki|todoroki;all might;dabi;tomura shigaraki|shigaraki;tamaki amajiki;satoru gojo|Gojo;
ryomen sukuna|sukuna;yuji itadori|itadori;megumi fushiguro;nobara kugisaki;tanjiro|tanjiro kamado;nezuko;zenitsu;inosuke;rengoku;gon freecss;killua|killua zoldyck;
hisoka;chrollo|chrollo lucilfer;kurapika;light yagami;ryuk;edward elric;alphonse elric;roy mustang;spike spiegel;shinji ikari;asuka langley;anya forger;
loid forger;yor forger;Saitama;Reigen;makima;Denji;griffith;thorfinn;askeladd;jotaro|jotaro kujo;dio brando;giorno;josuke;usagi tsukino;
kaguya shinomiya;marin kitagawa;subaru natsuki;megumin;kirito;asuna;rimuru;ainz ooal gown|Ainz;senku;vash the stampede;kagome;sesshomaru;bruce wayne;
clark kent;wonder woman;peter parker|miles morales;tony stark;steve rogers;Wolverine;Storm;
jean grey;magneto;professor x;Gambit;emma frost;harley quinn;the joker|Joker;catwoman;supergirl;nightwing;starfire;beast boy;darth vader;luke skywalker;han solo;
princess leia;Yoda;obi-wan kenobi|obi-wan;anakin skywalker|Anakin;ahsoka|ahsoka tano;grogu|baby yoda;boba fett;kylo ren;chewbacca;r2-d2;c-3po;hermione|hermione granger;
ron weasley;dumbledore;severus snape|snape;draco malfoy;voldemort;hagrid;sirius black;luna lovegood;molly weasley;gandalf;frodo|frodo baggins;aragorn;legolas;gimli;gollum;
sauron;bilbo baggins;tyrion|tyrion lannister;jon snow;daenerys|daenerys targaryen;arya stark;sansa stark;cersei;jaime lannister;Spock;jean-luc picard|Picard;
homer simpson;bart simpson;marge simpson;peter griffin;stewie griffin;rick sanchez;morty smith;patrick star;squidward;mickey mouse;bugs bunny;
Garfield;Snoopy;bandit heeler;Elsa;Olaf;buzz lightyear;michael scott;dwight schrute;jim halpert;walter white|heisenberg;
jesse pinkman;saul goodman;tony soprano;don draper;jax teller;frasier crane;jack sparrow;hannibal lecter;freddy krueger;jason voorhees;
michael myers;pennywise;ghostface;Pomni;Aang;Zuko;katara;toph;sokka;azula;silco;homelander;billy butcher;omni-man;
the thirteenth doctor|the tenth doctor|the eleventh doctor;hatsune miku;princess zelda"""

ARTISTS = """taylor swift;beyoncé|beyonce;Drake;kanye west|kanye;kendrick lamar|kendrick;eminem;jay-z;rihanna;ariana grande;billie eilish;lady gaga;bad bunny;the weeknd;
ed sheeran;harry styles;olivia rodrigo;sabrina carpenter;chappell roan;charli xcx;dua lipa;doja cat;SZA;travis scott;post malone;lana del rey;frank ocean;tyler, the creator|tyler the creator;
kali uchis;mitski;phoebe bridgers;boygenius;Hozier;arctic monkeys;radiohead;the beatles|beatles;the rolling stones|rolling stones;led zeppelin;pink floyd;Queen;Nirvana;pearl jam;
soundgarden;alice in chains;foo fighters;red hot chili peppers|rhcp;metallica;iron maiden;black sabbath;megadeth;Slayer;slipknot;system of a down|soad;linkin park;Green Day;
blink-182|blink 182;my chemical romance|MCR;fall out boy;panic! at the disco|panic at the disco;paramore;twenty one pilots;imagine dragons;coldplay;U2;Oasis;
The Smiths;The Cure;joy division;New Order;depeche mode;duran duran;tears for fears;The Killers;The Strokes;Muse;gorillaz;daft punk;tame impala;MGMT;vampire weekend;
bon iver;fleetwood mac;ABBA;bee gees;david bowie|Bowie;michael jackson;Madonna;whitney houston;mariah carey;elton john;billy joel;bruce springsteen|springsteen;
bob dylan;johnny cash;dolly parton;elvis presley|Elvis;frank sinatra;jimi hendrix;The Doors;ac/dc|acdc;guns n' roses|guns n roses;aerosmith;van halen;def leppard;bon jovi;
deftones;Korn;rage against the machine|ratm;bring me the horizon|bmth;sleep token;gojira;Mastodon;opeth;dream theater;avenged sevenfold;evanescence;Pixies;
sonic youth;R.E.M.;Talking Heads;cocteau twins;mazzy star;slowdive;my bloody valentine;Beach House;Sade;stevie wonder;marvin gaye;aretha franklin;bob marley;tupac|2pac;
notorious b.i.g.|biggie smalls;snoop dogg;dr. dre|dr dre;Ice Cube;50 Cent;lil wayne;nicki minaj;cardi b;megan thee stallion;j. cole|j cole;mac miller;
childish gambino;kid cudi;a$ap rocky|asap rocky;playboi carti;lil uzi vert;young thug;21 savage;metro boomin;juice wrld;xxxtentacion;mf doom;wu-tang clan|wu-tang;outkast;run the jewels;
death grips;BTS;blackpink;TWICE;Stray Kids;NewJeans|New Jeans|newjeans;itzy|ITZY;aespa;le sserafim;SEVENTEEN;enhypen;ateez;Red Velvet;BIGBANG;girls' generation;
babymetal;yoasobi;kenshi yonezu;Bad Omens;troye sivan;Lorde;Halsey;melanie martinez;marina and the diamonds;florence and the machine|florence + the machine;
lizzo;Adele;amy winehouse;sam smith;shawn mendes;justin bieber;selena gomez;miley cyrus;katy perry;britney spears;christina aguilera;kelly clarkson;demi lovato;jonas brothers;
One Direction;5 seconds of summer|5sos;backstreet boys;nsync;spice girls;destiny's child;bruno mars;justin timberlake;john mayer;mumford & sons;
the lumineers;noah kahan;zach bryan;morgan wallen;luke combs;chris stapleton;tyler childers;kacey musgraves;shania twain;garth brooks;carrie underwood;willie nelson;elliott smith;
neutral milk hotel;modest mouse;death cab for cutie;the front bottoms|front bottoms;Car Seat Headrest;alvvays;Japanese Breakfast;Clairo;beabadoobee;mac demarco;steve lacy;
rex orange county;Cigarettes After Sex;the neighbourhood;Glass Animals;hippo campus;Wallows;weezer;Nine Inch Nails;marilyn manson;rammstein;Falco;kraftwerk;
björk|bjork;kate bush;enya;sigur rós|sigur ros;aphex twin;skrillex;deadmau5;avicii;calvin harris;martin garrix;marshmello;Fred again..|Fred Again;porter robinson;madeon;Zedd;tiësto|tiesto;
david guetta;odesza;illenium;subtronics;grateful dead;Phish;dave matthews band;allman brothers;lynyrd skynyrd;creedence clearwater revival|CCR;
the beach boys|beach boys;simon & garfunkel|simon and garfunkel;neil young;tom petty;billy idol;joan jett;stevie nicks;sabaton;powerwolf;nightwish;judas priest;motörhead|motorhead;
ozzy osbourne;pantera;trivium;killswitch engage;Parkway Drive;spiritbox;polyphia;animals as leaders;king gizzard|king gizzard and the lizard wizard;
khruangbin;hiatus kaiyote;snarky puppy;thom yorke;mozart;beethoven;Bach;chopin;debussy;Ravel;tchaikovsky;vivaldi;liszt;rachmaninoff;brahms;schubert;mahler;
stravinsky;hans zimmer;joe hisaishi;nobuo uematsu;koji kondo;The Police;The Clash;sex pistols;ramones;the velvet underground;
iggy pop;patti smith;lou reed;leonard cohen;nick cave;tom waits;sufjan stevens;fiona apple;tori amos;alanis morissette;No Doubt;gwen stefani;The Cranberries;
The Smashing Pumpkins|Smashing Pumpkins;stone temple pilots;nickelback;3 doors down;three days grace;breaking benjamin;shinedown;five finger death punch;
papa roach;limp bizkit;Incubus;The Offspring;Bad Religion;Rise Against;A Day to Remember;Pierce the Veil;sleeping with sirens;Falling in Reverse;
Taking Back Sunday;Modern Baseball;Turnstile;Knocked Loose;The 1975;the xx;lcd soundsystem;
Arcade Fire;The Shins;fleet foxes;the decemberists;of monsters and men;jungkook;jimin;
jisoo;taeyeon;g-dragon;utada hikaru;radwimps;one ok rock;king crimson;jethro tull;Porcupine Tree;
steven wilson;the mars volta;coheed and cambria;deafheaven;meshuggah;the jackson 5;earth, wind & fire;james brown;ray charles;b.b. king;etta james;
nina simone;billie holiday;ella fitzgerald;louis armstrong;miles davis;john coltrane;duke ellington;thelonious monk;herbie hancock;the kinks;The Temptations"""

TEAMS = """arizona cardinals;atlanta falcons|Falcons;baltimore ravens|Ravens;buffalo bills|Bills;carolina panthers;chicago bears|Bears;cincinnati bengals|Bengals;cleveland browns|Browns;
dallas cowboys|Cowboys;denver broncos|Broncos;detroit lions;green bay packers|Packers;houston texans;indianapolis colts|Colts;jacksonville jaguars|Jaguars|Jags;kansas city chiefs|Chiefs;
las vegas raiders|oakland raiders|Raiders;los angeles chargers|Chargers;los angeles rams;miami dolphins|Dolphins;minnesota vikings|Vikings;new england patriots|Patriots|Pats;
new orleans saints|Saints;new york giants;new york jets;philadelphia eagles|Eagles;pittsburgh steelers|Steelers;san francisco 49ers|49ers|Niners;seattle seahawks|Seahawks;
tampa bay buccaneers|Buccaneers|Bucs;tennessee titans|Titans;washington commanders|Commanders;atlanta hawks;boston celtics|Celtics;brooklyn nets|Nets;charlotte hornets|Hornets;
chicago bulls|Bulls;cleveland cavaliers|Cavaliers|Cavs;dallas mavericks|Mavericks|Mavs;denver nuggets|Nuggets;detroit pistons|Pistons;golden state warriors|Warriors;
houston rockets|Rockets;indiana pacers|Pacers;los angeles clippers|Clippers;los angeles lakers|Lakers;memphis grizzlies|Grizzlies;miami heat;milwaukee bucks|Bucks;
minnesota timberwolves|Timberwolves;new orleans pelicans|Pelicans;new york knicks|Knicks;oklahoma city thunder|okc thunder|OKC;orlando magic;philadelphia 76ers|76ers|Sixers;
phoenix suns|Suns;portland trail blazers|trail blazers|Blazers;sacramento kings;san antonio spurs;toronto raptors|Raptors;utah jazz;washington wizards|Wizards;
arizona diamondbacks|Diamondbacks|D-backs;atlanta braves|Braves;baltimore orioles|Orioles;boston red sox|red sox;chicago cubs|Cubs;chicago white sox|white sox;cincinnati reds;
cleveland guardians|Guardians;colorado rockies;detroit tigers;houston astros|Astros;kansas city royals|Royals;los angeles angels;los angeles dodgers|Dodgers;miami marlins|Marlins;
milwaukee brewers|Brewers;minnesota twins;new york mets|Mets;new york yankees|Yankees;oakland athletics|A's;philadelphia phillies|Phillies;pittsburgh pirates;san diego padres|Padres;
san francisco giants;seattle mariners|Mariners;st. louis cardinals;tampa bay rays;texas rangers;toronto blue jays|blue jays;washington nationals|Nats;
anaheim ducks;boston bruins|Bruins;buffalo sabres|Sabres;calgary flames|Flames;carolina hurricanes|Canes;chicago blackhawks|Blackhawks;colorado avalanche|Avalanche|Avs;
columbus blue jackets|blue jackets;dallas stars;detroit red wings|red wings;edmonton oilers|Oilers;florida panthers;los angeles kings;minnesota wild;montreal canadiens|Canadiens|Habs;
nashville predators|Preds;new jersey devils;new york islanders;new york rangers;ottawa senators|Sens;philadelphia flyers;pittsburgh penguins;
san jose sharks;seattle kraken|Kraken;st. louis blues;tampa bay lightning;toronto maple leafs|maple leafs|Leafs;utah hockey club|utah mammoth;vancouver canucks|Canucks;
vegas golden knights|golden knights;washington capitals;winnipeg jets;Arsenal|Gunners;aston villa|Villa;Bournemouth;Brentford;brighton & hove albion|Brighton;
Burnley;Chelsea;crystal palace;Everton;Fulham;leeds united|Leeds;liverpool fc|Liverpool;manchester city|man city;manchester united|man united|man utd|Man U;newcastle united|Newcastle;
nottingham forest;Sunderland;tottenham hotspur|tottenham;west ham united|west ham;wolverhampton wanderers;leicester city;Southampton;ipswich town;
fc barcelona|Barcelona|Barca|barça;real madrid;atletico madrid|atlético madrid|atleti;Sevilla;real betis;valencia cf;athletic bilbao;real sociedad;villarreal;
bayern munich|bayern münchen|Bayern;borussia dortmund|Dortmund|BVB;bayer leverkusen|leverkusen;rb leipzig;eintracht frankfurt;schalke 04|Schalke;
juventus|juve;ac milan;inter milan|internazionale|Inter;Napoli;as roma|Roma;Lazio;atalanta;fiorentina;paris saint-germain|psg|PSG;olympique de marseille;olympique lyonnais;
Ajax;psv eindhoven|PSV;feyenoord;benfica;fc porto;sporting cp|sporting lisbon;Celtic;rangers fc;galatasaray;fenerbahce|fenerbahçe;besiktas;
boca juniors;river plate;flamengo;Corinthians;palmeiras;santos fc;club america|club américa;chivas;inter miami;la galaxy;lafc;seattle sounders;atlanta united;portland timbers;
chennai super kings|CSK;mumbai indians;royal challengers bengaluru|royal challengers bangalore|rcb|RCB;kolkata knight riders|KKR;sunrisers hyderabad|SRH;rajasthan royals;delhi capitals;
punjab kings;lucknow super giants;gujarat titans;alabama crimson tide|Crimson Tide;ohio state buckeyes|buckeyes;michigan wolverines;georgia bulldogs;texas longhorns|Longhorns;
notre dame fighting irish;lsu tigers;oregon ducks;clemson tigers;penn state nittany lions|nittany lions;duke blue devils;north carolina tar heels|tar heels;kentucky wildcats;
kansas jayhawks|jayhawks;uconn huskies;gonzaga bulldogs|gonzaga;washington state cougars;new york liberty;las vegas aces;indiana fever;chicago sky;
scuderia ferrari;red bull racing;toronto blue jays;All Blacks;Wallabies;springboks;team liquid;fnatic;cloud9;g2 esports"""

ATHLETES = """lebron james|lebron;michael jordan|Jordan;kobe bryant|Kobe;stephen curry|steph curry;kevin durant;giannis antetokounmpo|giannis;nikola jokic|nikola jokić|jokic|jokić;
luka doncic|luka dončić|doncic|dončić;shai gilgeous-alexander|SGA|Shai;victor wembanyama|wembanyama|wemby;jayson tatum;anthony edwards;ja morant;joel embiid|embiid;kawhi leonard|kawhi;
damian lillard;kyrie irving|kyrie;james harden;russell westbrook;chris paul;shaquille o'neal|shaq;tim duncan;dirk nowitzki;kareem abdul-jabbar;magic johnson;larry bird;allen iverson;
dwyane wade;caitlin clark;a'ja wilson;khris middleton;jimmy butler;devin booker;donovan mitchell;jalen brunson;paul george;klay thompson;draymond green;
lionel messi|messi;cristiano ronaldo|ronaldo|cr7;kylian mbappé|kylian mbappe|mbappe|mbappé;erling haaland|haaland;neymar;mohamed salah|Salah;kevin de bruyne|de bruyne|KDB;
harry kane;jude bellingham|bellingham;vinicius junior|vinicius jr|vini jr;robert lewandowski|lewandowski;luka modric|luka modrić|modric|modrić;zlatan ibrahimovic|zlatan;wayne rooney;
david beckham;thierry henry;zinedine zidane|zidane;ronaldinho;pelé|pele;diego maradona|maradona;johan cruyff;bukayo saka|Saka;martin ødegaard|odegaard|ødegaard;declan rice;cole palmer;
phil foden;lamine yamal|yamal;son heung-min;virgil van dijk|van dijk;trent alexander-arnold;antoine griezmann|griezmann;karim benzema|benzema;kaká;andrea pirlo;francesco totti;
paolo maldini;sergio ramos;andrés iniesta|iniesta;xavi hernandez;steven gerrard|gerrard;frank lampard;
tom brady;patrick mahomes|mahomes;josh allen;lamar jackson;joe burrow;jalen hurts;aaron rodgers;peyton manning;travis kelce|kelce;justin jefferson;saquon barkley;derrick henry;jerry rice;
joe montana;ja'marr chase;cj stroud;brock purdy;dak prescott;micah parsons;
shohei ohtani|ohtani;aaron judge;mike trout;babe ruth;derek jeter;mookie betts;juan soto;bryce harper;freddie freeman;clayton kershaw;paul skenes;ken griffey jr;
wayne gretzky|gretzky;connor mcdavid|mcdavid;sidney crosby;alexander ovechkin|alex ovechkin|ovechkin;auston matthews;nathan mackinnon|mackinnon;leon draisaitl|draisaitl;cale makar;
macklin celebrini|celebrini;connor bedard|bedard;mario lemieux;jaromir jagr|jaromír jágr|jagr;mitch marner;william nylander;james van riemsdyk;
roger federer|federer;rafael nadal|nadal;novak djokovic|djokovic;carlos alcaraz|alcaraz;jannik sinner;serena williams;venus williams;coco gauff;iga swiatek|iga świątek;aryna sabalenka;
tiger woods;rory mcilroy;scottie scheffler;lewis hamilton;max verstappen|verstappen;charles leclerc|leclerc;lando norris;fernando alonso;ayrton senna;michael schumacher;oscar piastri;
carlos sainz;sebastian vettel;kimi räikkönen|kimi raikkonen;usain bolt;simone biles;michael phelps;muhammad ali;mike tyson;floyd mayweather;conor mcgregor;jon jones;
khabib nurmagomedov|khabib;israel adesanya;canelo alvarez|canelo;tyson fury;anthony joshua;oleksandr usyk|usyk;virat kohli|kohli;ms dhoni|dhoni;sachin tendulkar;rohit sharma;
jasprit bumrah;babar azam;ben stokes;joe root;john cena;dwayne johnson|The Rock;roman reigns;cm punk;stone cold steve austin;The Undertaker;cody rhodes;seth rollins;rey mysterio;
magnus carlsen;hikaru nakamura;faker|Faker;s1mple"""

CELEBRITIES = """tom hanks;leonardo dicaprio;brad pitt;keanu reeves;tom cruise;johnny depp;robert downey jr;scarlett johansson;zendaya;timothée chalamet|timothee chalamet;pedro pascal;
ryan gosling;ryan reynolds;margot robbie;florence pugh;jennifer lawrence;meryl streep;denzel washington;morgan freeman;samuel l. jackson|samuel l jackson;will smith;jason momoa;
henry cavill;chris evans;chris hemsworth;chris pratt;tom holland;andrew garfield;tobey maguire;benedict cumberbatch;cillian murphy;christian bale;heath ledger;joaquin phoenix;
jack nicholson;al pacino;robert de niro;anthony hopkins;nicolas cage;jim carrey;adam sandler;jack black;jennifer aniston;julia roberts;sandra bullock;anne hathaway;emma stone;
emma watson;natalie portman;angelina jolie;nicole kidman;cate blanchett;viola davis;danny devito;steve carell;bill murray;robin williams;jeff goldblum;harrison ford;mark hamill;
sydney sweeney;jenna ortega;anya taylor-joy;paul mescal;jacob elordi;austin butler;glen powell;michael b. jordan;idris elba;oscar isaac;adam driver;willem dafoe;mads mikkelsen;
hugh jackman;ian mckellen;patrick stewart;kristen stewart;robert pattinson;daniel radcliffe;rupert grint;bryan cranston;aaron paul;bob odenkirk;jon hamm;kit harington;emilia clarke;
peter dinklage;millie bobby brown;steve buscemi;dave chappelle;kevin hart;john mulaney;bo burnham;bill burr;nate bargatze;taylor tomlinson;ricky gervais;jerry seinfeld;larry david;
conan o'brien|Conan;stephen colbert;jimmy fallon;john oliver;jon stewart;trevor noah;tina fey;amy poehler;will ferrell;steve martin;eddie murphy;chris rock;norm macdonald;nathan fielder;
tim robinson;kim kardashian;kylie jenner;kendall jenner;paris hilton;oprah winfrey|Oprah;gordon ramsay;martha stewart;bill nye;david attenborough;steve irwin;bob ross;fred rogers|mr. rogers|mister rogers;
anthony bourdain;guy fieri;nick offerman;aubrey plaza;jenna fischer;rainn wilson;john krasinski;paul rudd;seth rogen;jonah hill;michael cera;zac efron;dwayne the rock johnson;
rowan atkinson;hugh laurie;stephen fry;david tennant;jodie whittaker;peter capaldi;karen gillan;jenna coleman;olivia colman;judi dench;helen mirren;maggie smith;
emma thompson;kate winslet;keira knightley;orlando bloom;elijah wood;viggo mortensen;sean bean;sean connery;daniel craig;pierce brosnan;mel gibson;clint eastwood;
marilyn monroe;audrey hepburn;james dean;humphrey bogart;charlie chaplin;bruce lee;jackie chan;jet li;queen elizabeth;princess diana;prince harry;meghan markle"""

AUTHORS = """stephen king;j.k. rowling|jk rowling|j. k. rowling|rowling;j.r.r. tolkien|jrr tolkien|tolkien;george r.r. martin|george r. r. martin|grrm;brandon sanderson|sanderson;
terry pratchett|pratchett;neil gaiman|gaiman;agatha christie;jane austen;charles dickens;mark twain;ernest hemingway|hemingway;f. scott fitzgerald;george orwell|orwell;leo tolstoy|tolstoy;
fyodor dostoevsky|dostoevsky;franz kafka|kafka;haruki murakami|murakami;toni morrison;margaret atwood;kurt vonnegut|vonnegut;cormac mccarthy;ursula k. le guin|ursula le guin;
isaac asimov|asimov;frank herbert;philip k. dick;douglas adams;ray bradbury;h.p. lovecraft|hp lovecraft|lovecraft;edgar allan poe;arthur conan doyle;rick riordan;suzanne collins;
sarah j. maas|sarah j maas|SJM;rebecca yarros;colleen hoover;taylor jenkins reid;emily henry;sally rooney;donna tartt;john green;dan brown;james patterson;john grisham;lee child;
michael crichton;tom clancy;robert jordan;joe abercrombie;patrick rothfuss;robin hobb;steven erikson;brent weeks;pierce brown;r.f. kuang|rf kuang;andy weir;blake crouch;dean koontz;
anne rice;shirley jackson;octavia butler;n.k. jemisin;terry goodkind;raymond e. feist;david eddings;roald dahl;dr. seuss;c.s. lewis|cs lewis;lewis carroll;mary shelley;bram stoker;
oscar wilde;virginia woolf;william shakespeare|shakespeare;victor hugo;alexandre dumas;gabriel garcía márquez|gabriel garcia marquez;jorge luis borges;hunter s. thompson;
chuck palahniuk;bret easton ellis;jack kerouac;j.d. salinger;sylvia plath;maya angelou;khaled hosseini;kazuo ishiguro;ken follett;diana gabaldon;nora roberts;danielle steel;
jodi picoult;liane moriarty;gillian flynn;tana french;louise penny;ottessa moshfegh;ali hazelwood;jennifer l. armentrout;holly black;leigh bardugo;cassandra clare;
eiichiro oda;hajime isayama|isayama;masashi kishimoto|kishimoto;akira toriyama|toriyama;kentaro miura;junji ito;naoki urasawa;hirohiko araki;yoshihiro togashi|togashi;
tatsuki fujimoto;gege akutami;kohei horikoshi;stan lee;alan moore;frank miller;r.l. stine;judy blume;beverly cleary;lemony snicket;christopher paolini;veronica roth;
james s.a. corey;dennis lehane;stieg larsson;jo nesbø|jo nesbo;elena ferrante;salman rushdie;zadie smith;ian mcewan;john steinbeck|steinbeck;william faulkner;herman melville;
emily brontë|emily bronte;charlotte brontë|charlotte bronte;dante alighieri;albert camus|camus;jean-paul sartre;friedrich nietzsche|nietzsche;ayn rand;
v.e. schwab;tamsyn muir;martha wells;adrian tchaikovsky;john scalzi;dan simmons;iain m. banks;arthur c. clarke;robert a. heinlein|heinlein;larry niven;orson scott card"""

CREATORS = """mrbeast|mr beast;pewdiepie;markiplier;jacksepticeye;Dream;technoblade;xqc;pokimane;Ninja;Shroud;asmongold;hasan piker|hasanabi;kai cenat;ishowspeed;Ludwig;valkyrae;
sykkuno;corpse husband;tommyinnit;georgenotfound;sapnap;quackity;ranboo;philza;wilbur soot;captainsparklez;dantdm;jschlatt;moistcr1tikal|penguinz0;linus tech tips|LTT;mkbhd|marques brownlee;
casey neistat;philip defranco;kurzgesagt;veritasium;vsauce;mark rober;tom scott;cgp grey;3blue1brown;smarter every day;hbomberguy;contrapoints;philosophy tube;jacob geller;
internet historian;kitboga;jerma|jerma985;vinesauce;northernlion;dunkey|videogamedunkey;angry video game nerd|avgn;game grumps;rooster teeth;smosh;good mythical morning|rhett and link;
dude perfect;logan paul;jake paul;KSI;sidemen;emma chamberlain;james charles;jeffree star;david dobrik;shane dawson;joe rogan|Rogan;theo von;andrew schulz;call her daddy;
h3h3|ethan klein;Critical Role;dimension 20;brennan lee mulligan;matt mercer|matthew mercer;hololive;gawr gura;pekora;ironmouse;neuro-sama;summit1g;tyler1;sodapoppin;mizkif;
vaush;lirik;timthetatman;drlupo;cohhcarnage;dr disrespect;nickmercs;tfue;bugha;caedrel;kripparrian;day9;quin69;forsen;moonmoon;atrioc;fuslie;disguised toast;lilypichu;
amouranth;gothamchess|levy rozman;botez;zackrawrr;the try guys;yogscast;hermitcraft;grian;ldshadowlady;stampylongnose;ssundee;
sssniperwolf;dream smp;cr1tikal;danny gonzalez;drew gooden;kurtis conner;cody ko;noel miller;eddy burback;jenny nicholson;lindsay ellis;defunctland;
mrballen;nexpo;wendigoon;lemmino;jcs criminal psychology|jcs;coffeezilla;ryan trahan;airrack;mark wiens;binging with babish|babish;joshua weissman;kenji lopez-alt;
adam ragusea;Sorted Food;sam o'nella;OverSimplified;Extra Credits;The Dodo;yarnhub;tasting history;townsends;Forgotten Weapons;
the critical drinker|critical drinker;nostalgia critic;red letter media|redlettermedia;cinemasins;screen junkies;the film theorists|matpat"""

SPORTING = re.compile(r"(?i:\b(?:games?|season|seasons|playoffs?|fans?|coach|coaches|draft|drafted|trade|traded|league|finals?|rookie|roster|nba|nfl|mlb|nhl|mls|epl|premier league|"
                      r"champions league|la liga|serie a|bundesliga|ipl|cricket|football|soccer|basketball|baseball|hockey|rugby|tennis|golf|f1|formula 1|ufc|boxing|wwe|stadium|"
                      r"match|matches|scored|goals?|touchdowns?|innings|pitcher|quarterback|qb|striker|midfielder|defender|goalie|goalkeeper|super bowl|world cup|stanley cup|world series|"
                      r"mvp|all-star|dunk|three-pointer|hat trick|penalty|transfer|signing|manager|lineup|bench|starter|beat|won|win|wins|lost|losing|defeat|series|standings|seed|jersey)\b)")
ACTING = re.compile(r"(?i:\b(?:actor|actress|acting|movie|movies|film|films|role|roles|cast|casting|starred|starring|stars|show|series|comedian|comedy|stand-?up|special|"
                    r"hollywood|oscar|oscars|celebrity|celebrities|famous|interview|tv|netflix|hbo|scene|scenes|performance)\b)")
LEXICON_CONTEXT = {**CONTEXTS, "sports_team": SPORTING, "athlete": SPORTING, "celebrity": ACTING}
LEXICON_CONTEXT["character"] = re.compile(CONTEXTS["character"].pattern[:-4] + r"|games?|play|played|playing|anime|manga|show|series|movie|film|comics?|episode|season|story|lore|fanart|fan art|canon)\b)")
LEXICON_CONTEXT["artist"] = re.compile(CONTEXTS["artist"].pattern[:-4] + r"|sing|sings|sang|singing|playlist|records?|records|festival|fans?|stan)\b)")
LEXICON_CONTEXT["franchise"] = re.compile(CONTEXTS["franchise"].pattern[:-4] + r"|read|reading|fandom|canon|plot|characters?|finale|spinoff|reboot|adaptation)\b)")


def lexicon(block):
    folded, exact = {}, {}
    for entry in filter(None, (piece.strip() for piece in block.replace("\n", "").split(";"))):
        canonical, *aliases = entry.split("|")
        for alias in (canonical, *aliases):
            if alias == alias.lower():
                folded[alias] = canonical.lower()
            else:
                exact[alias] = canonical.lower()
    pattern = lambda table: "|".join(map(re.escape, sorted(table, key=len, reverse=True)))
    return re.compile(rf"(?<![\w'])(?:(?i:({pattern(folded)}))|({pattern(exact)}))(?!\w|'\w\w)"), folded, exact


LEXICONS = [(attributes, *lexicon(block)) for attributes, block in (
    (("video_game",), GAMES), (("video_game", "franchise"), SERIES), (("franchise",), FRANCHISES), (("character",), CHARACTERS), (("artist",), ARTISTS),
    (("sports_team",), TEAMS), (("athlete",), ATHLETES), (("celebrity",), CELEBRITIES), (("author",), AUTHORS), (("creator",), CREATORS))]


def opening(text, start):
    before = text[:start].rstrip(" \t\"'*(#>-_[")
    return not before or before[-1] in ".!?\n:"


SELF = re.compile(r"(?i:\b(?:i|i'm|im|i've|ive|i'd|i'll|my|me|mine|myself)\b)")
TEAM_SELF = re.compile(r"(?i:\b(?:i|i'm|im|i've|ive|my|me|we|we're|our|us|ours)\b)")
SHORT = 6
OPEN = frozenset({"franchise", "artist"})
ITEMS = re.compile(r"\s*(?:,|;|\||/|\band\b|&)\s*")


def engaged(text, start, end, attribute):
    left = max(text.rfind(mark, 0, start) for mark in ".!?\n") + 1
    right = min((found for found in (text.find(mark, end) for mark in ".!?\n") if found >= 0), default=len(text))
    sentence = text[left:right]
    if attribute in OPEN and SELF.search(text):
        return True
    if text[right:right + 1] == "?":
        return False
    if attribute == "video_game":
        sentence = text[max(0, left - 100):right + 100]
    return bool((TEAM_SELF if attribute == "sports_team" else SELF).search(sentence) or POSITIVE.search(sentence))


def known(text, found):
    spans = []
    for attributes, pattern, folded, exact in LEXICONS:
        for match in pattern.finditer(text):
            if match.group(1):
                if not (value := folded.get(match.group(1).lower())):
                    continue
            else:
                if (" " not in match.group(2) and opening(text, match.start())) or not all(LEXICON_CONTEXT[attribute].search(text) for attribute in attributes):
                    continue
                value = exact[match.group(2)]
            spans.extend((attribute, match.start(), match.end(), value) for attribute in attributes)
    for attribute, start, end, value in spans:
        if any(other == attribute and left <= start and end <= right and right - left > end - start for other, left, right, _ in spans):
            continue
        if engaged(text, start, end, attribute):
            named(attribute, value, found, start)
    listed(text, spans, found)


def pieces(text, start, end):
    cursor = start
    for separator in ITEMS.finditer(text, start, end):
        yield cursor, separator.start()
        cursor = separator.end()
    yield cursor, end


def lists(text):
    lines = [(line.start(), line.end()) for line in re.finditer(r"[^\n]*\S[^\n]*", text)]
    for start, end in lines:
        if len(items := list(pieces(text, start, end))) >= 3:
            yield items


def listed(text, spans, found):
    for items in lists(text):
        inside = [(attribute, left, right) for attribute, left, right, _ in spans if items[0][0] <= left and right <= items[-1][1]]
        if not inside:
            continue
        counts = {attribute: sum(other == attribute for other, _, _ in inside) for attribute, _, _ in inside}
        attribute = max(counts, key=counts.get)
        if counts[attribute] < 2 or attribute not in OPEN:
            continue
        for start, end in items:
            item = re.sub(r"^\W*(?:\d+[.)]\s*)?|[\W_]+$", "", text[start:end])
            words = item.lower().split()
            if not words or len(words) > SHORT or words[0] in COMMON or words[0] in GENERIC or not LETTERS.search(item):
                continue
            if any(left < end and start < right for _, left, right in inside):
                continue
            named(attribute, item.lower(), found, start)
