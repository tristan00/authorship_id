use std::io::Read;

pub struct Database {
    url: String,
}

fn failed(sql: &str, error: ureq::Error) -> ! {
    match error {
        ureq::Error::Status(code, response) => panic!("clickhouse {code} for {}: {}", &sql[..sql.len().min(300)], response.into_string().unwrap_or_default()),
        other => panic!("clickhouse request failed for {}: {other}", &sql[..sql.len().min(300)]),
    }
}

impl Database {
    pub fn new(host: &str, port: u16, database: &str) -> Database {
        Database { url: format!("http://{host}:{port}/?database={database}&max_execution_time=0") }
    }

    pub fn url(&self) -> &str {
        &self.url
    }

    fn post(&self, sql: &str) -> ureq::Response {
        ureq::post(&self.url).send_string(sql).unwrap_or_else(|error| failed(sql, error))
    }

    pub fn command(&self, sql: &str) -> String {
        self.post(sql).into_string().unwrap_or_else(|error| panic!("cannot read clickhouse reply: {error}"))
    }

    pub fn rows(&self, sql: &str) -> Rows {
        Rows { inner: self.post(sql).into_reader(), buffer: vec![0; 16 << 20], start: 0, end: 0 }
    }

    pub fn insert(&self, table: &str, body: &[u8]) {
        let sql = format!("INSERT INTO {table} FORMAT RowBinary");
        ureq::post(&self.url).query("query", &sql).send_bytes(body).unwrap_or_else(|error| failed(&sql, error));
    }
}

pub struct Rows {
    inner: Box<dyn Read + Send>,
    buffer: Vec<u8>,
    start: usize,
    end: usize,
}

impl Rows {
    fn fill(&mut self, need: usize) -> bool {
        if self.end - self.start >= need {
            return true;
        }
        self.buffer.copy_within(self.start..self.end, 0);
        self.end -= self.start;
        self.start = 0;
        if need > self.buffer.len() {
            self.buffer.resize(need, 0);
        }
        while self.end < need {
            let read = self.inner.read(&mut self.buffer[self.end..]).unwrap();
            if read == 0 {
                return false;
            }
            self.end += read;
        }
        true
    }

    pub fn done(&mut self) -> bool {
        !self.fill(1)
    }

    fn varint(&mut self) -> usize {
        let mut value = 0usize;
        let mut shift = 0;
        loop {
            assert!(self.fill(1), "truncated varint");
            let byte = self.buffer[self.start];
            self.start += 1;
            value |= usize::from(byte & 0x7f) << shift;
            if byte & 0x80 == 0 {
                return value;
            }
            shift += 7;
        }
    }

    pub fn bytes(&mut self) -> &[u8] {
        let length = self.varint();
        assert!(self.fill(length), "truncated string");
        self.start += length;
        &self.buffer[self.start - length..self.start]
    }

    pub fn fixed<const N: usize>(&mut self) -> [u8; N] {
        assert!(self.fill(N), "truncated fixed field");
        self.start += N;
        self.buffer[self.start - N..self.start].try_into().unwrap()
    }
}

pub fn text(bytes: &[u8]) -> String {
    String::from_utf8_lossy(bytes).into_owned()
}

pub fn put_string(out: &mut Vec<u8>, value: &str) {
    let mut length = value.len() as u64;
    loop {
        let byte = (length & 0x7f) as u8;
        length >>= 7;
        if length == 0 {
            out.push(byte);
            break;
        }
        out.push(byte | 0x80);
    }
    out.extend_from_slice(value.as_bytes());
}
