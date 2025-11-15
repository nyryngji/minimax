from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import oracledb
import pandas as pd
import random
from prediction_all import *
import torch
import random
# from chembl_webresource_client.new_client import new_client
import pubchempy as pcp
from datetime import datetime
import pubchempy as pcp

# & 가상환경 시작 & D:/minimax/.venv/Scripts/Activate.ps1
# 웹서버 시작 : uvicorn main:app --reload

app = FastAPI()

oracledb.init_oracle_client(lib_dir=r"D:\\instantclient_23_9")

conn = oracledb.connect(
    user="adsql",          # 사용자명
    password="oracle_4U",      # 비밀번호
    dsn="localhost:1521/xe" # 접속 정보 (SQL Developer와 동일)
)
cur = conn.cursor()

# 프론트엔드와 통신 허용 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 중엔 * 허용 (배포 시 도메인 지정)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 여기부터 백엔드 코드 시작
current_user_seq = 9

@app.post("/user_diy")
async def predict(request: Request): 
    # 1. 사용자 입력 받기
    molecule_name = 'acetaminophen'.upper()
    cur.execute("SELECT USER_INPUT_DB_SEQ.NEXTVAL FROM dual")

    user_input_pk = {'uinput_seq': cur.fetchone()[0], # 현재 user_input 시퀀스
                    'user_info_seq' : current_user_seq} # 현재 접속한 유저의 고유값

    pubchem_data = return_chembl_data(molecule_name) # 화학적 정보 pubchem에서 가져오기

    # 2. 원조 분자의 화학적 특징 추출하기
    chemical_info = molecule_chemical_info(pubchem_data['smiles']) # 독성, pki, pkd 등
    graph_data = calculate_graph_stat(chemical_info) # 이건 오각형 그래프 구현을 위한 값
    insert_user_input = user_input_pk | pubchem_data | chemical_info | graph_data

    # 3. 원조 분자 정보를 user_input DB에 저장함
    sql = 'select * from user_input where rownum <= 1'
    user_input_db_col = pd.read_sql(sql, conn).columns
    try:
        insert_data('user_input', user_input_db_col, insert_user_input.values())
        conn.commit()
    except:
        print('이미 입력한 분자입니다.')
    
    # 4. 새로운 분자 생성하기
    sql2 = 'select * from generative_molecule where rownum <= 1'
    gen_mol_db_col = pd.read_sql(sql2, conn).columns

    for new_smiles in [generate_smiles(insert_user_input['smiles']) for i in range(5)]:
        try:
            cur.execute("SELECT GEN_MOL_SEQ.NEXTVAL FROM dual")
            gen_mol_info = {
                'gm_seq' : cur.fetchone()[0],
                'uinput_seq' : user_input_pk['uinput_seq'],
                'r_seq' : None,
                'smiles' : new_smiles
            }
            mol = Chem.MolFromSmiles(new_smiles)
            if lipinski_rule(mol): # 만약 리핀스키 5규칙을 만족하면 generative_molecule DB에 새로 생성한 분자 정보 저장
                new_smiles_chemical_info = molecule_chemical_info(gen_mol_info['smiles'])
                new_smiles_graph_info = calculate_graph_stat(new_smiles_chemical_info)
                insert_gen_mol = gen_mol_info | new_smiles_chemical_info | new_smiles_graph_info | {'category' : 'U'}
                insert_data('generative_molecule', gen_mol_db_col, insert_gen_mol.values())
        except:
            print('에러 발생')
            continue
        
    return {'current_user' : current_user_seq}

@app.post("/button_diy") 
async def predict(request: Request):
    user_selected_button = '암 치료제' # 입력 : 누른 버튼 이름 

    extract_random_sql = f'''SELECT r_seq, r_canosmiles
                                FROM (
                                    SELECT *
                                    FROM remedy_input
                                    WHERE r_category = '{user_selected_button}'
                                    ORDER BY DBMS_RANDOM.VALUE
                                )
                                WHERE ROWNUM = 1
                                '''
    # 저장해놓은 암 치료제 분자 중 랜덤으로 한 행 추출

    random_smiles = pd.read_sql(extract_random_sql, conn).to_dict(orient='records')[0]

    gen_mol_query = 'select * from generative_molecule where rownum <= 1'
    gen_mol_db_col = pd.read_sql(gen_mol_query, conn).columns

    for new_smiles in [generate_smiles(random_smiles['R_CANOSMILES']) for i in range(5)]:
        try:
            cur.execute("SELECT GEN_MOL_SEQ.NEXTVAL FROM dual")
            gen_mol_info = {
                'gm_seq' : cur.fetchone()[0],
                'uinput_seq' : None,
                'r_seq' : random_smiles['R_SEQ'],
                'smiles' : new_smiles
            }
            mol = Chem.MolFromSmiles(new_smiles)
            if lipinski_rule(mol): # 만약 리핀스키 5규칙을 만족하면
                new_smiles_chemical_info = molecule_chemical_info(gen_mol_info['smiles'])
                new_smiles_graph_info = calculate_graph_stat(new_smiles_chemical_info)
                insert_gen_mol = gen_mol_info | new_smiles_chemical_info | new_smiles_graph_info | {'category' : 'R'}
                insert_data('generative_molecule', gen_mol_db_col, insert_gen_mol.values())
                # generative_molecule DB에 새로 생성한 분자 정보 저장
        except:
            print('에러 발생')
            continue
    return {'current_user' : current_user_seq}


