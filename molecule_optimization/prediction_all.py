import pandas as pd 
import deepchem as dc
from transformers import AutoTokenizer, AutoModel, T5Tokenizer, T5EncoderModel
import torch
import numpy as np
from sklearn.decomposition import PCA
import joblib
from tqdm import trange
import torch.nn as nn
import os
import random
from model.model import BAPULM
import selfies as sf
from rdkit import Chem
from model_architecture import Transformer,predict 
from rdkit.Chem import Crippen, QED, Descriptors, Draw, Lipinski, inchi
from rdkit.Chem.Scaffolds import MurckoScaffold
import pubchempy as pcp


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
file_path = 'D:\minimax원본\molecule_optimization\\for_predict_file'

toxic_pca = joblib.load(file_path + "\\toxic_pca.pkl")
toxic_model = joblib.load(file_path + "\\toxic_model.pkl")

SAVE_PATH = os.path.join(file_path + "\ki_model.pt")

PROT_MODEL = "facebook/esm2_t6_8M_UR50D"
CHEM_MODEL = "DeepChem/ChemBERTa-77M-MLM"

prot_tok = AutoTokenizer.from_pretrained(PROT_MODEL)
prot_model = AutoModel.from_pretrained(PROT_MODEL).to(device).eval()

chem_tok = AutoTokenizer.from_pretrained(CHEM_MODEL)
chem_model = AutoModel.from_pretrained(CHEM_MODEL).to(device).eval()

kd_mol_tokenizer = AutoTokenizer.from_pretrained("ibm/MoLFormer-XL-both-10pct", trust_remote_code=True)
kd_mol_model = AutoModel.from_pretrained("ibm/MoLFormer-XL-both-10pct", trust_remote_code=True).to(device)
kd_mol_model.eval()

bapulm_model = BAPULM(hidden_dim=512).to(device)
bapulm_model.load_state_dict(torch.load(file_path + "\kd_model.pth", map_location=device))
bapulm_model.eval()
 
# 1. 독성 예측 함수

def ChemBERTa_feature(smiles):    
	chem_model_name = 'seyonec/ChemBERTa-zinc-base-v1'
	chem_tokenizer = AutoTokenizer.from_pretrained(chem_model_name)
	chem_model = AutoModel.from_pretrained(chem_model_name)
	inputs = chem_tokenizer(smiles, return_tensors='pt', padding=True, truncation=True)

	with torch.no_grad():
		outputs = chem_model(**inputs)

	feature_vector = outputs.last_hidden_state[:, 0, :].numpy()
	return list(feature_vector.reshape(-1,))

def toxic_predict(smiles): 
	new_smiles_feature = []

	rdkit_featurizer = dc.feat.RDKitDescriptors()
	features = rdkit_featurizer.featurize(smiles)
	new_smiles_feature = list(features[0])

	circular_featurizer = dc.feat.CircularFingerprint(size=2048, radius=4)
	total_fp_sum = sum(circular_featurizer.featurize(smiles)[0])
	new_smiles_feature += [total_fp_sum]
	
	new_smiles_feature += list(ChemBERTa_feature(smiles))
	
	new_smiles_feature = np.nan_to_num(new_smiles_feature, nan=0.0)
	
	df_pca = toxic_pca.transform(np.array(new_smiles_feature).reshape(1,-1))
	return toxic_model.predict(df_pca)[0].sum() / 5

# 2. 분자 특성 추출 : logp, qed, hbd, hba
def lipinski_rule(mol):
	# logp 계산 : 분자가 수용성인지, 지용성인지
	logp = Crippen.MolLogP(mol)

	# QED 계산 : 화합물이 약처럼 될 가능성을 수치화(0~1까지)
	qed = QED.qed(mol)

	molecule_weight = Descriptors.MolWt(mol) # 500 이하

	hbd = Lipinski.NumHDonors(mol) # 수소 결합 주개(5개 이하)
	hba = Lipinski.NumHAcceptors(mol) # 수소 결합 받개(10개 이하)
	
	return [molecule_weight, logp, qed, hbd, hba]

