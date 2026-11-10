use unicode_general_category::{get_general_category, GeneralCategory as G};

pub type Text = [char];

pub fn chars(s: &str) -> Vec<char> {
    s.chars().collect()
}

pub fn st(s: &[char]) -> String {
    s.iter().collect()
}

pub fn eq(s: &[char], word: &str) -> bool {
    let mut it = s.iter();
    for c in word.chars() {
        if it.next() != Some(&c) {
            return false;
        }
    }
    it.next().is_none()
}

pub fn clamp(index: isize, len: usize) -> usize {
    if index < 0 {
        (len as isize + index).max(0) as usize
    } else {
        (index as usize).min(len)
    }
}

pub fn slice(s: &[char], a: isize, b: isize) -> &[char] {
    let start = clamp(a, s.len());
    let end = clamp(b, s.len());
    if start >= end {
        &s[0..0]
    } else {
        &s[start..end]
    }
}

pub fn before(s: &[char], start: usize, width: usize) -> &[char] {
    &s[start.saturating_sub(width)..start]
}

pub fn starts_at(s: &[char], at: usize, word: &str) -> bool {
    let mut index = at;
    for c in word.chars() {
        if index >= s.len() || s[index] != c {
            return false;
        }
        index += 1;
    }
    true
}

pub fn ends_at(s: &[char], end: usize, word: &str) -> bool {
    let size = word.chars().count();
    end <= s.len() && end >= size && starts_at(s, end - size, word)
}

pub fn find(s: &[char], word: &str, start: usize) -> Option<usize> {
    find_in(s, word, start, s.len())
}

pub fn find_in(s: &[char], word: &str, start: usize, end: usize) -> Option<usize> {
    let needle: Vec<char> = word.chars().collect();
    let end = end.min(s.len());
    if needle.is_empty() {
        return if start <= end { Some(start) } else { None };
    }
    if end < needle.len() {
        return None;
    }
    let first = needle[0];
    let mut index = start;
    while index + needle.len() <= end {
        if s[index] == first && s[index..index + needle.len()] == needle[..] {
            return Some(index);
        }
        index += 1;
    }
    None
}

pub fn findc(s: &[char], c: char, start: usize) -> Option<usize> {
    if start >= s.len() {
        return None;
    }
    s[start..].iter().position(|&x| x == c).map(|p| p + start)
}

pub fn rfindc(s: &[char], c: char, end: usize) -> Option<usize> {
    s[..end.min(s.len())].iter().rposition(|&x| x == c)
}

pub fn rfind_in(s: &[char], word: &str, start: usize, end: usize) -> Option<usize> {
    let needle: Vec<char> = word.chars().collect();
    let end = end.min(s.len());
    if needle.is_empty() {
        return if start <= end { Some(end) } else { None };
    }
    if end < needle.len() + start {
        return None;
    }
    let mut index = end - needle.len();
    loop {
        if s[index..index + needle.len()] == needle[..] {
            return Some(index);
        }
        if index == start {
            return None;
        }
        index -= 1;
    }
}

pub fn rfind(s: &[char], word: &str, end: usize) -> Option<usize> {
    rfind_in(s, word, 0, end)
}

pub fn contains(s: &[char], word: &str) -> bool {
    find(s, word, 0).is_some()
}

pub fn count(s: &[char], word: &str) -> usize {
    let needle: Vec<char> = word.chars().collect();
    if needle.is_empty() {
        return s.len() + 1;
    }
    let mut total = 0;
    let mut index = 0;
    while index + needle.len() <= s.len() {
        if s[index..index + needle.len()] == needle[..] {
            total += 1;
            index += needle.len();
        } else {
            index += 1;
        }
    }
    total
}

pub fn last_mark(s: &[char], end: usize, marks: &str) -> usize {
    let end = end.min(s.len());
    match s[..end].iter().rposition(|c| marks.contains(*c)) {
        Some(p) => p + 1,
        None => 0,
    }
}

pub fn next_mark(s: &[char], start: usize, marks: &str) -> usize {
    if start >= s.len() {
        return s.len();
    }
    match s[start..].iter().position(|c| marks.contains(*c)) {
        Some(p) => p + start,
        None => s.len(),
    }
}

pub fn line_start(s: &[char], start: usize) -> usize {
    rfindc(s, '\n', start).map_or(0, |p| p + 1)
}

pub fn line_end(s: &[char], start: usize) -> usize {
    findc(s, '\n', start).unwrap_or(s.len())
}

pub fn category(c: char) -> G {
    get_general_category(c)
}

pub fn is_alpha(c: char) -> bool {
    matches!(category(c), G::UppercaseLetter | G::LowercaseLetter | G::TitlecaseLetter | G::ModifierLetter | G::OtherLetter)
}

pub fn is_decimal(c: char) -> bool {
    category(c) == G::DecimalNumber
}

pub fn is_numeric(c: char) -> bool {
    matches!(category(c), G::DecimalNumber | G::LetterNumber | G::OtherNumber)
}

pub fn is_alnum(c: char) -> bool {
    is_alpha(c) || is_numeric(c)
}