@app.post("/show_generate_molecule")
async def predict(request: Request):
    show_all_mols = {'R' : [], 'U' : []} # R : 버튼 기반, U : 유저 입력 기반

    # remedy_input에 있는 기본 제공 분자 + 버튼으로 생성한 분자 정보 조회하기
    remedy_gen_sql = f'''select ri.r_seq as ri_r_seq, ri.*,gm.r_seq as gm_r_seq, gm.*
                        from remedy_input ri 
                        join generative_molecule gm
                        on ri.r_seq = gm.r_seq
                        join g_unique_info gu
                        on gm.gm_seq = gu.gm_seq
                        where user_info_seq = {current_user_seq}'''

    # 사용자 입력 분자 + 사용자 입력 분자 기반으로 생성한 분자 정보 조회하기
    uinput_gen_sql = f'''select ui.uinput_seq ui_seq, ui.*,gm.*
                        from user_input ui
                        join generative_molecule gm
                        on ui.uinput_seq = gm.uinput_seq
                        where ui.user_info_seq = {current_user_seq}'''
    
    # sql 쿼리 결과를 pandas 데이터 프레임으로 가져오기
    remedy_gen_info = pd.read_sql(remedy_gen_sql, conn)
    uinput_gen_info = pd.read_sql(uinput_gen_sql, conn)

    # on 절로 인한 겹치는 컬럼 제거하기
    remedy_gen_info = remedy_gen_info.drop('R_SEQ',axis=1)
    uinput_gen_info = uinput_gen_info.drop('UINPUT_SEQ',axis=1)

    # base64를 str로 전환 (전환 안하면 oracle.CLOB 형태로 보임)
    remedy_gen_info = remedy_gen_info.apply(lambda col: col.map(lob_to_str))
    uinput_gen_info = uinput_gen_info.apply(lambda col: col.map(lob_to_str))

    # 원조 분자 정보와 생성된 분자 컬럼 분리하기
    remedy_par_cols = [c for c in remedy_gen_info.columns if c.startswith("R_") or c.startswith("r_")]
    remedy_child_cols  = [c for c in remedy_gen_info.columns if c not in remedy_par_cols]

    uinput_par_cols = [c for c in uinput_gen_info.columns if c.startswith("U_") or c.startswith("u_")]
    uinput_child_cols  = [c for c in uinput_gen_info.columns if c not in uinput_par_cols]

    for r_seq, group in remedy_gen_info.groupby("RI_R_SEQ"):
        parent = group[remedy_par_cols].iloc[0].to_dict()
        gm_list = group[remedy_child_cols].to_dict(orient='records')

        # 원조 분자 + 생성된 n개 분자로 딕셔너리에 저장
        show_all_mols['R'].append({
            'parent' : parent,
            'children': gm_list
        })

    for r_seq, group in uinput_gen_info.groupby("UI_SEQ"):
        parent = group[uinput_par_cols].iloc[0].to_dict()
        gm_list = group[uinput_child_cols].to_dict(orient='records')

        show_all_mols['U'].append({
            'parent' : parent,
            'children': gm_list
        })
        
    return {'show_all_mols' : show_all_mols}

@app.post("/optim_molecule")
async def predict(request: Request): # 분자 최적화 수행하기
    find_target_sql = '''select gm_seq, g_canosmiles from generative_molecule
					     where rownum <= 1'''
    target_info = pd.read_sql(find_target_sql, conn).iloc[0].to_dict()

    return {'optim_return_value' : ''}



@app.post("/optim_molecule_show")
async def predict(request: Request):
    return {'' : ''}