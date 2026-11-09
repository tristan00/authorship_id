use std::path::{Path, PathBuf};

const SOURCE: &str = "C:/reddit_data/tools/rust/pcre2-10.42/src";
const GENERATED: [(&str, &str); 3] = [("config.h.generic", "config.h"), ("pcre2.h.generic", "pcre2.h"), ("pcre2_chartables.c.dist", "pcre2_chartables.c")];
const FILES: [&str; 26] = [
    "pcre2_auto_possess.c", "pcre2_compile.c", "pcre2_config.c", "pcre2_context.c", "pcre2_convert.c",
    "pcre2_dfa_match.c", "pcre2_error.c", "pcre2_extuni.c", "pcre2_find_bracket.c", "pcre2_jit_compile.c", "pcre2_maketables.c",
    "pcre2_match.c", "pcre2_match_data.c", "pcre2_newline.c", "pcre2_ord2utf.c", "pcre2_pattern_info.c", "pcre2_script_run.c",
    "pcre2_serialize.c", "pcre2_string_utils.c", "pcre2_study.c", "pcre2_substitute.c", "pcre2_substring.c", "pcre2_tables.c",
    "pcre2_ucd.c", "pcre2_valid_utf.c", "pcre2_xclass.c",
];

fn main() {
    let src = Path::new(SOURCE);
    let out = PathBuf::from(std::env::var("OUT_DIR").unwrap());
    for (generic, target) in GENERATED {
        std::fs::copy(src.join(generic), out.join(target)).unwrap_or_else(|error| panic!("cannot copy {generic} from {SOURCE}: {error}"));
    }
    let mut build = cc::Build::new();
    build
        .include(&out)
        .include(src)
        .define("PCRE2_CODE_UNIT_WIDTH", "32")
        .define("HAVE_CONFIG_H", "1")
        .define("PCRE2_STATIC", "1")
        .define("SUPPORT_UNICODE", "1")
        .define("SUPPORT_JIT", "1")
        .define("HAVE_STDINT_H", "1")
        .opt_level(3)
        .warnings(false);
    build.file(out.join("pcre2_chartables.c"));
    for file in FILES {
        build.file(src.join(file));
    }
    build.compile("pcre2_32");
    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-changed={SOURCE}");
}
