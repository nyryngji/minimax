from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import oracledb
import pandas as pd
import random
from prediction_all import *
import torch
import random
from chembl_webresource_client.new_client import new_client
from datetime import datetime

# & 가상환경 시작 & D:/minimax/.venv/Scripts/Activate.ps1
# 웹서버 시작 : uvicorn main:app --reload

app = FastAPI()

# oracledb.init_oracle_client(lib_dir=r"D:\\instantclient_23_9")
try:
    oracledb.init_oracle_client(lib_dir=r"D:\\instantclient_23_9")
    conn = oracledb.connect(
        user="adsql",          
        password="oracle_4U",      
        dsn="localhost:1521/xe" 
    )
    cur = conn.cursor()
    ORACLE_AVAILABLE = True
    print("Oracle database connected successfully")
except Exception as e:
    print(f"Oracle database not available: {e}")
    print("Running without Oracle database...")
    ORACLE_AVAILABLE = False
    conn = None
    cur = None



# 프론트엔드와 통신 허용 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 중엔 * 허용 (배포 시 도메인 지정)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 여기부터 백엔드 코드 시작

@app.post("/user_diy")
async def predict(request: Request): 
    user_input = 'caffeine'
    user_input_data = return_chembl_data(user_input)

    select_user_input = pd.read_csv('user_input.csv')
    select_user_input = select_user_input.iloc[0:0]

    select_user_input.loc[len(select_user_input)] = user_input_data
    select_user_input.to_csv('user_input.csv',index=False)

    user_input_info = select_user_input.to_dict(orient='records')[0]

    user_gen_db = pd.read_csv('user_generative.csv')
    user_gen_db = user_gen_db.iloc[0:0]

    user_generate_molecule_result = [] 
    unew_names = []

    for j in range(5):
        seq_user_gen_val = j
        user_gen_data = [user_input_info['U_CHEMBL_ID']] + [f"UNEW_MOLECULE{seq_user_gen_val}"]
        try:
            torch.manual_seed(torch.randint(0, 1000000, (1,)).item())
            user_gen_data += make_smiles(user_input_info['U_CANOSMILES'])
            user_generate_molecule_result.append(user_gen_data)
            unew_names.append(f"UNEW_MOLECULE{seq_user_gen_val}")
        except:
            print('에러 발생')
            continue
        print(unew_names)

    for user_gen_row in user_generate_molecule_result:
        try:
            pki = list(predict_pKi(user_gen_row[2]))
            pkd = list(predict_pKd(user_gen_row[2]))
            toxic = [toxic_predict(user_gen_row[2])]
            user_gen_data2 = user_gen_row + pki + pkd + toxic
            user_gen_db.loc[len(user_gen_db)] = user_gen_data2
            print('삽입 완료')
        except:
            unew_names.remove(user_gen_row[1])
            print('데이터 삽입 실패')
            continue

    user_input_info['UNEW_NAMES'] = unew_names
    user_gen_db.to_csv('user_generative.csv',index=False)
    
    with open("user_gen_result.json", "w", encoding="utf-8") as f:
        json.dump(user_input_info, f, ensure_ascii=False, indent=2)
    
    return {'user_generative_result': user_input_info}

