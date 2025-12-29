# 참조 : https://magmatart.dev/development/2020/01/05/Python-Genetic-Example.html

import json
from func import *


with open("D:\minimax\minimax_backend\model\\for_predict_file\\vocab.json", "r", encoding="utf-8") as f:
    data = json.load(f)   # JSON → 파이썬 딕셔너리/리스트 변환

def make_random_chrono(target): # 분자의 일부를 삭제하거나 더하는 걸 랜덤으로 수행함
	chrono = list(sf.split_selfies(sf.encoder(target)))
	for i in range(3):
		x = random.randint(0,1)
		if x == 0:
			remove_molecule = random.randint(0, len(chrono)-1)
			chrono.remove(chrono[remove_molecule])
		else:
			rand_mole = random.sample(['[O]', '[N]', '[C]', '[=O]'],1)
			chrono.insert(random.randint(0,len(chrono)),rand_mole[0])

	return sf.decoder(''.join(chrono))

def get_fitness(after_optim_smiles, orig_chem_info):
	after_optim_mol = Chem.MolFromSmiles(after_optim_smiles)
	after_optim_chem_info = molecule_chemical_info2(after_optim_smiles)          
	score = 10
	# Lipinski 기준 만족 여부 (True=1, False=0)
	if lipinski_rule(after_optim_mol):
	# 간단한 스코어링: 낮은 tox → 1/tox, 높은 qed, 높은 pKi, 높은 pKd
		score += sum([-(after_optim_chem_info['toxic'] - orig_chem_info['toxic']),
					(after_optim_chem_info['qed'] - orig_chem_info['qed']),
					(after_optim_chem_info['pki'] - orig_chem_info['pki']),
					(after_optim_chem_info['pkd'] - orig_chem_info['pkd'])])
	return round(score,2)

def make_roulette(generation, orig_chem_info):
    fitnesses = [get_fitness(c,orig_chem_info) for c in generation] # 적합도 계산
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

def crossover(ca, cb):
	ca2 = list(sf.split_selfies(sf.encoder(ca)))
	cb2 = list(sf.split_selfies(sf.encoder(cb)))
	cross_point = random.randint(1, min(len(ca2),len(cb2))-1)     
	offspring = ca2[:cross_point] + cb2[cross_point:]  
	return offspring

# mutation: 변이 연산 #
def mutation(chrono):
	mutated_chrono = chrono.copy() # 이건 
	propability = 0.5      # 변이 확률 0.5
	good_token = ['[O]', '[N]', '[c]', '[=O]']
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
def sort_generation(generation,orig_chem_info):
    fitnesses = [get_fitness(c,orig_chem_info) for c in generation]
    sorted_gen = [c for _, c in sorted(zip(fitnesses, generation))]
    return sorted_gen # 적합도 낮은 거부터 튀어나옴

# make_offsprings: 부모 세대로부터 자식 세대 생성 #
def make_offsprings(generation, orig_chem_info, gen_size):
    ggap = 0.8  # 세대차
    sorted_gen = sort_generation(generation, orig_chem_info)    # 정렬된 해집단
    n_parents = int(gen_size * (1.0 - ggap))    # 남겨놓을 부모 해의 개수는 3개
    offsprings = sorted_gen[-n_parents:]         # 우수한 부모 해 그대로 남기기 (적합도 높은 상위 3개)
    roulette = make_roulette(sorted_gen, orig_chem_info)        # 룰렛 생성

    # 남은 수만큼 자식해 생성 후 대치
    for i in range(gen_size - n_parents):
        ca = selection(sorted_gen, roulette)    # 부모해 선택 1 (dart 던져서 적합도가 높은 거1, 근데 dart가 랜덤이라 걍 랜덤으로 추출하는듯)
        cb = selection(sorted_gen, roulette)    # 부모해 선택 2 (dart 던져서 적합도가 높은 거2)
        offspring = crossover(ca, cb)           # 교차
        offspring = mutation(offspring)         # 변이
        try:
            offspring_smiles = sf.decoder(''.join(offspring))
            offspring_smiles = Chem.MolToSmiles(Chem.MolFromSmiles(offspring_smiles))  # 정규화
            offsprings.append(offspring_smiles)
        except:
            continue
    return offsprings

# get_best_chrono: 가장 우수한 해와 그 적합도 반환 #    
def get_best_chrono(generation, orig_chem_info):
    fitnesses = [get_fitness(c,orig_chem_info) for c in generation]
    best_fitness = max(fitnesses)
    best_idx = fitnesses.index(best_fitness)
    return generation[best_idx], best_fitness