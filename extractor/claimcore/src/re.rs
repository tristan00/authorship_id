use std::cell::RefCell;
use std::ffi::c_void;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::OnceLock;

type Code = c_void;

#[link(name = "pcre2_32", kind = "static")]
extern "C" {
    fn pcre2_compile_32(pattern: *const u32, length: usize, options: u32, errorcode: *mut i32, erroroffset: *mut usize, ccontext: *mut c_void) -> *mut Code;
    fn pcre2_jit_compile_32(code: *mut Code, options: u32) -> i32;
    fn pcre2_match_32(code: *const Code, subject: *const u32, length: usize, startoffset: usize, options: u32, match_data: *mut c_void, mcontext: *mut c_void) -> i32;
    fn pcre2_match_data_create_32(ovecsize: u32, gcontext: *mut c_void) -> *mut c_void;
    fn pcre2_get_ovector_pointer_32(match_data: *mut c_void) -> *const usize;
    fn pcre2_pattern_info_32(code: *const Code, what: u32, where_: *mut c_void) -> i32;
    fn pcre2_get_error_message_32(errorcode: i32, buffer: *mut u32, bufflen: usize) -> i32;
    fn pcre2_jit_stack_create_32(startsize: usize, maxsize: usize, gcontext: *mut c_void) -> *mut c_void;
    fn pcre2_match_context_create_32(gcontext: *mut c_void) -> *mut c_void;
    fn pcre2_jit_stack_assign_32(mcontext: *mut c_void, callback: *mut c_void, callback_data: *mut c_void);
}

const ANCHORED: u32 = 0x80000000;
const NO_UTF_CHECK: u32 = 0x40000000;
const UCP: u32 = 0x00020000;
const UTF: u32 = 0x00080000;
const ALT_CIRCUMFLEX: u32 = 0x00200000;
const NOTEMPTY_ATSTART: u32 = 0x00000008;
const JIT_COMPLETE: u32 = 1;
const INFO_CAPTURECOUNT: u32 = 4;
const UNSET: usize = usize::MAX;

pub const I: u32 = 0x00000008;
pub const S: u32 = 0x00000020;
pub const M: u32 = 0x00000400;

pub const MAXG: usize = 48;

pub static FAILURES: AtomicU64 = AtomicU64::new(0);
pub static JIT_FAILURES: AtomicU64 = AtomicU64::new(0);

pub struct Re {
    code: *mut Code,
    pub groups: usize,
    pub pattern: String,
    pub flags: u32,
    anchored: OnceLock<Box<Re>>,
    full: OnceLock<Box<Re>>,
}

unsafe impl Send for Re {}
unsafe impl Sync for Re {}

struct Scratch {
    data: *mut c_void,
    context: *mut c_void,
}

thread_local! {
    static SCRATCH: RefCell<Scratch> = RefCell::new(unsafe {
        let data = pcre2_match_data_create_32(MAXG as u32, std::ptr::null_mut());
        let context = pcre2_match_context_create_32(std::ptr::null_mut());
        let stack = pcre2_jit_stack_create_32(64 * 1024, 16 * 1024 * 1024, std::ptr::null_mut());
        pcre2_jit_stack_assign_32(context, std::ptr::null_mut(), stack);
        Scratch { data, context }
    });
}

fn dotted(c: char) -> bool {
    matches!(c, 'i' | 'I' | '\u{131}' | '\u{130}')
}

fn class_end(chars: &[char], start: usize) -> (usize, bool) {
    let mut index = start + 1;
    if index < chars.len() && chars[index] == '^' {
        index += 1;
    }
    let first = index;
    let mut covers = false;
    let mut previous: Option<char> = None;
    while index < chars.len() && (chars[index] != ']' || index == first) {
        let mut c = chars[index];
        if c == '\\' && index + 1 < chars.len() {
            index += 1;
            c = if chars[index].is_ascii_alphanumeric() { '\0' } else { chars[index] };
        }
        if c == '-' && previous.is_some() && index + 1 < chars.len() && chars[index + 1] != ']' {
            let mut high = chars[index + 1];
            index += 1;
            if high == '\\' && index + 1 < chars.len() {
                index += 1;
                high = chars[index];
            }
            let low = previous.unwrap();
            if (low <= 'i' && 'i' <= high) || (low <= 'I' && 'I' <= high) {
                covers = true;
            }
            previous = None;
            index += 1;
            continue;
        }
        if dotted(c) {
            covers = true;
        }
        previous = Some(c);
        index += 1;
    }
    (index, covers)
}

