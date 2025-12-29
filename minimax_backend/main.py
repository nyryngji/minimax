from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import oracledb
import pandas as pd
import random
from func import *
from genetic_algorithm import *
import random

# & 가상환경 시작 & D:/minimax/.venv/Scripts/Activate.ps1
# 웹서버 시작 : uvicorn main:app --reload

app = FastAPI()

load_dotenv('key.env')

oracledb.init_oracle_client(lib_dir=r"D:\\instantclient_23_9")

db_user_name = os.getenv("db_user_name")
db_pwd = os.getenv("db_pwd")
db_dsn = os.getenv("db_dsn")

conn = oracledb.connect(
    user=db_user_name,          # 사용자명
    password=db_pwd,      # 비밀번호
    dsn=db_dsn # 접속 정보 (SQL Developer와 동일)
)

cur = conn.cursor()
conn.commit()

# 프론트엔드와 통신 허용 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 중엔 * 허용 (배포 시 도메인 지정)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

current_user_seq = 1 # 현재 접속한 유저 고유 ID

parents_mol_sql = 'select * from parents_mol where rownum <= 1'
parents_mol_db_col = pd.read_sql(parents_mol_sql, conn).columns

gen_mol_sql = 'select * from generate_mol where rownum <= 1'
gen_mol_db_col = pd.read_sql(gen_mol_sql, conn).columns

@app.post("/user_diy") 
async def user_diy(request: Request): 
    # body = await request.json()
    # molecule_name = body["molecule_name"] # 입력 받는 부분
    molecule_name = 'aspirin'

    pubchem_info = return_pubchem_data(molecule_name)
    new_smiles_chemical_info = molecule_chemical_info(pubchem_info['smiles'])
    new_smiles_graph_info = calculate_graph_stat(new_smiles_chemical_info)

    insert_parents_mol_value = {'user_seq' : current_user_seq} | pubchem_info | new_smiles_chemical_info | {'btn_category' : None} | new_smiles_graph_info | {'category' : 'U'}
    try:
        insert_data('parents_mol', parents_mol_db_col, insert_parents_mol_value.values())
    except Exception as e:
        print(e)

    for new_smiles in [generate_smiles(insert_parents_mol_value['smiles'])['generated_smiles'] for i in range(5)]:
        gen_mol_info = {
            'user_seq' : current_user_seq,
            'smiles' : new_smiles
        }
        
        mol = Chem.MolFromSmiles(new_smiles)
        if lipinski_rule(mol)['lipinski']: # 만약 리핀스키 5규칙을 만족하면 generative_molecule DB에 새로 생성한 분자 정보 저장
            new_smiles_chemical_info = molecule_chemical_info(gen_mol_info['smiles'])
            new_smiles_graph_info = calculate_graph_stat(new_smiles_chemical_info)
            insert_gen_mol = gen_mol_info | new_smiles_chemical_info | new_smiles_graph_info | {'category' : 'U'} | {'p_canosmiles' : insert_parents_mol_value['smiles']}
            try:
                insert_data('generate_mol', gen_mol_db_col, insert_gen_mol.values())
                print(f'새로운 분자 생성 완료 : {new_smiles}')
            except Exception as e:
                print(e)
                continue
    
    rename_col = dict(zip(insert_parents_mol_value.keys(), parents_mol_db_col))
    user_diy_return_value = { rename_col.get(k, k): v for k, v in insert_parents_mol_value.items() }

    return user_diy_return_value

