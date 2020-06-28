import os
from walk import walk
from shp2txt import multiShp2txt
from txt2coco import multi_divide
import shutil
import cfg
from visual_tmp import visual
from utils import json_load

def show_example(output_dir):
    data = json_load(os.path.join(output_dir, 'filelist.json'))
    for k, v in data.items():
        print(k)
        print(v)
        break

if __name__ == '__main__':
    # prefix shouble be changed with data being changed
    dst1 = ['train', 'val']
    dst2 = ['JPEGImages', 'visual']

    input_dir = cfg.input_dir
    output_dir = cfg.output_dir
    if os.path.exists(os.path.join(output_dir, 'tmp')):
        shutil.rmtree(os.path.join(output_dir, 'tmp'))
    os.makedirs(os.path.join(output_dir, 'tmp'))

    for d1 in dst1:
        for d2 in dst2:
            if os.path.exists(os.path.join(output_dir, d1, d2)):
                shutil.rmtree(os.path.join(output_dir, d1, d2))
            os.makedirs(os.path.join(output_dir, d1, d2))

    print('begin walk')
    walk(cfg)
    show_example(output_dir)
    
    print('begin shp2txt')
    multiShp2txt(cfg)
    show_example(output_dir)

    if cfg.visual_tmp:
        print('visual tmp')
        visual(cfg)

    print('begin divide')
    multi_divide(cfg)