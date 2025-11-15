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
current_user_seq = 1

@app.post("/user_diy") 
async def predict(request: Request): 
    molecule_name = input().upper()

    parents_mol_sql = 'select * from parents_mol where rownum <= 1'
    parents_mol_db_col = pd.read_sql(parents_mol_sql, conn).columns

    pubchem_info = return_pubchem_data(molecule_name)
    new_smiles_chemical_info = molecule_chemical_info(pubchem_info['smiles'])
    new_smiles_graph_info = calculate_graph_stat(new_smiles_chemical_info)

    insert_parents_mol_value = {'user_seq' : current_user_seq} | pubchem_info | new_smiles_chemical_info | {'btn_category' : None} | new_smiles_graph_info | {'category' : 'U'}

    select_pm_query = 'select * from parents_mol where rownum <= 1'
    parents_mol_db_col = pd.read_sql(select_pm_query, conn).columns
    try:
        insert_data('parents_mol', parents_mol_db_col, insert_parents_mol_value.values())
    except:
        print('이미 있는 분자입니다.')
        continue

    # 4. 새로운 분자 생성하기
    sql2 = 'select * from generate_mol where rownum <= 1'
    gen_mol_db_col = pd.read_sql(sql2, conn).columns

    for new_smiles in [generate_smiles(insert_parents_mol_value['smiles']) for i in range(5)]:
        gen_mol_info = {
            'user_seq' : current_user_seq,
            'smiles' : new_smiles
        }
        mol = Chem.MolFromSmiles(new_smiles)
        if lipinski_rule(mol): # 만약 리핀스키 5규칙을 만족하면 generative_molecule DB에 새로 생성한 분자 정보 저장
            new_smiles_chemical_info = molecule_chemical_info(gen_mol_info['smiles'])
            new_smiles_graph_info = calculate_graph_stat(new_smiles_chemical_info)
            insert_gen_mol = gen_mol_info | new_smiles_chemical_info | new_smiles_graph_info | {'category' : 'U'} | {'p_canosmiles' : insert_parents_mol_value['smiles']}
            try:
                insert_data('generate_mol', gen_mol_db_col, insert_gen_mol.values())
            except:
                print('이미 생성된 분자입니다.')
                continue
    
    rename_col = dict(zip(insert_parents_mol_value.keys(), parents_mol_db_col))
    user_diy_return_value = { rename_col.get(k, k): v for k, v in insert_parents_mol_value.items() }

    return {'user_diy_return_value' : user_diy_return_value}

@app.post("/button_diy") 
async def predict(request: Request):
    user_selected_button = input() # 입력 : 누른 버튼 이름 

    extract_random_sql = f'''SELECT *
                                FROM (
                                    SELECT *
                                    FROM remedy_list
                                    WHERE r_category = '{user_selected_button}'
                                    ORDER BY DBMS_RANDOM.VALUE
                                )
                                WHERE ROWNUM = 1
                                '''
    # 저장해놓은 치료제 분자 중 랜덤으로 한 행 추출

    random_smiles = pd.read_sql(extract_random_sql, conn)
    random_smiles = random_smiles.apply(lambda col: col.map(lob_to_str)).iloc[0].to_dict()

    select_pm_query = 'select * from parents_mol where rownum <= 1'
    parents_mol_db_col = pd.read_sql(select_pm_query, conn).columns
    insert_parents_mol_value = {'user_seq' : 1} | random_smiles | {'p_category' : 'R'}

    try:
        insert_data('parents_mol', parents_mol_db_col, insert_parents_mol_value.values())
    except:
        print('이미 존재하는 부모 분자입니다')

    gen_mol_sql = 'select * from generate_mol where rownum <= 1'
    gen_mol_db_col = pd.read_sql(gen_mol_sql, conn).columns

    for new_smiles in [generate_smiles(insert_parents_mol_value['R_CANOSMILES']) for i in range(5)]:
        gen_mol_info = {
            'user_seq' : 1,
            'smiles' : new_smiles
        }
        mol = Chem.MolFromSmiles(new_smiles)
        if lipinski_rule(mol): # 만약 리핀스키 5규칙을 만족하면 generative_molecule DB에 새로 생성한 분자 정보 저장
            new_smiles_chemical_info = molecule_chemical_info(gen_mol_info['smiles'])
            new_smiles_graph_info = calculate_graph_stat(new_smiles_chemical_info)
            insert_gen_mol = gen_mol_info | new_smiles_chemical_info | new_smiles_graph_info | {'category' : 'U'} | {'p_canosmiles' : insert_parents_mol_value['R_CANOSMILES']}
            try:		
                insert_data('generate_mol', gen_mol_db_col, insert_gen_mol.values())
            except:
                print('이미 존재하는 생성 분자입니다.')
                continue

    rename_col = dict(zip(insert_parents_mol_value.keys(), parents_mol_db_col))
    btn_diy_return_value = {rename_col.get(k, k): v for k, v in insert_parents_mol_value.items()}
    
    return {'btn_diy_return_value' : btn_diy_return_value}