@app.post("/btn_diy") 
async def btn_diy(request: Request):
    # body = await request.json()
    # user_selected_button = body["button_type"] # 입력 : 누른 버튼 이름 

    user_selected_button = '항바이러스제'
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

    insert_parents_mol_value = {'user_seq' : current_user_seq} | random_smiles | {'p_category' : 'R'}

    try:
        insert_data('parents_mol', parents_mol_db_col, insert_parents_mol_value.values())
    except Exception as e:
        print(e)

    for new_smiles in [generate_smiles(insert_parents_mol_value['R_CANOSMILES'])['generated_smiles'] for i in range(5)]:
        gen_mol_info = {
            'user_seq' : current_user_seq,
            'smiles' : new_smiles
        }
        mol = Chem.MolFromSmiles(new_smiles)
        if lipinski_rule(mol)['lipinski']: # 만약 리핀스키 5규칙을 만족하면 generative_molecule DB에 새로 생성한 분자 정보 저장
            new_smiles_chemical_info = molecule_chemical_info(gen_mol_info['smiles'])
            new_smiles_graph_info = calculate_graph_stat(new_smiles_chemical_info)
            insert_gen_mol = gen_mol_info | new_smiles_chemical_info | new_smiles_graph_info | {'category' : 'U'} | {'p_canosmiles' : insert_parents_mol_value['R_CANOSMILES']}
            try:		
                insert_data('generate_mol', gen_mol_db_col, insert_gen_mol.values())
                print(f'새로운 분자 생성 완료 : {new_smiles}')
            except Exception as e:
                print(e)
                continue

    rename_col = dict(zip(insert_parents_mol_value.keys(), parents_mol_db_col))
    btn_diy_return_value = {rename_col.get(k, k): v for k, v in insert_parents_mol_value.items()}
    
    return btn_diy_return_value

@app.post("/show_parents_mol") 
async def show_parents_mol(request: Request):
    par_return_value = {
        "U": [],
        "R": {}
    }

    par_mol_sql = 'select * from parents_mol where user_seq = 1'
    par_mol_db = pd.read_sql(par_mol_sql, conn)
    par_mol_db = par_mol_db.apply(lambda col: col.map(lob_to_str))

    for i in range(len(par_mol_db)):
        x = par_mol_db.iloc[i].to_dict()
        if x['P_CATEGORY'] == 'U':
            par_return_value['U'].append(x)

        else:	
            if x['P_BTN_CATEGORY'] not in par_return_value['R']:
                par_return_value["R"][x['P_BTN_CATEGORY']] = []
            par_return_value["R"][x['P_BTN_CATEGORY']].append(x)

    return par_return_value
    
@app.post("/user_diy_show") 
async def user_diy_show(request: Request):
    click_par_mol_sql = """
    SELECT p.P_CANOSMILES
    FROM GENERATE_MOL g
    JOIN parents_mol p
        ON g.P_CANOSMILES = p.P_CANOSMILES
    WHERE g.user_seq = 1
    AND p.P_CATEGORY = 'U'
    """
    click_par_mol_db = pd.read_sql(click_par_mol_sql, conn)['P_CANOSMILES'].unique()
    click_par_mol = random.sample(list(click_par_mol_db),1)[0]
        
    find_gen_mol_sql = "select * from generate_mol where user_seq = :current_user_seq and p_canosmiles = :click_par_mol"

    gen_mol_info = pd.read_sql(find_gen_mol_sql, conn, params = {'current_user_seq':current_user_seq, 'click_par_mol' : click_par_mol})
    gen_mol_info = gen_mol_info.apply(lambda col: col.map(lob_to_str))

    user_diy_show_return_value = gen_mol_info.to_dict(orient='records')
    return user_diy_show_return_value

@app.post("/button_diy_show")
async def button_diy_show(request: Request):
    click_par_mol_sql = """
    SELECT p.P_CANOSMILES
    FROM GENERATE_MOL g
    JOIN parents_mol p
        ON g.P_CANOSMILES = p.P_CANOSMILES
    WHERE g.user_seq = 1
    AND p.P_CATEGORY = 'R'
    """
    click_par_mol_db = pd.read_sql(click_par_mol_sql, conn)['P_CANOSMILES'].unique()
    click_par_mol = random.sample(list(click_par_mol_db),1)[0]

    find_gen_mol_sql = "select * from generate_mol where user_seq = :user_seq and p_canosmiles = :click_par_mol"

    gen_mol_info = pd.read_sql(find_gen_mol_sql, conn, params={'user_seq':current_user_seq, 'click_par_mol':click_par_mol})
    gen_mol_info = gen_mol_info.apply(lambda col: col.map(lob_to_str))

    button_diy_show_return_value = gen_mol_info.to_dict(orient='records')
    return button_diy_show_return_value

