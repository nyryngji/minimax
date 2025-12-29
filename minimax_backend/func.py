import pandas as pd 
import deepchem as dc
from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
import joblib
import torch.nn as nn
import os
import random
from model.model.model import BAPULM
import selfies as sf
from rdkit import Chem
from model_architecture import Transformer, predict
from rdkit.Chem import Crippen, QED, Descriptors, Lipinski, inchi
from rdkit.Chem.Scaffolds import MurckoScaffold
import pubchempy as pcp
from rdkit.Chem.Draw import rdMolDraw2D
import base64
import oracledb
from dotenv import load_dotenv

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
file_path = 'D:\minimax_project\minimax_backend\model\\for_predict_file'

toxic_pca = joblib.load(file_path + "\\toxic_pca.pkl")
toxic_model = joblib.load(file_path + "\\toxic_model.pkl")

SAVE_PATH = os.path.join(file_path + "\ki_model.pt")

PROT_MODEL = "facebook/esm2_t6_8M_UR50D"
CHEM_MODEL = "DeepChem/ChemBERTa-77M-MLM"

prot_tok = AutoTokenizer.from_pretrained(PROT_MODEL)
prot_model = AutoModel.from_pretrained(PROT_MODEL).to(device).eval()

chem_tok = AutoTokenizer.from_pretrained(CHEM_MODEL)
chem_model = AutoModel.from_pretrained(CHEM_MODEL).to(device).eval()

class FFN(nn.Module):
    def __init__(self, d_in):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_in, 1024), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(1024, 256), nn.ReLU(), nn.Dropout(0.1),
            nn.Linear(256, 1)
        )
    def forward(self, x): return self.net(x)
    
kd_mol_tokenizer = AutoTokenizer.from_pretrained("ibm/MoLFormer-XL-both-10pct", trust_remote_code=True)
kd_mol_model = AutoModel.from_pretrained("ibm/MoLFormer-XL-both-10pct", trust_remote_code=True).to(device)
kd_mol_model.eval()

bapulm_model = BAPULM(hidden_dim=512).to(device)
bapulm_model.load_state_dict(torch.load(file_path + "\kd_model.pth", map_location=device))
bapulm_model.eval()

chem_model_name = 'seyonec/ChemBERTa-zinc-base-v1'
chem_tokenizer = AutoTokenizer.from_pretrained(chem_model_name)
chem_model = AutoModel.from_pretrained(chem_model_name)
 
checkpoint = torch.load(file_path + '\model_checkpoint.pt', map_location=device, weights_only=False)
token2id = checkpoint['token2id']
id2token = checkpoint['id2token']

config = checkpoint['config'].copy()
config['max_len'] = checkpoint['max_len']
 
oracledb.init_oracle_client(lib_dir=r"D:\\instantclient_23_9")
load_dotenv('.env')
db_user_name = os.getenv("db_user_name")
db_pwd = os.getenv("db_pwd")
db_dsn = os.getenv("db_dsn")

conn = oracledb.connect(
    user=db_user_name,          # 사용자명
    password=db_pwd,      # 비밀번호
    dsn=db_dsn # 접속 정보 (SQL Developer와 동일)
)

cur = conn.cursor()

# 1. 독성 예측 함수
def ChemBERTa_feature(smiles):    
	# chem_model_name = 'seyonec/ChemBERTa-zinc-base-v1'
	# chem_tokenizer = AutoTokenizer.from_pretrained(chem_model_name)
	# chem_model = AutoModel.from_pretrained(chem_model_name)
	inputs = chem_tokenizer(smiles, return_tensors='pt', padding=True, truncation=True)

	with torch.no_grad():
		outputs = chem_model(**inputs)

	feature_vector = outputs.last_hidden_state[:, 0, :].numpy()
	return {'smiles_vector' : list(feature_vector.reshape(-1,))}

