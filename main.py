import getopt
import json
import os
import string
import sys
from datetime import datetime
from pathlib import Path

from scipy.spatial.distance import cosine

LETTERS_LIST = list(string.ascii_uppercase)
RESULT_FOLDER_NAME = 'result'
LOG_FOLDER_NAME = 'logs'
INPUT_STAGE = 'similarity'
CURRENT_STAGE = 'diversity'
START_TIME = str(datetime.now().isoformat()).replace(":", "_").replace("/", "_")


def main(argv):
    opts, args = getopt.getopt(argv, "s:n:", ["source=", "n_trial="])
    if opts is None:
        print('Please provide source folder')
        sys.exit(2)

    source_folder = ''
    n_trial = 10
    for opt, arg in opts:
        if opt in ("-s", "--source"):
            source_folder = Path(arg)
            print(f'Source folder: {source_folder}')
        if opt in ("-n", "--n_trial"):
            n_trial = int(arg)
            print(f'Number of trials: {n_trial}')

    log_folder = create_log_folder(source_folder)
    teams = list_all_dirs(source_folder)
    for team in teams:
        team_log = f'[{str(datetime.now().isoformat())}] Processing - team: {team}'
        append_log(str(log_folder), team_log)
        team_path = Path(source_folder, team)
        characters = list_all_files(str(team_path / INPUT_STAGE))
        if characters is not None:
            characters = sorted(characters)
            for character in characters:
                character_log = f'[{str(datetime.now().isoformat())}] Processing - team: {team} - character: {character}'
                append_log(str(log_folder), character_log)
                file_path = Path(team_path / INPUT_STAGE, character)

                output = {
                    'diversityRate': 0,
                    'trials': [],
                    'diversities': []
                }

                with open(file_path) as json_file:
                    data = json.load(json_file)
                    num_trials = data['count']
                    output['count'] = num_trials
                    for i in range(num_trials):
                        similarity_logits = data['similarities'][i]['raws']
                        trial_id = data['similarities'][i]['id'].split('.')[0]
                        vectorized_logits = vectorize(similarity_logits)
                        output['trials'].append({
                            'trial': trial_id,
                            'vector': vectorized_logits
                        })

                diversity_rate = 0
                all_pairs = generate_cartesian_product(output['trials'], output['trials'])
                for pair in all_pairs:
                    distance = cosine(pair[0]['vector'], pair[1]['vector'])
                    output['diversities'].append({
                        'pair': {
                            'trial1': pair[0]['trial'],
                            'trial2': pair[1]['trial']
                        },
                        'distance': distance
                    })
                    diversity_rate += distance

                output['diversityRate'] = diversity_rate / (n_trial * (n_trial + 1) / 2 - n_trial)
                json_output = json.dumps(output, indent=2)
                output_path = create_output_folder(str(team_path / INPUT_STAGE / character.split(".")[0]),
                                                   CURRENT_STAGE, INPUT_STAGE)
                output_file_path = Path(output_path, f'{character.split(".")[0]}.json')
                with open(output_file_path, 'w') as f:
                    f.write(json_output)


def vectorize(similarity_logits: list):
    similarity_logits.sort(key=lambda x: x['label'])
    vectorized_logits = []
    for i in range(len(similarity_logits)):
        vectorized_logits.append(similarity_logits[i]['softmax_prob'])

    return vectorized_logits


def generate_cartesian_product(arr1: list, arr2: list):
    lst = []
    for i in range(len(arr1)):
        for j in range(i + 1, len(arr2)):
            lst.append((arr1[i], arr2[j]))
    return lst


def search(key, val, arr):
    return [el for el in arr if el[key] == val]


def list_all_dirs(source_folder: str):
    for (_, dirnames, _) in os.walk(source_folder):
        temp = dirnames
        out = []
        for t in temp:
            path = Path(source_folder, t)
            if os.path.isdir(path) and not t.startswith('.') and t != LOG_FOLDER_NAME and t != RESULT_FOLDER_NAME:
                out.append(t)
        return out


def list_all_files(source_folder: str):
    for (_, _, filenames) in os.walk(source_folder):
        temp = []
        for filename in filenames:
            temp.append(filename)
        return temp


def list_characters_dirs(source_folder: str, stage: str):
    path = Path(source_folder, stage)
    characters = list_all_dirs(str(path))
    return characters


def create_output_folder(path: str, output_folder_name: str, stage: str):
    if sys.platform == 'win32':
        root, team, stage_folder = "\\".join(str(path).split('\\')[0:-3]), str(path).split('\\')[-3], str(
            path).split(
            '\\')[-2:-1]
    else:
        root, team, stage_folder = "/".join(str(path).split('/')[0:-3]), str(path).split('/')[-3], str(path).split(
            '/')[
                                                                                                   -2:-1]

    output_dir = Path(root, team, output_folder_name)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    current_dir = Path(output_dir)
    for folder in stage_folder:
        if folder == stage:
            continue
        current_dir = Path(current_dir, folder)
        if not os.path.exists(current_dir):
            os.makedirs(current_dir)
    return current_dir


def create_log_folder(source_folder: str):
    output_dir = Path(source_folder, LOG_FOLDER_NAME)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return output_dir


def append_log(log_folder_path: str, log: str):
    print(log)
    log_file_path = Path(log_folder_path, f'diversity_log_{START_TIME}.txt')
    if not os.path.exists(log_file_path):
        with open(log_file_path, 'w') as f:
            f.write('')
    with open(log_file_path, 'a') as f:
        f.write(f'{log}\n')


if __name__ == '__main__':
    main(sys.argv[1:])
