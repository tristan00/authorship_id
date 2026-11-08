use std::io::Read;

pub struct Database {
    url: String,
}

fn failed(sql: &str, error: ureq::Error) -> ! {
    match error {
        ureq::Error::Status(code, response) => panic!("clickhouse {code} for {}: {}", &sql[..sql.len().min(200)], response.into_string().unwrap_or_default()),
        other => panic!("clickhouse request failed for {}: {other}", &sql[..sql.len().min(200)]),
    }
}

impl Database {
    pub fn new(host: &str, port: u16, database: &str) -> Database {
        Database { url: format!("http://{host}:{port}/?database={database}&max_execution_time=0") }
    }

    fn post(&self, sql: &str) -> ureq::Response {
        ureq::post(&self.url).send_string(sql).unwrap_or_else(|error| failed(sql, error))
    }

    pub fn command(&self, sql: &str) -> String {
        self.post(sql).into_string().unwrap_or_else(|error| panic!("cannot read clickhouse reply: {error}"))
    }

    pub fn stream(&self, sql: &str) -> Box<dyn Read + Send> {
        self.post(sql).into_reader()
    }

    pub fn insert(&self, table: &str, body: &[u8]) {
        let sql = format!("INSERT INTO {table} FORMAT RowBinary");
        ureq::post(&self.url).query("query", &sql).send_bytes(body).unwrap_or_else(|error| failed(&sql, error));
    }
}

pub fn varint(reader: &mut impl Read) -> Option<u64> {
    let mut value = 0u64;
    let mut shift = 0;
    let mut byte = [0u8; 1];
    loop {
        if reader.read(&mut byte).unwrap() == 0 {
            assert!(shift == 0, "truncated varint");
            return None;
        }
        value |= u64::from(byte[0] & 0x7f) << shift;
        if byte[0] & 0x80 == 0 {
            return Some(value);
        }
        shift += 7;
    }
}

pub fn string(reader: &mut impl Read) -> Option<String> {
    let length = varint(reader)? as usize;
    let mut bytes = vec![0u8; length];
    reader.read_exact(&mut bytes).unwrap();
    Some(String::from_utf8(bytes).unwrap_or_else(|error| String::from_utf8_lossy(error.as_bytes()).into_owned()))
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