def toxic_predict(smiles):
    new_smiles_feature = []

    rdkit_featurizer = dc.feat.RDKitDescriptors()
    features = rdkit_featurizer.featurize(smiles)
    new_smiles_feature = list(features[0])

    circular_featurizer = dc.feat.CircularFingerprint(size=2048, radius=4)
    total_fp_sum = sum(circular_featurizer.featurize(smiles)[0])
    new_smiles_feature += [total_fp_sum]

    smiles_vector = ChemBERTa_feature(smiles)['smiles_vector']
    new_smiles_feature += smiles_vector

    new_smiles_feature = np.nan_to_num(new_smiles_feature, nan=0.0)

    expected_features = toxic_pca.n_features_in_
    
    current_feature_array = np.array(new_smiles_feature).reshape(1, -1)
    
    if current_feature_array.shape[1] > expected_features:
        current_feature_array = current_feature_array[:, :expected_features]
    elif current_feature_array.shape[1] < expected_features:
        padding = np.zeros((1, expected_features - current_feature_array.shape[1]))
        current_feature_array = np.hstack([current_feature_array, padding])

    df_pca = toxic_pca.transform(current_feature_array)
    
    return {'toxic_score' : toxic_model.predict(df_pca)[0].sum() / 5}

# 2. 리핀스키 5규칙
def lipinski_rule(mol):
	logp = Crippen.MolLogP(mol) # logp 계산 : 분자가 수용성인지, 지용성인지
	molecule_weight = Descriptors.MolWt(mol) # 500 이하
	hbd = Lipinski.NumHDonors(mol) # 수소 결합 주개(5개 이하)
	hba = Lipinski.NumHAcceptors(mol) # 수소 결합 받개(10개 이하)
	
	if logp <= 5 and hbd <= 5 and hba <= 10 and molecule_weight <= 500:
		return {'lipinski' : True} # 해당 조건 4가지를 모두 만족하면 True 반환
	else:
		return {'lipinski' : False}

# 3. pKi 예측
def predict_pKi(smiles):
    prot_dim, chem_dim = 320, 384
    in_dim = prot_dim + chem_dim
    
    pki_model = FFN(in_dim).to(device)
    pki_model.load_state_dict(torch.load(SAVE_PATH, map_location=device))
    pki_model.eval()

    @torch.no_grad()
    def embed_smiles_local(smi):
        toks = chem_tok([smi], return_tensors="pt", truncation=True, padding=True).to(device)
        out = chem_model(**toks)
        z = out.last_hidden_state[:, 0, :].cpu().numpy().astype("float32")[0]
        return z[:chem_dim]

    @torch.no_grad()
    def embed_protein_local(fasta):
        seq = " ".join(list(fasta))
        toks = prot_tok([seq], return_tensors="pt", truncation=True, padding=True).to(device)
        h = prot_model(**toks).last_hidden_state
        p_vec = h.mean(dim=1).cpu().numpy().astype("float32")[0]
        return p_vec[:prot_dim]

    fasta_info = pd.read_csv(file_path + '\\for_binding_affinity_predict.csv')
    target_names = fasta_info["타겟 질환"].tolist()
    target_fastas = fasta_info["fasta"].tolist()

    C = embed_smiles_local(smiles)
    preds = []

    for name, fasta in zip(target_names, target_fastas):
        P = embed_protein_local(fasta) 

        X = np.concatenate([P, C])[None, :]
        
        with torch.no_grad():
            X_tensor = torch.tensor(X).to(device)
            y_pred = pki_model(X_tensor).item()
            preds.append((name, y_pred))

    preds.sort(key=lambda x: x[1], reverse=True)
    
    return {
        'suited_disease': preds[0][0], 
        'pki': round(preds[0][1], 2)
    }

