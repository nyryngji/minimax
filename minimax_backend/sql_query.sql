-- CREATE SEQUENCE USER_INFO_DB_SEQ
-- START WITH 1       
-- INCREMENT BY 1       
-- NOCACHE              
-- NOCYCLE; 

-- CREATE SEQUENCE USER_INPUT_DB_SEQ
-- START WITH 1       
-- INCREMENT BY 1       
-- NOCACHE              
-- NOCYCLE; 

-- CREATE SEQUENCE REMEDY_INPUT_SEQ
-- START WITH 1       
-- INCREMENT BY 1       
-- NOCACHE              
-- NOCYCLE; 

-- CREATE SEQUENCE GEN_MOL_SEQ 
-- START WITH 1       
-- INCREMENT BY 1       
-- NOCACHE              
-- NOCYCLE; 

-- CREATE SEQUENCE OPTIM_MOL_SEQ 
-- START WITH 1       
-- INCREMENT BY 1       
-- NOCACHE              
-- NOCYCLE; 

CREATE TABLE user_info 
    ( 
     user_info_seq NUMBER  NOT NULL , 
     email         VARCHAR2 (200)  NOT NULL , 
     affiliation   VARCHAR2 (100)  NOT NULL 
    ) 
;

CREATE TABLE user_input 
    ( 
     uinput_seq     NUMBER  NOT NULL , 
     user_info_seq  NUMBER  NOT NULL , 
     u_pubchem_id   VARCHAR2 (100)  NOT NULL , 
     u_mol_name     VARCHAR2 (200)  NOT NULL , 
     u_canosmiles   VARCHAR2 (500)  NOT NULL , 
     u_scaffold     VARCHAR2 (300)  NOT NULL , 
     u_formula      VARCHAR2 (300)  NOT NULL , 
     u_image_base64 CLOB  NOT NULL , 
     u_mol_weight   NUMBER (6,2)  NOT NULL , 
     u_logp         NUMBER (4,2)  NOT NULL , 
     u_qed          NUMBER (3,2)  NOT NULL , 
     u_pki_res      VARCHAR2 (20)  NOT NULL , 
     u_pki          NUMBER (4,2)  NOT NULL , 
     u_pkd          NUMBER (4,2)  NOT NULL , 
     u_toxic        NUMBER (4,2)  NOT NULL , 
     u_graph_logp   NUMBER (2,1)  NOT NULL , 
     u_graph_qed    NUMBER (2,1)  NOT NULL , 
     u_graph_pki    NUMBER (2,1)  NOT NULL , 
     u_graph_pkd    NUMBER (2,1)  NOT NULL , 
     u_graph_toxic  NUMBER (2,1)  NOT NULL 
    ) 
;

CREATE TABLE generative_molecule 
    ( 
     gm_seq         NUMBER  NOT NULL , 
     uinput_seq     NUMBER  NULL , 
     r_seq          NUMBER  NULL , 
     g_canosmiles   VARCHAR2 (500)  NOT NULL , 
     g_image_base64 CLOB  NOT NULL , 
     g_mol_weight   NUMBER (6,2)  NOT NULL , 
     g_logp         NUMBER (4,2)  NOT NULL , 
     g_qed          NUMBER (3,2)  NOT NULL , 
     g_pki_res      VARCHAR2 (20)  NOT NULL , 
     g_pki          NUMBER (4,2)  NOT NULL , 
     g_pkd          NUMBER (4,2)  NOT NULL , 
     g_toxic        NUMBER (4,2)  NOT NULL , 
     g_graph_logp   NUMBER (2,1)  NOT NULL , 
     g_graph_qed    NUMBER (2,1)  NOT NULL , 
     g_graph_pki    NUMBER (2,1)  NOT NULL , 
     g_graph_pkd    NUMBER (2,1)  NOT NULL , 
     g_graph_toxic  NUMBER (2,1)  NOT NULL , 
     g_category     CHAR (1)  NOT NULL 
    ) 
;

CREATE TABLE remedy_input 
    ( 
     r_seq          NUMBER  NOT NULL , 
     r_pubchem_id   VARCHAR2 (100)  NOT NULL , 
     r_mol_name     VARCHAR2 (500)  NOT NULL , -- 200으로는 택도 없음
     r_canosmiles   VARCHAR2 (500)  NOT NULL , 
     r_scaffold     VARCHAR2 (300)  NOT NULL , 
     r_formula      VARCHAR2 (300)  NOT NULL , 
     r_image_base64 CLOB  NOT NULL , 
     r_mol_weight   NUMBER (6,2)  NOT NULL , 
     r_logp         NUMBER (4,2)  NOT NULL , 
     r_qed          NUMBER (3,2)  NOT NULL , 
     r_pki_res      VARCHAR2 (20)  NOT NULL , 
     r_pki          NUMBER (4,2)  NOT NULL , 
     r_pkd          NUMBER (4,2)  NOT NULL , 
     r_toxic        NUMBER (4,2)  NOT NULL , 
     r_category     VARCHAR2 (50)  NOT NULL , 
     r_graph_logp   NUMBER (2,1)  NOT NULL , 
     r_graph_qed    NUMBER (2,1)  NOT NULL , 
     r_graph_pki    NUMBER (2,1)  NOT NULL , 
     r_graph_pkd    NUMBER (2,1)  NOT NULL , 
     r_graph_toxic  NUMBER (2,1)  NOT NULL 
    ) 
