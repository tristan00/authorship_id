import psycopg
from psycopg.types.json import Jsonb

from database import DSN, timed

SCHEMA = """
CREATE TABLE IF NOT EXISTS demographic_runs (
    run_id uuid PRIMARY KEY,
    consolidation_run uuid NOT NULL,
    status text NOT NULL CHECK (status IN ('loading','ready')),
    users integer NOT NULL,
    folds integer NOT NULL CHECK (folds = 3),
    manifest jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz
);
CREATE TABLE IF NOT EXISTS demographic_models (
    run_id uuid NOT NULL REFERENCES demographic_runs,
    fold smallint NOT NULL CHECK (fold BETWEEN 0 AND 2),
    checkpoint_sha256 text NOT NULL,
    training jsonb NOT NULL,
    evaluation jsonb,
    PRIMARY KEY (run_id,fold)
);
CREATE TABLE IF NOT EXISTS demographic_assignments (
    run_id uuid NOT NULL REFERENCES demographic_runs,
    author text NOT NULL,
    fold smallint NOT NULL CHECK (fold BETWEEN 0 AND 2),
    PRIMARY KEY (run_id,author),
    UNIQUE (run_id,author,fold)
);
CREATE TABLE IF NOT EXISTS demographic_predictions (
    run_id uuid NOT NULL,
    author text NOT NULL,
    fold smallint NOT NULL,
    attributes jsonb NOT NULL,
    PRIMARY KEY (run_id,author),
    FOREIGN KEY (run_id,author,fold) REFERENCES demographic_assignments(run_id,author,fold),
    FOREIGN KEY (run_id,fold) REFERENCES demographic_models(run_id,fold)
);
CREATE TABLE IF NOT EXISTS demographic_state (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    run_id uuid NOT NULL REFERENCES demographic_runs
);
"""


@timed
def initialize(manifest, authors, folds):
    with psycopg.connect(DSN) as conn:
        conn.execute(SCHEMA)
        conn.execute("INSERT INTO demographic_runs(run_id,consolidation_run,status,users,folds,manifest) VALUES (%s,%s,'loading',%s,%s,%s) ON CONFLICT(run_id) DO NOTHING", [manifest["run_id"], manifest["consolidation_run"], len(authors), manifest["folds"], Jsonb(manifest)])
        previous = conn.execute("SELECT manifest FROM demographic_runs WHERE run_id=%s", [manifest["run_id"]]).fetchone()[0]
        if previous != manifest:
            raise ValueError("The stored run has a different dataset manifest")
        existing = conn.execute("SELECT count(*) FROM demographic_assignments WHERE run_id=%s", [manifest["run_id"]]).fetchone()[0]
        if existing == 0:
            with conn.cursor().copy("COPY demographic_assignments(run_id,author,fold) FROM STDIN") as copy:
                for author, fold in zip(authors, folds, strict=True):
                    copy.write_row((manifest["run_id"], author, int(fold)))
        elif existing != len(authors):
            raise ValueError("Incomplete fold assignments")


@timed
def load_fold(manifest, fold, checkpoint_hash, training, evaluation, predictions):
    with psycopg.connect(DSN) as conn:
        active = conn.execute("SELECT 1 FROM demographic_state WHERE run_id=%s", [manifest["run_id"]]).fetchone()
        if active:
            raise ValueError("This run is already published; its predictions are immutable")
        conn.execute("INSERT INTO demographic_models(run_id,fold,checkpoint_sha256,training,evaluation) VALUES (%s,%s,%s,%s,%s) ON CONFLICT(run_id,fold) DO UPDATE SET checkpoint_sha256=EXCLUDED.checkpoint_sha256,training=EXCLUDED.training,evaluation=EXCLUDED.evaluation", [manifest["run_id"], fold, checkpoint_hash, Jsonb(training), Jsonb(evaluation)])
        conn.execute("DELETE FROM demographic_predictions WHERE run_id=%s AND fold=%s", [manifest["run_id"], fold])
        with conn.cursor().copy("COPY demographic_predictions(run_id,author,fold,attributes) FROM STDIN") as copy:
            for author, attributes in predictions:
                if set(attributes) != set(manifest["fields"]):
                    raise ValueError(f"Incomplete predicted attributes for {author}")
                copy.write_row((manifest["run_id"], author, fold, Jsonb(attributes)))


@timed
def publish(manifest):
    with psycopg.connect(DSN) as conn:
        count = conn.execute("SELECT count(*) FROM demographic_predictions WHERE run_id=%s", [manifest["run_id"]]).fetchone()[0]
        models = conn.execute("SELECT count(*) FROM demographic_models WHERE run_id=%s", [manifest["run_id"]]).fetchone()[0]
        if count != manifest["users"] or models != manifest["folds"]:
            raise ValueError("Every encoded user must have one out-of-fold prediction before publishing")
        conn.execute("UPDATE demographic_runs SET status='ready',finished_at=now() WHERE run_id=%s", [manifest["run_id"]])
        conn.execute("INSERT INTO demographic_state(singleton,run_id) VALUES (true,%s) ON CONFLICT(singleton) DO UPDATE SET run_id=EXCLUDED.run_id", [manifest["run_id"]])