@app.post("/optim_molecule")
async def optim_molecule(request: Request): # 분자 최적화 수행하기
    click_par_mol_sql = "select g_canosmiles from GENERATE_MOL"
    click_par_mol_db = pd.read_sql(click_par_mol_sql, conn)['G_CANOSMILES'].unique()
    target = random.sample(list(click_par_mol_db),1)[0]
    
    gen_size = 3
    generation = [make_random_chrono(target) for _ in range(gen_size)]
    orig_chem_info = molecule_chemical_info2(target)
    max_iter = 1
    best_fitness = 10
    iteration = 0

    mol = Chem.MolFromSmiles(target)

    # 종료 조건 만족(최적해 발견) 시까지 반복
    while best_fitness <= 20 and iteration < max_iter:
        iteration += 1
        best_chrono, best_fitness = get_best_chrono(generation, orig_chem_info)
        print('Gen', iteration, '---', 'Best:', best_chrono, 'fitness:', best_fitness)
        generation = make_offsprings(generation, orig_chem_info, gen_size)
    
    
    g_mol_sql = "select g_logp, g_qed, g_pki, g_pkd, g_toxic from generate_mol where g_canosmiles = :target"
    g_mol_chem_info = pd.read_sql(g_mol_sql, conn, params={"target": target}).iloc[0].to_dict()
    
    optim_mol_sql = "select * from optim_mol where rownum <= 1"

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
    
    return insert_optim_mol

@app.post("/optim_molecule_show")
async def optim_molecule_show(request: Request):
    click_par_mol_sql = "select g_canosmiles from GENERATE_MOL"
    click_par_mol_db = pd.read_sql(click_par_mol_sql, conn)['G_CANOSMILES'].unique()
    target = random.sample(list(click_par_mol_db),1)[0]
    
    gen_size = 3
    generation = [make_random_chrono(target) for _ in range(gen_size)]
    orig_chem_info = molecule_chemical_info2(target)
    max_iter = 1
    best_fitness = 10
    iteration = 0

    mol = Chem.MolFromSmiles(target)

    # 종료 조건 만족(최적해 발견) 시까지 반복
    while best_fitness <= 20 and iteration < max_iter:
        iteration += 1
        best_chrono, best_fitness = get_best_chrono(generation, orig_chem_info)
        print('Gen', iteration, '---', 'Best:', best_chrono, 'fitness:', best_fitness)
        generation = make_offsprings(generation, orig_chem_info, gen_size)
    
    
    g_mol_sql = "select g_logp, g_qed, g_pki, g_pkd, g_toxic from generate_mol where g_canosmiles = :target"
    g_mol_chem_info = pd.read_sql(g_mol_sql, conn, params = {'target' : target}).iloc[0].to_dict()
    
    optim_mol_sql = "select * from optim_mol where rownum <= 1"

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
        print('최적화 분자 생성 완료')
    except:
        print('이미 생성된 분자입니다.')
        
    find_gen_mol_sql = "select * from optim_mol where user_seq = :current_user_seq and g_canosmiles = :target"

    gen_mol_info = pd.read_sql(find_gen_mol_sql, conn, params = {'current_user_seq' : current_user_seq, 'target':target})
    gen_mol_info = gen_mol_info.apply(lambda col: col.map(lob_to_str))

    optim_molecule_show_return_value = gen_mol_info.to_dict(orient='records')
    return optim_molecule_show_return_value