@app.post("/button_diy") 
async def predict(request: Request):
    user_selected_button = '암 치료제' # 입력 : 누른 버튼 이름 

    sql = f"SELECT D_CHEMBL_ID, D_CANOSMILES, D_CATEGORY FROM disease_input where d_category = '{user_selected_button}'"
    sql_res = pd.read_sql(sql, conn)

    sql_res = pd.read_csv('disease_input.csv')
    sql_res = sql_res[sql_res['D_CATEGORY'] == user_selected_button]
    randoms = [0,1]
    orig_molecule = sql_res.iloc[randoms].to_dict(orient='records') # 카테고리별 smiles 2개 관련 정보

    sql2_res = pd.read_csv('disease_generative.csv')
    sql2_res = sql2_res.iloc[0:0]
    seq_val = 0 

    for i in orig_molecule:
        dnew_names = []
        generate_molecule_result = []
        for j in range(5):
            res = [i['D_CHEMBL_ID']] + [f"DNEW_MOLECULE{seq_val}"]
            
            try:
                torch.manual_seed(torch.randint(0, 1000000, (1,)).item())
                res += make_smiles(i['D_CANOSMILES'])
                generate_molecule_result.append(res)
                dnew_names.append(f"DNEW_MOLECULE{seq_val}")
            except:
                print('에러 발생')
                continue
            seq_val += 1

        for res in generate_molecule_result:
            try:
                pki = list(predict_pKi(res[2]))
                pkd = list(predict_pKd(res[2]))
                toxic = [toxic_predict(res[2])]
                res2 = res + pki + pkd + toxic + [user_selected_button]
                sql2_res.loc[len(sql2_res)] = res2
                print('삽입 성공')
            except:
                print('데이터 에러 발생')
                continue

        i['dnew_name'] = dnew_names

    with open("button_gen_result.json", "w", encoding="utf-8") as f:
        json.dump(orig_molecule, f, ensure_ascii=False, indent=2)

    sql2_res = sql2_res.drop_duplicates()
    sql2_res.to_csv('disease_generative.csv',index=False)
    
    return {'button_generative_result': orig_molecule}

@app.post("/user_diy_show")
async def predict(request: Request):
    with open('user_gen_result.json', 'r', encoding='utf-8') as f:
        user_gen_result = json.load(f)

    new_moluecule_names = user_gen_result['UNEW_NAMES']

    user_gen_info = pd.read_csv('user_generative.csv')
    user_gen_info = user_gen_info[user_gen_info['UNEW_NAME'].isin(new_moluecule_names)]

    # 이건 새로 생성한 분자 데이터(5개 들어있어여)
    user_gen_info['UNEW_IMAGE_BASE64'] = user_gen_info['UNEW_IMAGE_BASE64'].apply(lambda x: x.read() if hasattr(x, 'read') else x)

    user_gen_info = user_gen_info.to_dict(orient='records')

    with open("user_diy_show.json", "w", encoding="utf-8") as f:
        json.dump(user_gen_info, f, ensure_ascii=False, indent=2)
    
    return {'show_new_user_mol':user_gen_info}
        
@app.post("/button_diy_show")
async def predict(request: Request):
    with open('button_gen_result.json', 'r', encoding='utf-8') as f:
    # json.load() 함수를 사용하여 파일 내용을 딕셔너리로 변환합니다.
        btn_gen_result = json.load(f)
        # 이건 원조 분자용 데이터

    user_click = 0 # 유저가 클릭한 분자

    if user_click == 0: # 0말고 원조 분자 id를 받아와야 할듯
        use_data = btn_gen_result[0] # 첫번째를 누르면 첫번째 원소 불러옴
    else:
        use_data = btn_gen_result[1] # 밑에 누르면 두 번째 원소 불러옴
        
    orig_mol_info = pd.read_csv('disease_input.csv')
    orig_mol_info = orig_mol_info[orig_mol_info['D_CHEMBL_ID'] == use_data['D_CHEMBL_ID']].to_dict(orient='records')

    btn_gen_info = pd.read_csv('disease_generative.csv')
    btn_gen_info = btn_gen_info.drop_duplicates()
    btn_gen_info = btn_gen_info[btn_gen_info['DNEW_NAME'].isin(use_data['dnew_name'])]

    btn_gen_info['DNEW_IMAGE_BASE64'] = btn_gen_info['DNEW_IMAGE_BASE64'].apply(lambda x: x.read() if hasattr(x, 'read') else x)
    btn_gen_info = btn_gen_info.to_dict(orient='records')
    # btn_gen_info : 새로 만들어진 분자 정보

    with open("button_diy_show.json", "w", encoding="utf-8") as f:
        json.dump(btn_gen_info, f, ensure_ascii=False, indent=2)
    
    return {'button_diy_show':btn_gen_info}