pub fn is_word(c: char) -> bool {
    c == '_' || is_alnum(c)
}

pub fn is_space(c: char) -> bool {
    matches!(c, '\t'..='\r' | '\x1c'..='\x1f' | ' ' | '\u{85}' | '\u{a0}' | '\u{1680}' | '\u{2000}'..='\u{200a}' | '\u{2028}' | '\u{2029}' | '\u{202f}' | '\u{205f}' | '\u{3000}')
}

pub fn is_upper_char(c: char) -> bool {
    c.is_uppercase()
}

pub fn is_lower_char(c: char) -> bool {
    c.is_lowercase()
}

pub fn is_cased(c: char) -> bool {
    c.is_uppercase() || c.is_lowercase() || category(c) == G::TitlecaseLetter
}

pub fn isalpha(s: &[char]) -> bool {
    !s.is_empty() && s.iter().all(|&c| is_alpha(c))
}

pub fn isascii(s: &[char]) -> bool {
    s.iter().all(|c| c.is_ascii())
}

pub fn isdigit(s: &[char]) -> bool {
    !s.is_empty() && s.iter().all(|&c| is_decimal(c) || matches!(category(c), G::OtherNumber) && c.to_digit(10).is_some())
}

pub fn isupper(s: &[char]) -> bool {
    let mut cased = false;
    for &c in s {
        if c.is_lowercase() || category(c) == G::TitlecaseLetter {
            return false;
        }
        if c.is_uppercase() {
            cased = true;
        }
    }
    cased
}

pub fn islower(s: &[char]) -> bool {
    let mut cased = false;
    for &c in s {
        if c.is_uppercase() || category(c) == G::TitlecaseLetter {
            return false;
        }
        if c.is_lowercase() {
            cased = true;
        }
    }
    cased
}

pub fn istitle(s: &[char]) -> bool {
    let mut cased = false;
    let mut previous = false;
    for &c in s {
        let title = category(c) == G::TitlecaseLetter;
        if c.is_uppercase() || title {
            if previous {
                return false;
            }
            previous = true;
            cased = true;
        } else if c.is_lowercase() {
            if !previous {
                return false;
            }
            previous = true;
            cased = true;
        } else {
            previous = false;
        }
    }
    cased
}

pub fn lower(s: &[char]) -> Vec<char> {
    let text: String = s.iter().collect();
    let lowered: Vec<char> = text.to_lowercase().chars().collect();
    if lowered.len() == s.len() {
        lowered
    } else {
        s.iter().map(|&c| {
            let mut it = c.to_lowercase();
            let first = it.next().unwrap_or(c);
            if it.next().is_some() { c } else { first }
        }).collect()
    }
}

pub fn lower_str(s: &str) -> String {
    s.to_lowercase()
}

pub fn digit_value(c: char) -> Option<u32> {
    if c.is_ascii_digit() {
        return Some(c as u32 - '0' as u32);
    }
    if !is_decimal(c) {
        return None;
    }
    let mut code = c as u32;
    let mut value = 0;
    while code > 0 {
        match char::from_u32(code - 1) {
            Some(previous) if is_decimal(previous) => {
                code -= 1;
                value += 1;
            }
            _ => break,
        }
    }
    Some(value % 10)
}

pub fn py_int(s: &[char]) -> Option<i64> {
    let trimmed: Vec<char> = s.iter().copied().filter(|&c| c != '_').collect();
    let trimmed = strip_space(&trimmed);
    if trimmed.is_empty() {
        return None;
    }
    let (negative, digits) = match trimmed[0] {
        '-' => (true, &trimmed[1..]),
        '+' => (false, &trimmed[1..]),
        _ => (false, trimmed),
    };
    if digits.is_empty() {
        return None;
    }
    let mut value: i64 = 0;
    for &c in digits {
        value = value.checked_mul(10)?.checked_add(digit_value(c)? as i64)?;
    }
    Some(if negative { -value } else { value })
}

pub fn py_float(s: &[char]) -> Option<f64> {
    let ascii: String = strip_space(s).iter().map(|&c| digit_value(c).map_or(c, |d| char::from_digit(d, 10).unwrap())).filter(|&c| c != '_').collect();
    ascii.parse::<f64>().ok()
}

pub fn strip_space(s: &[char]) -> &[char] {
    let mut a = 0;
    let mut b = s.len();
    while a < b && is_space(s[a]) {
        a += 1;
    }
    while b > a && is_space(s[b - 1]) {
        b -= 1;
    }
    &s[a..b]
}

pub fn strip_chars<'a>(s: &'a [char], set: &str) -> &'a [char] {
    let mut a = 0;
    let mut b = s.len();
    while a < b && set.contains(s[a]) {
        a += 1;
    }
    while b > a && set.contains(s[b - 1]) {
        b -= 1;
    }
    &s[a..b]
}

pub fn rounded(x: f64) -> String {
    (x.round() as i64).to_string()
}

pub fn split_ws(s: &[char]) -> Vec<&[char]> {
    s.split(|&c| is_space(c)).filter(|part| !part.is_empty()).collect()
}