pub fn translate(pattern: &str, flags: u32) -> String {
    let chars: Vec<char> = pattern.chars().collect();
    let mut out = String::with_capacity(pattern.len() + 8);
    let mut index = 0;
    let mut caseless = flags & I != 0;
    let mut stack: Vec<bool> = Vec::new();
    while index < chars.len() {
        let c = chars[index];
        if c == '\\' && index + 1 < chars.len() {
            let next = chars[index + 1];
            if next == 'Z' {
                out.push_str("\\z");
            } else {
                out.push(c);
                out.push(next);
            }
            index += 2;
            continue;
        }
        if c == '[' {
            let (end, covers) = class_end(&chars, index);
            let mut body: String = chars[index..end.min(chars.len())].iter().collect();
            let first = if chars.get(index + 1) == Some(&'^') { index + 2 } else { index + 1 };
            if chars.get(first) == Some(&']') {
                let prefix: String = chars[index..first].iter().collect();
                body = format!("{prefix}\\]{}", chars[first + 1..end.min(chars.len())].iter().collect::<String>());
            }
            out.push_str(&body);
            if caseless && covers {
                out.push_str("iI\u{131}\u{130}");
            }
            if end < chars.len() {
                out.push(']');
            }
            index = end + 1;
            continue;
        }
        if c == '(' {
            stack.push(caseless);
            if chars.get(index + 1) == Some(&'?') {
                let mut scan = index + 2;
                let mut on = true;
                let mut letters = false;
                let mut state = caseless;
                while scan < chars.len() && (chars[scan].is_ascii_alphabetic() || chars[scan] == '-') {
                    letters = true;
                    match chars[scan] {
                        '-' => on = false,
                        'i' => state = on,
                        _ => {}
                    }
                    scan += 1;
                }
                let mut header = index + 2;
                if letters && scan < chars.len() && matches!(chars[scan], ')' | ':') {
                    if chars[scan] == ')' {
                        stack.pop();
                    }
                    caseless = state;
                    header = scan + 1;
                } else if matches!(chars.get(index + 2), Some('P') | Some('<')) && !matches!(chars.get(index + 3), Some('=') | Some('!')) {
                    header = index + 2;
                    while header < chars.len() && !matches!(chars[header], '>' | ')') {
                        header += 1;
                    }
                    if header < chars.len() && chars[header] == ')' {
                        stack.pop();
                    }
                    header += 1;
                }
                out.extend(&chars[index..header.min(chars.len())]);
                index = header;
                continue;
            }
            out.push(c);
            index += 1;
            continue;
        }
        if c == ')' {
            if let Some(state) = stack.pop() {
                caseless = state;
            }
            out.push(c);
            index += 1;
            continue;
        }
        if caseless && dotted(c) {
            out.push_str("[iI\u{131}\u{130}]");
            index += 1;
            continue;
        }
        if c == '{' && index + 1 < chars.len() && chars[index + 1] == ',' {
            out.push_str("{0");
            index += 1;
            continue;
        }
        out.push(c);
        index += 1;
    }
    out
}

impl Re {
    pub fn new(pattern: &str) -> Re {
        Re::with(pattern, 0)
    }

    pub fn with(pattern: &str, flags: u32) -> Re {
        Re::build(pattern, flags, 0)
    }

