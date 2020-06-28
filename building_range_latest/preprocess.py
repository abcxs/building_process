import os
import glob
import ogr
import gdal
import osr
import json
import shutil
import numpy as np
import cv2
import multiprocessing
import random
from utils import json_load, json_dump, geo2cr, cr2geo
import math

ogr.RegisterAll()
gdal.SetConfigOption('SHAPE_ENCODING', "UTF-8")
gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")


def select_by_ids(files, ids=[]):
    if len(ids) == 0:
        return files
    files_ = {}
    for k, v in files.items():
        if v['id'] in ids:
            files_[k] = v
    return files_

def preprocess(cfg):
    output_dir = cfg.output_dir
    num_process = cfg.num_process
    global min_range_size
    global min_box_size
    min_box_size = cfg.min_box_size
    min_range_size = cfg.min_range_size
    files = json_load(os.path.join(output_dir, 'filelist.json'))

    # debug
    ids = []
    files = select_by_ids(files, ids)
    
    if num_process == 0 or num_process == 1:
        # for debug
        convert_results = {}
        process(0, files, os.path.join(output_dir, 'tmp'), convert_results)
    else:
        keys = list(files.keys())
        
        manager = multiprocessing.Manager()
        convert_results = manager.dict()
        processes = []
        
        for i in range(num_process):
            process_files = {}
            for key in keys[i::num_process]:
                process_files[key] = files[key]
        
            p = multiprocessing.Process(target=process, args=(i, process_files, os.path.join(output_dir, 'tmp'), convert_results))
            p.start()
            processes.append(p)
        for p in processes:
            p.join()

    for k, v in convert_results.items():
        files[k].update(v)
    json_dump(files, os.path.join(output_dir, 'filelist.json'))


def process(process_id, files, output_dir, convert_results):
    
    for k, v in files.items():
        id_ = v['id']
        tif_files = v['tif']
        shp_files = v['shp']
        fw_files = v['fw']
        split = v['split']
        background = v['background']
        
        print('process:', process_id, 'id:', id_, 'split:', split, 'path:', k)
        
        if len(fw_files) == 0:
            fw_files = [None]
        assert len(fw_files) == 1
        # shp文件仅仅存在背景的轮廓
        if background:
            shp_files = [None]
        else:
            assert len(shp_files) > 0

        #TODO: maybe can delete it
        assert len(fw_files) == 1
        convert_files = []
        cur_id = 0

        for tif_file in tif_files:
            for fw_file in fw_files:
                infos, cur_id = crop(tif_file, fw_file, output_dir, id_, cur_id)
                if infos is None or len(infos) == 0:
                    continue
                for shp_file in shp_files:
                    handle(infos, shp_file, output_dir, id_, convert_files)
        convert_results[k] = {'convert': convert_files}

def crop(tif_file, fw_file, output_dir, file_id, cur_id):
    
    infos = []

    dataset = gdal.Open(tif_file)
    width = dataset.RasterXSize
    height = dataset.RasterYSize
    assert dataset.RasterCount == 3, '假定通道数为3'

    srcArray = dataset.ReadAsArray()
    if srcArray is None:
        print('read array error', tif_file, 'file_id:', file_id, 'cur_id:', cur_id)
        return None, cur_id
    
    geoTransform = dataset.GetGeoTransform()
    if geoTransform is None:
        print('read geoTransfrom error', tif_file, 'file_id:', file_id, 'cur_id:', cur_id)
        return None, cur_id
    
    srcArray = srcArray.astype(np.uint8).transpose(1, 2, 0)[:, :, ::-1]
    height, width, _ = srcArray.shape

    if fw_file is None:
        infos.append({'geo': geoTransform, 'cur_id': cur_id, 'points': None, 'wh': [width, height], 'range': None})
        cv2.imwrite(os.path.join(output_dir, '%d_%d.png' % (file_id, cur_id)), srcArray)
        cur_id += 1
        return infos, cur_id

    dataSource = ogr.Open(fw_file)
    daLayer = dataSource.GetLayer(0)
    featureCount = daLayer.GetFeatureCount()

    daLayer.ResetReading()
    for _ in range(featureCount):
        feature = daLayer.GetNextFeature()
        geometry = feature.GetGeometryRef()
        if geometry is None:
            continue
        ring = geometry.GetGeometryRef(0)
        numPoints = ring.GetPointCount()

        # 起始点2次
        if numPoints < 4:
            continue

        points = []
        max_y = 0
        max_x = 0
        min_y = height - 1
        min_x = width - 1

        for i in range(numPoints - 1):
            x, y = geo2cr(geoTransform, ring.GetX(i), ring.GetY(i))
            
            x = max(min(x, width - 1), 0)
            y = max(min(y, height - 1), 0)

            max_x = max(max_x, x)
            max_y = max(max_y, y)
            min_x = min(min_x, x)
            min_y = min(min_y, y)

            points.append([x, y])

        if not (max_x - min_x >= min_range_size and max_y - min_y >= min_range_size):
            print(fw_file, 'range is so small, just skip')
            continue

        xp_start, yp_start = cr2geo(geoTransform, min_x, min_y)
        xp_end, yp_end = cr2geo(geoTransform, max_x, max_y)
        geo = [xp_start, geoTransform[1], geoTransform[2], yp_start, geoTransform[4], geoTransform[5]]

        # 范围轮廓坐标更替
        points = np.array(points)
        points = points - np.array([min_x, min_y])

        min_x = int(min_x)
        min_y = int(min_y)
        max_x = int(max_x)
        max_y = int(max_y)

        w = max_x - min_x
        h = max_y - min_y

        mask = np.zeros((h, w, 3), dtype=np.uint8)
        cv2.fillPoly(mask, [points.reshape(-1, 1, 2).astype(np.int)], (255, 255, 255))

        img = srcArray[min_y: max_y, min_x: max_x]

        mask = cv2.bitwise_and(mask, img)
        cv2.imwrite(os.path.join(output_dir, '%d_%d.png' % (file_id, cur_id)), mask)

        info = {'points': points, 'geo': geo, 'cur_id': cur_id, 'wh': [w, h], 'range':[xp_start, -yp_start, xp_end, -yp_end]}
        infos.append(info)
        cur_id += 1
    return infos, cur_id

