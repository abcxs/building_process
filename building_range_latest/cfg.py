'''
@Author: zfp
@Date: 2019-12-04 21:25:37
@LastEditTime : 2020-01-02 12:51:42
@FilePath: /maskrcnn-project/mytools/building_range/cfg.py
'''
site = 'guangdong'
input_dir = '/data/building/src/%s' % site
# input_dir = '/data/zfp/data/建筑物数据集/%s' % site
output_dir = '/data/building/dst/%s' % site
prefix = site
num_process = 8
seed = 1
percent = 0.8
thresh = 0.5
size = 512
overlap_size = 128
visual_tmp = True
min_box_size = 8
min_range_size = 100
padding = True
# 区分样本与背景，由于注释原因
sample_one_layer = ['jiangxi', 'qinghai', 'hainan', 'xizang', 'fujian', 'zhejiang', 'guangdong']
sample_two_layer = ['hunan', 'hubei', 'sichuan', 'guizhou']
background_one_layer = ['hainan', 'xizang', 'guangdong']
background_two_layer = ['qinghai', 'zhejiang', 'jiangxi']