# 4. pKd 예측
def predict_pKd(smiles):
	def set_seed(seed=42):
		random.seed(seed)
		np.random.seed(seed)
		torch.manual_seed(seed)
		torch.cuda.manual_seed_all(seed)
		torch.backends.cudnn.deterministic = True
		torch.backends.cudnn.benchmark = False

	set_seed(42)

	def get_molformer_embedding(smiles, device):
		res = []
		try:
			inputs = kd_mol_tokenizer(smiles, return_tensors="pt", padding=True).to(device)
			with torch.no_grad():
				emb = kd_mol_model(**inputs).last_hidden_state.mean(1).squeeze().cpu().numpy()
			res.append(emb)
		except:
			res.append(np.zeros(768))
		
		return res

	def predict_affinity(model, device, drug_emb, prot_emb):
		model.eval()
		with torch.no_grad():
			x = torch.tensor(np.concatenate([drug_emb, prot_emb]), dtype=torch.float32).unsqueeze(0).to(device)
			output = model(x)
		return float(output.item())

	target_df = pd.read_csv(file_path + "\\for_binding_affinity_predict.csv")
	target_names = target_df['타겟 질환'].tolist()

	mol_embeddings = get_molformer_embedding(smiles, device)
	prot_embeddings = np.load(file_path + "\\fasta_embedding.npy")

	results = []
	for j, target_name in enumerate(target_names):
		score = predict_affinity(bapulm_model, device, mol_embeddings[0], prot_embeddings[j])
		results.append([target_name, score])
	results.sort(key=lambda x : -x[1])
 
	return {
        'suited_disease': results[0][0], 
        'pkd': round(results[0][1],2)
    }

# 5. transformer 분자 생성

def find_molecule_exists(mol): # 새로 만들어진 물질이 기존에 존재하는 것인지 아닌지 확인
		inchikey = inchi.MolToInchiKey(mol)
		results = pcp.get_compounds(inchikey, "inchikey") # inchikey로 검색해서 결과가 존재하면 기존에 분자가 이미 있는 것
		if not results:
			return {'is_exists' : None}

def smiles_to_scaffold(smiles): # smiles -> scaffold
	mol = Chem.MolFromSmiles(smiles)  
	scaffold = MurckoScaffold.GetScaffoldForMol(mol)  
	return {'scaffold' : Chem.MolToSmiles(scaffold)}

def smiles_to_svg_base64(smiles: str, size=(300, 300)) -> str:
	mol = Chem.MolFromSmiles(smiles)
	if mol is None:
		raise ValueError("유효하지 않은 SMILES 문자열입니다.")

	# 분자 구조를 SVG로 그림
	drawer = rdMolDraw2D.MolDraw2DSVG(size[0], size[1])
	rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
	drawer.FinishDrawing()

	# 이미지 -> base64로 변환
	svg = drawer.GetDrawingText().replace("\n", "").strip()
	encoded = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
	return {'encoded' : encoded} 

def generate_smiles(cano_scaffold):
	model = Transformer(**config) # 모델 파라미터 정보

	# 학습된 파라미터 로드
	model.load_state_dict(checkpoint['model_state_dict'], strict=False)
	model.eval()
 
	sca_list = list(sf.split_selfies(sf.encoder(cano_scaffold)))
	token_sca_list = [token2id[i] for i in sca_list]

	res = [token2id['[SOS]']] + token_sca_list + [token2id['[EOS]']] + [token2id['[PAD]']]*(checkpoint['max_len']-len(token_sca_list))

	# Here we test some examples to observe how the model predicts
	example = torch.tensor([res], dtype=torch.long, device=device)

	result = predict(model, example, temperature = random.uniform(0.8, 1.3)) # EX) [57, 55, 43, 39, 66, 45, 50, 69, 37, 64]
	tokens = [id2token[i] for i in result if i not in [57, 30, 24]]
	sf_string = "".join(tokens)
	new_smiles = sf.decoder(sf_string)
	
	return {'generated_smiles' : new_smiles}

