CREATE SEQUENCE USER_INFO_SEQ
START WITH 1       
INCREMENT BY 1       
NOCACHE NOCYCLE; 

-- drop SEQUENCE USER_INFO_SEQ;

-- drop table user_info CASCADE CONSTRAINTS;
-- drop table parents_mol CASCADE CONSTRAINTS;
-- drop table generate_mol CASCADE CONSTRAINTS;
-- drop table optim_mol CASCADE CONSTRAINTS;
-- drop table remedy_list CASCADE CONSTRAINTS;

CREATE TABLE generate_mol 
    ( 
     user_seq       NUMBER  NOT NULL , 
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
     g_category     CHAR (1)  NOT NULL , 
     p_canosmiles   VARCHAR2 (500)  NOT NULL 
    ) 
;

ALTER TABLE generate_mol 
    ADD CONSTRAINT generate_mol_PK PRIMARY KEY ( user_seq, g_canosmiles ) ;

CREATE TABLE optim_mol 
    ( 
     user_seq       NUMBER  NOT NULL , 
     g_canosmiles   VARCHAR2 (500)  NOT NULL , 
     o_canosmiles   VARCHAR2 (500)  NOT NULL , 
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

ALTER TABLE optim_mol 
    ADD CONSTRAINT optim_mol_pk PRIMARY KEY ( o_canosmiles ) ;

CREATE TABLE parents_mol 
    ( 
     user_seq       NUMBER  NOT NULL , 
     p_canosmiles   VARCHAR2 (500)  NOT NULL , 
     p_pubchem_id   VARCHAR2 (100)  NOT NULL , 
     p_mol_name     VARCHAR2 (500)  NOT NULL , 
     p_scaffold     VARCHAR2 (300)  NOT NULL , 
     p_formula      VARCHAR2 (300)  NOT NULL , 
     p_image_base64 CLOB  NOT NULL , 
     p_mol_weight   NUMBER (6,2)  NOT NULL , 
     p_logp         NUMBER (4,2)  NOT NULL , 
     p_qed          NUMBER (3,2)  NOT NULL , 
     p_pki_res      VARCHAR2 (20)  NOT NULL , 
     p_pki          NUMBER (4,2)  NOT NULL , 
     p_pkd          NUMBER (4,2)  NOT NULL , 
     p_toxic        NUMBER (4,2)  NOT NULL , 
     p_btn_category VARCHAR2 (50)  NOT NULL , 
     p_graph_logp   NUMBER (2,1)  NOT NULL , 
     p_graph_qed    NUMBER (2,1)  NOT NULL , 
     p_graph_pki    NUMBER (2,1)  NOT NULL , 
     p_graph_pkd    NUMBER (2,1)  NOT NULL , 
     p_graph_toxic  NUMBER (2,1)  NOT NULL , 
     p_category     CHAR (1)  NOT NULL 
    ) 
;

ALTER TABLE parents_mol 
    ADD CONSTRAINT parents_mol_PK PRIMARY KEY ( p_canosmiles, user_seq ) ;

CREATE TABLE remedy_list 
    ( 
     r_canosmiles   VARCHAR2 (500)  NOT NULL , 
     r_pubchem_id   VARCHAR2 (100)  NOT NULL , 
     r_mol_name     VARCHAR2 (500)  NOT NULL , 
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


ALTER TABLE remedy_list 
    ADD CONSTRAINT remedy_list_PK PRIMARY KEY ( r_canosmiles ) ;

CREATE TABLE user_info 
    ( 
     user_seq    NUMBER  NOT NULL , 
     email       VARCHAR2 (200)  NOT NULL , 
     pwd         VARCHAR2 (100) , 
     affiliation VARCHAR2 (100)  NOT NULL 
    ) 
;

ALTER TABLE user_info 
    ADD CONSTRAINT user_info_PK PRIMARY KEY ( user_seq ) ;

ALTER TABLE generate_mol 
    ADD CONSTRAINT gm_pm_FK FOREIGN KEY 
    ( 
     p_canosmiles,
     user_seq
    ) 
    REFERENCES parents_mol 
    ( 
     p_canosmiles,
     user_seq
    ) 
;

ALTER TABLE optim_mol 
    ADD CONSTRAINT om_gm_FK FOREIGN KEY 
    ( 
     user_seq,
     g_canosmiles
    ) 
    REFERENCES generate_mol 
    ( 
     user_seq,
     g_canosmiles
    ) 
;


ALTER TABLE parents_mol 
    ADD CONSTRAINT pm_ui_FK FOREIGN KEY 
    ( 
     user_seq
    ) 
    REFERENCES user_info 
    ( 
     user_seq
    ) 
;

ALTER TABLE parents_mol
MODIFY p_btn_category NULL;

ALTER TABLE parents_mol
ADD CONSTRAINT ck_pm_btn_category
CHECK (
    (p_category = 'R' AND p_btn_category IS NOT NULL)
    OR
    (p_category <> 'R' AND p_btn_category IS NULL)
);

delete from OPTIM_MOL;
commit;
delete from generate_mol;
commit;
delete from PARENTS_MOL;
commit;

select * from remedy_list;