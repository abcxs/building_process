import json
import os
def json_dump(files, output_file):
    with open(output_file, 'w') as f:
        json.dump(files, f, ensure_ascii=False)

def json_load(input_file):
    with open(input_file, 'r') as f:
        files = json.load(f)
    return files

def find_item_by_id(output_dir, id):
    files = json_load(os.path.join(output_dir, 'filelist.json'))
    for k, v in files.items():
        if v['id'] == id:
            print(k)
            print(v)

def geo2cr(geoTransform, x, y):
    dTemp = geoTransform[1] * geoTransform[5] - geoTransform[2] * geoTransform[4]
    dcol = (geoTransform[5] * (x - geoTransform[0]) - geoTransform[2] * (
            y - geoTransform[3])) / dTemp + 0.5
    drow = (geoTransform[1] * (y - geoTransform[3]) - geoTransform[4] * (
            x - geoTransform[0])) / dTemp + 0.5
    return dcol, drow

def cr2geo(geoTransform, x, y):
    xp = geoTransform[0] + x * geoTransform[1] + y * geoTransform[2]
    yp = geoTransform[3] + x * geoTransform[4] + y * geoTransform[5]
    return xp, yp

if __name__ == '__main__':
    output_dir = '/data/zfp/data/building/hainan_1'
    find_item_by_id(output_dir, 126)