def area_of_boxes(box1, box2):
    '''
    :param box1: target box, [N, 4]
    :param box2: predict box, [M, 4]
    :return:
        area  [N, M]
    '''
    lt = np.maximum(box1[:, None, :2], box2[:, :2])
    rb = np.minimum(box1[:, None, 2:], box2[:, 2:])
    wh = np.clip((rb - lt), a_min=0, a_max=None)
    inter_area = wh[:, :, 0] * wh[:, :, 1]

    return inter_area

def check_mask_tif(tif_files):
    if len(tif_files) == 1:
        return [False]
    boxes = []
    for tif_file in tif_files:
        dataset = gdal.Open(tif_file)
        geoTransform = dataset.GetGeoTransform()
        width = dataset.RasterXSize
        height = dataset.RasterYSize
        xp_start, yp_start = cr2geo(geoTransform, 0, 0)
        xp_end, yp_end = cr2geo(geoTransform, width, height)
        boxes.append([xp_start, -yp_start, xp_end, -yp_end])
    boxes = np.array(boxes)
    inter_area = area_of_boxes(boxes, boxes)
    for i in range(boxes.shape[0]):
        inter_area[i, i] = 0
    mask = np.any(inter_area, axis=0)
    need_mask = mask.tolist()
    return need_mask

def check_mask(infos):
    if len(infos) == 1 and infos[0]['range'] is None:
        need_mask = [False]
    else:
        boxes = []
        for info in infos:
            boxes.append(info['range'])
        boxes = np.array(boxes)
        inter_area = area_of_boxes(boxes, boxes)
        for i in range(boxes.shape[0]):
            inter_area[i, i] = 0
        mask = np.any(inter_area, axis=0)
        need_mask = mask.tolist()
    return need_mask

def handle(infos, shp_file, output_dir, file_id, convert_files):
    # use for background
    if shp_file is None:
        for info in infos:
            cur_id = info['cur_id']
            img_path = os.path.join(output_dir, '%d_%d.png' % (file_id, cur_id))
            txt_path = os.path.join(output_dir, '%d_%d.txt' % (file_id, cur_id))
            with open(txt_path, 'w') as f:
                f.write('') 
            convert_files.append({'img_path': img_path, 'txt_path': txt_path})
        return      
    
    dataSource = ogr.Open(shp_file)
    daLayer = dataSource.GetLayer(0)
    featureCount = daLayer.GetFeatureCount()

    need_mask = check_mask(infos)

    for info, mask_per_tile in zip(infos, need_mask):
        geoTransform = info['geo']
        points = info['points']
        width, height = info['wh']
        cur_id = info['cur_id']
        if mask_per_tile:
            mask_content = np.zeros((height, width), dtype=np.uint8)
            cv2.fillPoly(mask_content, [points.reshape(-1, 1, 2).astype(np.int)], 1)

        msgs = []
        daLayer.ResetReading()
        for i in range(featureCount):
            feature = daLayer.GetNextFeature()
            geometry = feature.GetGeometryRef()
            if geometry is None:
                continue
            ring = geometry.GetGeometryRef(0)
            numPoints = ring.GetPointCount()

            if numPoints < 4:
                continue

            msg = []
            points = []

            max_y = 0
            max_x = 0
            min_y = height - 1
            min_x = width - 1

            for j in range(numPoints - 1):
                x, y = geo2cr(geoTransform, ring.GetX(j), ring.GetY(j))
                x = max(min(x, width - 1), 0)
                y = max(min(y, height - 1), 0)
                msg.append('%f' % x)
                msg.append('%f' % y)
                points.append([x, y])

                max_x = max(max_x, x)
                max_y = max(max_y, y)
                min_x = min(min_x, x)
                min_y = min(min_y, y)

            w = max_x - min_x + 1
            h = max_y - min_y + 1
            if msg and w >= min_box_size and h >= min_box_size:
                if mask_per_tile:
                    content = np.zeros((height, width), dtype=np.uint8)
                    points = np.array(points, dtype=np.int).reshape(-1, 1, 2)
                    cv2.fillPoly(content, [points], 1)
                    mask = cv2.bitwise_and(mask_content, content)
                    if mask.any():
                        msgs.append(' '.join(msg))
                else:
                    msgs.append(' '.join(msg))
        img_path = os.path.join(output_dir, '%d_%d.png' % (file_id, cur_id))
        txt_path = os.path.join(output_dir, '%d_%d.txt' % (file_id, cur_id))
        if len(msgs) > 0:
            #TODO: exist problems
            exist_msgs = 0
            if os.path.exists(txt_path):
                #TODO: logging
                print('warning: overwrite')
                exist_msgs = len(open(txt_path).read().split('\n'))
            if len(msgs) > exist_msgs:
                with open(txt_path, 'w') as f:
                    f.write('\n'.join(msgs))
            if exist_msgs == 0:  
                convert_files.append({'img_path': img_path, 'txt_path': txt_path}) 

if __name__ == '__main__':
    import cfg
    preprocess(cfg)