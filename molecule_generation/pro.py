from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold
from multiprocessing import Pool, cpu_count
import pandas as pd 
from tqdm import tqdm
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold

df = pd.read_csv('D:\minimax\molecule_generation\drug_design.csv')
df = df.drop_duplicates('SMILES')
df = df.reset_index(drop=True)


def worker(smiles):
    try:
        if not (37 <= len(smiles) <= 56):
            return None

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None

        scaffold = MurckoScaffold.GetScaffoldForMol(mol)
        if scaffold is None:
            return None

        cano_scaffold = Chem.MolToSmiles(scaffold, canonical=True)
        cano_smiles = Chem.MolToSmiles(mol, canonical=True)

        return [cano_scaffold, cano_smiles]

    except Exception:
        return None
            

if __name__ == "__main__":
    with Pool(cpu_count()) as p:
        results = list(
			tqdm(
				p.imap(
					worker,
					list(df['SMILES']),
					chunksize=500
				),
				total=df.shape[0]
			)
		)
        
    results = [r for r in results if r is not None]
    after = pd.DataFrame(results)
    after.columns = ['scaffold','smiles']
    after.to_csv('after_preprocessing.csv',index=False)