@app.post("/show_parents_mol") 
async def predict(request: Request):
    return_value = {
        "U": [],
        "R": {}
    }

    par_mol_sql = 'select * from parents_mol where user_seq = 1'
    par_mol_db = pd.read_sql(par_mol_sql, conn)
    par_mol_db = par_mol_db.apply(lambda col: col.map(lob_to_str))

    for i in range(len(par_mol_db)):
        x = par_mol_db.iloc[i].to_dict()
        if x['P_CATEGORY'] == 'U':
            return_value['U'].append(x)

        else:	
            if x['P_BTN_CATEGORY'] not in return_value['R']:
                return_value["R"][x['P_BTN_CATEGORY']] = []
            return_value["R"][x['P_BTN_CATEGORY']].append(x)

    return {'show_parents_mol_return_value' : return_value}
    
@app.post("/user_diy_show") 
async def predict(request: Request):
    # 부모 분자 중 하나 입력 받기
    click_par_mol = 'C1=CC(=C(C=C1CC(C(=O)O)N)O)O'
    find_gen_mol_sql = f"select * from generate_mol where user_seq = {current_user_seq} and p_canosmiles = '{click_par_mol}'"

    gen_mol_info = pd.read_sql(find_gen_mol_sql, conn)
    gen_mol_info = gen_mol_info.apply(lambda col: col.map(lob_to_str))

    return_value = gen_mol_info.to_dict(orient='records')
    return {'user_diy_show_return_value' : return_value}

@app.post("/button_diy_show")
async def predict(request: Request):
    # 부모 분자 중 하나 입력 받기
    click_par_mol = 'C1=CC(=C(C=C1CC(C(=O)O)N)O)O'
    find_gen_mol_sql = f"select * from generate_mol where user_seq = {current_user_seq} and p_canosmiles = '{click_par_mol}'"

    gen_mol_info = pd.read_sql(find_gen_mol_sql, conn)
    gen_mol_info = gen_mol_info.apply(lambda col: col.map(lob_to_str))

    return_value = gen_mol_info.to_dict(orient='records')
    return {'button_diy_show_return_value' : return_value}

@app.post("/optim_molecule")
async def predict(request: Request): # 분자 최적화 수행하기
    target = '[C-1]#[N+1][C-1]=[C-1]C(OP=NCN=COP(=O)(F)F)PCl'
    gen_size = 3
    generation = [make_random_chrono(target) for _ in range(gen_size)]
    orig_chem_info = molecule_chemical_info2(target)
    max_iter = 2
    best_fitness = 10
    iteration = 0

    mol = Chem.MolFromSmiles(target)

    # 종료 조건 만족(최적해 발견) 시까지 반복
    while best_fitness <= 20 and iteration < max_iter:
        iteration += 1
        best_chrono, best_fitness = get_best_chrono(generation, orig_chem_info)
        print('Gen', iteration, '---', 'Best:', best_chrono, 'fitness:', best_fitness)
        generation = make_offsprings(generation, orig_chem_info, gen_size)
    
    
    g_mol_sql = f"select g_logp, g_qed, g_pki, g_pkd, g_toxic from generate_mol where g_canosmiles = '{target}'"
    g_mol_chem_info = pd.read_sql(g_mol_sql, conn).iloc[0].to_dict()
    
    optim_mol_sql = f"select * from optim_mol where rownum <= 1"

    optim_mol_col = pd.read_sql(optim_mol_sql, conn).columns
    optim_mol_info = {
        'user_seq' : 1,
        'g_canosmiles' : target,
        'o_canosmiles' : best_chrono,
    }

    optim_mol_chem_info = molecule_chemical_info(best_chrono)
    cal_per_optim = calculate_per(g_mol_chem_info, optim_mol_chem_info)

    insert_optim_mol = optim_mol_info | optim_mol_chem_info | cal_per_optim

    try:
        insert_data('optim_mol', optim_mol_col, insert_optim_mol.values())
    except:
        print('이미 생성된 분자입니다.')
    
    return {'optim_molecule_return_value' : insert_optim_mol}

@app.post("/optim_molecule_show")
async def predict(request: Request):
    current_user_seq = 1
    click_gen_mol = '[C-1]#[N+1][C-1]=[C-1]C(OP=NCN=COP(=O)(F)F)PCl'
    find_gen_mol_sql = f"select * from optim_mol where user_seq = {current_user_seq} and g_canosmiles = '{click_gen_mol}'"

    gen_mol_info = pd.read_sql(find_gen_mol_sql, conn)
    gen_mol_info = gen_mol_info.apply(lambda col: col.map(lob_to_str))

    return_value = gen_mol_info.to_dict(orient='records')
    return {'optim_molecule_show_return_value' : return_value}