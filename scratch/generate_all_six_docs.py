import os
import sys

# Ensure scratch directory is in python path
sys.path.append(os.path.dirname(__file__))

from make_doc1 import generate_doc_1
from make_doc2 import generate_doc_2
from make_doc3 import generate_doc_3
from make_doc4 import generate_doc_4
from make_doc5 import generate_doc_5
from make_doc6 import generate_doc_6

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    prep_dir = os.path.join(base_dir, "docs", "team_prep")
    docs_dir = os.path.join(base_dir, "docs")
    
    os.makedirs(prep_dir, exist_ok=True)
    os.makedirs(docs_dir, exist_ok=True)
    
    docs_config = [
        ("Doc 1: Team Lead + ML & Data Engineer", "01_Team_Lead_ML_Data_Notes.docx", generate_doc_1),
        ("Doc 2: Weather & Renewable Energy Engineer", "02_Weather_Renewable_Notes.docx", generate_doc_2),
        ("Doc 3: Energy Optimization & Scheduling Engineer", "03_Optimization_Scheduling_Notes.docx", generate_doc_3),
        ("Doc 4: Backend & API Engineer", "04_Backend_API_Notes.docx", generate_doc_4),
        ("Doc 5: Frontend & UI Engineer", "05_Frontend_UI_Notes.docx", generate_doc_5),
        ("Doc 6: Testing, Validation & Documentation Engineer", "06_Testing_Validation_Documentation_Notes.docx", generate_doc_6),
    ]
    
    print("=" * 60)
    print("GENERATING ALL 6 SEPARATE POLAR GRID PREPARATION DOCS (.DOCX)")
    print("=" * 60)
    
    generated_files = []
    
    for title, filename, generator_fn in docs_config:
        path_prep = os.path.join(prep_dir, filename)
        path_docs = os.path.join(docs_dir, filename)
        print(f"\n--> Generating: {title} ...")
        generator_fn([path_prep, path_docs])
        size_prep = os.path.getsize(path_prep) / 1024.0
        size_docs = os.path.getsize(path_docs) / 1024.0
        print(f"    [OK] Saved {filename} ({size_prep:.1f} KB)")
        generated_files.append((filename, path_prep, size_prep))
        
    print("\n" + "=" * 60)
    print("ALL SIX DOCUMENTS SUCCESSFULLY GENERATED & VERIFIED:")
    print("=" * 60)
    for fn, p, sz in generated_files:
        print(f"  * {fn:<50} : {sz:.1f} KB")
    print("=" * 60)

if __name__ == "__main__":
    main()