# 3. pKi 예측
def predict_pKi(smiles):
	prot_dim, chem_dim = 320, 384
	in_dim = prot_dim + chem_dim

	class FFN(nn.Module):
		def __init__(self, d_in):
			super().__init__()
			self.net = nn.Sequential(
				nn.Linear(d_in, 1024), nn.ReLU(), nn.Dropout(0.2),
				nn.Linear(1024, 256), nn.ReLU(), nn.Dropout(0.1),
				nn.Linear(256, 1)
			)
		def forward(self, x): return self.net(x)

	model = FFN(in_dim).to(device)
	model.load_state_dict(torch.load(SAVE_PATH, map_location=device))
	model.eval()

	@torch.no_grad()
	def embed_protein(seq):
		seq = " ".join(list(seq))
		toks = prot_tok([seq], return_tensors="pt", truncation=True, padding=True).to(device)
		h = prot_model(**toks).last_hidden_state
		return h.mean(dim=1).cpu().numpy().astype("float32")[0]

	@torch.no_grad()
	def embed_smiles(smiles):
		toks = chem_tok([smiles], return_tensors="pt", truncation=True, padding=True).to(device)
		out = chem_model(**toks)
		z = out.last_hidden_state[:, 0, :]
		return z.cpu().numpy().astype("float32")[0]

	def predict_for_targets(smiles, target_names, target_fastas):
		C = embed_smiles(smiles)
		preds = []
		for name, fasta in zip(target_names, target_fastas):
			P = embed_protein(fasta)
			X = np.concatenate([P, C])[None, :]
			with torch.no_grad():
				y_pred = model(torch.tensor(X).to(device)).item()
			preds.append((name, y_pred))
		preds.sort(key=lambda x: x[1], reverse=True)
		return preds

	fasta_info = pd.read_csv(file_path + '\\for_binding_affinity_predict.csv')
	target_names  = fasta_info["타겟 질환"].tolist()
	target_fastas = fasta_info["fasta"].tolist()

	ranked = predict_for_targets(smiles, target_names, target_fastas)
	ranked.sort(key= lambda x : -x[1])
	return pd.Series([ranked[0][0], ranked[0][1]])

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
	return results[0]

# 5. transformer 분자 생성

def isit_available_medicine(mol): # 이 분자가 쓸만한가
	# logp 계산 : 분자가 수용성인지, 지용성인지
	logp = Crippen.MolLogP(mol)

	# QED 계산 : 화합물이 약처럼 될 가능성을 수치화(0~1까지)
	qed = QED.qed(mol)

	molecule_weight = Descriptors.MolWt(mol) # 500 이하

	hbd = Lipinski.NumHDonors(mol) # 수소 결합 주개(5개 이하)
	hba = Lipinski.NumHAcceptors(mol) # 수소 결합 받개(10개 이하)
	
	return [molecule_weight, logp, qed, hbd, hba]

def find_molecule_exists(mol): # 새로 만들어진 물질이 기존에 존재하는 것인지 아닌지 확인
		inchikey = inchi.MolToInchiKey(mol)
		results = pcp.get_compounds(inchikey, "inchikey") # inchikey로 검색해서 결과가 존재하면 기존에 분자가 이미 있는 것
		if not results:
			return None

def smiles_to_scaffold(smiles): # smiles -> scaffold
	mol = Chem.MolFromSmiles(smiles)  
	scaffold = MurckoScaffold.GetScaffoldForMol(mol)  
	return Chem.MolToSmiles(scaffold)

def make_smiles(smiles): # 분자 생성
	checkpoint = torch.load(file_path + '\model_checkpoint.pt', map_location=device, weights_only=False)
	token2id = checkpoint['token2id']
	id2token = checkpoint['id2token']

	config = checkpoint['config'].copy()
	config['max_len'] = checkpoint['max_len']

	# 모델 생성
	model = Transformer(**config) # 모델 파라미터 정보

	# 학습된 파라미터 로드
	model.load_state_dict(checkpoint['model_state_dict'], strict=False)
	
	new_scaffold = smiles_to_scaffold(smiles)
	cano_scaffold = Chem.MolToSmiles(Chem.MolFromSmiles(new_scaffold), canonical=True)
	sca_list = list(sf.split_selfies(sf.encoder(cano_scaffold)))
	token_sca_list = [token2id[i] for i in sca_list]

	res = [token2id['[SOS]']] + token_sca_list + [token2id['[EOS]']] + [token2id['[PAD]']]*(checkpoint['max_len']-len(token_sca_list))

	# Here we test some examples to observe how the model predicts
	example = torch.tensor([res], dtype=torch.long, device=device)
	
	new_molecule_list = []
 
	for i in range(1):
		result = predict(model, example) # EX) [57, 55, 43, 39, 66, 45, 50, 69, 37, 64]
		tokens = [id2token[i] for i in result if i not in [57, 30, 24]]
		sf_string = "".join(tokens)
		news = sf.decoder(sf_string)
		try:
			mol = Chem.MolFromSmiles(news) 
			mol_img = Draw.MolToImage(mol) # 분자 이미지
			if find_molecule_exists(mol) is None: # 만약 분자가 기존에 없는 것이라면
				medicine_standard = isit_available_medicine(mol) # 약이 될 수 있는지 관련 지표를 구해서 
				new_molecule_list.append([f'new molecule{i}',news,mol_img] + medicine_standard) # DB에 저장
		except:
			continue
	
	return new_molecule_list

# 6. 유전 알고리즘