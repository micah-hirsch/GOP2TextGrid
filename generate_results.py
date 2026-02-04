# GOP2TextGrid Function

# Author: Micah E. Hirsch, Ph.D. mehirsch@bu.edu

# Purpose: To convert output from tbright17's GOP algorithm to a Textgrid format readable by PRAAT.

import subprocess
import os
import re
import textgrid

def load_gop_scores(gop_file_path):
    gop_scores = {}
    # Regex to find all numbers (including negatives and decimals)
    num_pattern = re.compile(r"\[\s*(.*?)\s*\]")
    
    with open(gop_file_path, 'r') as f:
        for line in f:
            if not line.strip(): continue
            parts = line.split(maxsplit = 1)
            utt_id = parts[0]

            match = num_pattern.search(line)
            
            if match:
                # Extract the string of numbers from within the brackets
                scores_str = match.group(1)
                # Split that string by spaces to get individual numbers
                scores_list_str = scores_str.split()
                # Convert strings to floats
                scores = [float(s) for s in scores_list_str]
                gop_scores[utt_id] = scores
            else:
                print(f"Warning: No GOP scores found for utterance {utt_id}")
                gop_scores[utt_id] = []
    return gop_scores

def load_phone_map(phones_path):
    phone_map = {}
    with open(phones_path, 'r') as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2:
                phone_map[parts[1]] = parts[0]
    
    return phone_map

def GOP2Textgrid(results_dir, lang_dir, model_file):
    
    # Load GOP scores and phone mappings
    gop_scores = load_gop_scores(os.path.join(results_dir, "gop.txt"))
    phone_map = load_phone_map(os.path.join(lang_dir, "phones.txt"))

    # Getting phones and timestamps
    cmd = f"""
        source ./path.sh && 
        ali-to-phones --write-lengths=true {model_file} \
        "ark,t:{results_dir}/align.1" ark,t:- | 
        sed 's/;//g'
    """

    # Run command

    process = subprocess.Popen(cmd, shell=True, stdout = subprocess.PIPE, stderr = subprocess.PIPE, executable='/bin/bash')
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        print(f"Error running Kaldi command: {stderr.decode()}")
        return
    
    lines = stdout.decode().strip().split('\n')

    for line in lines:
        parts = line.split()
        if not parts: continue
        
        utt_id = parts[0]
        clean_list = parts[1:]
        
        # Create TextGrid
        tg = textgrid.TextGrid(name=utt_id)
        phone_tier = textgrid.IntervalTier(name = "Phones")
        gop_tier = textgrid.IntervalTier(name = "GOP_Score")
        
        current_time = 0.0
        scores = gop_scores.get(utt_id, [])
        gop_ptr = 0

        for i in range(0, len(clean_list) - 1, 2):
            phone_id = clean_list[i]
            phone_label = phone_map.get(phone_id, phone_id)
            
            duration_frames = int(clean_list[i+1])
            duration_sec = duration_frames * 0.01
            end_time = current_time + duration_sec

            # Map the GOP score
            current_score = scores[gop_ptr] if gop_ptr < len(scores) else "N/A"

            # Add the correct label and score
            phone_tier.add(current_time, end_time, phone_label)
            gop_tier.add(current_time, end_time, str(current_score))

            current_time = end_time
            gop_ptr += 1
        
        tg.append(phone_tier)
        tg.append(gop_tier)
    
        tg.write(os.path.join(results_dir, f"{utt_id}.TextGrid"))
        print(f"Successfully generated TextGrid for: {utt_id}")


if __name__ == "__main__":
    
    RES_DIR = "/mnt/c/Users/mehirsch/Documents/Test_GOP/results_dir"
    L_DIR = "data/lang"
    MOD = "exp/tri1/final.mdl"

    GOP2Textgrid(RES_DIR, L_DIR, MOD)