    fn build(pattern: &str, flags: u32, extra: u32) -> Re {
        let translated: Vec<u32> = translate(pattern, flags | extra).chars().map(|c| c as u32).collect();
        let mut error = 0i32;
        let mut offset = 0usize;
        let code = unsafe { pcre2_compile_32(translated.as_ptr(), translated.len(), flags | extra | UTF | UCP | ALT_CIRCUMFLEX | NO_UTF_CHECK, &mut error, &mut offset, std::ptr::null_mut()) };
        if code.is_null() {
            let mut buffer = [0u32; 256];
            let size = unsafe { pcre2_get_error_message_32(error, buffer.as_mut_ptr(), 256) };
            let message: String = buffer[..size.max(0) as usize].iter().filter_map(|&c| char::from_u32(c)).collect();
            panic!("pattern error {message} at {offset}: {pattern}");
        }
        let jit = unsafe { pcre2_jit_compile_32(code, JIT_COMPLETE) };
        if jit != 0 {
            JIT_FAILURES.fetch_add(1, Ordering::Relaxed);
        }
        let mut groups: u32 = 0;
        unsafe { pcre2_pattern_info_32(code, INFO_CAPTURECOUNT, &mut groups as *mut u32 as *mut c_void) };
        if groups as usize + 1 > MAXG {
            panic!("too many groups {groups}: {pattern}");
        }
        Re { code, groups: groups as usize, pattern: pattern.to_string(), flags, anchored: OnceLock::new(), full: OnceLock::new() }
    }

    fn anchored(&self) -> &Re {
        self.anchored.get_or_init(|| Box::new(Re::build(&self.pattern, self.flags, ANCHORED)))
    }

    fn full(&self) -> &Re {
        self.full.get_or_init(|| Box::new(Re::build(&format!("(?:{})\\Z", self.pattern), self.flags, ANCHORED)))
    }

    fn exec<'a>(&self, s: &'a [char], pos: usize, end: usize, options: u32) -> Option<Match<'a>> {
        let end = end.min(s.len());
        if pos > end {
            return None;
        }
        SCRATCH.with(|scratch| {
            let scratch = scratch.borrow();
            let rc = unsafe { pcre2_match_32(self.code, s.as_ptr() as *const u32, end, pos, options | NO_UTF_CHECK, scratch.data, scratch.context) };
            if rc < 0 {
                if rc != -1 {
                    FAILURES.fetch_add(1, Ordering::Relaxed);
                }
                return None;
            }
            let pointer = unsafe { pcre2_get_ovector_pointer_32(scratch.data) };
            let count = self.groups + 1;
            let mut ov = [u32::MAX; 2 * MAXG];
            let set = (rc as usize).min(count);
            for index in 0..2 * set {
                let value = unsafe { *pointer.add(index) };
                ov[index] = if value == UNSET { u32::MAX } else { value as u32 };
            }
            Some(Match { string: s, ov, n: count as u8 })
        })
    }

    fn probe(&self, s: &[char], pos: usize, end: usize) -> bool {
        let end = end.min(s.len());
        if pos > end {
            return false;
        }
        SCRATCH.with(|scratch| {
            let scratch = scratch.borrow();
            let rc = unsafe { pcre2_match_32(self.code, s.as_ptr() as *const u32, end, pos, NO_UTF_CHECK, scratch.data, scratch.context) };
            if rc < -1 {
                FAILURES.fetch_add(1, Ordering::Relaxed);
            }
            rc >= 0
        })
    }

    pub fn search<'a>(&self, s: &'a [char], pos: usize, end: usize) -> Option<Match<'a>> {
        self.exec(s, pos, end, 0)
    }

    pub fn find<'a>(&self, s: &'a [char]) -> Option<Match<'a>> {
        self.exec(s, 0, s.len(), 0)
    }

    pub fn find_from<'a>(&self, s: &'a [char], pos: usize) -> Option<Match<'a>> {
        self.exec(s, pos, s.len(), 0)
    }

    pub fn test(&self, s: &[char]) -> bool {
        self.probe(s, 0, s.len())
    }

    pub fn test_in(&self, s: &[char], pos: usize, end: usize) -> bool {
        self.probe(s, pos, end)
    }

    pub fn at<'a>(&self, s: &'a [char], pos: usize) -> Option<Match<'a>> {
        self.anchored().exec(s, pos, s.len(), 0)
    }

    pub fn at_in<'a>(&self, s: &'a [char], pos: usize, end: usize) -> Option<Match<'a>> {
        self.anchored().exec(s, pos, end, 0)
    }

    pub fn fullmatch<'a>(&self, s: &'a [char], pos: usize, end: usize) -> Option<Match<'a>> {
        self.full().exec(s, pos, end, 0)
    }

    pub fn iter<'a, 'r>(&'r self, s: &'a [char]) -> Matches<'a, 'r> {
        Matches { re: self, s, pos: 0, end: s.len(), empty: false }
    }

    pub fn iter_in<'a, 'r>(&'r self, s: &'a [char], pos: usize, end: usize) -> Matches<'a, 'r> {
        Matches { re: self, s, pos, end: end.min(s.len()), empty: false }
    }

    pub fn count(&self, s: &[char]) -> usize {
        self.iter(s).count()
    }

    pub fn sub_with(&self, s: &[char], mut replace: impl FnMut(&Match) -> Vec<char>) -> Vec<char> {
        let mut out = Vec::with_capacity(s.len());
        let mut last = 0;
        for found in self.iter(s) {
            out.extend_from_slice(&s[last..found.start()]);
            out.extend(replace(&found));
            last = found.end();
        }
        out.extend_from_slice(&s[last..]);
        out
    }

    pub fn sub(&self, s: &[char], with: &str) -> Vec<char> {
        let replacement: Vec<char> = with.chars().collect();
        self.sub_with(s, |_| replacement.clone())
    }

    pub fn split_last<'a>(&self, s: &'a [char]) -> &'a [char] {
        let mut last = 0;
        for found in self.iter(s) {
            last = found.end();
        }
        &s[last..]
    }
}

