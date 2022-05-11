-- accounts table
CREATE SEQUENCE accounts_seq
    INCREMENT BY 1 START WITH 1
    MINVALUE 1 MAXVALUE 9999999999999999999999999999
    NOCYCLE CACHE 2;

CREATE TABLE accounts (
    userid NUMBER NOT NULL,
    username VARCHAR2(30) NOT NULL,
    certuid VARCHAR(20) NOT NULL,
    role VARCHAR2(10) NOT NULL,
    registration_date DATE NOT NULL,
    registration_expires DATE,
    CONSTRAINT role_constraint CHECK (role IN ('admin', 'subscriber')),
    CONSTRAINT accounts_uc UNIQUE(username),
    PRIMARY KEY(userid)
);

CREATE OR REPLACE TRIGGER accounts_trg
BEFORE INSERT ON "ACCOUNTS"
FOR EACH ROW
BEGIN
    IF :new.userid IS NULL THEN
        SELECT accounts_seq.nextval INTO :new.userid FROM DUAL;
    END IF;
END;


-- file_metadata table
CREATE SEQUENCE file_metadata_seq
    INCREMENT BY 1 START WITH 1
    MINVALUE 1 MAXVALUE 999999999999999
    NOCYCLE CACHE 2;

CREATE TABLE file_metadata (
    fileid NUMBER(15) NOT NULL,
    name VARCHAR2(255) NOT NULL,
    checksum VARCHAR2(71) NOT NULL,
    "size" FLOAT NOT NULL,
    expires DATE NOT NULL,
    stream VARCHAR2(255) NOT NULL,
    shortname VARCHAR(255) NOT NULL,
    version VARCHAR2(3) NOT NULL,
    CONSTRAINT file_metadata_uc UNIQUE(name, checksum),
    PRIMARY KEY(fileid)
);

CREATE OR REPLACE TRIGGER file_metadata_trg
BEFORE INSERT ON "FILE_METADATA"
FOR EACH ROW
BEGIN
    IF :new.fileid IS NULL THEN
        SELECT file_metadata_seq.nextval INTO :new.fileid FROM DUAL;
    END IF;
END;


-- file_queue table
CREATE SEQUENCE file_queue_seq
    INCREMENT BY 1 START WITH 1
    MINVALUE 1 MAXVALUE 9999999999999999999999999999
    NOCYCLE CACHE 2;

CREATE TABLE file_queue (
    queueid NUMBER NOT NULL,
    username VARCHAR2(30) NOT NULL,
    fileid NUMBER(15) NOT NULL,
    entry_date DATE NOT NULL,
    expires DATE NOT NULL,
    FOREIGN KEY(fileid) REFERENCES file_metadata(fileid),
    FOREIGN KEY(username) REFERENCES accounts(username),
    CONSTRAINT file_queue_uc UNIQUE(username, fileid),
    PRIMARY KEY(queueid)
);

CREATE OR REPLACE TRIGGER file_queue_trg
BEFORE INSERT ON "FILE_QUEUE"
FOR EACH ROW
BEGIN
    IF :new.queueid IS NULL THEN
        SELECT file_queue_seq.nextval INTO :new.queueid FROM DUAL;
    END IF;
END;


-- transactions table
CREATE SEQUENCE transactions_seq
    INCREMENT BY 1 START WITH 1
    MINVALUE 1 MAXVALUE 9999999999999999999999999999
    NOCYCLE CACHE 2;

CREATE TABLE transactions (
    transactionid NUMBER NOT NULL,
    action VARCHAR(255) NOT NULL,
    username VARCHAR2(30) NOT NULL,
    start_time DATE NOT NULL,
    fileid NUMBER(15),
    source VARCHAR2(255),
    destination VARCHAR2(255),
    end_time DATE,
    complete NUMBER(1) CHECK (complete IN (0,1)),
    FOREIGN KEY(fileid) REFERENCES file_metadata(fileid),
    FOREIGN KEY(username) REFERENCES accounts(username),
    PRIMARY KEY(transactionid)
);

CREATE OR REPLACE TRIGGER transactions_trg
BEFORE INSERT ON "TRANSACTIONS"
FOR EACH ROW
BEGIN
    IF :new.transactionid IS NULL THEN
        SELECT transactions_seq.nextval INTO :new.transactionid FROM DUAL;
    END IF;
END;