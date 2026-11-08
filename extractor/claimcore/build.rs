use std::path::{Path, PathBuf};
use std::process::Command;

const VERSION: &str = "10.42";
const FILES: [&str; 27] = [
    "pcre2_auto_possess.c", "pcre2_chartables.c", "pcre2_compile.c", "pcre2_config.c", "pcre2_context.c", "pcre2_convert.c",
    "pcre2_dfa_match.c", "pcre2_error.c", "pcre2_extuni.c", "pcre2_find_bracket.c", "pcre2_jit_compile.c", "pcre2_maketables.c",
    "pcre2_match.c", "pcre2_match_data.c", "pcre2_newline.c", "pcre2_ord2utf.c", "pcre2_pattern_info.c", "pcre2_script_run.c",
    "pcre2_serialize.c", "pcre2_string_utils.c", "pcre2_study.c", "pcre2_substitute.c", "pcre2_substring.c", "pcre2_tables.c",
    "pcre2_ucd.c", "pcre2_valid_utf.c", "pcre2_xclass.c",
];

fn run(command: &mut Command) {
    let status = command.status().unwrap_or_else(|error| panic!("cannot run {command:?}: {error}"));
    assert!(status.success(), "{command:?} failed with {status}");
}

fn source(out: &Path) -> PathBuf {
    let root = out.join(format!("pcre2-{VERSION}"));
    let src = root.join("src");
    if !src.join("pcre2.h").exists() {
        let archive = out.join(format!("pcre2-{VERSION}.tar.gz"));
        run(Command::new("curl").args(["-sSfL", "-o"]).arg(&archive).arg(format!("https://github.com/PCRE2Project/pcre2/releases/download/pcre2-{VERSION}/pcre2-{VERSION}.tar.gz")));
        run(Command::new("tar").arg("-xzf").arg(&archive).arg("-C").arg(out));
        for (generic, target) in [("config.h.generic", "config.h"), ("pcre2.h.generic", "pcre2.h"), ("pcre2_chartables.c.dist", "pcre2_chartables.c")] {
            std::fs::copy(src.join(generic), src.join(target)).unwrap();
        }
    }
    src
}

fn main() {
    let src = source(&PathBuf::from(std::env::var("OUT_DIR").unwrap()));
    let mut build = cc::Build::new();
    build
        .include(&src)
        .define("PCRE2_CODE_UNIT_WIDTH", "32")
        .define("HAVE_CONFIG_H", "1")
        .define("PCRE2_STATIC", "1")
        .define("SUPPORT_UNICODE", "1")
        .define("SUPPORT_JIT", "1")
        .define("HAVE_STDINT_H", "1")
        .opt_level(3)
        .warnings(false);
    for file in FILES {
        build.file(src.join(file));
    }
    build.compile("pcre2_32");
    println!("cargo:rerun-if-changed=build.rs");
}