pub struct Matches<'a, 'r> {
    re: &'r Re,
    s: &'a [char],
    pos: usize,
    end: usize,
    empty: bool,
}

impl<'a, 'r> Iterator for Matches<'a, 'r> {
    type Item = Match<'a>;

    fn next(&mut self) -> Option<Match<'a>> {
        if self.pos > self.end {
            return None;
        }
        let found = self.re.exec(self.s, self.pos, self.end, if self.empty { NOTEMPTY_ATSTART } else { 0 })?;
        self.empty = found.start() == found.end();
        self.pos = found.end();
        Some(found)
    }
}

#[derive(Clone, Copy)]
pub struct Match<'a> {
    pub string: &'a [char],
    ov: [u32; 2 * MAXG],
    n: u8,
}

impl<'a> Match<'a> {
    pub fn start(&self) -> usize {
        self.ov[0] as usize
    }

    pub fn end(&self) -> usize {
        self.ov[1] as usize
    }

    pub fn has(&self, g: usize) -> bool {
        g < self.n as usize && self.ov[2 * g] != u32::MAX
    }

    pub fn span(&self, g: usize) -> Option<(usize, usize)> {
        if self.has(g) {
            Some((self.ov[2 * g] as usize, self.ov[2 * g + 1] as usize))
        } else {
            None
        }
    }

    pub fn start_of(&self, g: usize) -> isize {
        self.span(g).map_or(-1, |(a, _)| a as isize)
    }

    pub fn end_of(&self, g: usize) -> isize {
        self.span(g).map_or(-1, |(_, b)| b as isize)
    }

    pub fn group(&self, g: usize) -> Option<&'a [char]> {
        self.span(g).map(|(a, b)| &self.string[a..b])
    }

    pub fn text(&self) -> &'a [char] {
        &self.string[self.start()..self.end()]
    }

    pub fn gs(&self, g: usize) -> Option<String> {
        self.group(g).map(|part| part.iter().collect())
    }

    pub fn g(&self, g: usize) -> String {
        self.gs(g).unwrap_or_default()
    }

    pub fn nonempty(&self, g: usize) -> Option<&'a [char]> {
        self.group(g).filter(|part| !part.is_empty())
    }

    pub fn groups(&self) -> usize {
        self.n as usize - 1
    }

    pub fn first(&self) -> Option<&'a [char]> {
        (1..self.n as usize).find_map(|g| self.nonempty(g))
    }

    pub fn first_s(&self) -> Option<String> {
        self.first().map(|part| part.iter().collect())
    }

    pub fn first_index(&self) -> Option<usize> {
        (1..self.n as usize).find(|&g| self.nonempty(g).is_some())
    }

    pub fn lastindex(&self) -> Option<usize> {
        let mut best: Option<(usize, usize)> = None;
        for g in 1..self.n as usize {
            if let Some((_, end)) = self.span(g) {
                if best.map_or(true, |(_, e)| end > e) {
                    best = Some((g, end));
                }
            }
        }
        best.map(|(g, _)| g)
    }
}