@app.post("/optim_molecule")
async def predict(request: Request):
    def predict_feature(smiles):
        mol = Chem.MolFromSmiles(smiles) 
        new_optim_predict = [will_opt[f'{col_start}NEW_NAME'],
                                f'ONEW_MOLECULE{str(len(optim_molecule))}',
                                smiles,
                                smiles_to_svg_base64(smiles)]

        new_optim_predict += isit_available_medicine(mol) # [molecule_weight, logp, qed, hbd, hba]
        pki = list(predict_pKi(smiles))
        pkd = list(predict_pKd(smiles))
        toxic = [toxic_predict(smiles)]
        new_optim_predict = new_optim_predict + pki + pkd + toxic + [datetime.now().strftime('%Y-%m-%d %H:%M:%S')] + [0]
        
        optim_molecule.loc[len(optim_molecule)] = new_optim_predict
        return dict(zip(list(optim_molecule.columns),new_optim_predict))

    # randch: 무작위 문자 하나 생성
    def randch():
        rand_mole = random.sample([i for i in list(data.keys()) if i not in ['[EOS]','[SOS]','[PAD]']],1)
        return rand_mole[0] # 여기서 랜덤으로 하나 뽑기

    # make_random_chrono: 무작위 해 하나 생성
    def make_random_chrono(target): # 원조 분자의 일부를 삭제하거나 더하는 걸 랜덤으로 수행함
        chrono = list(sf.split_selfies(sf.encoder(target)))
        for i in range(3):
            x = random.randint(0,1)
            if x == 0:
                remove_molecule = random.randint(0, len(chrono)-1)
                chrono.remove(chrono[remove_molecule])
            else:
                chrono.insert(random.randint(0,len(chrono)),randch())

        return sf.decoder(''.join(chrono))

    # make_random_generation: 초기 해집단 생성(= 해를 gen_size개만큼 생성) = 5개
    def make_random_generation(target):
        return [make_random_chrono(target) for _ in range(gen_size)]

    # get_fitness: 적합도 계산 
    # 분자 smiles에서는 기존 독성 예측 등의 값과 해집단의 예측값을 비교해서 차이가 많이 나면 좋은거로
    def get_fitness(smiles, orig_features):
        mol = Chem.MolFromSmiles(smiles) 
        features = predict_feature(smiles)  # 새로운 분자 특성 예측      

        # Lipinski 기준 만족 여부 (True=1, False=0)
        lip_pass = (features['ONEW_MOL_WEIGHT'] <= 500 and
                features['ONEW_LOGP'] <= 5 and
                features['ONEW_HBD'] <= 5 and
                features['ONEW_HBA'] <= 10)

        # 간단한 스코어링: 낮은 tox → 1/tox, 높은 qed, 높은 pKi, 높은 pKd
        score = sum([-(features['ONEW_TOXIC'] - orig_features[f'{col_start}NEW_TOXIC']),
            (features['ONEW_QED'] - orig_features[f'{col_start}NEW_QED']),
            (features['ONEW_PKI'] - orig_features[f'{col_start}NEW_PKI']),
            (features['ONEW_PKD'] - orig_features[f'{col_start}NEW_PKD'])])
        # Lipinski 조건을 모두 만족하면 보너스
        if lip_pass:
            score += 10
        return score

    def make_roulette(generation):
        fitnesses = [get_fitness(c,orig_features) for c in generation] # 적합도 계산
        
        prev_value = 0.0
        roulette = [0.0]
        for f in fitnesses:
            value = float(f / sum(fitnesses))
            roulette.append(prev_value + value)
            prev_value += value
        
        return roulette

    # selection: 룰렛 휠 선택 연산 #
    def selection(chronos, roulette):
        selected_chrono = None
        dart = random.random()  # 다트 던지기 EX) 0.27

        # 룰렛에서 해 선택
        for idx in range(1, len(roulette)):
            if dart < roulette[idx]: # dart보다 룰렛 적합도가 높으면
                selected_chrono = chronos[idx-1] # 그 적합도가 높은 chrono를 선택함
                break
        
        return selected_chrono

    # crossover: 1점 교차 연산 -> 그냥 부모 2개 랜덤으로 잘라서 이어 붙이는거
    def crossover(ca, cb):
        ca2 = list(sf.split_selfies(sf.encoder(ca)))
        cb2 = list(sf.split_selfies(sf.encoder(cb)))
        cross_point = random.randint(1, min(len(ca2),len(cb2))-1)     
        offspring = ca2[:cross_point] + cb2[cross_point:]  
        return offspring

    # mutation: 변이 연산 #
    def mutation(chrono):
        mutated_chrono = chrono # 이건 
        propability = 0.1      # 변이 확률 0.03
        good_token = ['[O]', '[N]', '[C]', '[=O]']
        branch_list = [i for i in mutated_chrono if 'Branch' in i]

        if random.random() < propability:
            case = random.randint(0,1)
            if branch_list and case == 0:
                mutated_chrono.remove(random.choice(branch_list))
            else:
                mutated_chrono.append(random.choice(good_token))

        # 변이된 문자열 반환
        return sf.decoder(''.join(mutated_chrono))

    # sort_generation: 적합도를 기반으로 해집단 정렬
    def sort_generation(generation):
        fitnesses = [get_fitness(c,orig_features) for c in generation]
        sorted_gen = [c for _, c in sorted(zip(fitnesses, generation))]
        return sorted_gen # 적합도 낮은 거부터 튀어나옴

    # make_offsprings: 부모 세대로부터 자식 세대 생성 #
    def make_offsprings(generation):
        ggap = 0.8  # 세대차
        sorted_gen = sort_generation(generation)    # 정렬된 해집단
        n_parents = int(gen_size * (1.0 - ggap))    # 남겨놓을 부모 해의 개수는 3개
        offsprings = sorted_gen[-n_parents:]         # 우수한 부모 해 그대로 남기기 (적합도 높은 상위 3개)
        roulette = make_roulette(sorted_gen)        # 룰렛 생성

        # 남은 수만큼 자식해 생성 후 대치
        for i in range(gen_size - n_parents):
            ca = selection(sorted_gen, roulette)    # 부모해 선택 1 (dart 던져서 적합도가 높은 거1, 근데 dart가 랜덤이라 걍 랜덤으로 추출하는듯)
            cb = selection(sorted_gen, roulette)    # 부모해 선택 2 (dart 던져서 적합도가 높은 거2)
            offspring = crossover(ca, cb)           # 교차
            offspring = mutation(offspring)         # 변이
            offsprings.append(offspring)

        return offsprings

    # get_best_chrono: 가장 우수한 해와 그 적합도 반환 #    
    def get_best_chrono(chronos):
        fitnesses = [get_fitness(c,orig_features) for c in chronos]
        best_fitness = max(fitnesses)
        best_idx = fitnesses.index(best_fitness)
        return chronos[best_idx], best_fitness
    
    optim_molecule = pd.read_csv('optim_molecule.csv')
    optim_molecule = optim_molecule.iloc[0:0]

    checkpoint = torch.load('D:\minimax\minimax_backend\model\\for_predict_file\model_checkpoint.pt', map_location=device, weights_only=False)
    token2id = checkpoint['token2id']
    id2token = checkpoint['id2token']

    with open("D:\minimax\minimax_backend\model\\for_predict_file\\vocab.json", "r", encoding="utf-8") as f:
        data = json.load(f)   # JSON → 파이썬 딕셔너리/리스트 변환

    data = token2id

    # 최적화 버튼을 눌렀을 때
    mode = 'user_diy'

    # 1. 만약 이게 user가 입력해서 만든 분자를 최적화하려는 거면
    if mode == 'user_diy':
        df = pd.read_csv('user_generative.csv')
        col_start = 'U'
    else: # 버튼 누른거면
        df = pd.read_csv('disease_generative.csv')
        col_start = 'D'

    choose_optim = f'{col_start}NEW_MOLECULE3' # 이건 사용자가 클릭한 분자의 name
    will_opt = df[df[f'{col_start}NEW_NAME'] == choose_optim].to_dict(orient='records')[0]
    orig_features = will_opt

    max_iter = 1
    best_fitness = 10
    iteration = 0
    gen_size = 4

    best_results = []
    target = orig_features[f'{col_start}NEW_CANOSMILES']

    mol = Chem.MolFromSmiles(target)
    generation = make_random_generation(target) # chronons

    # 종료 조건 만족(최적해 발견) 시까지 반복
    while best_fitness <= 20 and iteration < max_iter:
        best_result = []
        iteration += 1
        best_chrono, best_fitness = get_best_chrono(generation)
        print('Gen', iteration, '---', 'Best:', best_chrono, 'fitness:', best_fitness)
        best_result += [iteration, best_chrono, best_fitness]
        generation = make_offsprings(list(optim_molecule.sort_values('ONEW_OPTIM_TIME',ascending=False).iloc[:4]['ONEW_CANOSMILES']))
        best_results.append(best_result)

    optim_molecule = optim_molecule.drop_duplicates('ONEW_CANOSMILES')
    optim_molecule.loc[optim_molecule['ONEW_CANOSMILES'].isin([i[1] for i in best_results]),'ONEW_BEST'] = 1
    optim_molecule.to_csv('optim_molecule.csv',index=False)

    return {'best_result_smiles' : [i[1] for i in best_results],
            'col_start':col_start}