# Chembl에서 분자 관련 info 반환
def return_pubchem_data(molecule_name):
    compounds = pcp.get_compounds(molecule_name, 'name')
    c = compounds[0]
    scaffold = smiles_to_scaffold(c.canonical_smiles)['scaffold']
    cano_scaffold = Chem.MolToSmiles(Chem.MolFromSmiles(scaffold), canonical=True)
    return {
        'smiles' : c.canonical_smiles,
		'pubchem_id' : c.cid,
		'mol_name' : molecule_name,
		'scaffold' : cano_scaffold,
		'formula' : c.molecular_formula
	}

# SQL insert문으로 DB에 데이터 넣기
def insert_data(table_name, db_col, data):
    columns = ', '.join(db_col)
    placeholders = ', '.join([f':{k}' for k in db_col])

    sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    
    dic = dict(zip(db_col, data))
    cur.execute(sql, dic)
    conn.commit()

# 분자의 화학적 특성 반환
def molecule_chemical_info(smiles):
    mol = Chem.MolFromSmiles(smiles)
    image_base64 = smiles_to_svg_base64(smiles) # 이미지 base64
    mol_weight = Descriptors.MolWt(mol)
    logp = round(Crippen.MolLogP(mol),2)
    qed = round(QED.qed(mol),2)
    pki_res = predict_pKi(smiles)['suited_disease']
    pki = predict_pKi(smiles)['pki']
    pkd = predict_pKd(smiles)['pkd']
    toxic = toxic_predict(smiles)['toxic_score']
    
    return {'image_base64':image_base64, 
            'mol_weight':mol_weight,
            'logp':logp,
            'qed':qed,
            'pki_res':pki_res,
            'pki':pki,
            'pkd':pkd,
            'toxic':toxic}

# 오각형 그래프 그릴 숫자 반환하기
def calculate_graph_stat(data): # 단일 행 딕셔너리로 넣기
	min_vals = {'logp': -3, 'qed': 0, 'pki': 0, 'pkd': 0, 'toxic': -10}
	max_vals = {'logp': 8, 'qed': 1, 'pki': 10, 'pkd': 20, 'toxic': 10}

	make_graph_col = ['logp', 'qed', 'pki', 'pkd', 'toxic']
	make_graph_col2 = ['logp_graph', 'qed_graph', 'pki_graph', 'pkd_graph', 'toxic_graph']

	norm_vals = [round((data[k] - min_vals[k]) / (max_vals[k] - min_vals[k]),1) for k in make_graph_col]
	return dict(zip(make_graph_col2, norm_vals))

# # CLOB → str / BLOB → bytes
def lob_to_str(x):
	if isinstance(x, oracledb.LOB):
		return x.read()   
	return x

def molecule_chemical_info2(smiles):
    mol = Chem.MolFromSmiles(smiles)
    mol_weight = Descriptors.MolWt(mol)
    logp = round(Crippen.MolLogP(mol),2)
    qed = round(QED.qed(mol),2)
    pki = predict_pKi(smiles)['pki']
    pkd = predict_pKd(smiles)['pkd']
    toxic = toxic_predict(smiles)['toxic_score']
    
    return {
            'mol_weight':mol_weight,
            'logp':logp,
            'qed':qed,
            'pki':pki,
            'pkd':round(pkd,2),
            'toxic':toxic}
    
def calculate_per(g_mol_chem_info, optim_mol_chem_info):
	rename_col = dict(zip(g_mol_chem_info.keys(), ['logp','qed','pki','pkd','toxic']))
	g_mol_chem_info = { rename_col.get(k, k): v for k, v in g_mol_chem_info.items() }

	make_graph_col = ['logp', 'qed', 'pki', 'pkd', 'toxic']
	make_graph_col2 = ['per_logp', 'per_qed', 'per_pki', 'per_pkd', 'per_toxic']

	norm_vals = [round(((g_mol_chem_info[k] - optim_mol_chem_info[k]) / g_mol_chem_info[k]),1) for k in make_graph_col]
 
	return dict(zip(make_graph_col2, norm_vals))