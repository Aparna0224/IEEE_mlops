import os
import csv
import random
from tqdm import tqdm

DATA_FILE = "mlops/data/sections_v1.csv"

def generate_synthetic_data(num_samples=100):
    topics = [
        "deep learning", "quantum computing", "blockchain technology",
        "NLP architectures", "computer vision", "reinforcement learning",
        "cybersecurity", "edge computing", "federated learning", "5G networks"
    ]
    
    sections = ["Abstract", "Introduction", "Methodology", "Results", "Conclusion"]
        
    good_templates = [
        "This paper explores {topic} to improve efficiency. Our novel approach yields a {metric}% improvement over baselines.",
        "We introduce a robust framework for {topic}. Through extensive evaluation, we demonstrate superior performance in real-world scenarios.",
        "The proposed methodology leverages {topic} to address existing limitations. Experimental results confirm the theoretical advantages."
    ]
    
    avg_templates = [
        "In this study we looked at {topic}. It is somewhat better than previous methods.",
        "We use {topic} in our model. It works okay on the test dataset.",
        "The experiments show that {topic} can be useful sometimes. More research is needed."
    ]
    
    bad_templates = [
        "We did {topic} and it didn't really work lol.",
        "this paper is about {topic}. very cool stuff.",
        "bad results for {topic}. i don't know why."
    ]

    new_rows = []
    
    print(f"Generating {num_samples} synthetic rows for dataset augmentation...")
    for _ in tqdm(range(num_samples)):
        section = random.choice(sections)
        topic = random.choice(topics)
        metric = random.randint(10, 50)
        
        quality = random.choices(['good', 'avg', 'bad'], weights=[0.5, 0.3, 0.2])[0]
        
        if quality == 'good':
            text = random.choice(good_templates).format(topic=topic, metric=metric)
            score = round(random.uniform(0.75, 0.98), 2)
            comp, compl, clar, cit = round(random.uniform(0.8, 1.0), 2), round(random.uniform(0.8, 1.0), 2), round(random.uniform(0.8, 1.0), 2), round(random.uniform(0.8, 1.0), 2)
        elif quality == 'avg':
            text = random.choice(avg_templates).format(topic=topic, metric=metric)
            score = round(random.uniform(0.40, 0.74), 2)
            comp, compl, clar, cit = round(random.uniform(0.4, 0.7), 2), round(random.uniform(0.4, 0.7), 2), round(random.uniform(0.4, 0.7), 2), round(random.uniform(0.4, 0.7), 2)
        else:
            text = random.choice(bad_templates).format(topic=topic, metric=metric)
            score = round(random.uniform(0.10, 0.39), 2)
            comp, compl, clar, cit = round(random.uniform(0.1, 0.3), 2), round(random.uniform(0.1, 0.3), 2), round(random.uniform(0.1, 0.3), 2), round(random.uniform(0.1, 0.3), 2)
            
        new_rows.append([section, text, score, comp, compl, clar, cit])
        
    return new_rows

def main():
    if not os.path.exists(DATA_FILE):
        print(f"Error: Base dataset {DATA_FILE} not found.")
        return
        
    new_data = generate_synthetic_data(150)
    
    with open(DATA_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(new_data)
        
    print(f"Successfully appended {len(new_data)} synthetically generated rows to {DATA_FILE}")
    print("Run `python mlops/train.py` or `dvc repro` to retrain the model on the expanded dataset.")

if __name__ == "__main__":
    main()