@app.post("/optim_molecule_show")
async def predict(request: Request):
    # 입력 : optim_molecule의 col_start값
    col_start = 'U'
    # 1. 만약 이게 user가 입력해서 만든 분자를 최적화하려는 거면
    if col_start == 'U':
        df = pd.read_csv('user_generative.csv')
        orig_diff_col = ['UNEW_MOL_WEIGHT', 'UNEW_LOGP', 'UNEW_QED', 'UNEW_TOXIC','UNEW_PKI','UNEW_PKD']
    else: # 버튼 누른거면
        df = pd.read_csv('disease_generative.csv')
        orig_diff_col = ['DNEW_MOL_WEIGHT', 'DNEW_LOGP', 'DNEW_QED', 'DNEW_TOXIC','DNEW_PKI','DNEW_PKD']

    optim_diff_col = ['ONEW_MOL_WEIGHT', 'ONEW_LOGP', 'ONEW_QED', 'ONEW_TOXIC','ONEW_PKI','ONEW_PKD']
    return_val_col = ['ONEW_NAME', 'ONEW_CANOSMILES', 'ONEW_IMAGE_BASE64',
                      'ONEW_MOL_WEIGHT', 'ONEW_LOGP', 'ONEW_QED', 
                      'ONEW_TOXIC','ONEW_PKI','ONEW_PKD']
    
    optim_molecule = pd.read_csv('optim_molecule.csv')
    optim_molecule = optim_molecule.drop_duplicates('ONEW_CANOSMILES')
    
    orig_mol = df[df[f'{col_start}NEW_NAME'].isin(optim_molecule['ONEW_ORIGIN_NAME'])]
    orig_mol = orig_mol[orig_diff_col].to_numpy()

    return_value = []
    for i in range(len(optim_molecule)):
        dic = optim_molecule[return_val_col].loc[i].to_dict()
        optim_mol = optim_molecule[optim_diff_col].loc[i].to_numpy()
        diff_res = optim_mol - orig_mol 
        dic['DIFF_INFO'] = dict(zip([i[5:] + '_DIFF' for i in optim_diff_col], diff_res[0].tolist()))
        return_value.append(dic)
    
    return {'return_value': return_value}
    # 이제 이 값으로 분자 최적화 전후 값 비교
    