;

CREATE TABLE optim_molecule 
    ( 
     gm_seq         NUMBER  NOT NULL , 
     o_seq          NUMBER  NOT NULL , 
     o_canosmiles   VARCHAR2 (500)  NOT NULL , 
     o_scaffold     VARCHAR2 (300)  NOT NULL , 
     o_formula      VARCHAR2 (300)  NOT NULL , 
     o_image_base64 CLOB  NOT NULL , 
     o_mol_weight   NUMBER (6,2)  NOT NULL , 
     o_logp         NUMBER (4,2)  NOT NULL , 
     o_qed          NUMBER (3,2)  NOT NULL , 
     o_pki_res      VARCHAR2 (20)  NOT NULL , 
     o_pki          NUMBER (4,2)  NOT NULL , 
     o_pkd          NUMBER (4,2)  NOT NULL , 
     o_toxic        NUMBER (4,2)  NOT NULL , 
     o_per_logp     NUMBER (4,1)  NOT NULL , 
     o_per_qed      NUMBER (4,1)  NOT NULL , 
     o_per_pki      NUMBER (4,1)  NOT NULL , 
     o_per_pkd      NUMBER (4,1)  NOT NULL , 
     o_per_toxic    NUMBER (4,1)  NOT NULL 
    ) 
;

CREATE TABLE g_unique_info 
    ( 
     gm_seq        NUMBER  NOT NULL , 
     user_info_seq NUMBER  NOT NULL 
    ) 
;


ALTER TABLE user_info 
    ADD CONSTRAINT user_info_PK PRIMARY KEY ( user_info_seq ) ;

ALTER TABLE user_input 
    ADD CONSTRAINT user_input_pk PRIMARY KEY ( uinput_seq ) ;

ALTER TABLE generative_molecule 
    ADD CONSTRAINT user_inputv1_PK PRIMARY KEY ( gm_seq ) ;

ALTER TABLE remedy_input 
    ADD CONSTRAINT remedy_input_pk PRIMARY KEY ( r_seq ) ;

ALTER TABLE optim_molecule 
    ADD CONSTRAINT optim_molecule_pk PRIMARY KEY ( o_seq ) ;

ALTER TABLE g_unique_info 
    ADD CONSTRAINT g_unique_info_PK PRIMARY KEY ( gm_seq ) ;


ALTER TABLE user_input 
    ADD CONSTRAINT user_input_user_info_FK FOREIGN KEY 
    ( 
     user_info_seq
    ) 
    REFERENCES user_info 
    ( 
     user_info_seq
    ) 
;

ALTER TABLE generative_molecule 
    ADD CONSTRAINT gm_ri_FK FOREIGN KEY 
    ( 
     r_seq
    ) 
    REFERENCES remedy_input 
    ( 
     r_seq
    ) 
;

ALTER TABLE generative_molecule 
    ADD CONSTRAINT uinput_gm_FK FOREIGN KEY 
    ( 
     uinput_seq
    ) 
    REFERENCES user_input 
    ( 
     uinput_seq
    ) 
;


ALTER TABLE generative_molecule
ADD CONSTRAINT gm_category_check
CHECK (
    (g_category = 'U' AND uinput_seq IS NOT NULL AND r_seq IS NULL)
 OR (g_category = 'R' AND r_seq IS NOT NULL AND uinput_seq IS NULL)
);

ALTER TABLE optim_molecule 
    ADD CONSTRAINT optim_mol_gen_mol_FK FOREIGN KEY 
    ( 
     gm_seq
    ) 
    REFERENCES generative_molecule 
    ( 
     gm_seq
    ) 
;

ALTER TABLE g_unique_info 
    ADD CONSTRAINT gu_gm_FK FOREIGN KEY 
    ( 
     gm_seq
    ) 
    REFERENCES generative_molecule 
    ( 
     gm_seq
    ) 
;


-- drop TABLE user_info CASCADE CONSTRAINTS;
-- -- drop TABLE remedy_input CASCADE CONSTRAINTS;

-- drop TABLE user_input CASCADE CONSTRAINTS;
-- drop TABLE generative_molecule CASCADE CONSTRAINTS;
-- drop TABLE g_unique_info CASCADE CONSTRAINTS;
-- drop TABLE optim_molecule CASCADE CONSTRAINTS;

-- INSERT INTO user_info ( -- user 기본 정보 삽입하기
--     user_info_seq,
--     email,
--     affiliation
-- ) VALUES (
--     USER_INFO_DB_SEQ.NEXTVAL,
--     'test@example.com',
--     'Research Center'
-- );

-- INSERT INTO user_info ( -- user 기본 정보 삽입하기
--     user_info_seq,
--     email,
--     affiliation
-- ) VALUES (
--     USER_INFO_DB_SEQ.NEXTVAL,
--     'test2@example.com',
--     'Research Center2'
-- );

-- commit;