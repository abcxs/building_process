
import json
import os
import random

from utils import json_dump


def walk_data_root(input_dir, background=False):
    files = {}
    result = walk_and_check(input_dir, background)
    if result is not None:
        files[input_dir] = result
    return files

def walk_data_one_layer(input_dir, background=False):
    files = {}
    l1s = os.listdir(input_dir)
    for l1 in l1s:
        if not os.path.isdir(os.path.join(input_dir, l1)):
            continue
        result = walk_and_check(os.path.join(input_dir, l1), background)
        if result is not None:
            files[os.path.join(input_dir, l1)] = result
    return files

def walk_data_two_layer(input_dir, background=False):
    files = {}
    l1s = os.listdir(input_dir)
    for l1 in l1s:
        if not os.path.isdir(os.path.join(input_dir, l1)):
            continue
        l2s = os.listdir(os.path.join(input_dir, l1))
        for l2 in l2s:
            if not os.path.isdir(os.path.join(input_dir, l1, l2)):
                continue
            result = walk_and_check(os.path.join(input_dir, l1, l2), background)
            if result is not None:
                files[os.path.join(input_dir, l1, l2)] = result
    return files

def walk(cfg):
    input_dir = cfg.input_dir
    output_dir = cfg.output_dir
    sample_one_layer = cfg.sample_one_layer
    sample_two_layer = cfg.sample_two_layer
    background_one_layer = cfg.background_one_layer
    background_two_layer = cfg.background_two_layer
    site = cfg.site
    seed = cfg.seed
    percent = cfg.percent
    random.seed(seed)
    files = {}

    assert site in sample_one_layer or site in sample_two_layer

    l1s = os.listdir(input_dir)
    for l1 in l1s:
        if not os.path.isdir(os.path.join(input_dir, l1)):
            continue
        if 'background' == l1:
            if site in background_one_layer:
                walk_background = walk_data_one_layer
            elif site in background_two_layer:
                walk_background = walk_data_two_layer
            else:
                walk_background = walk_data_root
            result_files = walk_background(os.path.join(input_dir, l1), background=True)
            for result_file in result_files.values():
                result_file['background'] = True
            files.update(result_files)
        else:
            if site in sample_one_layer:
                walk_data = walk_data_one_layer
            else:
                walk_data = walk_data_two_layer
            result_files = walk_data(os.path.join(input_dir, l1))
            for result_file in result_files.values():
                result_file['background'] = False
            files.update(result_files)
    files = dict(sorted(files.items()))
    for i, file in enumerate(files.values()):
        file['id'] = i
    
    ids = [file['id'] for file in files.values() if not file['background']]
    num_train = int(len(ids) * percent)
    train_id = random.sample(ids, num_train)
    val_id = [item for item in ids if item not in train_id]

    for file in files.values():
        if file['id'] in val_id:
            file['split'] = 'val'
        else:
            file['split'] = 'train'
    json_dump(files, os.path.join(output_dir, 'filelist.json'))
    
def check_range(path):
    # 文件夹名称或文件名称是否存在key值
    keys = ['范围', '边界']
    for key in keys:
        if os.path.dirname(path).split('/')[-1].find(key) != -1 or os.path.basename(path).find(key) != -1:
            return True
    return False

def walk_and_check(path, background=False):
    result_file = {}
    
    result_file['tif'] = []
    result_file['shp'] = []
    result_file['fw'] = []

    for root, _, files in os.walk(path):
        for item in files:
            if item.endswith('.tif'):
                result_file['tif'].append(os.path.join(root, item))
            elif item.endswith('.shp'):
                if check_range(os.path.join(root, item)):
                    result_file['fw'].append(os.path.join(root, item))
                    continue
                result_file['shp'].append(os.path.join(root, item))
    
    if (len(result_file['tif']) > 0 and len(result_file['shp']) > 0 and len(result_file['fw']) <= 1) or (background and len(result_file['tif']) > 0):
        print('background:', background, 'tif:', len(result_file['tif']), 'shp:', len(result_file['shp']), 'fw:', len(result_file['fw']), 'file:', path)
        return result_file  
    else:
        print('skip %s, it have %d tif, %d shp, %d fw' % (path, len(result_file['tif']), len(result_file['shp']), len(result_file['fw'])))

if __name__ == '__main__':
    import cfg
    walk(cfg)
